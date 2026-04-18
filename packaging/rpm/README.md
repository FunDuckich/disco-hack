# CloudFusion: сборка и установка **только через RPM**

Здесь **единственная** пошаговая инструкция: от пустой машины сборщика до установки `.rpm` на ALT (или другом rpm-based дистрибутиве). Всё остальное (разработка без RPM) в репозитории не дублируется.

**РЕПО** — каталог с клоном `disco-hack` (корень репозитория). Команды с `cd` ниже подразумевают, что вы уже сделали `cd РЕПО` (подставьте реальный путь, например `~/build/disco-hack`).

---

## Что откуда берётся (один раз прочитать)

| Инструмент | Откуда он появляется у вас | Зачем он нужен для RPM |
|------------|------------------------------|-------------------------|
| **Python 3** | Пакет дистрибутива (`python3`, иногда `python3-devel` для сборки колёс) | Скрипт PyInstaller и зависимости демона |
| **pip / venv** | Вместе с Python или `python3-pip` | Ставит библиотеки в изолированное окружение для сборки `cloudfusion-daemon` |
| **Node.js** | Пакет дистрибутива (`nodejs`, на части систем отдельно `npm`) | Движок для `npm` |
| **npm** | Почти всегда **ставится вместе с Node.js** как отдельная команда `npm` | Читает [`package.json`](../../package.json) в **РЕПО**, качает зависимости в **`РЕПО/node_modules/`** (React, Vite, **@tauri-apps/cli** и т.д.) |
| **Tauri** | **Не ставится отдельно.** Это два слоя: (1) **npm-пакет** `@tauri-apps/cli` в `node_modules` — это **CLI**; (2) Rust-библиотека `tauri` в **`РЕПО/src-tauri/Cargo.toml`** — подтягивается **cargo** при сборке | `npm run tauri build` вызывает локальный CLI из `node_modules/.bin/tauri`, он запускает **Vite** (`npm run build` → папка **`РЕПО/dist/`**) и **cargo** для Rust в **`РЕПО/src-tauri/`** |
| **Rust / cargo** | `rustup` или пакет `rust` / `cargo` дистрибутива | Собирает нативный бинарь окна приложения (то, что в меню будет называться CloudFusion) |
| **rpmbuild** | Пакет `rpm-build` или аналог на вашем дистрибутиве | Упаковывает уже готовые файлы по [`cloudfusion.spec`](cloudfusion.spec) |

Итого: **npm** — это программа из пакета **Node.js**. **Tauri** для сборки — это команда **`npm run tauri build`** из каталога **РЕПО**, которая использует установленные в **РЕПО/node_modules** CLI и ваш системный **cargo**.

Проверки «всё ли на месте»:

```bash
which node npm rustc cargo rpmbuild python3
node -v
npm -v
rustc -V
```

---

## Зависимости на машине **сборщика** (пример для ALT / rpm-based)

Установите через свой менеджер пакетов (имена пакетов могут отличаться — ищите аналоги):

- `git`, `rpm-build` (или как у вас называется пакет с `rpmbuild`)
- `python3`, `python3-pip` (при необходимости `python3-devel` для сборки нативных колёс)
- `nodejs` и **npm** (если в репозитории нет `npm` — отдельный пакет `npm`)
- `rust` + `cargo` **или** установка [rustup](https://rustup.rs/) под вашим пользователем
- Системные библиотеки для линковки Tauri на Linux (webkitgtk и др. — при ошибке `cargo`/`tauri build` дистрибутив подскажет пакет-зависимость; на ALT часто ставят группу «инструменты разработки» или пакеты из документации Tauri Linux)

FUSE на **машине сборщика** нужен только если вы там же гоняете FUSE-тесты; для **сборки** RPM достаточно того, что PyInstaller и Tauri успешно собираются.

---

## Шаг 1. Клон и конфиг Яндекса

```bash
cd ~/build   # или любой каталог
git clone https://github.com/FunDuckich/disco-hack.git
cd disco-hack
```

Дальше считаем, что вы в **РЕПО**.

Создайте файл **`daemon/.env`** (скопируйте из [`daemon/.env.example`](../../daemon/.env.example)) и заполните минимум:

```env
YANDEX_CLIENT_ID=...
YANDEX_CLIENT_SECRET=...
```

Без этого собранный **`cloudfusion-daemon`** при запуске сразу завершится с ошибкой (настройки читаются из окружения / `.env` в зависимости от способа запуска). Для **установленного из RPM** приложения пользователю нужно будет задать те же переменные в окружении сессии (например `~/.bash_profile`, конфиг systemd user, или графический сеанс — отдельно от RPM).

---

## Шаг 2. Сборка демона PyInstaller

Из **РЕПО**:

```bash
chmod +x scripts/build-linux-daemon.sh   # один раз, если нет права на запуск
./scripts/build-linux-daemon.sh
```

Скрипт сам создаёт временный venv, ставит `daemon/requirements-build.txt`, вызывает `pyinstaller` по [`daemon/pyinstaller/cloudfusion-daemon.spec`](../../daemon/pyinstaller/cloudfusion-daemon.spec).

**Результат:** исполняемый файл

**`РЕПО/dist/cloudfusion-daemon`**

Проверка (опционально, из **РЕПО**, с подгруженными переменными из `daemon/.env`):

```bash
set -a; source daemon/.env; set +a
./dist/cloudfusion-daemon
# в другом терминале: curl -s http://127.0.0.1:8000/health
# остановите демон Ctrl+C
```

---

## Шаг 3. Установка npm-зависимостей проекта

Из **РЕПО**:

```bash
npm install
```

Что произошло: в каталоге **`РЕПО/node_modules/`** появились зависимости из [`package.json`](../../package.json), в том числе **`node_modules/.bin/tauri`** — это и есть вызываемый **Tauri CLI** при сборке.

---

## Шаг 4. Сборка окна приложения (Tauri release)

Из **РЕПО**:

```bash
npm run tauri build
```

Что произходит по цепочке:

1. Вызывается **`tauri build`** из `node_modules/.bin/` (после `npm install` CLI уже в **РЕПО**; отдельно с сайта Tauri ничего ставить не нужно). Если `npm run tauri build` не сработал, используйте **`npx tauri build`** из **РЕПО**.
2. По [`src-tauri/tauri.conf.json`](../../src-tauri/tauri.conf.json) перед сборкой Rust выполняется **`beforeBuildCommand`**: `npm run build` → **Vite** собирает фронт в **`РЕПО/dist/`**.
3. **cargo** собирает крейт из **`РЕПО/src-tauri/`** и упаковывает бандл в **`РЕПО/src-tauri/target/release/bundle/`** (подкаталоги могут называться `deb`, `rpm`, `appimage` и т.д. — зависит от целей в конфиге).

**Нужный для нашего RPM файл** — это **исполняемый бинарь приложения**, а не обязательно `.rpm` внутри `bundle/`. Чаще всего удобно взять готовый ELF из release:

```bash
ls -la src-tauri/target/release/
```

Ищите исполняемый файл **без** расширения (имя может быть **`cloudfusion`** из `productName` в `tauri.conf.json` или **`app`** из имени крейта в `Cargo.toml` — смотрите фактическое имя в выводе `ls`).

Дополнительно можно поискать по дереву:

```bash
find src-tauri/target/release -maxdepth 3 -type f -perm -111 2>/dev/null | head -30
```

Этот бинарь нужно **скопировать в SOURCES под именем `cloudfusion`** (так указано в `cloudfusion.spec` как `Source0`).

Пример (подставьте реальный путь к найденному бинарю):

```bash
cp src-tauri/target/release/cloudfusion /tmp/cloudfusion-for-rpm
# если файл называется app:
# cp src-tauri/target/release/app /tmp/cloudfusion-for-rpm
mv /tmp/cloudfusion-for-rpm ~/rpmbuild/SOURCES/cloudfusion
chmod +x ~/rpmbuild/SOURCES/cloudfusion
```

---

## Шаг 5. Каталог `SOURCES` для rpmbuild

Стандартный путь: **`~/rpmbuild/SOURCES`**. Если у вас другой topdir — используйте свой `SOURCES`.

Из **РЕПО** выполните (после того как **`cloudfusion`** уже лежит в SOURCES, как в шаге 4):

```bash
mkdir -p ~/rpmbuild/SOURCES
cp dist/cloudfusion-daemon ~/rpmbuild/SOURCES/cloudfusion-daemon
cp integration/scripts/share_bridge.py ~/rpmbuild/SOURCES/
cp integration/desktop/cloudfusion-link.desktop ~/rpmbuild/SOURCES/
cp integration/desktop/cloudfusion-app.desktop ~/rpmbuild/SOURCES/
chmod +x ~/rpmbuild/SOURCES/cloudfusion-daemon
```

В **`~/rpmbuild/SOURCES`** должно быть **ровно пять** файлов с такими **именами**:

| Имя файла в SOURCES | Соответствие в spec |
|---------------------|---------------------|
| `cloudfusion` | GUI, вы собрали на шаге 4 |
| `cloudfusion-daemon` | `dist/cloudfusion-daemon` |
| `share_bridge.py` | `integration/scripts/share_bridge.py` |
| `cloudfusion-link.desktop` | `integration/desktop/cloudfusion-link.desktop` |
| `cloudfusion-app.desktop` | `integration/desktop/cloudfusion-app.desktop` |

---

## Шаг 6. Сборка RPM

Из **РЕПО** (файл spec в репозитории):

```bash
rpmbuild -ba packaging/rpm/cloudfusion.spec
```

Готовый пакет ищите в **`~/rpmbuild/RPMS/x86_64/`** (имя вида `cloudfusion-0.1.0-1....rpm`).

---

## Шаг 7. Установка на целевую машину

Скопируйте `.rpm` на компьютер пользователя и:

```bash
sudo rpm -Uvh cloudfusion-0.1.0-*.rpm
```

Что появится в системе (см. [`cloudfusion.spec`](cloudfusion.spec)):

| Путь | Назначение |
|------|------------|
| `/usr/bin/cloudfusion` | Запуск окна из меню |
| `/usr/libexec/cloudfusion/cloudfusion-daemon` | Демон API |
| `/usr/libexec/cloudfusion/share_bridge.py` | Мост для Dolphin |
| `/usr/share/applications/cloudfusion-app.desktop` | Ярлык в меню |
| `/usr/share/kio/servicemenus/cloudfusion-link.desktop` | Пункт «публичная ссылка» в Dolphin |

После установки перезапустите Dolphin: `kquitapp5 dolphin` и снова откройте Dolphin.

**OAuth:** пользователь должен иметь в среде запуска (сеанса) переменные **`YANDEX_CLIENT_ID`** и **`YANDEX_CLIENT_SECRET`** (как в `daemon/.env.example`). RPM их не создаёт по соображениям безопасности.

---

## Если что-то падает

- **`npm: command not found`** — не установлен Node.js / npm из дистрибутива.
- **`cargo: command not found`** — не установлен Rust.
- **`error while running tauri application` / ошибки линковки webkit** — доустановите системные `-devel` пакеты, которые просит лог `tauri build` для вашего дистрибутива.
- **`rpmbuild: command not found`** — установите пакет с `rpmbuild`.
- В spec поле **`Requires:`** для FUSE (`fuse3`) при необходимости замените на имя пакета вашего дистрибутива.

Тонкости интеграции Dolphin после установки: [`integration/README.md`](../../integration/README.md).
