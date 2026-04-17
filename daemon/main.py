import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn

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

@app.get("/api/auth/login")
def login_route():
    url = YandexAuthenticator.get_login_url()
    webbrowser.open(url)
    return {"status": "browser_opened"}

@app.get("/callback", response_class=HTMLResponse)
async def yandex_callback(code: str = Query(...)):
    token = YandexAuthenticator.get_token_from_code(code)

    if token:
        await db.set_config("yandex_token", token)
        print(f"🔥 Токен успешно сохранен в БД")

        # Можно отправить сигнал (через событие или переменную),
        # чтобы FUSE узнал о появлении токена
        return "<h1>Успешно! Теперь вернитесь в приложение.</h1>"
    else:
        return "<h1>Ошибка авторизации</h1>"

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
    lru_task = asyncio.create_task(lru_scheduler())
    yield
    lru_task.cancel()


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
    uvicorn.run(app, host="127.0.0.1", port=8000)