# DiscoHack (CloudFusion)

> **Нативный агрегатор облачных хранилищ с умным кэшированием для ALT Linux.**

Проект разработан в рамках хакатона по кейсу интеграции облачных сервисов в рабочую среду пользователя.

## 🚀 В чем проблема?
Современные облачные хранилища либо заставляют пользователя использовать браузер, либо предлагают медленный WebDAV, либо забивают локальный диск полной синхронизацией. Мы решаем это.

## ✨ Наше решение
**DiscoHack** — это мост между облаком и вашей системой. Мы используем технологию **FUSE**, чтобы создать виртуальный диск (сейчас точка монтирования по умолчанию — `~/CloudFusion`, см. `daemon/core/mount.py`), который объединяет Яндекс.Диск, Nextcloud и другие сервисы в одном окне вашего файлового менеджера (Dolphin/Nautilus).

### Ключевые фичи:
*   **Virtual File System (FUSE):** Облака выглядят как обычные папки. Никакого скачивания всего объема данных — файлы подгружаются только при обращении.
*   **Умное LRU-кэширование:** Вы сами задаете лимит кэша (например, 5 ГБ). Самые старые файлы удаляются автоматически, освобождая место для новых.
*   **Мгновенный поиск:** Благодаря индексации в **SQLite (FTS5)**, поиск по сотням тысяч файлов во всех облаках занимает миллисекунды.
*   **Глубокая интеграция с ALT Linux:** Контекстное меню "Поделиться" прямо в Dolphin и генерация QR-кодов во всплывающем окне.
*   **Реактивный UI:** Легковесный центр управления на **Tauri + React**, потребляющий минимум ресурсов системы.

---

## 🏗 Архитектура

Проект построен на принципе разделения ответственности (Microservices on Desktop):

1.  **UI Layer (Tauri + React):** Стильный интерфейс управления аккаунтами и настройками кэша.
2.  **Core Layer (Python 3.12 + FastAPI):** Системный демон (Sidecar), отвечающий за логику FUSE, взаимодействие с API облаков и алгоритмы кэширования.
3.  **Data Layer (SQLite):** Локальный индекс всех метаданных для мгновенной навигации и поиска.
4.  **VFS Layer (pyfuse3):** Реализация виртуальной файловой системы через FUSE 3.

---

## Если в подпапках на `~/CloudFusion` пусто

Индекс для FUSE берётся из **SQLite** (заполняется демоном из API облака). Если корень виден, а внутри папок пусто — перезапустите демон после обновления кода; при необходимости удалите файл БД (`~/.local/share/cloudfusion/cloudfusion.db` или ваш `DB_PATH` в `.env`) и дайте демону заново проиндексировать дерево. Индексация Яндекс.Диска: рекурсивный обход в `daemon/cloud_api/yandex.py` (`get_all_files_flat`).

---

## Проверка FUSE и индекса (Linux)

1. Установите зависимости демона, авторизуйте Яндекс через UI/эндпоинты, как в вашем сценарии.
2. Запустите демон с FUSE; в логах должны появиться строки вроде «Всего записей в индексе: …» и при открытии папки — «Найдено N элементов в БД» с **N > 0** для непустых каталогов.
3. В терминале: `ls -la ~/CloudFusion` и `ls -la ~/CloudFusion/ИмяПапки` — списки должны совпадать с тем, что видно в веб-интерфейсе Диска.
4. Дополнительно можно проверить SQLite (подставьте путь к своей БД, чаще всего `~/.local/share/cloudfusion/cloudfusion.db`):  
   `sqlite3 ~/.local/share/cloudfusion/cloudfusion.db "SELECT parent_id, COUNT(*) FROM files GROUP BY parent_id;"` — для идентификаторов папок с детьми счётчики должны быть больше нуля.

---

## 📂 Структура проекта

*   `/daemon` — Сердце проекта: FUSE-драйвер, работа с SQLite и API облаков.
*   `/src` — Фронтенд на React (JSX): интерфейс настроек и мониторинга.
*   `/src-tauri` — Бэкенд на Rust: управление окнами, треем и запуск Sidecar-процессов.
*   `/integration` — Системные конфиги для ALT Linux (Service Menus для Dolphin).

---

## Запуск и установка

Ниже **«РЕПО»** — это каталог, в который вы клонировали проект (например `C:\Users\you\disco-hack` или `~/disco-hack`). Все пути к файлам в тексте — **относительно РЕПО**, если не сказано иначе.

| Что запускается | Зачем | Рабочая директория (cwd) в терминале |
|-----------------|-------|--------------------------------------|
| `python -m daemon.main` | HTTP API для UI и Dolphin | **РЕПО** (корень), не папка `daemon/` |
| `npm run tauri dev` | Окно CloudFusion (Vite + Tauri) | **РЕПО** |
| `python run_mount.py` или `python -m daemon.core.mount` | Монтирование `~/CloudFusion` (FUSE) | **РЕПО** |
| `./scripts/build-linux-daemon.sh` | Сборка бинаря демона PyInstaller | **РЕПО** |
| `npm run tauri build` | Сборка установщика Tauri | **РЕПО** |

Проверка, что демон жив: в браузере или `curl` открыть `http://127.0.0.1:8000/health` — должен ответить JSON со статусом.

---

### Шаг 0. Один раз на машине

1. Установите **Python 3.12+**, **Node.js 18+**, **Rust** (toolchain с `cargo`, нужен для Tauri).
2. Клонируйте репозиторий и запомните путь к **РЕПО**:
   ```bash
   git clone https://github.com/FunDuckich/disco-hack.git
   cd disco-hack
   ```
3. Создайте конфиг демона: скопируйте файл [`daemon/.env.example`](daemon/.env.example) в **`daemon/.env`** (именно в подкаталоге `daemon/`, рядом с `requirements.txt`). Заполните **`YANDEX_CLIENT_ID`** и **`YANDEX_CLIENT_SECRET`**. Без этого команда `python -m daemon.main` упадёт при старте.
4. (Опционально) Для FUSE на Linux установите системные пакеты вроде **`fuse3`** / **`libfuse3`**, затем в venv подтянутся зависимости из `daemon/requirements.txt` (в т.ч. `pyfuse3`).

База SQLite по умолчанию: **`~/.local/share/cloudfusion/cloudfusion.db`**. Свой путь можно задать в **`daemon/.env`** переменной **`DB_PATH`**.

---

### Сценарий A. Разработка: Windows (или Linux без авто-старта демона)

Нужны **два терминала**. В обоих сначала выполните `cd РЕПО` (подставьте свой путь).

**Терминал 1 — только демон (API)**

1. `cd РЕПО`
2. `cd daemon`
3. `python -m venv venv`
4. Активируйте venv: Windows — `venv\Scripts\activate`; Linux/macOS — `source venv/bin/activate`
5. `pip install -r requirements.txt`
6. `cd ..`  ← вы снова в **РЕПО**, это важно
7. `python -m daemon.main`  
   Оставьте процесс работать. API: **`http://127.0.0.1:8000`**.

Альтернатива шага 7: `python run_backend.py`. Тестовые данные: `python -m daemon.seed` (тоже из **РЕПО**, venv активен).

**Терминал 2 — только окно приложения**

1. `cd РЕПО`
2. Один раз: `npm install`
3. Каждый запуск UI: `npm run tauri dev`  
   Откроется окно; фронт ходит на **`127.0.0.1:8000`**. Пока работает терминал 1, интерфейс видит API.

На **Windows** демон **всегда** ведёт себя как в терминале 1 (Tauri его не поднимает).

---

### Сценарий B. Разработка: Linux + FUSE (третий процесс)

Сначала сделайте **сценарий A** (терминал 1 с демоном уже запущен, venv активирован в том же терминале или заново активируйте в новом).

**Терминал 3 — монтирование диска в `~/CloudFusion`**

1. `cd РЕПО`
2. Активируйте тот же venv, что и для демона: `source daemon/venv/bin/activate` (Linux) или эквивалент на Windows/WSL.
3. Выполните **одну** из команд (обе из **РЕПО**):
   - `python run_mount.py`  
   - или `python -m daemon.core.mount`  

Не запускайте файл `daemon/core/mount.py` напрямую как скрипт — сломаются импорты.

**PyCharm:** рабочая директория — **РЕПО**; модуль `daemon.core.mount` или скрипт `run_mount.py`.

---

### Сценарий C. Linux: одно окно Tauri, демон стартует сам (PyInstaller)

Подходит, если вы уже собрали бинарь демона. Всё из **РЕПО**.

1. Сборка демона (нужен Linux, зависимости из `daemon/requirements-build.txt` ставит скрипт во временный venv):
   ```bash
   cd РЕПО
   chmod +x scripts/build-linux-daemon.sh   # если нужно
   ./scripts/build-linux-daemon.sh
   ```
   Результат: файл **`РЕПО/dist/cloudfusion-daemon`** (один исполняемый файл).

2. В **том же терминале**, из которого запускаете `npm run tauri dev`, должны быть видны переменные **`YANDEX_CLIENT_ID`** и **`YANDEX_CLIENT_SECRET`** (и при необходимости остальное из `daemon/.env`). Иначе дочерний процесс `cloudfusion-daemon` сразу завершится с ошибкой. Задайте их вручную через `export ИМЯ=значение` или скопируйте строки из `daemon/.env` в окружение сессии другим привычным вам способом.

3. Укажите путь к демону и запустите UI **из РЕПО**:
   ```bash
   cd РЕПО
   export CLOUDFUSION_DAEMON_BIN="$PWD/dist/cloudfusion-daemon"
   npm install   # если ещё не делали
   npm run tauri dev
   ```

Tauri ищет бинарь в таком порядке: **`CLOUDFUSION_DAEMON_BIN`** → файл **`cloudfusion-daemon` рядом с бинарём приложения** → **`/usr/libexec/cloudfusion/cloudfusion-daemon`** (после установки RPM). Если ничего не найдено — используйте **сценарий A** (отдельный терминал с `python -m daemon.main`).

---

### Сценарий D. Сборка установщика Tauri (без RPM)

Рабочая директория — **РЕПО**.

```bash
cd РЕПО
npm install
npm run tauri build
```

Готовые файлы ищите в **`РЕПО/src-tauri/target/release/bundle/`** (подкаталог зависит от ОС: `.deb`, `.rpm`, `.msi`, AppImage и т.д.).

---

### Сценарий E. Сборка и установка RPM (Linux для пользователя)

Делается на машине с **`rpmbuild`** и установленными зависимостями для сборки Tauri/Rust. Кратко:

| Шаг | Где (cwd) | Действие |
|-----|-----------|----------|
| 1 | **РЕПО** | `./scripts/build-linux-daemon.sh` → появится `dist/cloudfusion-daemon` |
| 2 | **РЕПО** | `npm install` и `npm run tauri build` → взять **бинарь приложения** из `src-tauri/target/release/bundle/` (имя может быть `cloudfusion` или похожее — см. каталог bundle) |
| 3 | каталог `SOURCES` для rpmbuild | Скопировать туда файлы по списку в [`packaging/rpm/README.md`](packaging/rpm/README.md): бинарь GUI, `dist/cloudfusion-daemon` как имя из spec, `integration/scripts/share_bridge.py`, оба `.desktop` из `integration/desktop/` |
| 4 | **РЕПО** (или домашний каталог rpmbuild) | `rpmbuild -ba packaging/rpm/cloudfusion.spec` |
| 5 | система | Установка: `sudo rpm -Uvh путь/к/собранному.rpm` |

После установки: приложение в меню как **CloudFusion**; демон лежит в **`/usr/libexec/cloudfusion/cloudfusion-daemon`**; Dolphin — см. [`integration/README.md`](integration/README.md). Перезапуск Dolphin: `kquitapp5 dolphin && dolphin`.

Если нужны нестандартные CORS-origins для WebView, см. переменные **`ALLOWED_ORIGINS`** и **`CORS_ORIGIN_REGEX`** в [`daemon/main.py`](daemon/main.py).

---

## 🎨 Стек технологий
*   **Desktop:** [Tauri](https://tauri.app/) (Rust)
*   **Frontend:** [React](https://reactjs.org/) + [Vite](https://vitejs.dev/)
*   **Backend Daemon:** [Python 3.12](https://www.python.org/) + [FastAPI](https://fastapi.tiangolo.com/)
*   **VFS:** [pyfuse3](https://github.com/libfuse/pyfuse3)
*   **Database:** [SQLite](https://www.sqlite.org/index.html) (FTS5)

---
