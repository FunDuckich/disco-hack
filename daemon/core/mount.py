import asyncio
import os

import pyfuse3
import pyfuse3.asyncio

import logging
import sys

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from daemon.core.vfs import CloudFusionVFS
from daemon.database.manager import DBManager
from daemon.database.importer import import_cloud_to_db
from daemon.cloud_api.yandex import YandexDiskAsyncClient

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

log = logging.getLogger(__name__)

async def start_cloud_fusion():
    mountpoint = os.path.expanduser("~/CloudFusion")
    db_path = "cloudfusion.db"
    os.makedirs(mountpoint, exist_ok=True)

    # 1. Инициализация БД
    db_manager = DBManager(db_path)
    await db_manager.init_db()

    # 2. Ожидание токена (блокируем выполнение, пока GUI не запишет токен)
    token = None
    while not token:
        token = await db_manager.get_config("yandex_token")
        if not token:
            logging.info("Ожидание авторизации через GUI...")
            await asyncio.sleep(5)
        else:
            logging.info("Токен найден!")

    # 3. Инициализация API и синхронизация
    cloud_api = YandexDiskAsyncClient(token=token)
    try:
        logging.info("Синхронизация структуры файлов...")
        cloud_files = await cloud_api.get_all_files_flat()
        if cloud_files:
            await import_cloud_to_db(db_manager, cloud_files, cloud_type="yandex")
    except Exception as e:
        logging.error(f"Ошибка синхронизации: {e}")
        # Решите, критично ли это. Если да — return

    # 4. Подготовка VFS
    vfs = CloudFusionVFS(db_manager, cloud_api)

    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('fsname=cloudfusion')
    fuse_options.add('allow_root') # Осторожно, требует прав root или настройки fuse.conf

    # 5. Монтирование и запуск
    pyfuse3.asyncio.enable()
    pyfuse3.init(vfs, mountpoint, fuse_options)

    logging.info(f"--- CloudFusion монтируется к {mountpoint} ---")

    try:
        await pyfuse3.main()
    except Exception as e:
        logging.error(f"Критическая ошибка FUSE: {e}")
    finally:
        pyfuse3.close()
        logging.info("Диск отмонтирован.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        # Запускаем один единственный Event Loop
        asyncio.run(start_cloud_fusion())
    except KeyboardInterrupt:
        logging.info("Демон остановлен пользователем.")

