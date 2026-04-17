import logging
import aiosqlite


class DBManager:
    def __init__(self, db_path="cloudfusion.db"):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
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

    async def bulk_upsert_metadata(self, metadata_list: list[dict]):
        async with aiosqlite.connect(self.db_path) as db:
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

    async def get_items_by_parent(self, parent_id):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM files WHERE parent_id IS ?"
            cursor = await db.execute(query, (parent_id,))
            return [dict(r) for r in await cursor.fetchall()]

    async def get_file_by_id(self, db_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM files WHERE id = ?", (db_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def lookup_file(self, parent_id: int, name: str):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT id FROM files WHERE name = ? AND parent_id IS ?"
            cursor = await db.execute(query, (name, parent_id))
            row = await cursor.fetchone()
            return row['id'] if row else None

    async def get_readdir_entries(self, parent_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, name FROM files WHERE parent_id IS ?", (parent_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_downloaded_file(self, db_id: int, local_path: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE files SET status = 'cached', local_path = ?, last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                (local_path, db_id)
            )
            await db.commit()

    async def search_files(self, query: str):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT f.id, f.name, f.remote_path, f.cloud_type, f.status, f.size 
                FROM files_fts AS fts
                JOIN files AS f ON f.id = fts.rowid
                WHERE fts.name MATCH ? LIMIT 50
            ''', (f"{query}*",))
            return [dict(r) for r in await cursor.fetchall()]
