import logging

import yadisk


class YandexDiskAsyncClient:
    """Реализует контракт CloudStorageDriver (см. cloud_api.protocol)."""
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

    async def mkdir_remote(self, remote_path: str):
        await self.client.mkdir(remote_path, wait=True)

    async def remove_remote(self, remote_path: str):
        await self.client.remove(remote_path, wait=True)

    async def move_remote(self, src_path: str, dst_path: str, *, overwrite: bool = True):
        await self.client.move(src_path, dst_path, wait=True, overwrite=overwrite)

    async def upload_local_file(self, local_path: str, remote_path: str):
        # overwrite=True: повторное сохранение (Kate/Dolphin) иначе 409 «уже существует».
        await self.client.upload(
            local_path, remote_path, wait=True, overwrite=True
        )

    async def get_meta(self, remote_path: str):
        return await self.client.get_meta(remote_path)

    async def listdir_metadata(self, remote_path: str) -> list[dict]:
        out: list[dict] = []
        async for item in self.client.listdir(remote_path, limit=1000):
            out.append({
                "path": item.path,
                "type": "dir" if item.type == "dir" else "file",
                "name": item.name,
                "size": item.size or 0,
                "revision": getattr(item, "revision", None),
            })
        return out

    async def get_last_uploaded_resources(self, limit: int = 50) -> list:
        return await self.client.get_last_uploaded(limit=limit)

    async def get_all_files_flat(self) -> list:
        logging.info("[Yandex API] Получаю дерево файлов (рекурсивный обход)...")
        result: list[dict] = []

        async def visit(remote_dir: str) -> None:
            async for item in self.client.listdir(remote_dir, limit=1000):
                result.append({
                    "path": item.path,
                    "type": "dir" if item.type == "dir" else "file",
                    "name": item.name,
                    "size": item.size or 0,
                    "revision": getattr(item, "revision", None),
                })
                if item.type == "dir":
                    await visit(item.path)

        try:
            await visit("disk:/")
            logging.info("[Yandex API] Всего записей в индексе: %s", len(result))
            return result
        except Exception as e:
            logging.error(f"[Yandex API] Ошибка получения структуры: {e}")
            return []
