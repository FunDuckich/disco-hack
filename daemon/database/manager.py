import logging
import os

import aiosqlite
import os

from ..api.schemas import FileItem

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
        await db.execute("PRAGMA journal_mode=WAL")
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
        await db.execute('''
            CREATE TRIGGER IF NOT EXISTS t_files_ai AFTER INSERT ON files BEGIN
                INSERT INTO files_fts(rowid, name) VALUES (new.id, new.name);
            END
        ''')
        await db.execute('''
            CREATE TRIGGER IF NOT EXISTS t_files_ad AFTER DELETE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, name) VALUES ('delete', old.id, old.name);
            END
        ''')
        await db.execute('''
            CREATE TRIGGER IF NOT EXISTS t_files_au AFTER UPDATE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, name) VALUES ('delete', old.id, old.name);
                INSERT INTO files_fts(rowid, name) VALUES (new.id, new.name);
            END
        ''')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_parent ON files(parent_id)')
        await db.commit()
        logging.info("Database initialized successfully")

    async def get_yandex_disk_wrapper_id(self) -> int | None:
        db = await self.get_db()
        cur = await db.execute(
            "SELECT id FROM files WHERE cloud_type = 'yandex' AND remote_path = 'disk:/' LIMIT 1"
        )
        row = await cur.fetchone()
        return int(row[0]) if row else None

    async def ensure_yandex_disk_root_folder(self) -> int:
        db = await self.get_db()
        wid = await self.get_yandex_disk_wrapper_id()
        if wid is not None:
            await db.execute(
                """
                UPDATE files SET parent_id = ?
                WHERE cloud_type = 'yandex' AND parent_id IS NULL AND id != ?
                """,
                (wid, wid),
            )
            await db.commit()
            return wid

        stored_rev = await self.get_config("yandex_disk_root_folder_revision") or ""

        cur = await db.execute(
            """
            INSERT INTO files (parent_id, name, is_dir, size, cloud_type, remote_path, etag, status)
            VALUES (NULL, 'YandexDisk', 1, 0, 'yandex', 'disk:/', ?, 'stub')
            RETURNING id
            """,
            (stored_rev,),
        )
        row = await cur.fetchone()
        new_id = int(row[0])
        await self._fts_insert_row(db, new_id, "YandexDisk")
        await db.execute(
            """
            UPDATE files SET parent_id = ?
            WHERE cloud_type = 'yandex' AND parent_id IS NULL AND id != ?
            """,
            (new_id, new_id),
        )
        await db.commit()
        return new_id


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

    async def get_file_id_by_remote_path(self, cloud_type: str, remote_path: str) -> int | None:
        db = await self.get_db()
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id FROM files WHERE cloud_type = ? AND remote_path = ?",
            (cloud_type, remote_path),
        )
        row = await cur.fetchone()
        return int(row["id"]) if row else None

    async def delete_yandex_children_subtrees(self, parent_id: int | None) -> None:
        db = await self.get_db()
        await db.execute(
            """
            WITH RECURSIVE doomed AS (
                SELECT id FROM files
                WHERE cloud_type = 'yandex' AND parent_id IS ?
                UNION ALL
                SELECT f.id FROM files AS f
                INNER JOIN doomed AS d ON f.parent_id = d.id
            )
            DELETE FROM files WHERE id IN (SELECT id FROM doomed)
            """,
            (parent_id,),
        )
        await db.commit()

    async def get_direct_children_yandex(self, parent_id: int | None) -> list[dict]:
        db = await self.get_db()
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT id, name, remote_path, is_dir
            FROM files
            WHERE cloud_type = 'yandex' AND parent_id IS ?
            """,
            (parent_id,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def upsert_yandex_direct_child(self, parent_db_id: int | None, item: dict) -> None:
        db = await self.get_db()
        file_data = {
            "parent_id": parent_db_id,
            "name": item["name"],
            "is_dir": 1 if item["type"] == "dir" else 0,
            "size": item.get("size", 0),
            "cloud_type": "yandex",
            "remote_path": item["path"],
            "etag": str(item.get("revision") or item.get("md5") or ""),
        }
        await db.execute(
            """
            INSERT INTO files (parent_id, name, is_dir, size, cloud_type, remote_path, etag, status)
            VALUES (:parent_id, :name, :is_dir, :size, :cloud_type, :remote_path, :etag, 'stub')
            ON CONFLICT(cloud_type, remote_path) DO UPDATE SET
                parent_id = excluded.parent_id,
                name = excluded.name,
                size = excluded.size,
                etag = excluded.etag,
                is_dir = excluded.is_dir
            """,
            file_data,
        )
        await db.commit()

    async def _fts_delete_row(self, db, rowid: int) -> None:
        await db.execute(
            "INSERT INTO files_fts(files_fts, rowid) VALUES('delete', ?)",
            (rowid,),
        )

    async def _fts_insert_row(self, db, rowid: int, name: str) -> None:
        await db.execute("INSERT INTO files_fts(rowid, name) VALUES (?, ?)", (rowid, name))

    async def delete_subtree(self, root_id: int) -> None:
        db = await self.get_db()
        cur = await db.execute(
            """
            WITH RECURSIVE doomed AS (
                SELECT id FROM files WHERE id = ?
                UNION ALL
                SELECT f.id FROM files AS f
                INNER JOIN doomed AS d ON f.parent_id = d.id
            )
            SELECT id FROM doomed
            """,
            (root_id,),
        )
        ids = [r[0] for r in await cur.fetchall()]
        for rid in ids:
            await self._fts_delete_row(db, rid)
        if ids:
            q = "DELETE FROM files WHERE id IN (%s)" % ",".join("?" * len(ids))
            await db.execute(q, ids)
        await db.commit()

    async def insert_yandex_child(
        self,
        *,
        parent_id: int | None,
        name: str,
        is_dir: bool,
        remote_path: str,
        size: int = 0,
        status: str = "stub",
        etag: str = "",
        local_path: str | None = None,
    ) -> int:
        db = await self.get_db()
        cur = await db.execute(
            """
            INSERT INTO files (parent_id, name, is_dir, size, cloud_type, remote_path, etag, status, local_path)
            VALUES (?, ?, ?, ?, 'yandex', ?, ?, ?, ?)
            RETURNING id
            """,
            (
                parent_id,
                name,
                1 if is_dir else 0,
                size,
                remote_path,
                etag,
                status,
                local_path,
            ),
        )
        row = await cur.fetchone()
        rid = int(row[0])
        await self._fts_insert_row(db, rid, name)
        await db.commit()
        return rid

    async def delete_file_row_yandex(self, file_id: int) -> None:
        db = await self.get_db()
        await self._fts_delete_row(db, file_id)
        await db.execute("DELETE FROM files WHERE id = ?", (file_id,))
        await db.commit()

    _META_UNSET = object()

    async def update_yandex_entry_meta(
        self,
        file_id: int,
        *,
        name=_META_UNSET,
        parent_id=_META_UNSET,
        remote_path=_META_UNSET,
        size=_META_UNSET,
        etag=_META_UNSET,
        status=_META_UNSET,
        local_path=_META_UNSET,
    ) -> None:
        db = await self.get_db()
        parts = []
        vals: list = []
        if name is not self._META_UNSET:
            parts.append("name = ?")
            vals.append(name)
        if parent_id is not self._META_UNSET:
            parts.append("parent_id = ?")
            vals.append(parent_id)
        if remote_path is not self._META_UNSET:
            parts.append("remote_path = ?")
            vals.append(remote_path)
        if size is not self._META_UNSET:
            parts.append("size = ?")
            vals.append(size)
        if etag is not self._META_UNSET:
            parts.append("etag = ?")
            vals.append(etag)
        if status is not self._META_UNSET:
            parts.append("status = ?")
            vals.append(status)
        if local_path is not self._META_UNSET:
            parts.append("local_path = ?")
            vals.append(local_path)
        if not parts:
            return
        vals.append(file_id)
        await db.execute(
            f"UPDATE files SET {', '.join(parts)} WHERE id = ?",
            vals,
        )
        if name is not self._META_UNSET:
            await self._fts_delete_row(db, file_id)
            await self._fts_insert_row(db, file_id, name)
        await db.commit()

    async def yandex_update_descendant_remotes_after_dir_move(
        self, dir_id: int, old_root_remote: str, new_root_remote: str
    ) -> None:
        db = await self.get_db()
        old_p = old_root_remote.rstrip("/")
        new_p = new_root_remote.rstrip("/")
        cur = await db.execute(
            """
            WITH RECURSIVE sub AS (
                SELECT id, remote_path FROM files WHERE parent_id = ?
                UNION ALL
                SELECT f.id, f.remote_path FROM files f INNER JOIN sub ON f.parent_id = sub.id
            )
            SELECT id, remote_path FROM sub
            """,
            (dir_id,),
        )
        for rid, rp in await cur.fetchall():
            s = str(rp)
            if not s.startswith(old_p + "/"):
                continue
            suffix = s[len(old_p) :]
            nr = new_p + suffix
            await db.execute("UPDATE files SET remote_path = ? WHERE id = ?", (nr, rid))
        await db.commit()

    async def update_file_etag(self, file_id: int, etag: str) -> None:
        db = await self.get_db()
        await db.execute("UPDATE files SET etag = ? WHERE id = ?", (etag, file_id))
        await db.commit()

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
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT
                    COUNT(CASE WHEN is_dir = 0 THEN 1 END) AS total_files,
                    COUNT(CASE WHEN is_dir = 0 AND status = 'cached' THEN 1 END) AS cached_count,
                    COUNT(CASE WHEN is_dir = 0 AND status = 'syncing' THEN 1 END) AS syncing_count,
                    COUNT(CASE WHEN is_dir = 0 AND is_pinned = 1 THEN 1 END) AS pinned_count,
                    COALESCE(SUM(CASE WHEN status = 'cached' THEN size ELSE 0 END), 0) AS cache_size
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
