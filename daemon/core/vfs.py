import asyncio
import errno
import logging
import os
import shutil
import stat
import time

import pyfuse3
import pyfuse3.asyncio

from .yandex_folder_sync import folder_sync_after_readdir

log = logging.getLogger(__name__)

_WRITE_FH_BASE = 1 << 30


def _remote_child(parent_remote: str | None, name: str) -> str:
    pr = parent_remote if parent_remote is not None else "disk:/"
    p = pr.rstrip("/")
    if p == "disk:":
        return f"disk:/{name}"
    return f"{p}/{name}"


def _yandex_revision(meta) -> str:
    r = getattr(meta, "revision", None)
    return str(r) if r is not None else ""


def _invalidate_inode_async(inode: int) -> None:
    try:
        asyncio.get_running_loop().create_task(
            asyncio.to_thread(pyfuse3.invalidate_inode, inode, False)
        )
    except RuntimeError:
        pass


class CloudFusionVFS(pyfuse3.Operations):
    def __init__(self, db_manager, cloud_api):
        super().__init__()
        self.db_manager = db_manager
        self.cloud_api = cloud_api
        self.inode_2_dbid = {pyfuse3.ROOT_INODE: None}
        self.dbid_2_inode = {None: pyfuse3.ROOT_INODE}
        self.next_inode = pyfuse3.ROOT_INODE + 1
        self._next_write_fh = _WRITE_FH_BASE
        self._write_handles: dict[int, dict] = {}

    def _alloc_write_fh(self) -> int:
        self._next_write_fh += 1
        return self._next_write_fh

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
            entry.st_mode = stat.S_IFDIR | 0o755
            entry.st_size = 0
            return entry

        row = await self.db_manager.get_file_by_id(db_id)
        if not row:
            raise pyfuse3.FUSEError(errno.ENOENT)

        if row["is_dir"]:
            entry.st_mode = stat.S_IFDIR | 0o755
            entry.st_size = 0
        else:
            entry.st_mode = stat.S_IFREG | 0o644
            lp = row.get("local_path")
            if lp and os.path.isfile(lp):
                entry.st_size = os.path.getsize(lp)
            else:
                entry.st_size = row["size"]

        return entry

    async def access(self, inode, mode, ctx):
        return True

    async def statfs(self, ctx):
        s = pyfuse3.StatvfsData()
        s.f_bsize = 4096
        s.f_frsize = 4096
        s.f_blocks = 1 << 20
        s.f_bfree = 1 << 19
        s.f_bavail = 1 << 19
        s.f_files = 1 << 18
        s.f_ffree = 1 << 17
        s.f_favail = 1 << 17
        s.f_namemax = 255
        return s

    async def lookup(self, parent_inode, name, ctx=None):
        name_str = name.decode("utf-8")
        if name_str == ".":
            return await self.getattr(parent_inode)
        if name_str == "..":
            if parent_inode == pyfuse3.ROOT_INODE:
                return await self.getattr(pyfuse3.ROOT_INODE)
            parent_id = self.inode_2_dbid.get(parent_inode)
            if parent_id is None:
                return await self.getattr(pyfuse3.ROOT_INODE)
            row = await self.db_manager.get_file_by_id(parent_id)
            if not row:
                raise pyfuse3.FUSEError(errno.ENOENT)
            gp = row["parent_id"]
            if gp is None:
                return await self.getattr(pyfuse3.ROOT_INODE)
            ginode = self._get_inode(gp)
            return await self.getattr(ginode)

        parent_id = self.inode_2_dbid.get(parent_inode)

        db_id = await self.db_manager.lookup_file(parent_id, name_str)

        if not db_id:
            raise pyfuse3.FUSEError(errno.ENOENT)

        inode = self._get_inode(db_id)
        return await self.getattr(inode)

    async def opendir(self, inode, ctx):
        return inode

    async def readdir(self, inode, off, token):
        parent_db_id = self.inode_2_dbid.get(inode)
        log.debug("FUSE readdir inode=%s parent_db_id=%s", inode, parent_db_id)

        entries = await self.db_manager.get_readdir_entries(parent_db_id)

        for i, row in enumerate(entries[off:], start=off):
            child_inode = self._get_inode(row["id"])
            attr = pyfuse3.EntryAttributes()
            attr.st_ino = child_inode
            attr.st_mode = (stat.S_IFDIR | 0o755) if row["is_dir"] else (stat.S_IFREG | 0o644)

            if not pyfuse3.readdir_reply(token, row["name"].encode("utf-8"), attr, i + 1):
                break

        try:
            asyncio.get_running_loop().create_task(
                folder_sync_after_readdir(
                    self.db_manager,
                    self.cloud_api,
                    inode,
                    parent_db_id,
                )
            )
        except RuntimeError:
            log.warning("[sync] нет активного event loop — фоновая синхронизация пропущена")

    async def open(self, inode, flags, ctx):
        db_id = self.inode_2_dbid.get(inode)
        row = await self.db_manager.get_file_by_id(db_id)
        if not row:
            raise pyfuse3.FUSEError(errno.ENOENT)
        if row["is_dir"]:
            raise pyfuse3.FUSEError(errno.EISDIR)

        accmode = flags & os.O_ACCMODE
        if accmode == os.O_RDONLY:
            if row["status"] == "stub":
                log.info("FUSE: ленивая загрузка файла %s...", row["name"])
                cache_dir = os.path.expanduser("~/.cache/cloud-fusion/")
                os.makedirs(cache_dir, exist_ok=True)
                local_path = os.path.join(cache_dir, f"{db_id}_{row['name']}")

                await self.cloud_api.download(row["remote_path"], local_path)

                await self.db_manager.update_downloaded_file(db_id, local_path)

            return pyfuse3.FileInfo(fh=inode)

        if accmode in (os.O_WRONLY, os.O_RDWR):
            upload_dir = os.path.expanduser("~/.cache/cloud-fusion/uploads/")
            os.makedirs(upload_dir, exist_ok=True)
            temp = os.path.join(upload_dir, f"w-{db_id}-{os.getpid()}.part")

            if flags & os.O_TRUNC:
                open(temp, "wb").close()
            elif row.get("local_path") and os.path.isfile(row["local_path"]):
                shutil.copy2(row["local_path"], temp)
            elif row["status"] == "stub":
                await self.cloud_api.download(row["remote_path"], temp)
            else:
                open(temp, "wb").close()

            fh = self._alloc_write_fh()
            self._write_handles[fh] = {
                "inode": inode,
                "db_id": db_id,
                "temp": temp,
                "remote": row["remote_path"],
                "created": False,
                "dirty": bool(flags & os.O_TRUNC),
            }
            return pyfuse3.FileInfo(fh=fh)

        raise pyfuse3.FUSEError(errno.EINVAL)

    async def create(self, parent_inode, name, mode, flags, ctx):
        name_s = name.decode("utf-8")
        parent_id = self.inode_2_dbid.get(parent_inode)
        if parent_id is not None:
            prow = await self.db_manager.get_file_by_id(parent_id)
            if not prow or not prow["is_dir"]:
                raise pyfuse3.FUSEError(errno.ENOENT)
            rp_parent = prow["remote_path"]
        else:
            rp_parent = "disk:/"

        if await self.db_manager.lookup_file(parent_id, name_s):
            raise pyfuse3.FUSEError(errno.EEXIST)

        remote = _remote_child(rp_parent, name_s)
        upload_dir = os.path.expanduser("~/.cache/cloud-fusion/uploads/")
        os.makedirs(upload_dir, exist_ok=True)

        rid = await self.db_manager.insert_yandex_child(
            parent_id=parent_id,
            name=name_s,
            is_dir=False,
            remote_path=remote,
            size=0,
            status="uploading",
            etag="",
            local_path=None,
        )
        temp = os.path.join(upload_dir, f"new-{rid}.part")
        open(temp, "wb").close()
        await self.db_manager.update_yandex_entry_meta(rid, local_path=temp)

        inode = self._get_inode(rid)
        fh = self._alloc_write_fh()
        self._write_handles[fh] = {
            "inode": inode,
            "db_id": rid,
            "temp": temp,
            "remote": remote,
            "created": True,
            "dirty": True,
        }
        fi = pyfuse3.FileInfo(fh=fh)
        attr = await self.getattr(inode)
        return fi, attr

    async def read(self, fh, off, size):
        h = self._write_handles.get(fh)
        if h:
            temp = h["temp"]
            if not os.path.isfile(temp):
                raise pyfuse3.FUSEError(errno.EIO)
            try:
                with open(temp, "rb") as f:
                    f.seek(off)
                    return f.read(size)
            except OSError as e:
                log.error("FUSE read temp: %s", e)
                raise pyfuse3.FUSEError(errno.EIO) from e

        inode = fh
        db_id = self.inode_2_dbid.get(inode)
        row = await self.db_manager.get_file_by_id(db_id)

        local_path = row["local_path"]
        if not local_path or not os.path.exists(local_path):
            raise pyfuse3.FUSEError(errno.EIO)

        try:
            with open(local_path, "rb") as f:
                f.seek(off)
                return f.read(size)
        except OSError as e:
            log.error("FUSE read: %s", e)
            raise pyfuse3.FUSEError(errno.EIO) from e

    async def write(self, fh, off, buf):
        h = self._write_handles.get(fh)
        if not h:
            raise pyfuse3.FUSEError(errno.EBADF)
        try:
            with open(h["temp"], "r+b") as f:
                f.seek(off)
                f.write(buf)
            h["dirty"] = True
        except OSError as e:
            log.error("FUSE write: %s", e)
            raise pyfuse3.FUSEError(errno.EIO) from e
        return len(buf)

    async def release(self, fh):
        h = self._write_handles.pop(fh, None)
        if not h:
            return
        temp = h["temp"]
        try:
            if h.get("dirty") or h.get("created"):
                sz = os.path.getsize(temp) if os.path.isfile(temp) else 0
                await self.cloud_api.upload_local_file(temp, h["remote"])
                meta = await self.cloud_api.get_meta(h["remote"])
                rev = _yandex_revision(meta)
                cache_dir = os.path.expanduser("~/.cache/cloud-fusion/")
                os.makedirs(cache_dir, exist_ok=True)
                row = await self.db_manager.get_file_by_id(h["db_id"])
                base_name = row["name"] if row else os.path.basename(h["remote"])
                final = os.path.join(cache_dir, f"{h['db_id']}_{base_name}")
                if os.path.exists(final):
                    os.unlink(final)
                shutil.move(temp, final)
                await self.db_manager.update_yandex_entry_meta(
                    h["db_id"],
                    size=sz,
                    etag=rev,
                    status="cached",
                    local_path=final,
                )
            elif os.path.isfile(temp):
                os.unlink(temp)
        except Exception:
            log.exception("FUSE release / upload")
            if h.get("created"):
                try:
                    await self.db_manager.delete_file_row_yandex(h["db_id"])
                except Exception:
                    log.exception("FUSE rollback db")
            if os.path.isfile(temp):
                try:
                    os.unlink(temp)
                except OSError:
                    pass

    async def flush(self, fh):
        h = self._write_handles.get(fh)
        if not h:
            return
        try:
            with open(h["temp"], "r+b"):
                pass
        except OSError:
            pass

    async def setattr(self, inode, attr, fields, fh, ctx):
        if fields.update_size:
            size = int(attr.st_size)
            if fh is not None:
                h = self._write_handles.get(fh)
                if h:
                    with open(h["temp"], "r+b") as f:
                        f.truncate(size)
                    h["dirty"] = True
                    return await self.getattr(h["inode"])
            db_id = self.inode_2_dbid.get(inode)
            row = await self.db_manager.get_file_by_id(db_id)
            if not row or row["is_dir"]:
                raise pyfuse3.FUSEError(errno.EINVAL)
            lp = row.get("local_path")
            if lp and os.path.isfile(lp):
                with open(lp, "r+b") as f:
                    f.truncate(size)
                await self.db_manager.update_yandex_entry_meta(db_id, size=size)
            else:
                raise pyfuse3.FUSEError(errno.EINVAL)
            return await self.getattr(inode)
        return await self.getattr(inode)

    async def mkdir(self, parent_inode, name, mode, ctx):
        name_s = name.decode("utf-8")
        parent_id = self.inode_2_dbid.get(parent_inode)
        if parent_id is not None:
            prow = await self.db_manager.get_file_by_id(parent_id)
            if not prow or not prow["is_dir"]:
                raise pyfuse3.FUSEError(errno.ENOENT)
            rp_parent = prow["remote_path"]
        else:
            rp_parent = "disk:/"

        if await self.db_manager.lookup_file(parent_id, name_s):
            raise pyfuse3.FUSEError(errno.EEXIST)

        remote = _remote_child(rp_parent, name_s)
        await self.cloud_api.mkdir_remote(remote)
        meta = await self.cloud_api.get_meta(remote)
        rev = _yandex_revision(meta)

        rid = await self.db_manager.insert_yandex_child(
            parent_id=parent_id,
            name=name_s,
            is_dir=True,
            remote_path=remote,
            size=0,
            status="stub",
            etag=rev,
            local_path=None,
        )
        inode = self._get_inode(rid)
        _invalidate_inode_async(parent_inode)
        return await self.getattr(inode)

    async def unlink(self, parent_inode, name, ctx):
        name_s = name.decode("utf-8")
        parent_id = self.inode_2_dbid.get(parent_inode)
        fid = await self.db_manager.lookup_file(parent_id, name_s)
        if not fid:
            raise pyfuse3.FUSEError(errno.ENOENT)
        row = await self.db_manager.get_file_by_id(fid)
        if row["is_dir"]:
            raise pyfuse3.FUSEError(errno.EISDIR)
        await self.cloud_api.remove_remote(row["remote_path"])
        lp = row.get("local_path")
        if lp and os.path.isfile(lp):
            try:
                os.unlink(lp)
            except OSError:
                pass
        await self.db_manager.delete_file_row_yandex(fid)
        _invalidate_inode_async(parent_inode)

    async def rmdir(self, parent_inode, name, ctx):
        name_s = name.decode("utf-8")
        parent_id = self.inode_2_dbid.get(parent_inode)
        fid = await self.db_manager.lookup_file(parent_id, name_s)
        if not fid:
            raise pyfuse3.FUSEError(errno.ENOENT)
        row = await self.db_manager.get_file_by_id(fid)
        if not row["is_dir"]:
            raise pyfuse3.FUSEError(errno.ENOTDIR)
        kids = await self.db_manager.get_readdir_entries(fid)
        if kids:
            raise pyfuse3.FUSEError(errno.ENOTEMPTY)
        await self.cloud_api.remove_remote(row["remote_path"])
        await self.db_manager.delete_file_row_yandex(fid)
        _invalidate_inode_async(parent_inode)

    async def rename(self, parent_inode_old, name_old, parent_inode_new, name_new, flags, ctx):
        if flags & pyfuse3.RENAME_EXCHANGE:
            raise pyfuse3.FUSEError(errno.EINVAL)

        name_old_s = name_old.decode("utf-8")
        name_new_s = name_new.decode("utf-8")
        pid_old = self.inode_2_dbid.get(parent_inode_old)
        pid_new = self.inode_2_dbid.get(parent_inode_new)

        old_id = await self.db_manager.lookup_file(pid_old, name_old_s)
        if not old_id:
            raise pyfuse3.FUSEError(errno.ENOENT)

        exist_new = await self.db_manager.lookup_file(pid_new, name_new_s)
        if exist_new and (flags & pyfuse3.RENAME_NOREPLACE):
            raise pyfuse3.FUSEError(errno.EEXIST)

        if pid_new is not None:
            pnew = await self.db_manager.get_file_by_id(pid_new)
            if not pnew or not pnew["is_dir"]:
                raise pyfuse3.FUSEError(errno.ENOENT)
            rp_new_parent = pnew["remote_path"]
        else:
            rp_new_parent = "disk:/"

        new_remote = _remote_child(rp_new_parent, name_new_s)

        old_row = await self.db_manager.get_file_by_id(old_id)
        old_remote = old_row["remote_path"]

        if exist_new:
            await self.db_manager.delete_subtree(exist_new)

        await self.cloud_api.move_remote(old_remote, new_remote, overwrite=True)

        if old_row["is_dir"]:
            await self.db_manager.update_yandex_entry_meta(
                old_id,
                parent_id=pid_new,
                name=name_new_s,
                remote_path=new_remote,
            )
            await self.db_manager.yandex_update_descendant_remotes_after_dir_move(
                old_id, old_remote, new_remote
            )
        else:
            await self.db_manager.update_yandex_entry_meta(
                old_id,
                parent_id=pid_new,
                name=name_new_s,
                remote_path=new_remote,
            )

        _invalidate_inode_async(parent_inode_old)
        if parent_inode_new != parent_inode_old:
            _invalidate_inode_async(parent_inode_new)
