import os
import aiosqlite
import logging


async def run_lru_cleanup(db_path, cache_dir, max_size_gb=5):
    """Алгоритм вытеснения: удаляет старые файлы, если кэш переполнен"""
    max_size_bytes = max_size_gb * 1024 * 1024 * 1024
    cache_dir = os.path.expanduser(cache_dir)

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("SELECT SUM(size) as total FROM files WHERE status = 'cached'")
        row = await cursor.fetchone()
        current_size = row['total'] or 0

        if current_size > max_size_bytes:
            diff = current_size - max_size_bytes
            logging.info(f"LRU: Cache overflow ({current_size // 1024 ** 2} MB). Need to free {diff // 1024 ** 2} MB")

            cursor = await db.execute('''
                SELECT id, local_path, size 
                FROM files 
                WHERE status = 'cached' AND is_pinned = 0 
                ORDER BY last_accessed ASC
            ''')
            rows = await cursor.fetchall()

            freed = 0
            for file in rows:
                if freed >= diff: break

                if file['local_path'] and os.path.exists(file['local_path']):
                    try:
                        os.remove(file['local_path'])
                        logging.info(f"LRU: Deleted {file['local_path']}")
                    except Exception as e:
                        logging.error(f"LRU: Failed to delete {file['local_path']}: {e}")

                await db.execute(
                    "UPDATE files SET status = 'stub', local_path = NULL WHERE id = ?",
                    (file['id'],)
                )
                freed += file['size']

            await db.commit()
            logging.info(f"LRU: Cleanup finished. Freed {freed // 1024 ** 2} MB")
