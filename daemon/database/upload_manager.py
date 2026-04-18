import asyncio
import logging
import os
import shutil

log = logging.getLogger(__name__)

upload_queue = asyncio.Queue()


async def upload_worker(active_clients, db_manager):
    """Фоновый воркер: берет задачу из очереди и вызывает API облака"""
    log.info("[Uploader] Воркер загрузки запущен.")

    while True:
        task = await upload_queue.get()
        try:
            local_path = task['local_path']
            remote_path = task['remote_path']
            cloud_type = task['cloud_type']

            log.info(f"[Uploader] Начинаю передачу: {local_path} -> {cloud_type}:{remote_path}")

            client = active_clients.get(cloud_type)
            if client:
                await client.upload(local_path, remote_path)

                if os.path.exists(local_path):
                    os.remove(local_path)
                log.info(f"[Uploader] Успешно загружено: {remote_path}")
            else:
                log.error(f"[Uploader] Клиент для {cloud_type} не найден!")

        except Exception as e:
            log.error(f"[Uploader] Ошибка при загрузке {task.get('remote_path')}: {e}")
        finally:
            upload_queue.task_done()