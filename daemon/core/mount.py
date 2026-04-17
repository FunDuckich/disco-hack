import os
import asyncio
import pyfuse3
import pyfuse3.asyncio
import logging
import sys

from cloud_api.nextcloud import NextcloudAsyncClient
from vfs import CloudFusionVFS
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from daemon.core.vfs import CloudFusionVFS
from daemon.database.manager import DBManager
from daemon.database.importer import import_cloud_to_db
from daemon.cloud_api.yandex import YandexDiskAsyncClient

logging.basicConfig(level=logging.INFO)

async def mount():
    mountpoint = os.path.expanduser("~/CloudFusion")
    db_path = "cloudfusion.db"
    os.makedirs(mountpoint, exist_ok=True)

    db_manager = DBManager(db_path)
    await db_manager.init_db()

    cloud_api = None
    cloud_type = None

    while not cloud_api:
        yandex_token = await db_manager.get_config("yandex_token")

        nc_host = await db_manager.get_config("nc_host")
        nc_login = await db_manager.get_config("nc_login")
        nc_password = await db_manager.get_config("nc_password")

        if yandex_token:
            logging.info("Найден токен Яндекса. Инициализация...")
            cloud_api = YandexDiskAsyncClient(token=yandex_token)
            cloud_type = "yandex"

        elif nc_host and nc_login and nc_password:
            logging.info("Найдены данные Nextcloud. Инициализация...")
            cloud_api = NextcloudAsyncClient(nc_host, nc_login, nc_password)
            cloud_type = "nextcloud"

        else:
            logging.info("Ожидание авторизации через GUI...")
            await asyncio.sleep(5)  # Ждем 5 секунд и проверяем базу снова

    try:
        logging.info(f"Синхронизация дерева файлов для {cloud_type}...")
        cloud_files = await cloud_api.get_all_files_flat()
        if cloud_files:
            await import_cloud_to_db(db_manager, cloud_files, cloud_type=cloud_type)
    except Exception as e:
        logging.error(f"Ошибка при первичной синхронизации: {e}")

    vfs = CloudFusionVFS(db_manager, cloud_api)
    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('allow_other')

    pyfuse3.asyncio.enable()

    try:
        pyfuse3.init(vfs, mountpoint, fuse_options)
        logging.info(f"--- CloudFusion успешно запущен и примонтирован к {mountpoint} ---")
        await pyfuse3.main()
    except Exception as e:
        logging.error(f"Критическая ошибка FUSE: {e}")

    finally:
        pyfuse3.close()
        logging.info("Диск успешно отмонтирован.")

if __name__ == '__main__':
    try:
        asyncio.run(mount())
    except KeyboardInterrupt:
        pass
