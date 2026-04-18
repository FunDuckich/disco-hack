import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from .api.middleware import LoggingMiddleware
from .api.routers import auth, files, sync, system
from .core.lru_engine import run_lru_cleanup
from .database.manager import DBManager
from .config import settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("cloudfusion")

db = DBManager(settings.db_path)

try:
    from .core.mount import start_cloud_fusion
    _FUSE_AVAILABLE = True
    _FUSE_IMPORT_ERROR: Exception | None = None
except ImportError as e:
    start_cloud_fusion = None
    _FUSE_AVAILABLE = False
    _FUSE_IMPORT_ERROR = e


async def lru_scheduler():
    while True:
        try:
            await run_lru_cleanup(db.db_path, settings.cache_dir, settings.max_cache_gb)
        except Exception:
            log.exception("LRU cleanup failed")
        await asyncio.sleep(600)


async def _cancel(task: asyncio.Task | None) -> None:
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.expanduser(settings.cache_dir), exist_ok=True)
    await db.init_db()
    lru_task = asyncio.create_task(lru_scheduler())
    log.info("CloudFusion daemon started (cache=%s, limit=%dGB)", settings.cache_dir, settings.max_cache_gb)

    mount_task: asyncio.Task | None = None
    if settings.enable_fuse:
        if not _FUSE_AVAILABLE:
            log.warning(
                "ENABLE_FUSE=true but FUSE imports failed (%s). Server will run without mount.",
                _FUSE_IMPORT_ERROR,
            )
        else:
            try:
                mount_task = asyncio.create_task(start_cloud_fusion())
                log.info("FUSE mount task started (mountpoint=%s)", settings.mountpoint)
            except Exception:
                log.exception("Failed to start FUSE mount task — continuing without mount")
    else:
        log.info("FUSE disabled (set ENABLE_FUSE=true to enable)")

    try:
        yield
    finally:
        await _cancel(mount_task)
        await _cancel(lru_task)
        await db.close()
        log.info("CloudFusion daemon stopped")


app = FastAPI(title="CloudFusion", lifespan=lifespan)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(system.make_router(db))
app.include_router(auth.make_router(db))
app.include_router(files.make_router(db))
app.include_router(sync.make_router(db))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)