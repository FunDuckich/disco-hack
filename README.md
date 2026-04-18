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

### Что подготовить один раз

- **Python 3.12+**, **Node.js 18+**, **Rust** (для `npm run tauri dev` и `npm run tauri build`).
- Скопируйте [`daemon/.env.example`](daemon/.env.example) в **`daemon/.env`** в корне репозитория и укажите **`YANDEX_CLIENT_ID`** и **`YANDEX_CLIENT_SECRET`** (без этого демон не стартует).
- Для монтирования **`~/CloudFusion`** нужны **Linux или WSL**, пакеты **`libfuse3`** и зависимости из `daemon/requirements.txt` (в т.ч. `pyfuse3`).

База SQLite по умолчанию: **`~/.local/share/cloudfusion/cloudfusion.db`** (или `$XDG_DATA_HOME/cloudfusion/cloudfusion.db`). Переопределение: переменная **`DB_PATH`** в `.env`.

---

### Обычная разработка (два терминала)

Все команды Python — из **корня репозитория** (`disco-hack`), чтобы импортировался пакет `daemon`.

**Терминал 1 — демон (API на `http://127.0.0.1:8000`):**

```bash
git clone https://github.com/FunDuckich/disco-hack.git
cd disco-hack
cd daemon
python -m venv venv
```

Активация venv:

- Linux / macOS: `source venv/bin/activate`
- Windows: `venv\Scripts\activate`

Далее:

```bash
pip install -r requirements.txt
cd ..
python -m daemon.main
```

Можно вместо последней строки: `python run_backend.py`. Тестовое наполнение: `python -m daemon.seed`.

**Терминал 2 — окно CloudFusion:**

```bash
cd disco-hack
npm install
npm run tauri dev
```

Откроется окно; интерфейс обращается к тому же `127.0.0.1:8000`.

На **Windows** демон всегда запускайте **вручную** (терминал 1). На **Linux** см. следующий блок — демон может подняться вместе с Tauri, если уже собран бинарь PyInstaller.

**Опционально (только Linux / WSL) — FUSE**, из корня репозитория, с активированным venv:

```bash
python run_mount.py
```

То же по смыслу: `python -m daemon.core.mount`. Не запускайте `daemon/core/mount.py` напрямую как файл — сломаются относительные импорты.

**PyCharm:** конфигурация Python, **модуль** `daemon.core.mount` или скрипт `run_mount.py`, **рабочая директория** — корень репо; интерпретатор с установленными `pyfuse3` и системным FUSE (часто WSL).

---

### Linux: один запуск UI + демон (PyInstaller)

Если есть исполняемый файл демона, Tauri на Linux может **сам** его запустить до открытия окна и завершить при закрытии главного окна. Поиск бинаря:

1. переменная **`CLOUDFUSION_DAEMON_BIN`** (полный путь), или  
2. файл **`cloudfusion-daemon`** рядом с бинарём Tauri, или  
3. путь после RPM: **`/usr/libexec/cloudfusion/cloudfusion-daemon`**.

Сборка демона:

```bash
./scripts/build-linux-daemon.sh
# результат: ./dist/cloudfusion-daemon
```

Пример:

```bash
export CLOUDFUSION_DAEMON_BIN="$PWD/dist/cloudfusion-daemon"
npm run tauri dev
```

Переменные окружения (`YANDEX_*`, `ENABLE_FUSE`, `DB_PATH` и др.) демон наследует от процесса Tauri. Если бинарь **не найден**, работайте как в разделе «два терминала» выше.

---

### Сборка установщика (без RPM)

```bash
npm install
npm run tauri build
```

Артефакты смотрите в `src-tauri/target/release/bundle/` (формат зависит от ОС).

---

### Установка на Linux через RPM (ALT и другие rpm-based)

Соберите пакет на машине с `rpmbuild`, затем установите обычным способом, например `sudo rpm -Uvh cloudfusion-*.rpm` (или через графический установщик дистрибутива).

1. Соберите демон: `./scripts/build-linux-daemon.sh`.  
2. Соберите приложение: `npm run tauri build`, возьмите бинарь GUI из `src-tauri/target/release/bundle/`.  
3. Положите файлы в `SOURCES` и выполните `rpmbuild -ba packaging/rpm/cloudfusion.spec`, как в [`packaging/rpm/README.md`](packaging/rpm/README.md) (там же список файлов для `SOURCES`).  
4. После установки RPM: приложение **CloudFusion** в меню; демон — `/usr/libexec/cloudfusion/cloudfusion-daemon`; для пункта Dolphin «публичная ссылка» перезапустите Dolphin (`kquitapp5 dolphin && dolphin`).

Подробности по Dolphin: [`integration/README.md`](integration/README.md). Дополнительно для CORS: переменные **`ALLOWED_ORIGINS`** и **`CORS_ORIGIN_REGEX`** в [`daemon/main.py`](daemon/main.py).

---

## 🎨 Стек технологий
*   **Desktop:** [Tauri](https://tauri.app/) (Rust)
*   **Frontend:** [React](https://reactjs.org/) + [Vite](https://vitejs.dev/)
*   **Backend Daemon:** [Python 3.12](https://www.python.org/) + [FastAPI](https://fastapi.tiangolo.com/)
*   **VFS:** [pyfuse3](https://github.com/libfuse/pyfuse3)
*   **Database:** [SQLite](https://www.sqlite.org/index.html) (FTS5)

---
