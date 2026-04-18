import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


def load_dotenv_layers() -> None:
    """Подхватываем .env из cwd, рядом с бинарём (PyInstaller) и из ~/.config (установленный RPM)."""
    load_dotenv()
    if getattr(sys, "frozen", False):
        beside = Path(sys.executable).resolve().parent / ".env"
        if beside.is_file():
            load_dotenv(beside, override=True)
    cfg = Path.home() / ".config" / "cloudfusion" / ".env"
    if cfg.is_file():
        load_dotenv(cfg, override=True)
    etc = Path("/etc/cloudfusion.env")
    if etc.is_file():
        load_dotenv(etc, override=True)


load_dotenv_layers()


def default_db_path() -> str:
    """Absolute SQLite path under XDG_DATA_HOME (stable for PyInstaller / sidecar)."""
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    base = xdg if xdg else os.path.expanduser("~/.local/share")
    return os.path.join(base, "cloudfusion", "cloudfusion.db")


class Settings(BaseModel):
    cache_dir: str = "~/.cache/cloud-fusion/"
    max_cache_gb: int = 5
    mountpoint: str = "~/CloudFusion"
    db_path: str
    enable_fuse: bool = False
    yandex_client_id: str
    yandex_client_secret: str
    yandex_redirect_uri: str = "http://localhost:8000/callback"


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _load() -> Settings:
    mock = _env_bool("CLOUDFUSION_MOCK_YANDEX", False)
    yid = os.getenv("YANDEX_CLIENT_ID")
    ysec = os.getenv("YANDEX_CLIENT_SECRET")
    if mock:
        yid = yid or "mock-client-id"
        ysec = ysec or "mock-client-secret"
    elif not yid or not ysec:
        raise RuntimeError(
            "Missing YANDEX_CLIENT_ID / YANDEX_CLIENT_SECRET. "
            "Put them in ~/.config/cloudfusion/.env (see daemon/.env.example) "
            "or export before starting cloudfusion; for UI-only dev use CLOUDFUSION_MOCK_YANDEX=1."
        )
    try:
        return Settings(
            cache_dir=os.getenv("CACHE_DIR", "~/.cache/cloud-fusion/"),
            max_cache_gb=int(os.getenv("MAX_CACHE_GB", "5")),
            mountpoint=os.getenv("MOUNTPOINT", "~/CloudFusion"),
            db_path=os.getenv("DB_PATH") or default_db_path(),
            enable_fuse=_env_bool("ENABLE_FUSE", False),
            yandex_client_id=yid,
            yandex_client_secret=ysec,
            yandex_redirect_uri=os.getenv("YANDEX_REDIRECT_URI", "http://localhost:8000/callback"),
        )
    except Exception as e:
        raise RuntimeError(f"Invalid configuration: {e}") from e


settings = _load()