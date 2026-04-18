# CloudFusion: сборка и установка **только через RPM**

**РЕПО** — корень клона `disco-hack`. Все команды сборки — **из РЕПО** (`cd` в каталог репозитория).

---

## Два способа

| Способ | Когда |
|--------|--------|
| **[`scripts/build-cloudfusion-rpm.sh`](../../scripts/build-cloudfusion-rpm.sh)** | Обычный случай: одна команда после установки пакетов ОС. |
| **Шаги 1–8 ниже** | Нужен контроль каждого шага, отладка или нестандартный `_topdir`. |

---

## Быстрый путь: один скрипт

**Перед первым запуском** установите зависимости сборщика — см. раздел **«Пакеты на машине сборщика»** ниже в этом файле.

Запуск из **РЕПО**:

```bash
./scripts/build-cloudfusion-rpm.sh
```

(После `git clone` бит исполняемости уже выставлен в репозитории; если shell пишет «Отказано в доступу» — один раз: `chmod +x scripts/build-cloudfusion-rpm.sh`.)

**Что делает скрипт**

1. Проверяет наличие в `PATH`: `git`, `python3`, `node`, `npm`, `cargo`, `rpmbuild`.
2. Если установлен **`dos2unix`**, приводит к Unix переводам строк в [`cloudfusion.spec`](cloudfusion.spec) (снимает типичные проблемы после клона с Windows).
3. Если нет **`daemon/.env`**, копирует из **`daemon/.env.example`** и напоминает заполнить **`YANDEX_*`** (для **запуска** демона; сама сборка PyInstaller от этого не зависит).
4. Запускает **[`scripts/build-linux-daemon.sh`](../../scripts/build-linux-daemon.sh)** → появляется **`dist/cloudfusion-daemon`**.
5. **`npm install`** (пропуск: **`./scripts/build-cloudfusion-rpm.sh --skip-npm`**).
6. **`npm run tauri build`** → ELF в **`src-tauri/target/release/`** (`app` или `cloudfusion`).
7. Копирует **пять файлов** в **`$RPMBUILD_TOPDIR/SOURCES`** (по умолчанию **`~/rpmbuild`**): GUI как **`cloudfusion`**, демон, `share_bridge.py`, два `.desktop`.
8. **`rpmbuild -ba --define "_topdir …"`** — готовый RPM в **`$RPMBUILD_TOPDIR/RPMS/`** (часто **`…/RPMS/x86_64/`**).

**Дополнительно**

```bash
./scripts/build-cloudfusion-rpm.sh --only-sources
```

Только шаги 1–7 без **`rpmbuild`** (удобно проверить SOURCES). Другой каталог вместо **`~/rpmbuild`**:

```bash
RPMBUILD_TOPDIR=/tmp/my-rpm ./scripts/build-cloudfusion-rpm.sh
```

Справка по флагам: **`./scripts/build-cloudfusion-rpm.sh --help`**.

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

### Шаг 3. Демон (PyInstaller)

```bash
chmod +x scripts/build-linux-daemon.sh
```

```bash
./scripts/build-linux-daemon.sh
```

```bash
test -f dist/cloudfusion-daemon && echo OK || echo FAIL
```

### Шаг 4. Node-зависимости

```bash
npm install
```

### Шаг 5. Tauri release

```bash
npm run tauri build
```

При необходимости:

```bash
npx tauri build
```

Проверка ELF:

```bash
ls -la src-tauri/target/release/
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
cp dist/cloudfusion-daemon ~/rpmbuild/SOURCES/cloudfusion-daemon
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

Явный **`_topdir`** совпадает с тем, что делает скрипт сборки:

```bash
rpmbuild -ba --define "_topdir $HOME/rpmbuild" packaging/rpm/cloudfusion.spec
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
| `cp: ... dist/cloudfusion-daemon` | Шаг **3** или скрипт **`build-linux-daemon.sh`**. |
| `Файл ... cloudfusion.spec не похож на файл спецификации` | Часто **CRLF**: **`dos2unix packaging/rpm/cloudfusion.spec`**, проверка **`file`** / **`head`**. |
| `rpmbuild: command not found` | Пакет **`rpm-build`** (или аналог в вашем дистрибутиве). |

В [`cloudfusion.spec`](cloudfusion.spec) при необходимости поправьте **`Requires:`** для FUSE под имя пакета вашего дистрибутива.
