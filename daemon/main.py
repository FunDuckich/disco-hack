import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.middleware import LoggingMiddleware
from api.schemas import FileItem, PinResponse, SearchResult, StatsResponse
from core.lru_engine import run_lru_cleanup
from database.manager import DBManager


CACHE_DIR = "~/.cache/cloud-fusion/"
MAX_CACHE_GB = 5
MOUNTPOINT = "~/CloudFusion"
DB_PATH = "cloudfusion.db"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("cloudfusion")

db = DBManager(DB_PATH)

try:
    from core.mount import DummyCloudAPI, fuse_runner
    from core.vfs import CloudFusionVFS
    _FUSE_IMPORT_ERROR: Exception | None = None
except ImportError as e:
    DummyCloudAPI = None
    fuse_runner = None
    CloudFusionVFS = None
    _FUSE_IMPORT_ERROR = e


async def lru_scheduler():
    while True:
        try:
            await run_lru_cleanup(db.db_path, CACHE_DIR, MAX_CACHE_GB)
        except Exception:
            log.exception("LRU cleanup failed")
        await asyncio.sleep(600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.expanduser(CACHE_DIR), exist_ok=True)
    await db.init_db()

    background_tasks: list[asyncio.Task] = [asyncio.create_task(lru_scheduler())]

    if fuse_runner is not None:
        vfs = CloudFusionVFS(db, DummyCloudAPI())
        mountpoint = os.path.expanduser(MOUNTPOINT)
        background_tasks.append(asyncio.create_task(fuse_runner(vfs, mountpoint)))
    else:
        # pyfuse3 is Linux-only; on Windows we still serve the API so the UI can be developed.
        log.warning("FUSE mount skipped — pyfuse3 unavailable (%s)", _FUSE_IMPORT_ERROR)

    try:
        yield
    finally:
        for task in background_tasks:
            task.cancel()
        await asyncio.gather(*background_tasks, return_exceptions=True)


app = FastAPI(title="CloudFusion", lifespan=lifespan)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/search", response_model=list[SearchResult])
async def api_search(q: str = Query(..., min_length=1)):
    return await db.search_files(q)


@app.get("/api/stats", response_model=StatsResponse)
async def api_stats():
    return await db.get_stats()


@app.get("/api/files/list", response_model=list[FileItem])
async def api_list(parent_id: int = None):
    return await db.get_items_by_parent(parent_id)


@app.get("/api/files/{file_id}", response_model=FileItem)
async def api_file(file_id: int):
    file = await db.get_file_by_id(file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@app.post("/api/files/{file_id}/pin", response_model=PinResponse)
async def api_pin(file_id: int, pinned: bool):
    await db.toggle_pin(file_id, pinned)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
