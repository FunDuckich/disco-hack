# -*- mode: python ; coding: utf-8 -*-
# Сборка из корня репозитория:
#   pip install -r daemon/requirements-build.txt
#   pyinstaller --clean -y daemon/pyinstaller/cloudfusion-daemon.spec
# Точка входа: daemon/pyinstaller/entry.py (абсолютные импорты; не daemon/__main__.py).
# Результат: build/daemon-release/cloudfusion-daemon (один файл; distpath задаётся в build-linux-daemon.sh).
from pathlib import Path

SPECDIR = Path(SPECPATH).resolve()
ROOT = SPECDIR.parents[1]

block_cipher = None

hiddenimports = [
    "aiofiles",
    "daemon",
    "daemon.main",
    "daemon.api",
    "daemon.api.routers",
    "daemon.api.routers.auth",
    "daemon.api.routers.files",
    "daemon.api.routers.sync",
    "daemon.api.routers.system",
    "multipart",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
]

try:
    from PyInstaller.utils.hooks import collect_submodules

    hiddenimports += collect_submodules("daemon")
    hiddenimports += collect_submodules("starlette")
    hiddenimports += collect_submodules("fastapi")
except Exception:
    pass

a = Analysis(
    [str(ROOT / "daemon" / "pyinstaller" / "entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="cloudfusion-daemon",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
