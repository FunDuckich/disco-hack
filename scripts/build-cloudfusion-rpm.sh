#!/usr/bin/env bash
# Полная подготовка SOURCES и сборка RPM CloudFusion из корня репозитория (Linux).
# Не ставит пакеты ОС — только то, что делается в РЕПО (PyInstaller, npm, Tauri, rpmbuild).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RPM_TOP="${RPMBUILD_TOPDIR:-$HOME/rpmbuild}"
SPEC="$ROOT/packaging/rpm/cloudfusion.spec"

usage() {
  echo "Использование: $0 [опции]" >&2
  echo "  --pull           git pull --ff-only в РЕПО (если есть .git), затем сборка" >&2
  echo "  --skip-npm       не вызывать npm install (если node_modules уже актуален)" >&2
  echo "  --only-sources   только SOURCES, без rpmbuild -ba" >&2
  echo "  -h, --help       эта справка" >&2
  echo "Переменные: RPMBUILD_TOPDIR (по умолчанию ~/rpmbuild)" >&2
}

SKIP_NPM=0
ONLY_SOURCES=0
DO_PULL=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull) DO_PULL=1 ;;
    --skip-npm) SKIP_NPM=1 ;;
    --only-sources) ONLY_SOURCES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Неизвестный аргумент: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Ошибка: не найдена команда «$1». Установите пакеты сборщика (см. packaging/rpm/README.md)." >&2
    exit 1
  fi
}

if [[ "$DO_PULL" -eq 1 ]]; then
  if [[ -d "$ROOT/.git" ]] && command -v git >/dev/null 2>&1; then
    echo "== git pull --ff-only =="
    (cd "$ROOT" && git pull --ff-only) || {
      echo "Ошибка: git pull --ff-only не удался (конфликт или нет сети)." >&2
      exit 1
    }
  else
    echo "Предупреждение: --pull пропущен (нет .git или git)." >&2
  fi
fi

echo "== CloudFusion: проверка инструментов =="
for c in git python3 node npm cargo rpmbuild; do
  need_cmd "$c"
done

if [[ ! -f "$SPEC" ]]; then
  echo "Ошибка: нет файла $SPEC" >&2
  exit 1
fi

if command -v dos2unix >/dev/null 2>&1; then
  dos2unix "$SPEC" 2>/dev/null || true
fi

if [[ ! -f daemon/.env ]]; then
  if [[ -f daemon/.env.example ]]; then
    cp daemon/.env.example daemon/.env
    echo "Создан daemon/.env из примера — заполните YANDEX_* перед запуском демона."
  else
    echo "Предупреждение: нет daemon/.env (и нет .env.example)." >&2
  fi
fi

# Порядок важен: Vite кладёт фронт в dist/ и может очистить каталог — демон собираем в build/daemon-release/ ПОСЛЕ tauri build.
if [[ "$SKIP_NPM" -eq 0 ]]; then
  echo "== 1/5 npm install =="
  (cd "$ROOT" && npm install)
else
  echo "== 1/5 npm install (пропуск --skip-npm) =="
fi

echo "== 2/5 Tauri release =="
(cd "$ROOT" && npm run tauri build)

DAEMON_BIN="${ROOT}/build/daemon-release/cloudfusion-daemon"
echo "== 3/5 PyInstaller: cloudfusion-daemon → ${DAEMON_BIN} =="
chmod +x "$ROOT/scripts/build-linux-daemon.sh"
"$ROOT/scripts/build-linux-daemon.sh"
test -f "$DAEMON_BIN" || { echo "Ошибка: нет ${DAEMON_BIN}" >&2; exit 1; }

GUI=""
if [[ -x "$ROOT/src-tauri/target/release/cloudfusion" ]]; then
  GUI="$ROOT/src-tauri/target/release/cloudfusion"
elif [[ -f "$ROOT/src-tauri/target/release/cloudfusion" ]]; then
  GUI="$ROOT/src-tauri/target/release/cloudfusion"
elif [[ -x "$ROOT/src-tauri/target/release/app" ]]; then
  GUI="$ROOT/src-tauri/target/release/app"
elif [[ -f "$ROOT/src-tauri/target/release/app" ]]; then
  GUI="$ROOT/src-tauri/target/release/app"
else
  echo "Ошибка: не найден бинарь в src-tauri/target/release/ (ожидались cloudfusion или app)." >&2
  exit 1
fi

echo "== 4/5 Копирование в $RPM_TOP/SOURCES =="
mkdir -p "$RPM_TOP"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
install -m0755 "$GUI" "$RPM_TOP/SOURCES/cloudfusion"
install -m0755 "$DAEMON_BIN" "$RPM_TOP/SOURCES/cloudfusion-daemon"
install -m0755 "$ROOT/integration/scripts/share_bridge.py" "$RPM_TOP/SOURCES/share_bridge.py"
install -m0644 "$ROOT/integration/desktop/cloudfusion-link.desktop" "$RPM_TOP/SOURCES/cloudfusion-link.desktop"
install -m0644 "$ROOT/integration/desktop/cloudfusion-app.desktop" "$RPM_TOP/SOURCES/cloudfusion-app.desktop"

echo "SOURCES:"
ls -la "$RPM_TOP/SOURCES/"

if [[ "$ONLY_SOURCES" -eq 1 ]]; then
  echo "Готово (--only-sources). Дальше вручную: rpmbuild -ba \"$SPEC\""
  exit 0
fi

echo "== 5/5 rpmbuild -ba =="
rpmbuild -ba --define "_topdir $RPM_TOP" "$SPEC"

echo "Готово. Пакет:"
find "$RPM_TOP/RPMS" -maxdepth 3 -name 'cloudfusion-*.rpm' -print 2>/dev/null || true
ls -la "$RPM_TOP/RPMS/x86_64/" 2>/dev/null || ls -la "$RPM_TOP/RPMS/" 2>/dev/null || true
