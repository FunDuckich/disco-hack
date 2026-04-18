#!/usr/bin/env bash
# Сборка PyInstaller-демона (Linux). Запускать из корня репозитория.
#
# Важно: только интерпретатор из .venv-build-daemon (python -m pip / -m PyInstaller).
# Иначе pip пишет в ~/.local («site-packages is not writeable»), в venv не попадает
# nc_py_api, а команда pyinstaller не находится — собирается старый сломанный onefile.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV="${ROOT}/.venv-build-daemon"
rm -rf "${VENV}"
python3 -m venv "${VENV}"

PY="${VENV}/bin/python"

# Не подмешивать ~/.local при сборке и при запуске PyInstaller из этого venv.
export PYTHONNOUSERSITE=1
unset PIP_USER

"${PY}" -m pip install --upgrade pip setuptools wheel

# PyPI: nc-py-api → import nc_py_api
"${PY}" -m pip install -r daemon/requirements-build.txt
"${PY}" -m pip install -r daemon/requirements.txt

# Проверка до PyInstaller: пакет реально в venv, не в user-site.
"${PY}" -c "import nc_py_api; print('nc_py_api OK:', nc_py_api.__file__)"

# Не пишем в dist/: Vite (npm run build / tauri build) очищает dist/ и удалил бы бинарь демона.
"${PY}" -m PyInstaller --clean -y \
  --distpath "${ROOT}/build/daemon-release" \
  --workpath "${ROOT}/build/daemon-work" \
  daemon/pyinstaller/cloudfusion-daemon.spec

echo "Готово: ${ROOT}/build/daemon-release/cloudfusion-daemon"
echo "Для RPM: см. scripts/build-cloudfusion-rpm.sh или packaging/rpm/README.md"
