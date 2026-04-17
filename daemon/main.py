from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import webbrowser
from cloud_api.auth import YandexAuthenticator

app = FastAPI()


# 1. Сюда React обращается, когда юзер жмет кнопку "Войти в Яндекс"
@app.get("/api/auth/login")
def login_route():
    url = YandexAuthenticator.get_login_url()
    webbrowser.open(url)
    return {"status": "browser_opened"}


# 2. Сюда Яндекс перенаправит пользователя после успешного входа
@app.get("/callback", response_class=HTMLResponse)
def yandex_callback(code: str = Query(...)):
    token = YandexAuthenticator.get_token_from_code(code)

    if token:
        # TODO: Сохранить токен в SQLite или системный Keyring!
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