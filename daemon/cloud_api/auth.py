import yadisk


class YandexAuthenticator:
    # Эти ключи общие для всего приложения
    CLIENT_ID = "92b225afdfb54df1ba7f18c13597d16b"
    CLIENT_SECRET = "95c9d7aad4d6446aacc827c38e9ad491"

    # URL, который слушает ваш локальный FastAPI сервер
    REDIRECT_URI = "http://localhost:8000/callback"

    @classmethod
    def get_auth_client(cls):
        """Создает клиента только для процесса авторизации"""
        return yadisk.Client(id=cls.CLIENT_ID, secret=cls.CLIENT_SECRET)

    @classmethod
    def get_login_url(cls) -> str:
        """Отдает ссылку, которую нужно открыть в браузере пользователя"""
        client = cls.get_auth_client()
        # Генерируем ссылку для авторизации
        return client.get_code_url(display="popup")

    @classmethod
    def get_token_from_code(cls, code: str) -> str:
        """Меняет временный код от Яндекса на постоянный токен пользователя"""
        client = cls.get_auth_client()
        try:
            response = client.get_token(code)
            return response.access_token
        except Exception as e:
            print(f"[ERROR] Не удалось получить токен: {e}")
            return None