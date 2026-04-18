import logging

from fastapi import APIRouter, HTTPException, Query

from ..schemas import FileItem, PathSegment, PinResponse, SearchResult, SyncResponse
from ...config import settings
from ...database.manager import DBManager
from ...cloud_api.yandex import YandexDiskAsyncClient
from ...cloud_api.nextcloud import NextcloudAsyncClient
from pydantic import BaseModel
import os

log = logging.getLogger("cloudfusion")

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

    from fastapi import Body


    @router.post("/api/files/publish")
    async def publish_file(data: dict = Body(...)):
        local_path = data.get("local_path")
        if not local_path:
            return {"error": "No path provided"}
        rel_path = os.path.relpath(local_path, os.path.expanduser(settings.mountpoint))
        parts = rel_path.split(os.sep)

        cloud_type = parts[0].lower()
        cloud_path = "/" + "/".join(parts[1:])

        file_info = await db.get_file_by_remote_path(cloud_path, cloud_type)

        try:
            if cloud_type == "yandex":
                res = await yandex_client.publish(cloud_path)  # Метод возвращает public_url
                public_url = res

            elif cloud_type == "nextcloud":

                share = await nc_client.nc.files.sharing.create_share(
                    path=cloud_path,
                    share_type=3  # 3 = PUBLIC_LINK
                )
                public_url = share.url

            # 4. Отправка в Tauri
            # Чтобы Tauri (Rust) узнал о событии, можно использовать WebSocket
            # или если Tauri сам вызвал этот запрос, вернуть в ответе.
            # Но для контекстного меню (внешний вызов) лучше emit через event bus.

            return {"status": "ok", "url": public_url}

        except Exception as e:
            return {"status": "error", "detail": str(e)}

    return router
