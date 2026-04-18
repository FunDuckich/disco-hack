import logging

from fastapi import APIRouter, HTTPException, Query

from ..schemas import FileItem, PathSegment, PinResponse, SearchResult, SyncResponse
from ...database.manager import DBManager

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

    return router