from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FileItem(BaseModel):
    id: int
    parent_id: int | None
    name: str
    size: int
    is_dir: bool
    cloud_type: str | None
    remote_path: str | None
    local_path: str | None
    etag: str | None
    status: Literal["stub", "cached", "syncing"]
    is_pinned: bool
    last_accessed: datetime


class SearchResult(BaseModel):
    id: int
    name: str
    remote_path: str | None
    cloud_type: str | None
    status: Literal["stub", "cached", "syncing"]
    size: int

class StatsResponse(BaseModel):
    total_files: int
    cached_count: int
    syncing_count: int
    pinned_count: int
    cache_size: int
    max_size: int
    indexed_bytes: int = 0
    # Поля для дашборда (исторически ожидал фронт)
    used_space: int = 0
    total_space: int = 0
    used_cache_size: int = 0
    total_files_count: int = 0
    cached_files_count: int = 0

class PinResponse(BaseModel):
    status: str


class AuthStatusResponse(BaseModel):
    """connected — как раньше: только Яндекс (обратная совместимость)."""
    connected: bool
    providers: dict[str, bool]


class SyncResponse(BaseModel):
    status: str


class PathSegment(BaseModel):
    id: int
    name: str


class SettingsResponse(BaseModel):
    max_cache_gb: float


class SettingsUpdate(BaseModel):
    max_cache_gb: float