import errno
import os
import pyfuse3
import pyfuse3.asyncio
import asyncio
import stat
import time


class CloudFusionVFS(pyfuse3.Operations):
    def __init__(self, db_manager, cloud_api):
        super().__init__()
        self.db = db_manager
        self.api = cloud_api
        # Простой кэш для перевода inode <-> path (в реальности берется из БД)
        self.inode_to_path = {pyfuse3.ROOT_INODE: "/"}
        self.next_inode = pyfuse3.ROOT_INODE + 1

    async def getattr(self, inode, ctx=None):
        """ОС спрашивает: 'Что это за файл и какие у него права?'"""
        path = self.inode_to_path.get(inode)
        if not path:
            raise pyfuse3.FUSEError(errno.ENOENT)  # Файл не найден

        # Идем в БД (асинхронно!), узнаем статус файла
        file_info = await self.db.get_info(path)

        entry = pyfuse3.EntryAttributes()
        if file_info['is_dir']:
            entry.st_mode = (stat.S_IFDIR | 0o755)
            entry.st_size = 0
        else:
            entry.st_mode = (stat.S_IFREG | 0o644)
            entry.st_size = file_info['size']

        # Обязательные поля для FUSE
        stamp = int(time.time() * 1e9)
        entry.st_atime_ns = stamp
        entry.st_ctime_ns = stamp
        entry.st_mtime_ns = stamp
        entry.st_gid = os.getgid()
        entry.st_uid = os.getuid()
        entry.st_ino = inode

        return entry

    async def lookup(self, parent_inode, name, ctx=None):
        """ОС ищет файл 'photo.jpg' внутри папки."""
        name_str = name.decode('utf-8')
        parent_path = self.inode_to_path.get(parent_inode)

        # Формируем полный путь и ищем в БД
        full_path = os.path.join(parent_path, name_str)
        file_info = await self.db.get_info(full_path)

        if not file_info:
            raise pyfuse3.FUSEError(errno.ENOENT)

        # Выделяем inode (или берем из БД, если храните их там)
        inode = self._get_or_create_inode(full_path)
        return await self.getattr(inode)

    async def opendir(self, inode, ctx):
        """Разрешение на чтение папки (возвращает хэндлер)."""
        return inode

    async def readdir(self, inode, off, token):
        """Отрисовка содержимого папки."""
        path = self.inode_to_path.get(inode)

        # Получаем список файлов из SQLite
        children = await self.db.get_children(path)

        for i, child_name in enumerate(children[off:], start=off):
            full_path = os.path.join(path, child_name)
            child_inode = self._get_or_create_inode(full_path)

            # Отдаем имя файла ядру Linux
            is_more = pyfuse3.readdir_reply(
                token,
                child_name.encode('utf-8'),
                await self.getattr(child_inode),
                i + 1
            )
            if not is_more:
                break

    async def open(self, inode, flags, ctx):
        """Срабатывает при попытке открыть файл."""
        path = self.inode_to_path.get(inode)
        file_info = await self.db.get_info(path)

        if file_info['status'] == 'cloud_only':
            # БЛОКИРУЕМ ОС: Ждем, пока скачается в ~/.cache/
            await self.api.download_file(file_info['remote_path'], file_info['local_path'])
            await self.db.update_status(path, 'cached')

        # Возвращаем хэндлер файла (временно отдаем inode)
        return pyfuse3.FileInfo(fh=inode)

    async def read(self, inode, off, size):
        """Чтение байтов из скачанного кэша."""
        path = self.inode_to_path.get(inode)
        file_info = await self.db.get_info(path)

        # Читаем реальный файл из локального кэша
        with open(file_info['local_path'], 'rb') as f:
            f.seek(off)
            return f.read(size)

    def _get_or_create_inode(self, path):
        """Вспомогательный метод (лучше реализовать через БД)."""
        for ino, p in self.inode_to_path.items():
            if p == path: return ino
        self.next_inode += 1
        self.inode_to_path[self.next_inode] = path
        return self.next_inode