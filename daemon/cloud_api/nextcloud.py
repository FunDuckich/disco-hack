# daemon/cloud_api/nextcloud.py
import logging

from nc_py_api import AsyncNextcloud

from .paths import strip_cloud_scheme


def _nextcloud_api_path(remote_path: str) -> str:
    """Путь для nc_py_api (ведущий /, корень = '/')."""
    p = strip_cloud_scheme(remote_path, "nextcloud").replace("\\", "/").rstrip("/")
    if not p.startswith("/"):
        p = "/" + p if p else "/"
    if p == "":
        return "/"
    return p


class NextcloudAsyncClient:
    """Реализует контракт CloudStorageDriver (см. cloud_api.protocol)."""

    def __init__(self, host: str, login: str, password: str):
        self.login = login

        self.nc = AsyncNextcloud(
            nextcloud_url=host,
            nc_auth_user=login,
            nc_auth_pass=password,
        )

    async def check_connection(self) -> bool:
        logging.info("[Nextcloud] Проверка связи с сервером...")
        try:
            await self.nc.users.get_user(self.login)
            logging.info("[Nextcloud] Подключение успешно!")
            return True
        except Exception as e:
            logging.error(
                f"[Nextcloud] Ошибка авторизации (неверный пароль или URL): {e}"
            )
            return False

    async def download(self, remote_path: str, local_path: str):
        clean_path = _nextcloud_api_path(remote_path)
        logging.info(f"[Nextcloud] Скачиваю (поток): {clean_path}")
        try:
            await self.nc.files.download2stream(clean_path, local_path)
            logging.info(f"[Nextcloud] Успешно скачан в {local_path}")
        except Exception as e:
            logging.error(f"[Nextcloud] Ошибка скачивания {clean_path}: {e}")
            raise e

    async def upload_local_file(self, local_path: str, remote_path: str):
        clean = _nextcloud_api_path(remote_path)
        logging.info("[Nextcloud] Загрузка %s -> %s", local_path, clean)
        await self.nc.files.upload_stream(clean, local_path)

    async def remove_remote(self, remote_path: str):
        clean = _nextcloud_api_path(remote_path)
        logging.info("[Nextcloud] Удаление %s", clean)
        await self.nc.files.delete(clean)

    async def mkdir_remote(self, remote_path: str):
        clean = _nextcloud_api_path(remote_path)
        logging.info("[Nextcloud] mkdir %s", clean)
        await self.nc.files.mkdir(clean)

    async def move_remote(self, src_path: str, dst_path: str, *, overwrite: bool = True):
        src = _nextcloud_api_path(src_path)
        dst = _nextcloud_api_path(dst_path)
        logging.info("[Nextcloud] move %s -> %s", src, dst)
        await self.nc.files.move(src, dst, overwrite=overwrite)

    async def get_meta(self, remote_path: str):
        clean = _nextcloud_api_path(remote_path)
        return await self.nc.files.by_path(clean)

    async def listdir_metadata(self, remote_path: str) -> list[dict]:
        path = _nextcloud_api_path(remote_path)
        nodes = await self.nc.files.listdir(path)
        out: list[dict] = []
        for node in nodes:
            out.append(
                {
                    "path": f"nextcloud:{node.user_path}",
                    "type": "dir" if node.is_dir else "file",
                    "name": node.name,
                    "size": node.info.size if not node.is_dir else 0,
                    "revision": node.etag,
                }
            )
        return out

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

                result.append(
                    {
                        "path": full_path,
                        "type": "dir" if node.is_dir else "file",
                        "name": node.name,
                        "size": node.info.size if not node.is_dir else 0,
                        "revision": node.etag,
                    }
                )

                if node.is_dir:
                    sub_files = await self.get_all_files_flat(node.user_path)
                    result.extend(sub_files)

            return result
        except Exception as e:
            logging.error(f"[Nextcloud] Ошибка при сканировании {path}: {e}")
            return result
