import logging
import os

from fastapi import APIRouter, Body, HTTPException, Query
from ..schemas import FileItem, PathSegment, PinBody, PinResponse, SearchResult, SyncResponse
from ...cloud_api.nextcloud import NextcloudAsyncClient
from ...cloud_api.yandex import YandexDiskAsyncClient
from ...config import settings
from ...database.manager import DBManager

log = logging.getLogger("cloudfusion")


def _fuse_local_to_cloud_remote(local_abs: str, mount_abs: str) -> tuple[str, str]:
    """
    Путь в смонтированном FUSE → (cloud_type, remote_path как в SQLite).

    Первый сегмент пути относительно точки монтирования — имя корневой папки
    («YandexDisk» / «Nextcloud» из ensure_*), а не строка cloud_type.
    """
    rel = os.path.relpath(local_abs, mount_abs)
    if rel in (".", os.curdir):
        raise ValueError("path is the mount root")
    parts = rel.split(os.sep)
    root_name = parts[0]
    tail = parts[1:] if len(parts) > 1 else []
    tail_s = "/".join(tail)

    key = root_name.lower()
    if key in ("yandexdisk", "yandex"):
        remote = f"disk:/{tail_s}" if tail_s else "disk:/"
        return "yandex", remote
    if key == "nextcloud":
        remote = f"nextcloud:/{tail_s}" if tail_s else "nextcloud:/"
        return "nextcloud", remote
    raise ValueError(f"unknown top-level folder under mount: {root_name!r}")

def make_router(db: DBManager) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["files"])
    @router.get("/search", response_model=list[SearchResult])
    async def api_search(q: str = Query(..., min_length=1)):
        return await db.search_files(q)

    @router.get("/files/list", response_model=list[FileItem])
    async def api_list(parent_id: int | None = None):
        return await db.get_items_by_parent(parent_id)

    @router.get("/files/{file_id}", response_model=FileItem)
    async def api_file(file_id: int):
        file = await db.get_file_by_id(file_id)
        if file is None:
            raise HTTPException(status_code=404, detail="File not found")
        return file

    @router.get("/files/{file_id}/path", response_model=list[PathSegment])
    async def api_file_path(file_id: int):
        file = await db.get_file_by_id(file_id)
        if file is None:
            raise HTTPException(status_code=404, detail="File not found")
        return await db.get_ancestors(file_id)

    @router.post("/files/{file_id}/pin", response_model=PinResponse)
    async def api_pin(file_id: int, body: PinBody):
        """Тело JSON: {\"pinned\": true|false} — иначе FastAPI ждал бы query-параметр."""
        file = await db.get_file_by_id(file_id)
        if file is None:
            raise HTTPException(status_code=404, detail="File not found")
        await db.toggle_pin(file_id, body.pinned)
        return {"status": "ok"}

    @router.post("/files/{file_id}/drop_local_cache", response_model=PinResponse)
    async def api_drop_local_cache(file_id: int):
        """Убрать локальную копию (cached или частичный stub), строка в БД → stub без local_path."""
        file = await db.get_file_by_id(file_id)
        if file is None:
            raise HTTPException(status_code=404, detail="File not found")
        if file.get("is_dir"):
            raise HTTPException(status_code=400, detail="cannot drop cache for a directory")
        if file.get("is_pinned"):
            raise HTTPException(status_code=409, detail="file is pinned")
        ok = await db.drop_local_cache_file(file_id)
        if not ok:
            raise HTTPException(status_code=404, detail="File not found")
        return {"status": "ok"}

    @router.post("/files/{file_id}/sync", response_model=SyncResponse)
    async def api_sync(file_id: int):
        file = await db.get_file_by_id(file_id)
        if file is None:
            raise HTTPException(status_code=404, detail="File not found")
        if file["is_dir"]:
            raise HTTPException(status_code=400, detail="Cannot sync a directory")
        await db.set_file_status(file_id, "syncing")
        log.info("File %d marked for sync", file_id)
        return {"status": "syncing"}

    @router.post("/files/publish")
    async def publish_file(data: dict = Body(...)):
        """Публичная ссылка по локальному пути внутри FUSE (Dolphin Service Menu)."""
        local_path = data.get("local_path")
        if not local_path:
            raise HTTPException(status_code=400, detail="local_path is required")

        mount_abs = os.path.realpath(os.path.expanduser(settings.mountpoint))
        try:
            local_abs = os.path.realpath(os.path.expanduser(local_path))
        except OSError as e:
            raise HTTPException(status_code=400, detail=f"invalid path: {e}") from e

        try:
            cloud_type, remote_path = _fuse_local_to_cloud_remote(local_abs, mount_abs)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        row = await db.get_file_by_remote_path(remote_path, cloud_type)
        if row is None:
            raise HTTPException(status_code=404, detail="file not in index (sync FUSE first)")
        if row.get("is_dir"):
            raise HTTPException(status_code=400, detail="cannot publish a directory")

        try:
            if cloud_type == "yandex":
                token = await db.get_config("yandex_token")
                if not token:
                    raise HTTPException(status_code=503, detail="Yandex is not connected")
                client = YandexDiskAsyncClient(token=token)
                public_url = await client.publish(remote_path)
            elif cloud_type == "nextcloud":
                nc_host = await db.get_config("nc_host")
                nc_login = await db.get_config("nc_login")
                nc_password = await db.get_config("nc_password")
                if not (nc_host and nc_login and nc_password):
                    raise HTTPException(status_code=503, detail="Nextcloud is not connected")
                client = NextcloudAsyncClient(nc_host, nc_login, nc_password)
                public_url = await client.publish(remote_path)
            else:
                raise HTTPException(status_code=500, detail="unsupported cloud_type")

            return {"status": "ok", "url": public_url}
        except HTTPException:
            raise
        except Exception as e:
            log.exception("publish failed for %s", remote_path)
            raise HTTPException(status_code=502, detail=str(e)) from e

    return router
