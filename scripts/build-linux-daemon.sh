#!/usr/bin/env bash
# Сборка PyInstaller-демона (Linux). Запускать из корня репозитория.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -m venv .venv-build-daemon
# shellcheck disable=SC1091
source .venv-build-daemon/bin/activate
pip install -r daemon/requirements-build.txt
pyinstaller --clean -y daemon/pyinstaller/cloudfusion-daemon.spec
echo "Готово: ${ROOT}/dist/cloudfusion-daemon"
echo "Для RPM: cp dist/cloudfusion-daemon packaging/rpm/SOURCES/ (или см. packaging/rpm/README.md)"
