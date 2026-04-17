import os
import asyncio
import webbrowser
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from cloud_api.auth import YandexAuthenticator

from database.manager import DBManager
from core.lru_engine import run_lru_cleanup

CACHE_DIR = "~/.cache/cloud-fusion/"
MAX_CACHE_GB = 5

db = DBManager("cloudfusion.db")

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


@app.get("/api/auth/login")
def login_route():
    url = YandexAuthenticator.get_login_url()
    webbrowser.open(url)
    return {"status": "browser_opened"}

@app.get("/callback", response_class=HTMLResponse)
def yandex_callback(code: str = Query(...)):
    token = YandexAuthenticator.get_token_from_code(code)

    if token:
        # TODO: Сохранить токен в SQLite! 
        # Теперь у тебя есть доступ к объекту `db`, 
        # можешь попросить коллегу добавить метод вроде await db.save_token(token)
        print(f"🔥 Успех! Получен токен пользователя: {token}")

        return """
        <html>
            <body style="display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif; background:#f4f4f4;">
                <div style="background:white; padding:40px; border-radius:10px; box-shadow:0 4px 10px rgba(0,0,0,0.1); text-align:center;">
                    <h2 style="color:#28a745;">CloudFusion успешно подключен!</h2>
                    <p>Теперь вы можете закрыть эту вкладку и вернуться в приложение.</p>
                </div>
            </body>
        </html>
        """
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