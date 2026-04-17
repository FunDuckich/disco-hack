import os
import asyncio
import webbrowser
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from cloud_api.auth import YandexAuthenticator

from database.manager import DBManager
from core.lru_engine import run_lru_cleanup

from pydantic import BaseModel
from fastapi import HTTPException
from cloud_api.nextcloud import NextcloudAsyncClient

class NextcloudInit(BaseModel):
    host: str

CACHE_DIR = "~/.cache/cloud-fusion/"
MAX_CACHE_GB = 5

db = DBManager("core/cloudfusion.db")

async def lru_scheduler():
    while True:
        try:
            await run_lru_cleanup(db.db_path, CACHE_DIR, MAX_CACHE_GB)
        except Exception as e:
            print(f"LRU Error: {e}")
        await asyncio.sleep(600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.expanduser(CACHE_DIR), exist_ok=True)
    await db.init_db()
    lru_task = asyncio.create_task(lru_scheduler())
    yield
    lru_task.cancel()

app = FastAPI(title="CloudFusion", lifespan=lifespan)


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

        # Можно отправить сигнал (через событие или переменную),
        # чтобы FUSE узнал о появлении токена
        return "<h1>Успешно! Теперь вернитесь в приложение.</h1>"
    else:
        return "<h1>Ошибка авторизации</h1>"



@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1)):
    return await db.search_files(q)

@app.get("/api/stats")
async def api_stats():
    return await db.get_stats()

@app.get("/api/files/list")
async def api_list(parent_id: int = None):
    return await db.get_items_by_parent(parent_id)

@app.post("/api/files/{file_id}/pin")
async def api_pin(file_id: int, pinned: bool):
    await db.toggle_pin(file_id, pinned)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)