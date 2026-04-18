import logging

import aiosqlite

_COMMIT_EVERY = 512


async def import_cloud_to_db(db_manager, cloud_files, cloud_type, path_to_id_seed: dict | None = None):
    logging.info(f"Starting import for {len(cloud_files)} items from {cloud_type}")

    cloud_files.sort(key=lambda x: x['path'].count('/'))

    path_to_id = {"": None}
    if path_to_id_seed:
        path_to_id.update(path_to_id_seed)

    async with aiosqlite.connect(db_manager.db_path) as db:
        for idx, item in enumerate(cloud_files):
            full_path = item['path'].replace('disk:', '').rstrip('/')
            if not full_path.startswith('/'):
                full_path = '/' + full_path

            parts = full_path.split('/')
            parent_path = "/".join(parts[:-1])

            parent_db_id = path_to_id.get(parent_path)

            file_data = {
                "parent_id": parent_db_id,
                "name": item['name'],
                "is_dir": 1 if item['type'] == 'dir' else 0,
                "size": item.get('size', 0),
                "cloud_type": cloud_type,
                "remote_path": item['path'],
                "etag": item.get('md5') or item.get('revision', '')
            }

            cursor = await db.execute('''
                INSERT INTO files (parent_id, name, is_dir, size, cloud_type, remote_path, etag)
                VALUES (:parent_id, :name, :is_dir, :size, :cloud_type, :remote_path, :etag)
            ON CONFLICT(cloud_type, remote_path) DO UPDATE SET
                    parent_id = excluded.parent_id,
                    name = excluded.name,
                    size = excluded.size,
                    etag = excluded.etag
                    RETURNING id
             ''', file_data)
            row = await cursor.fetchone()
            new_id = row[0]
            path_to_id[full_path] = new_id

            if (idx + 1) % _COMMIT_EVERY == 0:
                await db.commit()

        await db.commit()

    logging.info(f"Import finished. Tree structure rebuilt in SQLite.")
