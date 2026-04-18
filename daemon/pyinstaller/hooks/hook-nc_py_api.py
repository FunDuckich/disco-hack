# PyInstaller: пакет nc-py-api часто не подхватывается анализатором целиком (niquests, подмодули).
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("nc_py_api")
