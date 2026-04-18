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
        max_size = int(settings.max_cache_gb * 1024**3)
        indexed = int(stats.get("indexed_bytes") or 0)
        cache_sz = int(stats.get("cache_size") or 0)
        total_files = int(stats.get("total_files") or 0)
        cached_count = int(stats.get("cached_count") or 0)
        # «Занято в облаке» по индексу БД; верхняя граница — хотя бы лимит кэша, чтобы не было 0/0
        used_space = indexed
        total_space = max(max_size, used_space, 1)
        return {
            **stats,
            "max_size": max_size,
            "used_space": used_space,
            "total_space": total_space,
            "used_cache_size": cache_sz,
            "total_files_count": total_files,
            "cached_files_count": cached_count,
        }

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