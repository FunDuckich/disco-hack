import asyncio
import logging
import os

import pyfuse3
import pyfuse3.asyncio

import logging
import sys
from vfs import CloudFusionVFS
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from daemon.core.vfs import CloudFusionVFS
from daemon.database.manager import DBManager
from daemon.database.importer import import_cloud_to_db
from daemon.cloud_api.yandex import YandexDiskAsyncClient

log = logging.getLogger(__name__)


logging.basicConfig(level=logging.INFO)


async def mount():
    mountpoint = os.path.expanduser("~/CloudFusion")
    db_path = "cloudfusion.db"
    os.makedirs(mountpoint, exist_ok=True)

    # 1. Инициализация менеджера базы данных
    db_manager = DBManager(db_path)
    await db_manager.init_db()


    # 2. ЦИКЛ ОЖИДАНИЯ ТОКЕНА
    token = None
    while not token:
        token = await db_manager.get_config("yandex_token")
        if not token:
            logging.info("Ожидание авторизации пользователя через GUI...")
            await asyncio.sleep(5) # Проверяем базу каждые 5 секунд
        else:
            logging.info("Токен найден! Начинаю подключение к облаку...")

    # 3. Инициализация API клиента с реальным токеном
    cloud_api = YandexDiskAsyncClient(token=token)

    # 4. ПРЕДВАРИТЕЛЬНАЯ СИНХРОНИЗАЦИЯ
    # Подтягиваем дерево файлов, чтобы VFS сразу знала структуру облака
    try:
        logging.info("Синхронизация структуры файлов...")
        cloud_files = await cloud_api.get_all_files_flat()
        if cloud_files:
            await import_cloud_to_db(db_manager, cloud_files, cloud_type="yandex")
    except Exception as e:
        logging.error(f"Ошибка при первичной синхронизации: {e}")
        # Если нет интернета, FUSE все равно можно запустить (будет работать оффлайн-кеш)

    # 5. Настройка и запуск FUSE
    vfs = CloudFusionVFS(db_manager, cloud_api)
    fuse_options = set(pyfuse3.default_options)
    # allow_other позволяет другим пользователям/процессам видеть диск
    # fuse_options.add('allow_other')

    pyfuse3.asyncio.enable()
    pyfuse3.init(vfs, mountpoint, fuse_options)
    log.info("Успешно примонтировано к %s", mountpoint)

    try:
        await pyfuse3.main()
    finally:
        pyfuse3.close()
        log.info("Отмонтировано.")


async def _standalone():
    """Run the VFS by itself (no FastAPI). Invoke with `python -m core.mount` from daemon/."""
    from database.manager import DBManager
    from core.vfs import CloudFusionVFS

    db = DBManager("cloudfusion.db")
    await db.init_db()
    vfs = CloudFusionVFS(db, DummyCloudAPI())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(_standalone())
    except KeyboardInterrupt:
        log.info("Остановка демона...")
        pyfuse3.init(vfs, mountpoint, fuse_options)
        logging.info(f"--- CloudFusion успешно запущен и примонтирован к {mountpoint} ---")
        await pyfuse3.main()
    except Exception as e:
        logging.error(f"Критическая ошибка FUSE: {e}")

    finally:
        pyfuse3.close()
        logging.info("Диск успешно отмонтирован.")

