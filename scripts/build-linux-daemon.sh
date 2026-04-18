#!/usr/bin/env bash
# Сборка PyInstaller-демона (Linux). Запускать из корня репозитория.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -m venv .venv-build-daemon
# shellcheck disable=SC1091
source .venv-build-daemon/bin/activate
pip install -r daemon/requirements-build.txt
# Не пишем в dist/: Vite (npm run build / tauri build) очищает dist/ и удалил бы бинарь демона.
pyinstaller --clean -y \
  --distpath "${ROOT}/build/daemon-release" \
  --workpath "${ROOT}/build/daemon-work" \
  daemon/pyinstaller/cloudfusion-daemon.spec
echo "Готово: ${ROOT}/build/daemon-release/cloudfusion-daemon"
echo "Для RPM: см. scripts/build-cloudfusion-rpm.sh или packaging/rpm/README.md"
