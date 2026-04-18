from __future__ import annotations

import asyncio
import logging
import time

import pyfuse3

from ..cloud_api.yandex import YandexDiskAsyncClient
from ..database.importer import import_cloud_to_db
from ..database.manager import DBManager

log = logging.getLogger(__name__)

CONFIG_ROOT_REVISION = "yandex_disk_root_folder_revision"
_DEBOUNCE_SEC = 1.5

_last_sync_monotonic: dict[str, float] = {}
_sync_locks: dict[str, asyncio.Lock] = {}


def _parent_key(parent_db_id: int | None) -> str:
    return str(parent_db_id) if parent_db_id is not None else "__root__"


def _sync_lock(key: str) -> asyncio.Lock:
    if key not in _sync_locks:
        _sync_locks[key] = asyncio.Lock()
    return _sync_locks[key]


def _revision_str(meta) -> str:
    r = getattr(meta, "revision", None)
    if r is None:
        return ""
    return str(r)


def _fp_api(children: list[dict]) -> tuple:
    return tuple(sorted((c["name"], c["type"], c.get("size") or 0) for c in children))


def _fp_db(rows: list[dict]) -> tuple:
    return tuple(
        sorted(
            (r["name"], "dir" if r["is_dir"] else "file", r.get("size") or 0)
            for r in rows
        )
    )


def _debounce_ok(parent_db_id: int | None) -> bool:
    key = _parent_key(parent_db_id)
    now = time.monotonic()
    if now - _last_sync_monotonic.get(key, 0) < _DEBOUNCE_SEC:
        return False
    _last_sync_monotonic[key] = now
    return True


async def sync_yandex_folder_if_stale(
    db: DBManager,
    cloud_api: YandexDiskAsyncClient,
    parent_db_id: int | None,
    *,
    force: bool = False,
) -> bool:
    if parent_db_id is not None:
        row = await db.get_file_by_id(parent_db_id)
        if not row or not row["is_dir"]:
            return False
        remote_path = row["remote_path"]
        stored_rev = (row.get("etag") or "") if row else ""
    else:
        remote_path = "disk:/"
        stored_rev = (await db.get_config(CONFIG_ROOT_REVISION)) or ""

    try:
        meta = await cloud_api.get_meta(remote_path)
    except Exception as e:
        log.warning("[sync] get_meta(%s): %s", remote_path, e)
        return False

    cloud_rev = _revision_str(meta)

    if not force and cloud_rev and cloud_rev == stored_rev:
        return False

    try:
        children = await cloud_api.listdir_metadata(remote_path)
    except Exception as e:
        log.warning("[sync] listdir(%s): %s", remote_path, e)
        return False

    if not force and not cloud_rev:
        db_rows = await db.get_readdir_entries(parent_db_id)
        if _fp_api(children) == _fp_db(db_rows):
            return False

    api_paths = {c["path"] for c in children}
    db_children = await db.get_direct_children_yandex(parent_db_id)
    for row in db_children:
        if row["remote_path"] not in api_paths:
            await db.delete_subtree(row["id"])

    for c in children:
        await db.upsert_yandex_direct_child(parent_db_id, c)

    if parent_db_id is None:
        await db.set_config(CONFIG_ROOT_REVISION, cloud_rev)
    else:
        await db.update_file_etag(parent_db_id, cloud_rev)

    log.info(
        "[sync] папка %s обновлена (revision %s → %s, детей=%s)",
        remote_path,
        stored_rev or "—",
        cloud_rev or "—",
        len(children),
    )
    return True


def resource_to_import_chain(res) -> list[dict]:
    path = res.path
    norm = path.replace("disk:", "").strip("/")
    parts = norm.split("/") if norm else []
    if not parts:
        return []

    out: list[dict] = []
    acc: list[str] = []
    for i in range(len(parts) - 1):
        acc.append(parts[i])
        rp = "disk:/" + "/".join(acc)
        out.append(
            {
                "path": rp,
                "type": "dir",
                "name": parts[i],
                "size": 0,
                "revision": None,
            }
        )

    t = getattr(res, "type", None)
    is_dir = t == "dir" or (getattr(t, "value", None) == "dir")
    out.append(
        {
            "path": path,
            "type": "dir" if is_dir else "file",
            "name": parts[-1],
            "size": getattr(res, "size", None) or 0,
            "revision": getattr(res, "revision", None),
        }
    )
    return out


async def merge_last_uploaded(db: DBManager, cloud_api: YandexDiskAsyncClient, limit: int = 50) -> int:
    try:
        items = await cloud_api.get_last_uploaded_resources(limit=limit)
    except Exception as e:
        log.warning("[sync] get_last_uploaded: %s", e)
        return 0

    n = 0
    for res in items:
        chain = resource_to_import_chain(res)
        if not chain:
            continue
        try:
            wid = await db.get_yandex_disk_wrapper_id()
            if wid is None:
                wid = await db.ensure_yandex_disk_root_folder()
            await import_cloud_to_db(db, chain, "yandex", path_to_id_seed={"": wid})
            n += 1
        except Exception:
            log.exception("[sync] merge last-uploaded path=%s", getattr(res, "path", res))
    return n


async def folder_sync_after_readdir(
    db: DBManager,
    cloud_api: YandexDiskAsyncClient,
    dir_inode: int,
    parent_db_id: int | None,
) -> None:
    if parent_db_id is None:
        return
    if not _debounce_ok(parent_db_id):
        return
    key = _parent_key(parent_db_id)
    async with _sync_lock(key):
        try:
            changed = await sync_yandex_folder_if_stale(
                db, cloud_api, parent_db_id, force=False
            )
        except Exception:
            log.exception("[sync] фоновая синхронизация parent_id=%s", parent_db_id)
            return

    if not changed:
        return

    try:
        await asyncio.to_thread(pyfuse3.invalidate_inode, dir_inode, False)
    except OSError as e:
        log.warning("[sync] invalidate_inode(%s): %s", dir_inode, e)
    except Exception as e:
        log.warning("[sync] invalidate_inode(%s): %s", dir_inode, e)


async def merge_last_uploaded_loop(
    db: DBManager,
    cloud_api: YandexDiskAsyncClient,
) -> None:
    while True:
        try:
            merged = await merge_last_uploaded(db, cloud_api)
            if merged:
                log.info("[sync] last-uploaded: импортировано цепочек=%s", merged)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("[sync] цикл last-uploaded")

        raw = await db.get_config("sync_poll_interval_minutes")
        try:
            minutes = float(raw) if raw is not None else 1.0
        except (TypeError, ValueError):
            minutes = 5.0
        minutes = max(0.5, minutes)
        await asyncio.sleep(minutes * 60.0)