#!/usr/bin/env bash
# Полная подготовка SOURCES и сборка RPM CloudFusion из корня репозитория (Linux).
# Spec для rpmbuild генерируется здесь же (ASCII + LF), не из git — меньше сбоев на ALT.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RPM_TOP="${RPMBUILD_TOPDIR:-$HOME/rpmbuild}"
SPEC="$ROOT/packaging/rpm/cloudfusion.spec"

usage() {
  echo "Использование: $0 [опции]" >&2
  echo "  --pull           git pull --ff-only в РЕПО (если есть .git), затем сборка" >&2
  echo "  --skip-npm       не вызывать npm install (если node_modules уже актуален)" >&2
  echo "  --only-sources   только SOURCES + spec в SPECS, без rpmbuild" >&2
  echo "  --tarball        без rpmbuild: архив build/cloudfusion-VERSION-linux-x86_64.tar.gz" >&2
  echo "  -h, --help       эта справка" >&2
  echo "Переменные: RPMBUILD_TOPDIR (по умолчанию ~/rpmbuild)" >&2
}

SKIP_NPM=0
ONLY_SOURCES=0
DO_PULL=0
TARBALL_ONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull) DO_PULL=1 ;;
    --skip-npm) SKIP_NPM=1 ;;
    --only-sources) ONLY_SOURCES=1 ;;
    --tarball) TARBALL_ONLY=1 ;;
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
for c in git python3 node npm cargo; do
  need_cmd "$c"
done
if [[ "$TARBALL_ONLY" -eq 0 ]]; then
  need_cmd rpmbuild
fi

if [[ ! -f "$SPEC" ]]; then
  echo "Предупреждение: нет $SPEC (справочно в репозитории)." >&2
fi

write_embedded_spec() {
  local dest="$RPM_TOP/SPECS/cloudfusion.spec"
  mkdir -p "$RPM_TOP/SPECS"
  python3 - "$ROOT" "$dest" <<'PY'
import datetime, json, pathlib, sys

root, dest = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
cfg = json.loads((root / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
version = str(cfg.get("version", "0.1.0")).strip()
try:
    import locale as _loc

    _loc.setlocale(_loc.LC_TIME, "C")
except Exception:
    pass
d = datetime.date.today()
cl_head = d.strftime("* %a %b %d %Y") + " CloudFusion Packaging <packaging@local> - " + version + "-1"

# Только .replace — без str.format, чтобы % из RPM-макросов не ломали разбор.
SPEC_TEMPLATE = r"""%global debug_package %{nil}

Name:           cloudfusion
Version:        __VERSION__
Release:        1%{?dist}
Summary:        CloudFusion desktop and Dolphin integration
License:        MIT
URL:            https://github.com/FunDuckich/disco-hack
Source0:        cloudfusion
Source1:        cloudfusion-daemon
Source2:        share_bridge.py
Source3:        cloudfusion-link.desktop
Source4:        cloudfusion-app.desktop

BuildArch:      x86_64

Requires:       fuse3

%description
CloudFusion: FastAPI sidecar (PyInstaller), Tauri UI, Dolphin service menu for public links.

%prep
# Binary-only; sources already in SOURCES.

%build
# Pre-built.

%install
install -d %{buildroot}%{_bindir}
install -d %{buildroot}%{_libexecdir}/cloudfusion
install -d %{buildroot}%{_datadir}/applications
install -d %{buildroot}%{_datadir}/kio/servicemenus

install -m0755 %{SOURCE0} %{buildroot}%{_bindir}/cloudfusion
install -m0755 %{SOURCE1} %{buildroot}%{_libexecdir}/cloudfusion/cloudfusion-daemon
install -m0755 %{SOURCE2} %{buildroot}%{_libexecdir}/cloudfusion/share_bridge.py

sed 's|REPLACE_CF_SHARE_BRIDGE|%{_libexecdir}/cloudfusion/share_bridge.py|' %{SOURCE3} > %{buildroot}%{_datadir}/kio/servicemenus/cloudfusion-link.desktop
chmod 0644 %{buildroot}%{_datadir}/kio/servicemenus/cloudfusion-link.desktop

install -m0644 %{SOURCE4} %{buildroot}%{_datadir}/applications/cloudfusion-app.desktop

%post
echo "CloudFusion installed. Restart Dolphin for KIO (kquitapp5 dolphin && dolphin)."

%files
%{_bindir}/cloudfusion
%{_libexecdir}/cloudfusion/cloudfusion-daemon
%{_libexecdir}/cloudfusion/share_bridge.py
%{_datadir}/kio/servicemenus/cloudfusion-link.desktop
%{_datadir}/applications/cloudfusion-app.desktop

%changelog
__CHANGELOG_HEAD__
- Built by scripts/build-cloudfusion-rpm.sh (embedded spec).
"""
spec = SPEC_TEMPLATE.replace("__VERSION__", version).replace("__CHANGELOG_HEAD__", cl_head)
if not spec.endswith("\n"):
    spec += "\n"
dest.write_text(spec, encoding="ascii", newline="\n")
PY
  echo "Spec для rpmbuild (встроенный): $dest"
}

build_rootfs_tarball() {
  local ver="$1"
  local staging="$ROOT/build/rootfs-staging"
  local out="$ROOT/build/cloudfusion-${ver}-linux-x86_64.tar.gz"
  rm -rf "$staging"
  mkdir -p "$staging/usr/bin" "$staging/usr/libexec/cloudfusion" \
    "$staging/usr/share/applications" "$staging/usr/share/kio/servicemenus"
  install -m0755 "$GUI" "$staging/usr/bin/cloudfusion"
  install -m0755 "$DAEMON_BIN" "$staging/usr/libexec/cloudfusion/cloudfusion-daemon"
  install -m0755 "$ROOT/integration/scripts/share_bridge.py" "$staging/usr/libexec/cloudfusion/share_bridge.py"
  sed "s|REPLACE_CF_SHARE_BRIDGE|/usr/libexec/cloudfusion/share_bridge.py|" \
    "$ROOT/integration/desktop/cloudfusion-link.desktop" \
    >"$staging/usr/share/kio/servicemenus/cloudfusion-link.desktop"
  chmod 0644 "$staging/usr/share/kio/servicemenus/cloudfusion-link.desktop"
  install -m0644 "$ROOT/integration/desktop/cloudfusion-app.desktop" "$staging/usr/share/applications/cloudfusion-app.desktop"
  mkdir -p "$ROOT/build"
  (cd "$staging" && tar czvf "$out" .)
  echo "Готово (без RPM): $out"
  echo "Установка: sudo tar -xzf $out -C /"
}

if [[ ! -f daemon/.env ]]; then
  if [[ -f daemon/.env.example ]]; then
    cp daemon/.env.example daemon/.env
    echo "Создан daemon/.env из примера — заполните YANDEX_* перед запуском демона."
  else
    echo "Предупреждение: нет daemon/.env (и нет .env.example)." >&2
  fi
fi

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

CF_VERSION="$(python3 -c "import json;print(json.load(open('src-tauri/tauri.conf.json'))['version'])")"

if [[ "$TARBALL_ONLY" -eq 1 ]]; then
  echo "== Режим --tarball (без rpmbuild) =="
  build_rootfs_tarball "$CF_VERSION"
  exit 0
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

write_embedded_spec

if [[ "$ONLY_SOURCES" -eq 1 ]]; then
  echo "Готово (--only-sources). Дальше из $RPM_TOP:"
  echo "  cd \"$RPM_TOP\" && LC_ALL=C rpmbuild -ba --define \"_topdir $RPM_TOP\" SPECS/cloudfusion.spec"
  exit 0
fi

echo "== 5/5 rpmbuild -ba =="
set +e
( cd "$RPM_TOP" && LC_ALL=C LANG=C rpmbuild -ba --define "_topdir ${RPM_TOP}" SPECS/cloudfusion.spec )
RPM_RC=$?
set -e
if [[ "$RPM_RC" -ne 0 ]]; then
  echo "rpmbuild завершился с кодом $RPM_RC — собираю tar.gz как запасной вариант." >&2
  build_rootfs_tarball "$CF_VERSION"
  exit "$RPM_RC"
fi

echo "Готово. Пакет:"
find "$RPM_TOP/RPMS" -maxdepth 3 -name 'cloudfusion-*.rpm' -print 2>/dev/null || true
ls -la "$RPM_TOP/RPMS/x86_64/" 2>/dev/null || ls -la "$RPM_TOP/RPMS/" 2>/dev/null || true
