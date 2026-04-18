import asyncio
import logging
import os

import pyfuse3
import pyfuse3.asyncio

from ..cloud_api.yandex import YandexDiskAsyncClient
from ..database.importer import import_cloud_to_db
from ..database.manager import DBManager
from .vfs import CloudFusionVFS
from .yandex_folder_sync import merge_last_uploaded_loop

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


async def start_cloud_fusion():
    if os.geteuid() == 0:
        msg = (
            "монтирование FUSE от root недоступно: обычные процессы (Dolphin) не увидят файловую систему. "
            "запустите без sudo"
        )
        if os.environ.get("SUDO_UID"):
            msg += " (или залогиньтесь под нужным пользователем и не используйте sudo для mount)"
        logging.error(msg)
        raise SystemExit(1)

    mountpoint = os.path.expanduser("~/CloudFusion")
    os.makedirs(mountpoint, exist_ok=True)
    try:
        os.chmod(mountpoint, 0o755)
    except OSError as e:
        logging.warning("не удалось chmod 755 на %s: %s", mountpoint, e)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(current_dir, "..", "database", "cloudfusion.db"))

    db_manager = DBManager(db_path)
    await db_manager.init_db()
    yandex_root_id = await db_manager.ensure_yandex_disk_root_folder()

    token = None
    while not token:
        token = await db_manager.get_config("yandex_token")
        if not token:
            logging.info("Ожидание авторизации через GUI...")
            await asyncio.sleep(5)
        else:
            logging.info("Токен найден!")

    cloud_api = YandexDiskAsyncClient(token=token)
    try:
        logging.info("Синхронизация структуры файлов...")
        cloud_files = await cloud_api.get_all_files_flat()
        if cloud_files:
            await import_cloud_to_db(
                db_manager,
                cloud_files,
                cloud_type="yandex",
                path_to_id_seed={"": yandex_root_id},
            )
    except Exception as e:
        logging.error(f"Ошибка синхронизации: {e}")

    vfs = CloudFusionVFS(db_manager, cloud_api)
    poll_task = asyncio.create_task(merge_last_uploaded_loop(db_manager, cloud_api))

    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('fsname=cloudfusion')

    pyfuse3.asyncio.enable()
    pyfuse3.init(vfs, mountpoint, fuse_options)

    logging.info(f"--- CloudFusion монтируется к {mountpoint} ---")

    try:
        await pyfuse3.main()
    except Exception as e:
        logging.error(f"Критическая ошибка FUSE: {e}")
    finally:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass
        pyfuse3.close()
        logging.info("Диск отмонтирован.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(start_cloud_fusion())
    except KeyboardInterrupt:
        logging.info("Демон остановлен пользователем.")
