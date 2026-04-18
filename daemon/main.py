import asyncio
import logging
import os
import webbrowser
from contextlib import asynccontextmanager
import httpx
import uvicorn

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, JSONResponse

from .api.middleware import LoggingMiddleware
from .api.schemas import FileItem, PinResponse, SearchResult, StatsResponse, AuthStatusResponse, PathSegment, SyncResponse
from .cloud_api.auth import YandexAuthenticator
from .cloud_api.yandex import YandexDiskAsyncClient
from .core.lru_engine import run_lru_cleanup
from .core.yandex_folder_sync import merge_last_uploaded, sync_yandex_folder_if_stale
from .database.manager import DBManager
from .config import settings
from pydantic import BaseModel
from ..cloud_api.nextcloud import NextcloudAsyncClient

class NextcloudInit(BaseModel):
    host: str

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("cloudfusion")

db = DBManager(settings.db_path)

try:
    from core.mount import start_cloud_fusion
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


@app.post("/api/auth/nextcloud/start")
async def start_nextcloud_auth(data: NextcloudInit):
    host = data.host.rstrip('/')

    # 1. Просим Nextcloud начать процесс входа
    # Отправляем User-Agent, чтобы Nextcloud знал, как нас называть
    headers = {"User-Agent": "CloudFusion App"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{host}/index.php/login/v2",
                headers=headers
            )
            response.raise_for_status()
            nc_data = response.json()

            login_url = nc_data['login']
            poll_token = nc_data['poll']['token']
            poll_endpoint = nc_data['poll']['endpoint']

            # 2. Открываем браузер пользователю
            webbrowser.open(login_url)

            # 3. Запускаем фоновую задачу ожидания (polling)
            # В реальности лучше не блокировать ответ, но для хакатона сойдет
            asyncio.create_task(poll_nextcloud_token(host, poll_endpoint, poll_token))

            return {"status": "browser_opened", "message": "Пожалуйста, авторизуйтесь в браузере"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Не удалось связаться с сервером: {e}")


# Фоновая функция, которая каждую секунду дергает сервер
async def poll_nextcloud_token(host: str, poll_endpoint: str, poll_token: str):
    print("Начинаю ожидание авторизации в браузере...")

    async with httpx.AsyncClient() as client:
        # Пингуем сервер 60 раз (1 минуту), пока юзер логинится
        for _ in range(60):
            response = await client.post(poll_endpoint, data={"token": poll_token})

            if response.status_code == 200:
                result = response.json()
                app_password = result['appPassword']
                login = result['loginName']

                print(f"🔥 УСПЕХ! Получен пароль для {login}")

                # Сохраняем в нашу базу!
                await db.set_config("nc_host", host)
                await db.set_config("nc_login", login)
                await db.set_config("nc_password", app_password)
                await db.set_config("active_cloud", "nextcloud")
                return

            elif response.status_code == 404:
                # 404 означает "Юзер еще не нажал кнопку разрешить". Просто ждем.
                await asyncio.sleep(1)
            else:
                print("Ошибка при polling:", response.text)
                break

    print("Таймаут ожидания авторизации Nextcloud.")

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

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/search", response_model=list[SearchResult], tags=["files"])
async def api_search(q: str = Query(..., min_length=1)):
    return await db.search_files(q)


@app.get("/api/stats", response_model=StatsResponse, tags=["stats"])
async def api_stats():
    stats = await db.get_stats()
    return {**stats, "max_size": settings.max_cache_gb * 1024 ** 3}


@app.get("/api/files/list", response_model=list[FileItem], tags=["files"])
async def api_list(parent_id: int | None = None):
    return await db.get_items_by_parent(parent_id)


@app.get("/api/files/{file_id}", response_model=FileItem, tags=["files"])
async def api_file(file_id: int):
    file = await db.get_file_by_id(file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@app.get("/api/files/{file_id}/path", response_model=list[PathSegment], tags=["files"])
async def api_file_path(file_id: int):
    file = await db.get_file_by_id(file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    return await db.get_ancestors(file_id)


@app.post("/api/files/{file_id}/pin", response_model=PinResponse, tags=["files"])
async def api_pin(file_id: int, pinned: bool):
    await db.toggle_pin(file_id, pinned)
    return {"status": "ok"}


@app.get("/api/auth/login", tags=["auth"])
def login_route():
    url = YandexAuthenticator.get_login_url()
    webbrowser.open(url)
    return {"status": "browser_opened"}


@app.get("/callback", response_class=HTMLResponse, tags=["auth"])
async def yandex_callback(code: str = Query(...)):
    token = YandexAuthenticator.get_token_from_code(code)

    if token:
        await db.set_config("yandex_token", token)
        log.info("Yandex token saved to DB")

        # Можно отправить сигнал (через событие или переменную),
        # чтобы FUSE узнал о появлении токена
        return "<h1>Успешно! Теперь вернитесь в приложение.</h1>"
    else:
        log.warning("Yandex auth failed: no token returned for code")
        return "<h1>Ошибка авторизации</h1>"


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


@app.get("/api/auth/status", response_model=AuthStatusResponse, tags=["auth"])
async def auth_status():
    token = await db.get_config("yandex_token")
    return {"connected": token is not None}


@app.post("/api/auth/logout", tags=["auth"])
async def logout_route():
    await db.delete_config("yandex_token")
    log.info("Yandex token cleared from DB")
    return {"status": "ok"}


@app.post("/api/files/{file_id}/sync", response_model=SyncResponse, tags=["files"])
async def api_sync(file_id: int):
    file = await db.get_file_by_id(file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    if file["is_dir"]:
        raise HTTPException(status_code=400, detail="Cannot sync a directory")
    await db.set_file_status(file_id, "syncing")
    log.info("File %d marked for sync", file_id)
    return {"status": "syncing"}
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
    changed = await sync_yandex_folder_if_stale(db, client, parent_id, force=force)
    return {"ok": True, "changed": changed}


@app.post("/api/sync/last-uploaded")
async def api_sync_last_uploaded(limit: int = Query(default=50, ge=1, le=200)):
    client = await _yandex_client_or_401()
    n = await merge_last_uploaded(db, client, limit=limit)
    return {"ok": True, "merged": n}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
