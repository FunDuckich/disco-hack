# Запуск (Linux)
Запусить терминал в домашней директории. Убедиться, что установлены GIT и python3.
Скопировать репозиторий:
```bash
git clone https://github.com/FunDuckich/disco-hack/
```
# Переход в созданную директорию
```bash
cd disco-hack
```
# Переключение на ветку master
```bash
git checkout master
```

Из **корня репозитория**:

```bash
chmod +x scripts/build-local-bundle.sh
./scripts/build-local-bundle.sh
```

После сборки:

```bash
./src-tauri/target/release/app
```

Если в `src-tauri/target/release/` оказался бинарь **`cloudfusion`** вместо **`app`** — запускайте `./src-tauri/target/release/cloudfusion`.
