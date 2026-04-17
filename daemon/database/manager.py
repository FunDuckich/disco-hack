import logging
import aiosqlite
import os
import sys

from daemon.api.schemas import FileItem

class DBManager:
    def __init__(self, db_path="cloudfusion.db"):
        print(db_path)
        self.db_path = db_path
        self._db = None

        if not os.path.isabs(db_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(base_dir, db_path)
        else:
            self.db_path = db_path

        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logging.info(f"Создана директория для базы: {db_dir}")

        self._db = None
        logging.info(f"DBManager инициализирован с путем: {self.db_path}")

    async def get_db(self):
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row
        return self._db

    async def init_db(self):
        db = await self.get_db()
        await db.execute('''
            CREATE TABLE IF NOT EXISTS config(
               key TEXT PRIMARY KEY,
               value TEXT
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                name TEXT NOT NULL,
                size INTEGER DEFAULT 0,
                is_dir BOOLEAN DEFAULT 0,
                cloud_type TEXT,
                remote_path TEXT,
                local_path TEXT,
                etag TEXT,
                status TEXT DEFAULT 'stub', 
                is_pinned BOOLEAN DEFAULT 0,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cloud_type, remote_path)
            )
        ''')
        await db.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts 
            USING fts5(name, content='files', content_rowid='id')
        ''')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_parent ON files(parent_id)')
        await db.commit()
        logging.info("Database initialized successfully")


    async def set_config(self, key: str, value: str):
        db = await self.get_db()
        await db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()

    async def get_config(self, key: str):
        db = await self.get_db()
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row['value'] if row else None

    async def delete_config(self, key: str):
        db = await self.get_db()
        await db.execute("DELETE FROM config WHERE key = ?", (key,))
        await db.commit()

    async def bulk_upsert_metadata(self, metadata_list: list[dict]):
        db = await self.get_db()
        await db.executemany('''
            INSERT INTO files (parent_id, name, size, is_dir, cloud_type, remote_path, etag, status)
            VALUES (:parent_id, :name, :size, :is_dir, :cloud_type, :remote_path, :etag, 'stub')
            ON CONFLICT(cloud_type, remote_path) DO UPDATE SET
                name = excluded.name,
                size = excluded.size,
                etag = excluded.etag,
                parent_id = excluded.parent_id
        ''', metadata_list)
        await db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def get_items_by_parent(self, parent_id):
        db = await self.get_db()
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM files WHERE parent_id IS ?"
        cursor = await db.execute(query, (parent_id,))
        return [dict(r) for r in await cursor.fetchall()]

    async def get_file_by_id(self, db_id: int):
        db = await self.get_db()
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM files WHERE id = ?", (db_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def lookup_file(self, parent_id: int, name: str):
        db = await self.get_db()
        db.row_factory = aiosqlite.Row
        query = "SELECT id FROM files WHERE name = ? AND parent_id IS ?"
        cursor = await db.execute(query, (name, parent_id))
        row = await cursor.fetchone()
        return row['id'] if row else None

    async def get_readdir_entries(self, parent_id: int):
        db = await self.get_db()
        query = "SELECT id, name, is_dir, size FROM files WHERE parent_id IS ?"
        async with db.execute(query, (parent_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_downloaded_file(self, db_id: int, local_path: str):
        db = await self.get_db()
        await db.execute(
            "UPDATE files SET status = 'cached', local_path = ?, last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
            (local_path, db_id)
        )
        await db.commit()

    async def set_file_status(self, file_id: int, status: str):
        db = await self.get_db()
        await db.execute("UPDATE files SET status = ? WHERE id = ?", (status, file_id))
        await db.commit()

    async def get_stats(self):
        """Статистика для React Dashboard"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT
                    COUNT(*) as total_files,
                    COALESCE(SUM(CASE WHEN status = 'cached' THEN size ELSE 0 END), 0) as cache_size,
                    COUNT(CASE WHEN is_pinned = 1 THEN 1 END) as pinned_count
                FROM files
            ''')
            return dict(await cursor.fetchone())

    async def toggle_pin(self, file_id: int, is_pinned: bool):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE files SET is_pinned = ? WHERE id = ?",
                (1 if is_pinned else 0, file_id),
            )
            await db.commit()

    async def search_files(self, query: str):
        db = await self.get_db()
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT f.id, f.name, f.remote_path, f.cloud_type, f.status, f.size
            FROM files_fts AS fts
            JOIN files AS f ON f.id = fts.rowid
            WHERE fts.name MATCH ? LIMIT 50
        ''', (f"{query}*",))
        return [dict(r) for r in await cursor.fetchall()]

    async def get_ancestors(self, file_id: int):
        db = await self.get_db()
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            WITH RECURSIVE ancestors(id, parent_id, name, depth) AS (
                SELECT id, parent_id, name, 0 FROM files WHERE id = ?
                UNION ALL
                SELECT f.id, f.parent_id, f.name, a.depth + 1
                FROM files f
                JOIN ancestors a ON f.id = a.parent_id
                WHERE a.depth < 64
            )
            SELECT id, name FROM ancestors ORDER BY depth DESC
        ''', (file_id,))
        return [dict(r) for r in await cursor.fetchall()]
