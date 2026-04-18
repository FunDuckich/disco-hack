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

## Установка и запуск: только RPM

Официальная поставка для Linux — **один RPM-пакет** по [`packaging/rpm/cloudfusion.spec`](packaging/rpm/cloudfusion.spec). Полная инструкция по зависимостям ОС, сбоям и ручным шагам: **[packaging/rpm/README.md](packaging/rpm/README.md)**.

### Сборка RPM у себя (кратко)

1. Клонировать репозиторий и перейти в корень (**РЕПО**).
2. Один раз поставить пакеты сборщика (ALT или Fedora) — **готовые команды по одной строке** в начале [packaging/rpm/README.md](packaging/rpm/README.md) (в т.ч. **`libwebkit2gtk4.1-devel`** для Tauri на ALT p11).
3. Запустить из РЕПО **[`build-rpm.sh`](build-rpm.sh)** (или то же самое: [`scripts/build-cloudfusion-rpm.sh`](scripts/build-cloudfusion-rpm.sh)). Пакеты ОС скрипт **не** ставит; подготавливает **`SOURCES`** и вызывает **`rpmbuild`**.

```bash
./build-rpm.sh
```

Опционально сначала подтянуть коммиты: **`./build-rpm.sh --pull`** (нужен **`git`** и настроенный **`git pull`** для ветки).

Порядок внутри скрипта: проверки инструментов → **`daemon/.env`** из примера при отсутствии → **`npm install`** → **`npm run tauri build`** → **[`scripts/build-linux-daemon.sh`](scripts/build-linux-daemon.sh)** (демон в **`build/daemon-release/`**, не в **`dist/`**) → **`SOURCES`** → нормализованный **`SPECS/cloudfusion.spec`** (без BOM/CRLF) → **`rpmbuild -ba`**. Флаги: **`--skip-npm`**, **`--only-sources`**, **`--pull`**, **`RPMBUILD_TOPDIR`**.

4. Готовый файл: **`~/rpmbuild/RPMS/x86_64/cloudfusion-*.rpm`** (или подкаталог `RPMS` вашего `_topdir`).

Тот же путь **вручную** (без скрипта) расписан в [packaging/rpm/README.md](packaging/rpm/README.md) шагами **1–8**.

### Уже есть готовый `.rpm`

```bash
sudo rpm -Uvh cloudfusion-0.1.0-*.rpm
```

Пункт в меню **CloudFusion**; для OAuth в сеансе нужны **`YANDEX_CLIENT_ID`** и **`YANDEX_CLIENT_SECRET`** (см. [`daemon/.env.example`](daemon/.env.example)). После установки перезапустите Dolphin для KIO — [`integration/README.md`](integration/README.md).

База SQLite по умолчанию: **`~/.local/share/cloudfusion/cloudfusion.db`** (`DB_PATH` в `daemon/.env` при ручном запуске демона).

---

## 🎨 Стек технологий
*   **Desktop:** [Tauri](https://tauri.app/) (Rust)
*   **Frontend:** [React](https://reactjs.org/) + [Vite](https://vitejs.dev/)
*   **Backend Daemon:** [Python 3.12](https://www.python.org/) + [FastAPI](https://fastapi.tiangolo.com/)
*   **VFS:** [pyfuse3](https://github.com/libfuse/pyfuse3)
*   **Database:** [SQLite](https://www.sqlite.org/index.html) (FTS5)

---
