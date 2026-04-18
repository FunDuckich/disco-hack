from fastapi import APIRouter, HTTPException

from ..schemas import StatsResponse, SettingsResponse, SettingsUpdate
from ...config import settings
from ...database.manager import DBManager

def make_router(db: DBManager) -> APIRouter:
    router = APIRouter(tags=["system"])

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.get("/api/stats", response_model=StatsResponse)
    async def api_stats():
        stats = await db.get_stats()
        return {**stats, "max_size": settings.max_cache_gb * 1024 ** 3}

    @router.get("/api/settings", response_model=SettingsResponse)
    async def get_settings():
        return {"max_cache_gb": settings.max_cache_gb}

    @router.post("/api/settings", response_model=SettingsResponse)
    async def update_settings(body: SettingsUpdate):
        if body.max_cache_gb <= 0:
            raise HTTPException(status_code=422, detail="max_cache_gb must be positive")
        settings.max_cache_gb = body.max_cache_gb
        await db.set_config("max_cache_gb", str(body.max_cache_gb))
        return {"max_cache_gb": settings.max_cache_gb}

    return router