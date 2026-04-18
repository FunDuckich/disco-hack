import os

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    cache_dir: str = "~/.cache/cloud-fusion/"
    max_cache_gb: int = 5
    mountpoint: str = "~/CloudFusion"
    db_path: str = "cloudfusion.db"
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
    try:
        return Settings(
            cache_dir=os.getenv("CACHE_DIR", "~/.cache/cloud-fusion/"),
            max_cache_gb=int(os.getenv("MAX_CACHE_GB", "5")),
            mountpoint=os.getenv("MOUNTPOINT", "~/CloudFusion"),
            db_path=os.getenv("DB_PATH", "cloudfusion.db"),
            enable_fuse=_env_bool("ENABLE_FUSE", False),
            yandex_client_id=os.environ["YANDEX_CLIENT_ID"],
            yandex_client_secret=os.environ["YANDEX_CLIENT_SECRET"],
            yandex_redirect_uri=os.getenv("YANDEX_REDIRECT_URI", "http://localhost:8000/callback"),
        )
    except KeyError as e:
        raise RuntimeError(
            f"Missing required environment variable: {e.args[0]}. "
            f"See daemon/.env.example for the full list."
        ) from e


settings = _load()