import yadisk
from typing import List, Dict
from .base import BaseCloudClient


class YandexDiskClient(BaseCloudClient):
    def __init__(self, token: str):
        self.client = yadisk.Client(token=token)

        # Проверяем токен на валидность сразу при запуске
        if not self.client.check_token():
            print("[ERROR] Неверный токен Яндекс.Диска!")

    def get_metadata(self, path: str = "/") -> List[Dict]:
        print(f"[Yandex API] Запрашиваю метаданные для: {path}")
        result = []

        try:
            for item in self.client.listdir(path):
                result.append({
                    "name": item.name,
                    "is_dir": item.type == "dir",
                    "size": item.size or 0,
                    "etag": item.revision,  # Ревизия для проверки синхронизации
                    "path": item.path
                })
            return result
        except yadisk.exceptions.PathNotFoundError:
            print(f"[ERROR] Путь {path} не найден")
            return []
        except Exception as e:
            print(f"[ERROR] Ошибка API: {e}")
            return []

    def download_file(self, remote_path: str, local_path: str) -> bool:
        print(f"[Yandex API] Скачиваю {remote_path} в {local_path}")
        try:
            self.client.download(remote_path, local_path)
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка скачивания: {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        print(f"[Yandex API] Загружаю {local_path} в {remote_path}")
        try:
            self.client.upload(local_path, remote_path)
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки: {e}")
            return False