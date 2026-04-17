import os
import asyncio
import pyfuse3
import pyfuse3.asyncio
import logging
from vfs import CloudFusionVFS

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

    cloud_api = DummyCloudAPI() # ВСТАВИТЬ ВИТАЛЬКУ
    vfs = CloudFusionVFS(db_path, cloud_api)

    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('allow_root')

    pyfuse3.asyncio.enable()

    try:
        pyfuse3.init(vfs, mountpoint, fuse_options)
        logging.info(f"Успешно примонтировано к {mountpoint}.")
        logging.info("Открой Dolphin и зайди в эту папку. Нажми Ctrl+C для выхода.")

        await pyfuse3.main()
    except pyfuse3.FUSEError as e:
        logging.error(f"Ошибка монтирования: {e}")
    except KeyboardInterrupt:
        logging.info("Остановка демона...")
    finally:
        pyfuse3.close()
        logging.info("Отмонтировано.")


if __name__ == '__main__':
    asyncio.run(mount())