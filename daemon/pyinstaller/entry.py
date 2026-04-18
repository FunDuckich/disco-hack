"""
Точка входа только для PyInstaller (один файл / onedir).
Абсолютные импорты — у скрипта нет родительского пакета, в отличие от `python -m daemon`.
"""
from __future__ import annotations

import uvicorn

from daemon.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
