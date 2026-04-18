# Интеграция с рабочим столом (Dolphin / KDE)

## Service Menu «публичная ссылка»

1. Убедитесь, что демон запущен (`python -m daemon.main` или `run_backend.py`) и точка монтирования совпадает с `MOUNTPOINT` в `.env` (по умолчанию `~/CloudFusion`).
2. Скопируйте `desktop/cloudfusion-link.desktop` в каталог меню KIO:
   - пользователь: `~/.local/share/kio/servicemenus/`
   - системно: `/usr/share/kio/servicemenus/` (нужны права root)
3. В строке `Exec=` укажите **абсолютный** путь к `integration/scripts/share_bridge.py` (или установите скрипт в `~/bin` и вызовите его оттуда).
4. Перезапустите Dolphin (или выполните `kquitapp5 dolphin` и откройте снова).
5. Правый клик по **файлу** (не каталогу) внутри `YandexDisk` или `Nextcloud` под точкой монтирования → действие «CloudFusion: Получить публичную ссылку».

Переменная `CLOUDFUSION_API_BASE` (например `http://127.0.0.1:8000`) задаёт адрес API, если демон слушает не localhost:8000.

## Как тестировать быстро

- Запустить демон, смонтировать FUSE, положить тестовый файл в облако, дождаться строки в SQLite.
- Вызвать вручную:  
  `python3 integration/scripts/share_bridge.py "$HOME/CloudFusion/YandexDisk/…/file.txt"`  
  или с Nextcloud:  
  `…/CloudFusion/Nextcloud/…/file.txt`
- В ответе в stdout должна появиться URL; при ошибке — stderr и (если есть) `notify-send`.

## Единый пакет: Tauri + фронт + трей + Python sidecar

Сейчас в `src-tauri/src/lib.rs` только минимальный `Builder` — **трей и sidecar нужно добавить в Rust** (план):

1. **Sidecar:** в `tauri.conf.json` → `bundle.externalBin` или `app` spawn: при старте приложения запускать `python -m daemon.main` (или один бинарь из PyInstaller) с `cwd` на ресурс пакета, логи в файл.
2. **Трей:** зависимость `tauri` с фичей `tray-icon` (в Tauri 2 — плагин или встроенный API), в меню: «Открыть», «Остановить демон», «Выход».
3. **Сборка:** `npm run tauri build` — в бандл кладутся `frontendDist` и иконки; Python нужно либо вшить как `externalBin`, либо документировать зависимость пакета `cloudfusion-daemon` в `.deb`/RPM.
4. **.desktop для Dolphin** в post-install скрипте пакета: подставить установленный путь к `share_bridge.py` через `sed` от `$DESTDIR`.

Пока для разработки достаточно трёх процессов: терминал 1 — демон, терминал 2 — `python -m daemon.core.mount` (Linux), терминал 3 — `npm run tauri dev`.
