import logging
import os

from fastapi import APIRouter, HTTPException, Query

from ..schemas import FileItem, PathSegment, PinResponse, SearchResult, SyncResponse
from ...database.manager import DBManager
from ...config import settings

log = logging.getLogger("cloudfusion")

def make_router(db: DBManager) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["files"])

    @router.get("/search", response_model=list[SearchResult])
    async def api_search(q: str = Query(..., min_length=1)):
        return await db.search_files(q)

    @router.get("/files/list", response_model=list[FileItem])
    async def api_list(parent_id: int | None = None):
        return await db.get_items_by_parent(parent_id)

    @router.get("/files/by-path", response_model=FileItem)
    async def api_file_by_path(
        cloud_type: str = Query(...),
        remote_path: str = Query(...),
    ):
        file = await db.get_file_by_remote_path(cloud_type, remote_path)
        if file is None:
            raise HTTPException(status_code=404, detail="File not found")
        return file

    @router.get("/files/locate", response_model=FileItem)
    async def api_locate(path: str = Query(..., description="Absolute FUSE path")):
        """Resolve a file by its absolute FUSE path by walking the DB tree."""
        mountpoint = os.path.expanduser(settings.mountpoint)
        real_path = os.path.realpath(path)
        real_mount = os.path.realpath(mountpoint)
        if not real_path.startswith(real_mount + os.sep) and real_path != real_mount:
            raise HTTPException(status_code=400, detail="Path is not inside the CloudFusion mountpoint")
        relative = real_path[len(real_mount):].lstrip(os.sep)
        if not relative:
            raise HTTPException(status_code=400, detail="Cannot locate the mount root itself")
        components = relative.replace("\\", "/").split("/")
        file = await db.locate_by_path_components(components)
        if file is None:
            raise HTTPException(status_code=404, detail="File not found")
        return file

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
    async def api_pin(file_id: int, pinned: bool):
        await db.toggle_pin(file_id, pinned)
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

    @router.post("/files/{file_id}/evict", response_model=SyncResponse)
    async def api_evict(file_id: int):
        """Delete the local cache copy; file reverts to stub (cloud-only)."""
        file = await db.get_file_by_id(file_id)
        if file is None:
            raise HTTPException(status_code=404, detail="File not found")
        if file["is_dir"]:
            raise HTTPException(status_code=400, detail="Cannot evict a directory")
        evicted = await db.evict_file(file_id)
        log.info("File %d evicted from cache (was_cached=%s)", file_id, evicted)
        return {"status": "stub"}

    @router.post("/files/{file_id}/cache", response_model=SyncResponse)
    async def api_cache(file_id: int):
        """Download the file from cloud into the local cache."""
        file = await db.get_file_by_id(file_id)
        if file is None:
            raise HTTPException(status_code=404, detail="File not found")
        if file["is_dir"]:
            raise HTTPException(status_code=400, detail="Cannot cache a directory")
        if file["status"] == "cached":
            return {"status": "cached"}

        remote_path = file.get("remote_path")
        if not remote_path:
            raise HTTPException(status_code=400, detail="File has no remote path")

        cloud_type = file.get("cloud_type")
        cache_dir = os.path.expanduser(settings.cache_dir)
        os.makedirs(cache_dir, exist_ok=True)
        safe_name = os.path.basename(remote_path)
        local_path = os.path.join(cache_dir, f"{file_id}_{safe_name}")

        if cloud_type == "yandex":
            from ...cloud_api.yandex import YandexDiskAsyncClient
            token = await db.get_config("yandex_token")
            if not token:
                raise HTTPException(status_code=401, detail="Not authenticated with Yandex")
            await YandexDiskAsyncClient(token).download(remote_path, local_path)
        elif cloud_type == "nextcloud":
            from ...cloud_api.nextcloud import NextcloudAsyncClient
            nc_host = await db.get_config("nc_host")
            nc_login = await db.get_config("nc_login")
            nc_password = await db.get_config("nc_password")
            if not (nc_host and nc_login and nc_password):
                raise HTTPException(status_code=401, detail="Not authenticated with Nextcloud")
            await NextcloudAsyncClient(nc_host, nc_login, nc_password).download(remote_path, local_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported cloud type: {cloud_type}")

        await db.update_downloaded_file(file_id, local_path)
        log.info("File %d downloaded to cache: %s", file_id, local_path)
        return {"status": "cached"}

    return router