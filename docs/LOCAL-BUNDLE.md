# Сборка и запуск без RPM (всё в одном каталоге)

Один скрипт собирает **фронт**, **Tauri release** и **PyInstaller-демон**, затем кладёт `cloudfusion-daemon` **в ту же папку**, что и бинарь GUI (`src-tauri/target/release/`). Так работает поиск sidecar в `src-tauri/src/lib.rs` (рядом с `current_exe`).

## Требования

- Linux, **Node/npm**, **Rust/cargo**, зависимости Tauri (GTK, WebKit — как для обычной сборки).
- **Python 3** для скрипта демона (создаётся `.venv-build-daemon` в корне репо).

## Сборка

Из **корня репозитория**:

```bash
chmod +x scripts/build-local-bundle.sh
./scripts/build-local-bundle.sh
```

Пропуск `npm install` (если зависимости уже стоят):

```bash
./scripts/build-local-bundle.sh --skip-npm
```

Эквивалент через npm:

```bash
npm run linux:bundle
```

Результат:

- GUI: `src-tauri/target/release/app` или `src-tauri/target/release/cloudfusion` (имя зависит от конфигурации Cargo/Tauri).
- Демон: `src-tauri/target/release/cloudfusion-daemon` (копия из `build/daemon-release/`).

## Запуск

```bash
# пример, подставьте реальное имя бинаря из target/release/
./src-tauri/target/release/app
```

Рекомендуемые переменные для ВМ / без DMA-BUF (как в `.desktop`):

```bash
env LIBGL_ALWAYS_SOFTWARE=1 WEBKIT_DISABLE_DMABUF_RENDERER=1 GDK_BACKEND=x11 \
  ./src-tauri/target/release/app
```

Конфиг демона: **`~/.config/cloudfusion/.env`** (см. `daemon/.env.example`) или экспорт в сеансе. Собранный **`cloudfusion-daemon`** без **`YANDEX_*`** сам поднимется в **mock**-режиме (сообщение в stderr); из исходников **`python -m daemon`** без ключей по-прежнему нужен **`CLOUDFUSION_MOCK_YANDEX=1`** или `.env`.

Проверка API после старта окна:

```bash
curl -sS http://127.0.0.1:8000/health
```

## Только демон из исходников (без PyInstaller)

Из корня репо, с установленными зависимостями `daemon/requirements.txt`:

```bash
cd /путь/к/disco-hack
python3 -m venv .venv
source .venv/bin/activate
pip install -r daemon/requirements.txt
# скопируйте daemon/.env.example → daemon/.env и заполните
python3 -m daemon.main
```

В другом терминале — GUI из **debug** (Vite на порту 1420):

```bash
# один раз: положите демон рядом с debug-бинарём ИЛИ укажите путь:
export CLOUDFUSION_DAEMON_BIN="$PWD/build/daemon-release/cloudfusion-daemon"
npm run tauri dev
```

Либо поднимите только `python3 -m daemon.main` и откройте dev URL в браузере, если нужен только API.

## Альтернатива: tar из `build-rpm.sh --tarball`

Собирает корень файловой системы под `/usr/...` — установка **`sudo tar -xzf … -C /`** по сути как пакет. Для «без установки в систему» удобнее **`build-local-bundle.sh`**.
