#!/usr/bin/env bash
# Сборка «всё вместе» без RPM: release GUI + cloudfusion-daemon в одном каталоге.
# Запускать из корня репозитория (Linux).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKIP_NPM=0
for arg in "$@"; do
  case "$arg" in
    --skip-npm) SKIP_NPM=1 ;;
    -h|--help)
      echo "Usage: $0 [--skip-npm]"
      echo "  Собирает Vite+Tauri release, PyInstaller-демон и кладёт cloudfusion-daemon"
      echo "  рядом с бинарём GUI (как ожидает src-tauri/src/lib.rs)."
      exit 0
      ;;
  esac
done

if [[ "$SKIP_NPM" -eq 0 ]]; then
  echo "== npm install =="
  npm install
else
  echo "== npm install (пропуск --skip-npm) =="
fi

echo "== PyInstaller: cloudfusion-daemon =="
chmod +x "$ROOT/scripts/build-linux-daemon.sh"
"$ROOT/scripts/build-linux-daemon.sh"

DAEMON_BIN="${ROOT}/build/daemon-release/cloudfusion-daemon"
test -f "$DAEMON_BIN" || { echo "Ошибка: нет $DAEMON_BIN" >&2; exit 1; }

echo "== Tauri release =="
npm run tauri build

GUI=""
REL="$ROOT/src-tauri/target/release"
if [[ -x "$REL/cloudfusion" ]]; then
  GUI="$REL/cloudfusion"
elif [[ -f "$REL/cloudfusion" ]]; then
  GUI="$REL/cloudfusion"
elif [[ -x "$REL/app" ]]; then
  GUI="$REL/app"
elif [[ -f "$REL/app" ]]; then
  GUI="$REL/app"
else
  echo "Ошибка: не найден бинарь в $REL (ожидались cloudfusion или app)." >&2
  exit 1
fi

GUI_DIR="$(dirname "$GUI")"
install -m0755 "$DAEMON_BIN" "$GUI_DIR/cloudfusion-daemon"

echo ""
echo "Готово. Запуск без установки пакетов:"
echo "  $GUI"
echo ""
echo "Перед запуском задайте ~/.config/cloudfusion/.env или экспорт (YANDEX_* или CLOUDFUSION_MOCK_YANDEX=1)."
echo "Логи демона в том же терминале, если stderr не перенаправлен."
echo "Подробнее: docs/LOCAL-BUNDLE.md"
