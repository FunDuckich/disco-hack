import logging

from fastapi import APIRouter, Query
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

from ..schemas import AuthStatusResponse
from ...cloud_api.auth import YandexAuthenticator
from ...database.manager import DBManager

log = logging.getLogger("cloudfusion")


def make_router(db: DBManager) -> APIRouter:
    router = APIRouter(tags=["auth"])

    @router.get("/api/auth/login")
    def login_route(provider: str | None = Query(None)):
        """
        Редирект на страницу OAuth Яндекса (удобно открывать из браузера / Tauri opener).
        Nextcloud — только POST /api/auth/nextcloud/start.
        """
        p = (provider or "YANDEX").upper()
        if p == "NEXTCLOUD":
            return JSONResponse(
                {
                    "detail": "Nextcloud: POST /api/auth/nextcloud/start с JSON {\"host\": \"https://...\"}",
                },
                status_code=400,
            )
        url = YandexAuthenticator.get_login_url()
        return RedirectResponse(url, status_code=302)

    @router.get("/callback", response_class=HTMLResponse)
    async def yandex_callback(code: str = Query(...)):
        token = YandexAuthenticator.get_token_from_code(code)
        if token:
            await db.set_config("yandex_token", token)
            log.info("Yandex token saved to DB")
            return "<h1>Успешно! Теперь вернитесь в приложение.</h1>"
        log.warning("Yandex auth failed: no token returned for code")
        return "<h1>Ошибка авторизации</h1>"

    @router.get("/api/auth/status", response_model=AuthStatusResponse)
    async def auth_status():
        yandex = await db.get_config("yandex_token")
        nc_host = await db.get_config("nc_host")
        nc_login = await db.get_config("nc_login")
        nc_password = await db.get_config("nc_password")
        providers = {
            "YANDEX": yandex is not None,
            "NEXTCLOUD": bool(nc_host and nc_login and nc_password),
        }
        return {"connected": providers["YANDEX"], "providers": providers}

    @router.post("/api/auth/logout")
    async def logout_route(provider: str | None = Query("YANDEX")):
        p = (provider or "YANDEX").upper()
        if p == "NEXTCLOUD":
            for key in ("nc_host", "nc_login", "nc_password", "active_cloud"):
                await db.delete_config(key)
            log.info("Nextcloud credentials cleared from DB")
        else:
            await db.delete_config("yandex_token")
            log.info("Yandex token cleared from DB")
        return {"status": "ok"}

    return router
