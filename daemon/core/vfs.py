import os
import stat
import errno
import pyfuse3
import pyfuse3.asyncio
import time
import logging

log = logging.getLogger(__name__)


class CloudFusionVFS(pyfuse3.Operations):
    def __init__(self, db_manager, cloud_api):
        super().__init__()
        self.db_manager = db_manager
        self.cloud_api = cloud_api
        self.inode_2_dbid = {pyfuse3.ROOT_INODE: None}
        self.dbid_2_inode = {None: pyfuse3.ROOT_INODE}
        self.next_inode = pyfuse3.ROOT_INODE + 1

    def _get_inode(self, db_id: int) -> int:
        if db_id not in self.dbid_2_inode:
            self.dbid_2_inode[db_id] = self.next_inode
            self.inode_2_dbid[self.next_inode] = db_id
            self.next_inode += 1
        return self.dbid_2_inode[db_id]

    async def getattr(self, inode, ctx=None):
        db_id = self.inode_2_dbid.get(inode)
        entry = pyfuse3.EntryAttributes()

        stamp = int(time.time() * 1e9)
        entry.st_atime_ns = stamp
        entry.st_ctime_ns = stamp
        entry.st_mtime_ns = stamp
        entry.st_gid = os.getgid()
        entry.st_uid = os.getuid()
        entry.st_ino = inode

        if db_id is None:
            entry.st_mode = (stat.S_IFDIR | 0o755)
            entry.st_size = 0
            return entry

        row = await self.db_manager.get_file_by_id(db_id)
        if not row:
            raise pyfuse3.FUSEError(errno.ENOENT)

        if row['is_dir']:
            entry.st_mode = (stat.S_IFDIR | 0o755)
            entry.st_size = 0
        else:
            entry.st_mode = (stat.S_IFREG | 0o644)
            entry.st_size = row['size']

        return entry

    async def lookup(self, parent_inode, name, ctx=None):
        name_str = name.decode('utf-8')
        parent_id = self.inode_2_dbid.get(parent_inode)

        db_id = await self.db_manager.lookup_file(parent_id, name_str)

        if not db_id:
            raise pyfuse3.FUSEError(errno.ENOENT)

        inode = self._get_inode(db_id)
        return await self.getattr(inode)

    async def opendir(self, inode, ctx):
        return inode

    async def readdir(self, inode, off, token):
        parent_id = self.inode_2_dbid.get(inode)

        children = await self.db_manager.get_readdir_entries(parent_id)

        for i, row in enumerate(children[off:], start=off):
            child_inode = self._get_inode(row['id'])
            attr = await self.getattr(child_inode)

            is_more = pyfuse3.readdir_reply(
                token,
                row['name'].encode('utf-8'),
                attr,
                i + 1
            )
            if not is_more:
                break

    async def open(self, inode, flags, ctx):
        db_id = self.inode_2_dbid.get(inode)
        row = await self.db_manager.get_file_by_id(db_id)

        if not row:
            raise pyfuse3.FUSEError(errno.ENOENT)

        if row['status'] == 'stub':
            log.info(f"FUSE: Ленивая загрузка файла {row['name']}...")
            cache_dir = os.path.expanduser("~/.cache/disco-hack/")
            os.makedirs(cache_dir, exist_ok=True)
            local_path = os.path.join(cache_dir, f"{db_id}_{row['name']}")

            await self.cloud_api.download(row['remote_path'], local_path)

            await self.db_manager.update_downloaded_file(db_id, local_path)

            log.info(f"FUSE: Файл {row['name']} скачан в кэш!")

        return pyfuse3.FileInfo(fh=inode)

    async def read(self, inode, off, size):
        db_id = self.inode_2_dbid.get(inode)
        row = await self.db_manager.get_file_by_id(db_id)

        local_path = row['local_path']
        if not local_path or not os.path.exists(local_path):
            raise pyfuse3.FUSEError(errno.EIO)

        try:
            with open(local_path, 'rb') as f:
                f.seek(off)
                return f.read(size)
        except Exception as e:
            log.error(f"FUSE Read Error: {e}")
            raise pyfuse3.FUSEError(errno.EIO)
