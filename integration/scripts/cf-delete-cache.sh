#!/usr/bin/env bash
# cf-delete-cache.sh — evict a CloudFusion file from local cache (revert to stub).
# Called by the Dolphin service menu with selected file path(s) as arguments.

set -euo pipefail

API_BASE="${CLOUDFUSION_API:-http://127.0.0.1:8000}"

notify() {
    if command -v notify-send &>/dev/null; then
        notify-send --icon=edit-delete "CloudFusion" "$1"
    elif command -v kdialog &>/dev/null; then
        kdialog --passivepopup "$1" 3
    else
        echo "CloudFusion: $1" >&2
    fi
}

urlencode() {
    python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$1"
}

for filepath in "$@"; do
    encoded="$(urlencode "$filepath")"
    response="$(curl -sf "${API_BASE}/api/files/locate?path=${encoded}" 2>/dev/null)" || true

    if [[ -z "$response" ]]; then
        notify "Not a CloudFusion file or daemon not running: $(basename "$filepath")"
        continue
    fi

    file_id="$(echo "$response" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")"
    status="$(echo  "$response" | python3 -c "import json,sys; print(json.load(sys.stdin)['status'])")"
    is_dir="$(echo  "$response" | python3 -c "import json,sys; print(json.load(sys.stdin)['is_dir'])")"

    if [[ "$is_dir" == "True" ]]; then
        notify "Cannot evict a folder: $(basename "$filepath")"
        continue
    fi

    if [[ "$status" != "cached" ]]; then
        notify "File is not in cache: $(basename "$filepath")"
        continue
    fi

    result="$(curl -sf -X POST "${API_BASE}/api/files/${file_id}/evict" 2>/dev/null)" || true
    if [[ -n "$result" ]]; then
        notify "Deleted from cache: $(basename "$filepath")"
    else
        notify "Failed to delete from cache: $(basename "$filepath")"
    fi
done
