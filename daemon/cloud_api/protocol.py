"""Единый async-контракт драйвера облака для FUSE, mount и синхронизации."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CloudStorageDriver(Protocol):
    """Минимальный набор операций, совпадающий по смыслу с YandexDiskAsyncClient."""

    async def download(self, remote_path: str, local_path: str) -> None:
        """Скачать файл с облака на локальный путь."""

    async def upload_local_file(self, local_path: str, remote_path: str) -> None:
        """Загрузить локальный файл в облако (перезапись по политике клиента)."""

    async def remove_remote(self, remote_path: str) -> None:
        """Удалить файл или пустую папку на стороне облака."""

    async def mkdir_remote(self, remote_path: str) -> None:
        """Создать каталог (один уровень — как у текущего Yandex-пайплайна)."""

    async def move_remote(self, src_path: str, dst_path: str, *, overwrite: bool = True) -> None:
        """Переименовать / переместить объект."""

    async def listdir_metadata(self, remote_path: str) -> list[dict]:
        """
        Список прямых детей; каждый dict: path, type ('dir'|'file'), name, size, revision (или md5).
        Поле path — в формате БД (disk:… / nextcloud:…).
        """

    async def get_meta(self, remote_path: str) -> Any:
        """Метаданные объекта (revision/etag — см. вызывающий код)."""

    async def get_all_files_flat(self) -> list:
        """Плоский рекурсивный индекс для фонового импорта."""
