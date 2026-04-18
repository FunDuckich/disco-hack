#!/usr/bin/env bash
# install.sh — install CloudFusion Dolphin service menu and helper scripts.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS_DIR="$HOME/.local/share/cloudfusion"
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

# Install to both KDE5 and KDE6 locations so it works regardless of version
for target_dir in "$KDE5_DIR" "$KDE6_DIR"; do
    mkdir -p "$target_dir"
    cp "$REPO_ROOT/integration/desktop/cloudfusion.desktop" "$target_dir/cloudfusion.desktop"
    echo "  Service menu installed to $target_dir"
done

# Rebuild the KDE service cache
for cmd in kbuildsycoca6 kbuildsycoca5 kbuildsycoca; do
    if command -v "$cmd" &>/dev/null; then
        echo "  Rebuilding service cache via $cmd..."
        "$cmd" --noincremental 2>/dev/null || true
        break
    fi
done

echo "Done. Restart Dolphin to activate the context menu:"
echo "  dolphin --quit; dolphin &"
