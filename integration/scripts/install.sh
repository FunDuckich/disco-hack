#!/usr/bin/env bash
# install.sh — install CloudFusion Dolphin service menu and helper scripts.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS_DIR="$HOME/.local/share/cloudfusion"
# KDE 5: ~/.local/share/kservices5/ServiceMenus/
# KDE 6 / Dolphin 23+: ~/.local/share/kio/servicemenus/
KDE5_DIR="$HOME/.local/share/kservices5/ServiceMenus"
KDE6_DIR="$HOME/.local/share/kio/servicemenus"

echo "Installing CloudFusion Dolphin service menu..."

# Install helper scripts
mkdir -p "$SCRIPTS_DIR"
for script in cf-save-cache.sh cf-delete-cache.sh; do
    cp "$REPO_ROOT/integration/scripts/$script" "$SCRIPTS_DIR/$script"
    chmod +x "$SCRIPTS_DIR/$script"
done
echo "  Scripts installed to $SCRIPTS_DIR"

# Detect KDE version and install service menu to the right location
install_desktop() {
    local target_dir="$1"
    mkdir -p "$target_dir"
    cp "$REPO_ROOT/integration/desktop/cloudfusion.desktop" "$target_dir/cloudfusion.desktop"
    echo "  Service menu installed to $target_dir"
}

if dolphin --version 2>/dev/null | grep -qE "^Dolphin [2-9][0-9]\."; then
    install_desktop "$KDE6_DIR"
else
    install_desktop "$KDE5_DIR"
fi

echo "Done. Restart Dolphin (or log out and back in) to activate the context menu."
