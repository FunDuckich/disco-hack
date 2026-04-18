#!/usr/bin/env bash
# Установка Service Menu Dolphin для CloudFusion (пользовательский каталог).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BRIDGE="$ROOT/integration/scripts/share_bridge.py"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/kio/servicemenus"
mkdir -p "$DEST"
export CF_ROOT="$ROOT"
export CF_BRIDGE="$BRIDGE"
export CF_DEST="$DEST/cloudfusion-link.desktop"
python3 <<'PY'
import os
from pathlib import Path
root = Path(os.environ["CF_ROOT"])
bridge = Path(os.environ["CF_BRIDGE"])
out = Path(os.environ["CF_DEST"])
text = (root / "integration/desktop/cloudfusion-link.desktop").read_text(encoding="utf-8")
text = text.replace("REPLACE_CF_SHARE_BRIDGE", str(bridge))
out.write_text(text, encoding="utf-8")
PY
echo "Установлено: $DEST/cloudfusion-link.desktop"
echo "Перезапустите Dolphin (kquitapp5 dolphin && dolphin)."
