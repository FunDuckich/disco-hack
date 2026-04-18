# CloudFusion: сборка и установка **только через RPM**

**РЕПО** — каталог с клоном `disco-hack` (корень репозитория). Дальше все команды сборки выполняйте **из РЕПО** после `cd` в него.

---

## Сначала: пакеты на машине **сборщика** (одна ОС — один блок)

Ниже **не копируйте всё подряд**. Выберите **один** вариант (ALT или Fedora). Потом при необходимости блок с **rustup**. Команды с установкой пакетов обычно нужен **root** (`su -` или `sudo`).

### Вариант A — ALT Linux (apt-get, APT-RPM)

Обновить индекс и поставить базовые инструменты:

```bash
apt-get update
```

```bash
apt-get install -y git rpm-build gcc-c++ make pkgconfig openssl-devel zlib-devel
```

Python и pip для скрипта сборки демона:

```bash
apt-get install -y python3 python3-devel python3-module-pip
```

Если пакета `python3-devel` нет, найдите аналог:

```bash
apt-cache search python3 | grep -i devel
```

Node.js и npm (для `npm install` и `tauri build` в РЕПО):

```bash
apt-get install -y nodejs npm
```

Библиотеки для линковки **Tauri** (GTK / WebKit). Если какого-то имени нет — найдите аналог:

```bash
apt-cache search webkit | grep -i devel
apt-cache search gtk | grep -i devel
```

Пример набора (имена на вашей ветке ALT могут отличаться — смотрите вывод поиска выше):

```bash
apt-get install -y libgtk+3-devel libwebkit2gtk-devel librsvg-devel libsoup-devel
```

Один раз создать дерево каталогов для `rpmbuild` (если ещё не создавали):

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

Зависимости Tauri под GTK (типовой набор):

```bash
dnf install -y webkit2gtk4.1-devel gtk3-devel libappindicator-gtk3-devel librsvg2-devel patchelf
```

Дерево `rpmbuild`:

```bash
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
```

---

### Rust (cargo) — если в дистрибутиве нет или версия старая

Поставить **rustup** под обычным пользователем (не обязательно root):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
```

Подключить `cargo` в текущую сессию:

```bash
source "$HOME/.cargo/env"
```

Проверка:

```bash
rustc -V
cargo -V
```

---

### Проверка, что всё нужное в PATH

Выполните по очереди (должны печататься пути, а не «не найдено»):

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

## Откуда берутся npm и Tauri (коротко)

| Что | Откуда |
|-----|--------|
| **npm** | Установили пакетом ОС (см. блоки выше). |
| **Зависимости фронта и Tauri CLI** | Команда **`npm install`** в **РЕПО** скачивает их в **`РЕПО/node_modules/`** (в т.ч. `node_modules/.bin/tauri`). |
| **Сборка окна** | Команда **`npm run tauri build`** или **`npx tauri build`** в **РЕПО** вызывает этот локальный CLI и системный **cargo**. |

Отдельно программу «Tauri» с сайта ставить **не нужно**.

---

## Шаг 1. Клон репозитория

```bash
cd ~
```

```bash
git clone https://github.com/FunDuckich/disco-hack.git
```

```bash
cd disco-hack
```

Дальше везде вы в **РЕПО** (например `~/disco-hack`).

---

## Шаг 2. Файл с секретами Яндекса для сборки демона

```bash
cp daemon/.env.example daemon/.env
```

Отредактируйте `daemon/.env` и пропишите минимум:

```env
YANDEX_CLIENT_ID=...
YANDEX_CLIENT_SECRET=...
```

---

## Шаг 3. Сборка бинаря демона (PyInstaller)

Права на скрипт (один раз):

```bash
chmod +x scripts/build-linux-daemon.sh
```

Запуск сборки:

```bash
./scripts/build-linux-daemon.sh
```

Проверка, что файл появился:

```bash
test -f dist/cloudfusion-daemon && echo OK || echo FAIL
```

---

## Шаг 4. Зависимости Node для проекта

```bash
npm install
```

---

## Шаг 5. Сборка графического приложения (Tauri)

Попробовать основную команду:

```bash
npm run tauri build
```

Если не сработало — та же сборка через `npx`:

```bash
npx tauri build
```

Найти собранный ELF приложения (имя часто **`cloudfusion`** или **`app`**):

```bash
ls -la src-tauri/target/release/
```

Скопировать **один** исполняемый файл в `SOURCES` под именем **`cloudfusion`** (если бинарь называется `app` — всё равно копируйте его в файл с именем `cloudfusion`):

```bash
mkdir -p ~/rpmbuild/SOURCES
```

Если в release лежит `cloudfusion`:

```bash
cp src-tauri/target/release/cloudfusion ~/rpmbuild/SOURCES/cloudfusion
```

Если в release лежит `app`:

```bash
cp src-tauri/target/release/app ~/rpmbuild/SOURCES/cloudfusion
```

Сделать файл исполняемым:

```bash
chmod +x ~/rpmbuild/SOURCES/cloudfusion
```

---

## Шаг 6. Остальные файлы в `SOURCES`

Выполнять **из РЕПО**:

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

Проверка списка (должно быть **5** файлов):

```bash
ls -la ~/rpmbuild/SOURCES/
```

Имена: `cloudfusion`, `cloudfusion-daemon`, `share_bridge.py`, `cloudfusion-link.desktop`, `cloudfusion-app.desktop`.

---

## Шаг 7. Сборка RPM

```bash
rpmbuild -ba packaging/rpm/cloudfusion.spec
```

Готовый пакет:

```bash
ls -la ~/rpmbuild/RPMS/x86_64/
```

---

## Шаг 8. Установка RPM на целевую машину

Скопируйте `.rpm` на компьютер пользователя, затем:

```bash
sudo rpm -Uvh ~/rpmbuild/RPMS/x86_64/cloudfusion-0.1.0-*.rpm
```

(Подставьте реальное имя файла из каталога `RPMS`.)

После установки перезапуск Dolphin:

```bash
kquitapp5 dolphin
```

Пользователь должен задать **`YANDEX_CLIENT_ID`** и **`YANDEX_CLIENT_SECRET`** в окружении сеанса (RPM их не кладёт в домашний каталог). Подробнее про пути и Dolphin: [`integration/README.md`](../../integration/README.md).

---

## Если что-то ломается

| Сообщение | Что сделать |
|-----------|-------------|
| `npm: command not found` | Вернитесь к блоку установки **Node/npm** для вашей ОС. |
| `cargo: command not found` | Установите Rust из дистрибутива или блок **rustup** выше, затем `source ~/.cargo/env`. |
| Ошибки линковки **webkit / gtk** при `tauri build` | Доустановьте `-devel` пакеты; точные имена — через `apt-cache search` / `dnf search` по строкам из лога компилятора. |
| `rpmbuild: command not found` | Установите пакет **`rpm-build`** (или как он называется у вас). |

В [`cloudfusion.spec`](cloudfusion.spec) строка **`Requires:`** для FUSE при необходимости замените на имя пакета вашего дистрибутива.
