# Интеграция с рабочим столом (Dolphin / KDE)

## Если вы ставите из RPM

Сборка пакета и объяснение, **откуда берутся npm, Tauri и бинарь приложения**, — только здесь:

**[packaging/rpm/README.md](../packaging/rpm/README.md)**

После `rpm -Uvh` в системе появятся:

| Путь | Назначение |
|------|------------|
| `/usr/bin/cloudfusion` | Окно приложения из меню |
| `/usr/libexec/cloudfusion/cloudfusion-daemon` | Демон API (Tauri на Linux при старте окна может запускать его сам) |
| `/usr/libexec/cloudfusion/share_bridge.py` | Мост для Dolphin |
| `/usr/share/applications/cloudfusion-app.desktop` | Ярлык |
| `/usr/share/kio/servicemenus/cloudfusion-link.desktop` | Пункт «публичная ссылка» в Dolphin |

Перезапустите Dolphin: `kquitapp5 dolphin` и снова откройте его.

Переменная **`CLOUDFUSION_API_BASE`** (например `http://127.0.0.1:8000`) нужна мосту, если API не на стандартном адресе.

---

## Ручная установка KIO без RPM (разработка)

1. Демон должен слушать API (обычно `python -m daemon.main` из **корня репозитория** — см. `daemon/.env`).
2. Скопируйте `integration/desktop/cloudfusion-link.desktop` в `~/.local/share/kio/servicemenus/`.
3. В `Exec=` укажите **абсолютный** путь к `integration/scripts/share_bridge.py` или запустите из корня репо: **`integration/desktop/install-user.sh`** — он подставит пути сам.
4. Перезапустите Dolphin.

База по умолчанию: `~/.local/share/cloudfusion/cloudfusion.db` (`DB_PATH` в `daemon/.env`).

---

## Проверка моста из терминала

```bash
python3 /абсолютный/путь/к/репо/integration/scripts/share_bridge.py "$HOME/CloudFusion/YandexDisk/.../файл.txt"
```

При успехе URL — в stdout.
