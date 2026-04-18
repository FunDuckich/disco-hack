# CloudFusion: сборка и установка **только через RPM**

**РЕПО** — корень клона `disco-hack`. Все команды сборки — **из РЕПО** (`cd` в каталог репозитория).

---

## Два способа

| Способ | Когда |
|--------|--------|
| **[`build-rpm.sh`](../../build-rpm.sh)** (корень РЕПО) или **[`scripts/build-cloudfusion-rpm.sh`](../../scripts/build-cloudfusion-rpm.sh)** | Обычный случай: одна команда после установки пакетов ОС. |
| **Шаги 1–8 ниже** | Нужен контроль каждого шага, отладка или нестандартный `_topdir`. |

---

## Быстрый путь: один скрипт

**Перед первым запуском** установите зависимости сборщика — см. раздел **«Пакеты на машине сборщика»** ниже в этом файле.

Запуск из **РЕПО** (оба варианта эквивалентны):

```bash
./build-rpm.sh
```

```bash
./scripts/build-cloudfusion-rpm.sh
```

Если скрипта ещё нет (старый клон): **`git pull`**, затем при отказе в доступе: **`chmod +x build-rpm.sh scripts/build-cloudfusion-rpm.sh`**.

Обновить код и собрать за один проход (нужен настроенный **`git pull`** для текущей ветки):

```bash
./build-rpm.sh --pull
```

**Что делает скрипт**

1. Опционально **`--pull`**: **`git pull --ff-only`** в РЕПО.
2. Проверяет в `PATH`: **`git`**, **`python3`**, **`node`**, **`npm`**, **`cargo`**, **`rpmbuild`**.
3. При отсутствии **`daemon/.env`** — копия из **`daemon/.env.example`** (заполните **`YANDEX_*`** для запуска демона).
4. **`npm install`** (пропуск: **`--skip-npm`**).
5. **`npm run tauri build`** (Vite пишет во **`dist/`**).
6. **[`build-linux-daemon.sh`](../../scripts/build-linux-daemon.sh)** — PyInstaller кладёт бинарь в **`build/daemon-release/cloudfusion-daemon`**, не в **`dist/`**, чтобы фронт его не затёр.
7. Копирование пяти файлов в **`$RPMBUILD_TOPDIR/SOURCES`**.
8. **Встроенный** ASCII-spec в **`$RPMBUILD_TOPDIR/SPECS/cloudfusion.spec`** (не читается из git — обход BOM/CRLF и парсера на ALT).
9. **`cd _topdir && LC_ALL=C rpmbuild -ba … SPECS/cloudfusion.spec`** → **`$RPMBUILD_TOPDIR/RPMS/`**; при ошибке **`rpmbuild`** дополнительно собирается **`build/cloudfusion-VERSION-linux-x86_64.tar.gz`**. Только архив, без RPM: **`./build-rpm.sh --tarball`**.

**Дополнительно**

```bash
./build-rpm.sh --only-sources
```

Только подготовка **`SOURCES`** без **`rpmbuild`**. Другой каталог:

```bash
RPMBUILD_TOPDIR=/tmp/my-rpm ./build-rpm.sh
```

Справка: **`./build-rpm.sh --help`**. Флаги: **`--pull`**, **`--skip-npm`**, **`--only-sources`**, **`--tarball`**.

---

## Сначала: пакеты на машине **сборщика** (одна ОС — один блок)

Ниже **не смешивайте** блоки разных дистрибутивов. При необходимости отдельно поставьте **rustup**. Установка пакетов — под **root** (`su -` / `sudo`).

### Вариант A — ALT Linux (apt-get, APT-RPM)

```bash
apt-get update
```

```bash
apt-get install -y git rpm-build gcc-c++ make pkgconfig openssl-devel zlib-devel
```

```bash
apt-get install -y python3 python3-devel python3-module-pip
```

Если нет **`python3-devel`**:

```bash
apt-cache search python3 | grep -i devel
```

```bash
apt-get install -y nodejs npm
```

**Tauri на ALT p11** (ошибка **`javascriptcoregtk-4.1`**): не используйте имена в стиле Debian (`libwebkit2gtk-4.1-dev` в ALT не находится). Достаточно:

```bash
apt-get install -y libwebkit2gtk4.1-devel
```

Если **`cargo`** всё ещё ругается на GTK / soup / rsvg:

```bash
apt-cache search webkit2gtk | grep devel
```

```bash
apt-get install -y libgtk+3-devel librsvg-devel libsoup-devel
```

Дерево каталогов для **`rpmbuild`**:

```bash
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
```

---

### Вариант B — Fedora / RHEL‑подобные (dnf)

```bash
dnf install -y git rpm-build python3 python3-pip gcc gcc-c++ openssl-devel
```

```bash
dnf install -y nodejs npm
```

```bash
dnf install -y webkit2gtk4.1-devel gtk3-devel libappindicator-gtk3-devel librsvg2-devel patchelf
```

```bash
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
```

---

### Rust (cargo) — если в дистрибутиве нет или версия старая

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
```

```bash
source "$HOME/.cargo/env"
```

```bash
rustc -V
cargo -V
```

---

### Проверка `PATH`

```bash
which git
```

```bash
which python3
```

```bash
which node
```

```bash
which npm
```

```bash
which rustc
```

```bash
which cargo
```

```bash
which rpmbuild
```

---

## Откуда берутся npm и Tauri

| Что | Откуда |
|-----|--------|
| **npm** | Пакет ОС (см. блоки выше). |
| **Зависимости фронта и Tauri CLI** | **`npm install`** в **РЕПО** → **`РЕПО/node_modules/`** (в т.ч. **`node_modules/.bin/tauri`**). |
| **Сборка окна** | **`npm run tauri build`** в **РЕПО** использует локальный CLI и системный **cargo**. |
| **Сборка демона (PyInstaller)** | Скрипт **`build-linux-daemon.sh`** пишет во **`build/daemon-release/`**, не в **`dist/`**: иначе **`vite build`** при Tauri перезаписывает **`dist/`** и бинарь демона пропадает. |

Отдельно «установить Tauri» с сайта **не нужно**.

В [`src-tauri/tauri.conf.json`](../../src-tauri/tauri.conf.json) для Linux в **`bundle.targets`** заданы только **`deb`** и **`rpm`** (без **AppImage**), чтобы не упираться в **`linuxdeploy`** на части систем.

---

## Ручная сборка (шаги 1–8)

Используйте, если не запускаете **`build-cloudfusion-rpm.sh`**. Каталог **`rpmbuild`** ниже — **`$HOME/rpmbuild`**; при другом **`_topdir`** подставьте свой путь везде, где фигурирует **`~/rpmbuild`**, и в шаге 7 добавьте **`--define "_topdir /ваш/путь"`**.

### Шаг 1. Клон

```bash
cd ~
```

```bash
git clone https://github.com/FunDuckich/disco-hack.git
```

```bash
cd disco-hack
```

### Шаг 2. Секреты Яндекса

```bash
cp daemon/.env.example daemon/.env
```

В **`daemon/.env`** задайте минимум:

```env
YANDEX_CLIENT_ID=...
YANDEX_CLIENT_SECRET=...
```

### Шаг 3. Node-зависимости

```bash
npm install
```

### Шаг 4. Tauri release

```bash
npm run tauri build
```

При необходимости:

```bash
npx tauri build
```

Проверка ELF приложения:

```bash
ls -la src-tauri/target/release/
```

### Шаг 5. Демон (PyInstaller)

**После** шага 4: иначе Vite очистит **`dist/`** и бинарь демона пропадёт. Результат: **`build/daemon-release/cloudfusion-daemon`**.

```bash
chmod +x scripts/build-linux-daemon.sh
```

```bash
./scripts/build-linux-daemon.sh
```

```bash
test -f build/daemon-release/cloudfusion-daemon && echo OK || echo FAIL
```

### Шаг 6. Заполнить `SOURCES`

```bash
mkdir -p ~/rpmbuild/SOURCES
```

Если в **`release/`** есть **`cloudfusion`**:

```bash
cp src-tauri/target/release/cloudfusion ~/rpmbuild/SOURCES/cloudfusion
```

Если только **`app`** (типично для этого репозитория):

```bash
cp src-tauri/target/release/app ~/rpmbuild/SOURCES/cloudfusion
```

```bash
chmod +x ~/rpmbuild/SOURCES/cloudfusion
```

```bash
cp build/daemon-release/cloudfusion-daemon ~/rpmbuild/SOURCES/cloudfusion-daemon
```

```bash
cp integration/scripts/share_bridge.py ~/rpmbuild/SOURCES/
```

```bash
cp integration/desktop/cloudfusion-link.desktop ~/rpmbuild/SOURCES/
```

```bash
cp integration/desktop/cloudfusion-app.desktop ~/rpmbuild/SOURCES/
```

```bash
chmod +x ~/rpmbuild/SOURCES/cloudfusion-daemon
```

```bash
ls -la ~/rpmbuild/SOURCES/
```

Должно быть **ровно 5** имён: **`cloudfusion`**, **`cloudfusion-daemon`**, **`share_bridge.py`**, **`cloudfusion-link.desktop`**, **`cloudfusion-app.desktop`**.

### Шаг 7. `rpmbuild`

Явный **`_topdir`** и spec из **`SPECS/`** (так надёжнее для ALT, чем путь из git-клона):

```bash
mkdir -p ~/rpmbuild/SPECS
```

```bash
python3 <<'PY'
from pathlib import Path
src = Path("packaging/rpm/cloudfusion.spec")
dst = Path.home() / "rpmbuild/SPECS/cloudfusion.spec"
dst.parent.mkdir(parents=True, exist_ok=True)
b = src.read_bytes()
if b.startswith(b"\xef\xbb\xbf"):
    b = b[3:]
b = b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
if not b.endswith(b"\n"):
    b += b"\n"
dst.write_bytes(b)
PY
```

```bash
rpmbuild -ba --define "_topdir $HOME/rpmbuild" "$HOME/rpmbuild/SPECS/cloudfusion.spec"
```

```bash
ls -la ~/rpmbuild/RPMS/x86_64/
```

### Шаг 8. Установка RPM

```bash
sudo rpm -Uvh ~/rpmbuild/RPMS/x86_64/cloudfusion-0.1.0-*.rpm
```

```bash
kquitapp5 dolphin
```

Переменные **`YANDEX_*`** в сеансе пользователя; интеграция Dolphin: [`integration/README.md`](../../integration/README.md).

---

## Если что-то ломается

| Сообщение | Что сделать |
|-----------|-------------|
| `npm: command not found` | Блок установки **Node/npm** для вашей ОС выше. |
| `cargo: command not found` | Пакет **`rust`**/**`cargo`** дистрибутива или **rustup** + **`source ~/.cargo/env`**. |
| `javascriptcoregtk-4.1` / `No package 'javascriptcoregtk-4.1' found` | На **ALT p11**: **`libwebkit2gtk4.1-devel`**. Имена вроде **`libwebkit2gtk-4.1-dev`** — это **Debian/Ubuntu**. |
| `failed to run linuxdeploy` / `mtr-packet` | В актуальном репозитории **AppImage** отключён в **`tauri.conf.json`**. Обновите клон или уберите **AppImage** из **`bundle.targets`**. |
| `install: ... cloudfusion-daemon: Нет такого файла` | Собирайте демон **после** **`npm run tauri build`** или пользуйтесь **`./build-rpm.sh`**. Бинарь: **`build/daemon-release/cloudfusion-daemon`** (не **`dist/`**). |
| `Файл ... cloudfusion.spec не похож на файл спецификации` | Обновите скрипт: **`./build-rpm.sh`** генерирует spec в **`~/rpmbuild/SPECS/`** сам. Вручную из git-файла: **`dos2unix`**, см. **шаг 7**. Запасной вариант: **`./build-rpm.sh --tarball`** (без **`rpmbuild`**). |
| `rpmbuild: command not found` | Пакет **`rpm-build`** (или аналог в вашем дистрибутиве). |

В [`cloudfusion.spec`](cloudfusion.spec) при необходимости поправьте **`Requires:`** для FUSE под имя пакета вашего дистрибутива.
