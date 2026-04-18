# Сборка RPM (ALT / rpm-based)

**РЕПО** — корень клона `disco-hack`. Все команды ниже выполняйте из **РЕПО** (`cd` в этот каталог).

Каталог **`~/rpmbuild/SOURCES`** — стандартное место для `Source0`…`Source4` в spec (если у вас другой `%{_topdir}`, подставьте свой `SOURCES`).

---

## Полный порядок действий

### 1. Собрать демон (PyInstaller)

```bash
cd РЕПО
chmod +x scripts/build-linux-daemon.sh   # при необходимости
./scripts/build-linux-daemon.sh
```

Проверка: должен появиться файл **`РЕПО/dist/cloudfusion-daemon`** (исполняемый).

### 2. Собрать приложение Tauri

```bash
cd РЕПО
npm install
npm run tauri build
```

Найдите **бинарь с именем как у приложения** (часто `cloudfusion`) внутри:

**`РЕПО/src-tauri/target/release/bundle/`**

Точный подкаталог зависит от цели (`deb`, `rpm`, `appimage` и т.д.). Скопируйте **исполняемый файл GUI** в `~/rpmbuild/SOURCES/cloudfusion` — имя файла в `SOURCES` должно быть **`cloudfusion`** без расширения (так задано в `cloudfusion.spec` как `Source0`).

### 3. Скопировать остальные файлы в SOURCES

Из **РЕПО**:

```bash
mkdir -p ~/rpmbuild/SOURCES
cp dist/cloudfusion-daemon ~/rpmbuild/SOURCES/cloudfusion-daemon
cp integration/scripts/share_bridge.py ~/rpmbuild/SOURCES/
cp integration/desktop/cloudfusion-link.desktop ~/rpmbuild/SOURCES/
cp integration/desktop/cloudfusion-app.desktop ~/rpmbuild/SOURCES/
cp путь/к/собранному/бинарю/GUI ~/rpmbuild/SOURCES/cloudfusion
```

Последняя строка — это файл из шага 2, сохранённый под именем **`cloudfusion`**.

Итого в `~/rpmbuild/SOURCES` должны лежать **пять** имён:

| Имя в SOURCES | Откуда взять |
|---------------|----------------|
| `cloudfusion` | Бинарь Tauri из `src-tauri/target/release/bundle/...` |
| `cloudfusion-daemon` | `dist/cloudfusion-daemon` |
| `share_bridge.py` | `integration/scripts/share_bridge.py` |
| `cloudfusion-link.desktop` | `integration/desktop/cloudfusion-link.desktop` |
| `cloudfusion-app.desktop` | `integration/desktop/cloudfusion-app.desktop` |

### 4. Запустить rpmbuild

Из **РЕПО** (spec лежит в репозитории):

```bash
cd РЕПО
rpmbuild -ba packaging/rpm/cloudfusion.spec
```

Готовый `.rpm` обычно окажется в `~/rpmbuild/RPMS/x86_64/` (или аналогично для вашей архитектуры).

### 5. Установить на целевой системе

```bash
sudo rpm -Uvh ~/rpmbuild/RPMS/x86_64/cloudfusion-*.rpm
```

Далее — запуск из меню, перезапуск Dolphin (см. корневой README и [`integration/README.md`](../../integration/README.md)).

---

Имена пакетов в **`Requires:`** в [`cloudfusion.spec`](cloudfusion.spec) при необходимости поправьте под ваш дистрибутив (FUSE / libfuse3).
