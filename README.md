# Запуск (Linux)

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
