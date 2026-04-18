# Интеграция с рабочим столом (Dolphin / KDE)

## Service Menu «публичная ссылка»

1. Убедитесь, что демон запущен (`python -m daemon.main` или `run_backend.py`) и точка монтирования совпадает с `MOUNTPOINT` в `.env` (по умолчанию `~/CloudFusion`).
2. Скопируйте `desktop/cloudfusion-link.desktop` в каталог меню KIO:
   - пользователь: `~/.local/share/kio/servicemenus/`
   - системно: `/usr/share/kio/servicemenus/` (нужны права root)
3. В строке `Exec=` укажите **абсолютный** путь к `integration/scripts/share_bridge.py` (или установите скрипт в `~/bin` и вызовите его оттуда). Для пользовательской установки удобнее [`install-user.sh`](desktop/install-user.sh).
4. Перезапустите Dolphin (или выполните `kquitapp5 dolphin` и откройте снова).
5. Правый клик по **файлу** (не каталогу) внутри `YandexDisk` или `Nextcloud` под точкой монтирования → действие «CloudFusion: Получить публичную ссылку».

Переменная `CLOUDFUSION_API_BASE` (например `http://127.0.0.1:8000`) задаёт адрес API, если демон слушает не localhost:8000.

### База демона (XDG)

По умолчанию SQLite лежит в `~/.local/share/cloudfusion/cloudfusion.db` (или `$XDG_DATA_HOME/cloudfusion/cloudfusion.db`). Переопределение: переменная окружения `DB_PATH`.

## Как тестировать быстро

- Запустить демон, смонтировать FUSE, положить тестовый файл в облако, дождаться строки в SQLite.
- Вызвать вручную:  
  `python3 integration/scripts/share_bridge.py "$HOME/CloudFusion/YandexDisk/…/file.txt"`  
  или с Nextcloud:  
  `…/CloudFusion/Nextcloud/…/file.txt`
- В ответе в stdout должна появиться URL; при ошибке — stderr и (если есть) `notify-send`.

## Установка RPM (ALT и др.)

Готовый spec: [`packaging/rpm/cloudfusion.spec`](../packaging/rpm/cloudfusion.spec). Краткая инструкция по подготовке `SOURCES`: [`packaging/rpm/README.md`](../packaging/rpm/README.md).

После установки RPM:

- В меню появится **CloudFusion** (файл [`cloudfusion-app.desktop`](desktop/cloudfusion-app.desktop) → `/usr/share/applications/`).
- Демон как бинарь: `/usr/libexec/cloudfusion/cloudfusion-daemon` (PyInstaller).
- KIO: `/usr/share/kio/servicemenus/cloudfusion-link.desktop` с `Exec=` на `/usr/libexec/cloudfusion/share_bridge.py`.

Перезапустите Dolphin, чтобы подхватить сервисное меню.

## Единый запуск: Tauri + демон (Linux)

В [`src-tauri/src/lib.rs`](../src-tauri/src/lib.rs) на **Linux** при старте приложения:

1. Ищется исполняемый файл демона: `CLOUDFUSION_DAEMON_BIN`, затем `cloudfusion-daemon` рядом с бинарём Tauri, затем `/usr/libexec/cloudfusion/cloudfusion-daemon` (как после RPM).
2. Дочерний процесс получает те же переменные окружения, что и UI (`YANDEX_*`, `ENABLE_FUSE`, `DB_PATH`, пути XDG и т.д.).
3. Ожидается готовность `127.0.0.1:8000`, затем открывается окно.
4. При закрытии главного окна дочерний демон завершается.

Если бинарь демона не найден (например, разработка без сборки PyInstaller), демон нужно запускать вручную: `python -m daemon.main` из корня репозитория.

### Сборка PyInstaller-демона

Из корня репозитория на Linux:

```bash
./scripts/build-linux-daemon.sh
```

Спека: [`daemon/pyinstaller/cloudfusion-daemon.spec`](../daemon/pyinstaller/cloudfusion-daemon.spec). Зависимости сборки: `daemon/requirements-build.txt`.

Для разработки по-прежнему можно использовать три процесса: демон, при необходимости `python -m daemon.core.mount` (Linux), `npm run tauri dev`.
