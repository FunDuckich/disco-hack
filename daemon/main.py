import asyncio
import logging
import os
import webbrowser
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

from .api.middleware import LoggingMiddleware
from .api.schemas import FileItem, PinResponse, SearchResult, StatsResponse
from .cloud_api.auth import YandexAuthenticator
from .cloud_api.yandex import YandexDiskAsyncClient
from .core.lru_engine import run_lru_cleanup
from .core.yandex_folder_sync import merge_last_uploaded, sync_yandex_folder_if_stale
from .database.manager import DBManager

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.expanduser(CACHE_DIR), exist_ok=True)
    await db.init_db()
    await db.ensure_yandex_disk_root_folder()
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


async def _yandex_client_or_401() -> YandexDiskAsyncClient:
    token = await db.get_config("yandex_token")
    if not token:
        raise HTTPException(status_code=401, detail="Токен Яндекса не найден")
    return YandexDiskAsyncClient(token)


@app.post("/api/sync/folder")
async def api_sync_folder(
    parent_id: int | None = Query(
        default=None,
        description="id папки в SQLite; не указывать — корень диска",
    ),
    force: bool = Query(
        default=True,
        description="True — всегда перезапросить API (кнопка «обновить»)",
    ),
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


@app.post("/api/sync/last-uploaded")
async def api_sync_last_uploaded(limit: int = Query(default=50, ge=1, le=200)):
    client = await _yandex_client_or_401()
    n = await merge_last_uploaded(db, client, limit=limit)
    return {"ok": True, "merged": n}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
