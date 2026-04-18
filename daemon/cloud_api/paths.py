"""Общая нормализация путей для разных облаков (disk:, nextcloud:)."""

from __future__ import annotations


def strip_cloud_scheme(remote_path: str, cloud_type: str | None = None) -> str:
    """Убирает известный префикс схемы, оставляя путь как в WebDAV/Диске (часто с ведущим /)."""
    p = (remote_path or "").strip()
    if cloud_type == "nextcloud" or (cloud_type is None and p.startswith("nextcloud:")):
        p = p.removeprefix("nextcloud:")
    elif cloud_type == "yandex" or (cloud_type is None and p.startswith("disk:")):
        p = p.removeprefix("disk:")
    else:
        if p.startswith("nextcloud:"):
            p = p.removeprefix("nextcloud:")
        elif p.startswith("disk:"):
            p = p.removeprefix("disk:")
    return p.replace("\\", "/")


def normalize_importer_tree_key(remote_path: str, cloud_type: str) -> str:
    """
    Ключ дерева для импорта в SQLite: абсолютный путь без схемы, с ведущим /,
    без завершающего / (кроме корня «/» → пустая строка не используется — корень в path_to_id через seed "").
    """
    p = strip_cloud_scheme(remote_path, cloud_type).rstrip("/")
    if not p.startswith("/"):
        p = "/" + p if p else "/"
    if p == "/":
        return ""
    return p


def remote_child(parent_remote: str | None, name: str, cloud_type: str) -> str:
    """Собирает remote_path дочернего объекта (с префиксом схемы), как в БД."""
    if cloud_type == "nextcloud":
        pr = parent_remote if parent_remote is not None else "nextcloud:/"
        p = pr.rstrip("/")
        if p == "nextcloud:":
            return f"nextcloud:/{name}"
        return f"{p}/{name}"
    if cloud_type == "yandex":
        pr = parent_remote if parent_remote is not None else "disk:/"
        p = pr.rstrip("/")
        if p == "disk:":
            return f"disk:/{name}"
        return f"{p}/{name}"
    raise ValueError(f"unsupported cloud_type: {cloud_type}")
