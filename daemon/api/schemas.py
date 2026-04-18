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
    cache_size: int
    pinned_count: int

class PinResponse(BaseModel):
    status: str