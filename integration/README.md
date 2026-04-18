# Интеграция с рабочим столом (Dolphin / KDE)

**РЕПО** — корень клона проекта `disco-hack`. Пути ниже относительно **РЕПО**, если не указано абсолютно.

---

## Service Menu «публичная ссылка» (ручная установка без RPM)

Демон с API должен быть запущен (`python -m daemon.main` из **РЕПО**, см. корневой README). Точка монтирования по умолчанию — `~/CloudFusion` (переменная `MOUNTPOINT` в `daemon/.env`).

### Порядок действий

1. Откройте терминал, выполните `cd РЕПО`.
2. Убедитесь, что демон слушает `http://127.0.0.1:8000` (или задайте `CLOUDFUSION_API_BASE` при вызове моста).
3. Скопируйте шаблон **`integration/desktop/cloudfusion-link.desktop`** в каталог KIO:
   - для одного пользователя: **`~/.local/share/kio/servicemenus/`**
   - системно (root): **`/usr/share/kio/servicemenus/`**
4. В скопированном файле в строке **`Exec=`** должен быть **абсолютный** путь к скрипту **`РЕПО/integration/scripts/share_bridge.py`** (не относительный путь из РЕПО в короткой форме — Dolphin подставляет `%f`, путь к скрипту должен быть полным).

   Удобнее автоматизировать: из **РЕПО** запустите bash-скрипт **`integration/desktop/install-user.sh`** — он сам положит desktop-файл в `~/.local/share/kio/servicemenus/` и подставит путь к `share_bridge.py`.

5. Перезапустите Dolphin: `kquitapp5 dolphin` и снова откройте Dolphin (или просто перезапуск сессии).
6. В Dolphin: правый клик по **файлу** (не по каталогу) внутри смонтированного `YandexDisk` / `Nextcloud` под `~/CloudFusion` → пункт **«CloudFusion: Получить публичную ссылку»**.

Переменная **`CLOUDFUSION_API_BASE`** (например `http://127.0.0.1:8000`) задаёт URL API, если демон не на стандартном адресе.

### База демона

По умолчанию SQLite: **`~/.local/share/cloudfusion/cloudfusion.db`**. Иначе — переменная **`DB_PATH`** в `daemon/.env`.

---

## После установки RPM

Пути уже заданы пакетом:

- Ярлык приложения: **`/usr/share/applications/`** (см. `integration/desktop/cloudfusion-app.desktop` в репозитории как источник).
- Демон: **`/usr/libexec/cloudfusion/cloudfusion-daemon`**
- Мост Dolphin: **`/usr/libexec/cloudfusion/share_bridge.py`**
- KIO menu: **`/usr/share/kio/servicemenus/cloudfusion-link.desktop`**

Перезапустите Dolphin после установки.

Сборка RPM и список файлов для `SOURCES`: [`packaging/rpm/README.md`](../packaging/rpm/README.md) и [`packaging/rpm/cloudfusion.spec`](../packaging/rpm/cloudfusion.spec).

---

## Быстрая проверка моста из терминала

Рабочая директория может быть любой; важен **абсолютный** путь к файлу под `~/CloudFusion`:

```bash
python3 /полный/путь/к/РЕПО/integration/scripts/share_bridge.py "$HOME/CloudFusion/YandexDisk/.../файл.txt"
```

В stdout при успехе — URL; при ошибке — stderr и при наличии `notify-send` / `kdialog` — уведомление.

---

## Tauri и демон на Linux (кратко)

Логика в [`src-tauri/src/lib.rs`](../src-tauri/src/lib.rs): при старте UI ищется бинарь демона (`CLOUDFUSION_DAEMON_BIN` → рядом с exe → `/usr/libexec/cloudfusion/cloudfusion-daemon`), поднимается `127.0.0.1:8000`, при уничтожении главного окна процесс демона завершается. Подробные шаги сборки бинаря — в корневом **README**, сценарий C и E.

Сборка PyInstaller из **РЕПО**:

```bash
cd РЕПО
./scripts/build-linux-daemon.sh
```

Спека: [`daemon/pyinstaller/cloudfusion-daemon.spec`](../daemon/pyinstaller/cloudfusion-daemon.spec). Зависимости сборки: [`daemon/requirements-build.txt`](../daemon/requirements-build.txt).
