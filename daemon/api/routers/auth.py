import logging
import webbrowser

from fastapi import APIRouter, Query
from starlette.responses import HTMLResponse

from ..schemas import AuthStatusResponse
from ...cloud_api.auth import YandexAuthenticator
from ...database.manager import DBManager

log = logging.getLogger("cloudfusion")

def make_router(db: DBManager) -> APIRouter:
    router = APIRouter(tags=["auth"])
    @router.get("/api/auth/login")
    def login_route():
        url = YandexAuthenticator.get_login_url()
        webbrowser.open(url)
        return {"status": "browser_opened"}

    @router.get("/callback", response_class=HTMLResponse)
    async def yandex_callback(code: str = Query(...)):
        token = YandexAuthenticator.get_token_from_code(code)
        if token:
            await db.set_config("yandex_token", token)
            log.info("Yandex token saved to DB")
            return "<h1>Успешно! Теперь вернитесь в приложение.</h1>"
        else:
            log.warning("Yandex auth failed: no token returned for code")
            return "<h1>Ошибка авторизации</h1>"

    @router.get("/api/auth/status", response_model=AuthStatusResponse)
    async def auth_status():
        token = await db.get_config("yandex_token")
        return {"connected": token is not None}

    @router.post("/api/auth/logout")
    async def logout_route():
        await db.delete_config("yandex_token")
        log.info("Yandex token cleared from DB")
        return {"status": "ok"}

    return router