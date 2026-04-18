#!/usr/bin/env bash
# Точка входа в корне репозитория: полная сборка RPM (см. scripts/build-cloudfusion-rpm.sh).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
exec "$ROOT/scripts/build-cloudfusion-rpm.sh" "$@"
