import os
import asyncio
import pyfuse3
import pyfuse3.asyncio
import logging
import sys
from vfs import CloudFusionVFS
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from daemon.database.manager import DBManager
from daemon.core.vfs import CloudFusionVFS

logging.basicConfig(level=logging.INFO)


class DummyCloudAPI:
    """Заглушка для Бэкендера 3. Имитирует скачивание файла из облака"""

    async def download(self, remote_path, local_path):
        logging.info(f"CLOUD API: Имитация скачивания {remote_path}...")
        await asyncio.sleep(2)
        with open(local_path, 'wb') as f:
            f.write(b"Hello from the Cloud! This is dummy content.")


async def mount():
    mountpoint = os.path.expanduser("~/CloudFusion")
    db_path = "cloudfusion.db"

    os.makedirs(mountpoint, exist_ok=True)

    db_manager = DBManager(db_path)

    cloud_api = DummyCloudAPI() # Виталька

    await db_manager.init_db()
    vfs = CloudFusionVFS(db_manager, cloud_api)

    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('allow_root')

    pyfuse3.asyncio.enable()

    try:
        pyfuse3.init(vfs, mountpoint, fuse_options)
        logging.info(f"Успешно примонтировано к {mountpoint}.")
        await pyfuse3.main()
    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
    finally:
        pyfuse3.close()
        logging.info("Отмонтировано.")


if __name__ == '__main__':
    try:
        asyncio.run(mount())
    except KeyboardInterrupt:
        pass
