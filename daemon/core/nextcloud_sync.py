from __future__ import annotations

import asyncio
import logging
import time

import pyfuse3

from ..cloud_api.nextcloud import NextcloudAsyncClient
from ..database.importer import import_cloud_to_db
from ..database.manager import DBManager

log = logging.getLogger(__name__)

CONFIG_ROOT_REVISION = "nextcloud_root_folder_revision"
_DEBOUNCE_SEC = 1.5

_last_sync_monotonic: dict[str, float] = {}
_sync_locks: dict[str, asyncio.Lock] = {}


def _parent_key(parent_db_id: int | None) -> str:
    return str(parent_db_id) if parent_db_id is not None else "__root__"


def _sync_lock(key: str) -> asyncio.Lock:
    if key not in _sync_locks:
        _sync_locks[key] = asyncio.Lock()
    return _sync_locks[key]


def _fp_api(children_nodes: list) -> tuple:
    return tuple(
        sorted(
            (
                node.name,
                "dir" if node.is_dir else "file",
                node.info.size if not node.is_dir else 0
            )
            for node in children_nodes
        )
    )


def _fp_db(rows: list[dict]) -> tuple:
    return tuple(
        sorted(
            (
                r["name"],
                "dir" if r["is_dir"] else "file",
                r.get("size") or 0
            )
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


async def sync_nextcloud_folder_if_stale(
        db: DBManager,
        cloud_api: NextcloudAsyncClient,
        parent_db_id: int | None,
        *,
        force: bool = False,
) -> bool:
    if parent_db_id is not None:
        row = await db.get_file_by_id(parent_db_id)
        if not row or not row["is_dir"]:
            return False

        clean_path = row["remote_path"].replace("nextcloud:", "")
        if not clean_path:
            clean_path = "/"

        stored_rev = (row.get("etag") or "") if row else ""
    else:
        clean_path = "/"
        stored_rev = (await db.get_config(CONFIG_ROOT_REVISION)) or ""

    try:
        meta = await cloud_api.nc.files.by_path(clean_path)
    except Exception as e:
        log.warning("[nc_sync] get_meta(%s): %s", clean_path, e)
        return False

    cloud_rev = str(meta.etag) if meta.etag else ""

    if not force and cloud_rev and cloud_rev == stored_rev:
        return False

    try:
        children_nodes = await cloud_api.nc.files.listdir(clean_path)
    except Exception as e:
        log.warning("[nc_sync] listdir(%s): %s", clean_path, e)
        return False

    if not force and not cloud_rev:
        db_rows = await db.get_readdir_entries(parent_db_id)
        if _fp_api(children_nodes) == _fp_db(db_rows):
            return False

    api_paths = {f"nextcloud:{c.user_path}" for c in children_nodes}

    db_children = await db.get_items_by_parent(parent_db_id)
    for row in db_children:
        if row["remote_path"] not in api_paths:
            await db.delete_subtree(row["id"])

    for node in children_nodes:
        file_data = {
            "parent_id": parent_db_id,
            "name": node.name,
            "is_dir": 1 if node.is_dir else 0,
            "size": node.info.size if not node.is_dir else 0,
            "cloud_type": "nextcloud",
            "remote_path": f"nextcloud:{node.user_path}",
            "etag": node.etag
        }

        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute('''
                               INSERT INTO files (parent_id, name, is_dir, size, cloud_type, remote_path, etag)
                               VALUES (:parent_id, :name, :is_dir, :size, :cloud_type, :remote_path,
                                       :etag) ON CONFLICT(cloud_type, remote_path) DO
                               UPDATE SET
                                   parent_id = excluded.parent_id,
                                   name = excluded.name,
                                   size = excluded.size,
                                   etag = excluded.etag
                               ''', file_data)
            await conn.commit()

    if parent_db_id is None:
        await db.set_config(CONFIG_ROOT_REVISION, cloud_rev)
    else:
        # Прямой апдейт ETag
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("UPDATE files SET etag = ? WHERE id = ?", (cloud_rev, parent_db_id))
            await conn.commit()

    log.info(
        "[nc_sync] папка %s обновлена (revision %s → %s, детей=%s)",
        clean_path,
        stored_rev or "—",
        cloud_rev or "—",
        len(children_nodes),
    )
    return True


async def folder_sync_after_readdir(
        db: DBManager,
        cloud_api: NextcloudAsyncClient,
        dir_inode: int,
        parent_db_id: int | None,
) -> None:
    if not _debounce_ok(parent_db_id):
        return
    key = _parent_key(parent_db_id)
    async with _sync_lock(key):
        try:
            changed = await sync_nextcloud_folder_if_stale(
                db, cloud_api, parent_db_id, force=False
            )
        except Exception:
            log.exception("[nc_sync] JIT синхронизация parent_id=%s", parent_db_id)
            return

    if not changed:
        return

    try:
        await asyncio.to_thread(pyfuse3.invalidate_inode, dir_inode, False)
    except Exception as e:
        log.warning("[nc_sync] invalidate_inode(%s): %s", dir_inode, e)


async def nextcloud_sync_loop(
        db: DBManager,
        cloud_api: NextcloudAsyncClient,
) -> None:
    log.info("[nc_sync] Фоновый поллер Nextcloud запущен.")

    while True:
        try:
            root_node = await cloud_api.nc.files.by_path("/")
            cloud_rev = str(root_node.etag)
            stored_rev = (await db.get_config(CONFIG_ROOT_REVISION)) or ""

            if cloud_rev != stored_rev:
                log.info("[nc_sync] Изменился ETag корня (%s -> %s). Запуск полного сканирования...", stored_rev,
                         cloud_rev)

                cloud_files = await cloud_api.get_all_files_flat()
                if cloud_files:
                    await import_cloud_to_db(db, cloud_files, "nextcloud")
                    await db.set_config(CONFIG_ROOT_REVISION, cloud_rev)
                    log.info("[nc_sync] Полное обновление дерева Nextcloud завершено.")

        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("[nc_sync] Ошибка в цикле поллинга Nextcloud")

        raw = await db.get_config("sync_poll_interval_minutes")
        try:
            minutes = float(raw) if raw is not None else 1.0
        except (TypeError, ValueError):
            minutes = 5.0

        minutes = max(0.5, minutes)
        await asyncio.sleep(minutes * 60.0)