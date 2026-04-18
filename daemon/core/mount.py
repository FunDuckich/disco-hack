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
    os.makedirs(mountpoint, exist_ok=True)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(current_dir, "..", "database", "cloudfusion.db"))

    db_manager = DBManager(db_path)
    await db_manager.init_db()

    active_clients = {}
    while not active_clients:
        yandex_token = await db_manager.get_config("yandex_token")
        if yandex_token:
            logging.info("Найден токен Яндекса. Добавляем в пул...")
            active_clients["yandex"] = YandexDiskAsyncClient(token=yandex_token)

        nc_host = await db_manager.get_config("nc_host")
        nc_login = await db_manager.get_config("nc_login")
        nc_password = await db_manager.get_config("nc_password")
        if nc_host and nc_login and nc_password:
            logging.info("Найдены данные Nextcloud. Добавляем в пул...")
            active_clients["nextcloud"] = NextcloudAsyncClient(nc_host, nc_login, nc_password)

        if not active_clients:
            logging.info("Нет подключенных дисков. Ожидание авторизации...")
            await asyncio.sleep(5)

    for cloud_type, client in active_clients.items():
        try:
            logging.info(f"Синхронизация структуры для {cloud_type.upper()}...")
            cloud_files = await client.get_all_files_flat()

            if cloud_files:
                await import_cloud_to_db(db_manager, cloud_files, cloud_type=cloud_type)
                logging.info(f"✅ {cloud_type.upper()} синхронизирован.")
        except Exception as e:
            logging.error(f" Ошибка синхронизации {cloud_type}: {e}")

    vfs = CloudFusionVFS(db_manager, active_clients)
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
