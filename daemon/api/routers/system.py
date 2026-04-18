from fastapi import APIRouter

from ..schemas import StatsResponse
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

    return router