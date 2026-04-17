import asyncio
import logging
import os

import pyfuse3
import pyfuse3.asyncio

log = logging.getLogger(__name__)


class DummyCloudAPI:
    """Заглушка для Бэкендера 3. Имитирует скачивание файла из облака."""

    async def download(self, remote_path, local_path):
        log.info("CLOUD API: Имитация скачивания %s...", remote_path)
        await asyncio.sleep(2)
        with open(local_path, 'wb') as f:
            f.write(b"Hello from the Cloud! This is dummy content.")


async def fuse_runner(vfs, mountpoint: str):
    """Mount `vfs` at `mountpoint` and run pyfuse3 until the task is cancelled."""
    os.makedirs(mountpoint, exist_ok=True)

    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('fsname=cloudfusion')
    fuse_options.add('allow_root')

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
    await fuse_runner(vfs, os.path.expanduser("~/CloudFusion"))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(_standalone())
    except KeyboardInterrupt:
        log.info("Остановка демона...")
