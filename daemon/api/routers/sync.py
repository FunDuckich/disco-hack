from fastapi import APIRouter, HTTPException, Query

from ...cloud_api.yandex import YandexDiskAsyncClient
from ...core.yandex_folder_sync import merge_last_uploaded, sync_yandex_folder_if_stale
from ...database.manager import DBManager

def make_router(db: DBManager) -> APIRouter:
    router = APIRouter(prefix="/api/sync", tags=["sync"])
    async def _yandex_client_or_401() -> YandexDiskAsyncClient:
        token = await db.get_config("yandex_token")
        if not token:
            raise HTTPException(status_code=401, detail="Токен Яндекса не найден")
        return YandexDiskAsyncClient(token)

    @router.post("/folder")
    async def api_sync_folder(
        parent_id: int | None = Query(default=None, description="id папки в SQLite; не указывать — корень диска"),
        force: bool = Query(default=True, description="True — всегда перезапросить API"),
    ):
        client = await _yandex_client_or_401()
        effective_parent = parent_id
        if effective_parent is None:
            wid = await db.get_yandex_disk_wrapper_id()
            if wid is None:
                wid = await db.ensure_yandex_disk_root_folder()
            effective_parent = wid
        changed = await sync_yandex_folder_if_stale(
            db, client, effective_parent, force=force
        )
        return {"ok": True, "changed": changed}

    @router.post("/last-uploaded")
    async def api_sync_last_uploaded(limit: int = Query(default=50, ge=1, le=200)):
        client = await _yandex_client_or_401()
        n = await merge_last_uploaded(db, client, limit=limit)
        return {"ok": True, "merged": n}

    return router