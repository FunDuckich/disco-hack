#!/usr/bin/env bash
# Установка Service Menu Dolphin для CloudFusion (пользовательский каталог).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOLS="$ROOT/integration/scripts/cloudfusion_filetools.py"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/kio/servicemenus"
mkdir -p "$DEST"
export CF_ROOT="$ROOT"
export CF_TOOLS="$TOOLS"
export CF_DEST="$DEST/cloudfusion-link.desktop"
python3 <<'PY'
import os
from pathlib import Path
root = Path(os.environ["CF_ROOT"])
tools = Path(os.environ["CF_TOOLS"])
out = Path(os.environ["CF_DEST"])
text = (root / "integration/desktop/cloudfusion-link.desktop").read_text(encoding="utf-8")
text = text.replace("REPLACE_CF_FILETOOLS", str(tools))
out.write_text(text, encoding="utf-8")
PY
echo "Установлено: $DEST/cloudfusion-link.desktop"
echo "Перезапустите Dolphin (kquitapp5 dolphin && dolphin)."
