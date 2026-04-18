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

## 📂 Структура проекта

*   `/daemon` — Сердце проекта: FUSE-драйвер, работа с SQLite и API облаков.
*   `/src` — Фронтенд на React (TypeScript): интерфейс настроек и мониторинга.
*   `/src-tauri` — Бэкенд на Rust: управление окнами, треем и запуск Sidecar-процессов.
*   `/integration` — Системные конфиги для ALT Linux (Service Menus для Dolphin).

---

## 🛠 Установка и запуск (для разработчиков)

### Требования:
*   Python 3.12+
*   Node.js 18+
*   Rust (для сборки Tauri)
*   Библиотека `libfuse` (стандарт в ALT Linux)

### Быстрый старт:

1.  **Клонируйте репозиторий:**
    ```bash
    git clone https://github.com/FunDuckich/disco-hack.git
    cd disco-hack
    ```

2.  **Настройте бэкенд:** импорты внутри `daemon` — относительные, запускайте из **корня репозитория** (`disco-hack`), чтобы пакет `daemon` был виден Python.
    ```bash
    cd disco-hack
    pip install --ignored-installed -r deamon/requirements.txt
    cd ..
    python -m daemon.main
    ```
    в другом терминали :
    ```
    cd disco-hack
    python -m daemon.core.mount
    ```
    

4.  **FUSE (mount) — только Linux / WSL.** Скрипт `daemon/core/mount.py` **нельзя** запускать как файл (`python .../mount.py`): относительные импорты работают только как модуль пакета `daemon` из **корня репозитория**.
    ```bash
    cd /mnt/c/Documents/GitHub/disco-hack
    source daemon/venv/bin/activate
    python run_mount.py
    ```
    То же самое: `python -m daemon.core.mount` из того же каталога `disco-hack`. В Windows PowerShell FUSE обычно недоступен — открой терминал **дистрибутива WSL** (Ubuntu), перейди в `cd` на путь под `/mnt/c/...` к клону и запусти команду там.

    **PyCharm:** Run → Edit Configurations → **+** → Python → **Module name:** `daemon.core.mount` → **Working directory:** корень проекта (`disco-hack`, переменная `$ProjectFileDir$`). Интерпретатор — WSL, где стоят `pyfuse3` и `libfuse`. Либо **Script path:** `run_mount.py`, working directory — снова корень репо.

5.  **Запустите интерфейс (в другом терминале):**
    ```bash
    npm install
    npm run tauri dev
    ```

---

## 🎨 Стек технологий
*   **Desktop:** [Tauri](https://tauri.app/) (Rust)
*   **Frontend:** [React](https://reactjs.org/) + [Vite](https://vitejs.dev/)
*   **Backend Daemon:** [Python 3.12](https://www.python.org/) + [FastAPI](https://fastapi.tiangolo.com/)
*   **VFS:** [pyfuse3](https://github.com/libfuse/pyfuse3)
*   **Database:** [SQLite](https://www.sqlite.org/index.html) (FTS5)

---
