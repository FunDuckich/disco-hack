"""Яндекс.Диск как CloudStorageDriver — поведение идентично YandexDiskAsyncClient."""

from __future__ import annotations

from .protocol import CloudStorageDriver
from .yandex import YandexDiskAsyncClient


def yandex_as_driver(client: YandexDiskAsyncClient) -> CloudStorageDriver:
    """Структурная совместимость с протоколом; возвращается тот же экземпляр."""
    return client
