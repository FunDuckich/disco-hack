import asyncio
import logging
import os
import webbrowser
from contextlib import asynccontextmanager
import httpx
import uvicorn

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from .api.middleware import LoggingMiddleware
from .api.routers import auth, files, sync, system
from .core.lru_engine import run_lru_cleanup
from .database.manager import DBManager
from .config import settings
from pydantic import BaseModel
from .cloud_api.nextcloud import NextcloudAsyncClient

class NextcloudInit(BaseModel):
    host: str

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
    saved_max = await db.get_config("max_cache_gb")
    if saved_max is not None:
        settings.max_cache_gb = float(saved_max)
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