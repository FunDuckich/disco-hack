# daemon/cloud_api/yandex.py
import yadisk
import logging

class YandexDiskAsyncClient:
    def __init__(self, token: str):
        self.client = yadisk.AsyncClient(token=token)

    async def check_connection(self):
        is_valid = await self.client.check_token()
        if not is_valid:
            logging.error("Токен Яндекса недействителен!")
        return is_valid

    async def download(self, remote_path: str, local_path: str):
        logging.info(f"[Yandex API] Скачиваю из облака: {remote_path}")
        try:
            await self.client.download(remote_path, local_path)
            logging.info(f"[Yandex API] Скачивание {remote_path} завершено.")
        except Exception as e:
            logging.error(f"[Yandex API] Ошибка скачивания {remote_path}: {e}")
            raise e

    async def get_all_files_flat(self) -> list:
        logging.info("[Yandex API] Получаю дерево файлов...")
        result = []
        try:
            # Получаем все файлы рекурсивно (flat=True)
            # Это может занять время, если файлов много
            async for item in self.client.listdir("disk:/", limit=10000):
                result.append({
                    "path": item.path,
                    "type": "dir" if item.type == "dir" else "file",
                    "name": item.name,
                    "size": item.size or 0,
                    "revision": item.revision
                })
            return result
        except Exception as e:
            logging.error(f"[Yandex API] Ошибка получения структуры: {e}")
            return []