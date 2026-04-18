# Сборка RPM (ALT / rpm-based)

Перед `rpmbuild` положите бинарники в `~/rpmbuild/SOURCES/` (или `%{_topdir}/SOURCES`):

| Файл в SOURCES | Источник |
|----------------|----------|
| `cloudfusion` | Бинарь Tauri после `npm run tauri build` (из `src-tauri/target/release/bundle/` или установите путь в spec) |
| `cloudfusion-daemon` | `dist/cloudfusion-daemon` после [`scripts/build-linux-daemon.sh`](../../scripts/build-linux-daemon.sh) |
| `share_bridge.py` | Копия [`integration/scripts/share_bridge.py`](../../integration/scripts/share_bridge.py) |
| `cloudfusion-link.desktop` | Копия [`integration/desktop/cloudfusion-link.desktop`](../../integration/desktop/cloudfusion-link.desktop) |
| `cloudfusion-app.desktop` | Копия [`integration/desktop/cloudfusion-app.desktop`](../../integration/desktop/cloudfusion-app.desktop) |

Пример:

```bash
./scripts/build-linux-daemon.sh
mkdir -p ~/rpmbuild/SOURCES
cp dist/cloudfusion-daemon ~/rpmbuild/SOURCES/
cp integration/scripts/share_bridge.py ~/rpmbuild/SOURCES/
cp integration/desktop/cloudfusion-link.desktop ~/rpmbuild/SOURCES/
cp integration/desktop/cloudfusion-app.desktop ~/rpmbuild/SOURCES/
# cloudfusion (GUI) — скопируйте из артефакта `tauri build` под вашу цель
```

Далее:

```bash
rpmbuild -ba packaging/rpm/cloudfusion.spec
```

Имена пакетов `Requires` для FUSE при необходимости поправьте под ваш дистрибутив (см. комментарии в spec).
