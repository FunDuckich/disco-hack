# daemon/cloud_api/nextcloud.py
import logging
import asyncio
from nc_py_api import AsyncNextcloud


class NextcloudAsyncClient:
    def __init__(self, host: str, login: str, password: str):
        self.login = login
        
        self.nc = AsyncNextcloud(
            nextcloud_url=host,
            nc_auth_user=login,
            nc_auth_pass=password
        )

    async def check_connection(self) -> bool:
        logging.info("[Nextcloud] Проверка связи с сервером...")
        try:
            await self.nc.users.get_user(self.login)
            logging.info("[Nextcloud] Подключение успешно!")
            return True
        except Exception as e:
            logging.error(f"[Nextcloud] Ошибка авторизации (неверный пароль или URL): {e}")
            return False

    async def download(self, remote_path: str, local_path: str):
        clean_path = remote_path.replace('nextcloud:', '')
        if not clean_path.startswith('/'):
            clean_path = '/' + clean_path

        logging.info(f"[Nextcloud] Скачиваю: {clean_path}")
        try:
            file_bytes = await self.nc.files.download(clean_path)

            with open(local_path, 'wb') as f:
                f.write(file_bytes)

            logging.info(f"[Nextcloud] Успешно скачан в {local_path}")
        except Exception as e:
            logging.error(f"[Nextcloud] Ошибка скачивания {clean_path}: {e}")
            raise e

    async def get_all_files_flat(self, path: str = "/") -> list:
        """
        Рекурсивно обходит весь Nextcloud и собирает плоский список файлов.
        """
        if path == "/":
            logging.info("[Nextcloud] Начинаю сканирование дерева файлов...")

        result = []
        try:
            nodes = await self.nc.files.listdir(path)

            for node in nodes:
                full_path = f"nextcloud:{node.user_path}"

                result.append({
                    "path": full_path,
                    "type": "dir" if node.is_dir else "file",
                    "name": node.name,
                    "size": node.info.size if not node.is_dir else 0,
                    "revision": node.etag
                })

                if node.is_dir:
                    sub_files = await self.get_all_files_flat(node.user_path)
                    result.extend(sub_files)

            return result
        except Exception as e:
            logging.error(f"[Nextcloud] Ошибка при сканировании {path}: {e}")
            return result