#!/usr/bin/env python3
"""
Мост Dolphin → FastAPI: публичная ссылка на файл в смонтированном CloudFusion.

Переменные окружения:
  CLOUDFUSION_API_BASE — базовый URL демона (по умолчанию http://127.0.0.1:8000).

Установка в меню Dolphin: см. integration/README.md
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request


def _notify(title: str, body: str) -> None:
    if shutil.which("notify-send"):
        subprocess.Popen(
            ["notify-send", "-a", "CloudFusion", title, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif shutil.which("kdialog"):
        subprocess.Popen(
            ["kdialog", "--passivepopup", f"{title}\n{body}", "5"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def run() -> int:
    if len(sys.argv) < 2:
        print("usage: share_bridge.py <file>", file=sys.stderr)
        return 2

    # Рядом с RPM лежит cloudfusion_filetools.py — делегируем, один код для меню Dolphin.
    here = os.path.dirname(os.path.abspath(__file__))
    tools = os.path.join(here, "cloudfusion_filetools.py")
    if os.path.isfile(tools):
        return subprocess.call([sys.executable, tools, "share", sys.argv[1]])

    path = os.path.abspath(sys.argv[1])
    base = os.environ.get("CLOUDFUSION_API_BASE", "http://127.0.0.1:8000").rstrip("/")
    url = f"{base}/api/files/publish"
    payload = json.dumps({"local_path": path}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(err_body).get("detail", err_body)
        except json.JSONDecodeError:
            detail = err_body or str(e)
        msg = f"HTTP {e.code}: {detail}"
        print(msg, file=sys.stderr)
        _notify("CloudFusion", msg)
        return 1
    except urllib.error.URLError as e:
        msg = f"нет связи с демоном ({base}): {e.reason}"
        print(msg, file=sys.stderr)
        _notify("CloudFusion", msg)
        return 1
    except Exception as e:
        print(str(e), file=sys.stderr)
        _notify("CloudFusion", str(e))
        return 1

    if data.get("status") != "ok":
        msg = data.get("detail") or data.get("error") or str(data)
        print(msg, file=sys.stderr)
        _notify("CloudFusion", str(msg))
        return 1

    public = data.get("url") or ""
    if public:
        print(public)
        _notify("CloudFusion: ссылка", public)
        if shutil.which("wl-copy"):
            subprocess.run(["wl-copy"], input=public.encode(), check=False)
        elif shutil.which("xclip"):
            subprocess.run(["xclip", "-selection", "clipboard"], input=public.encode(), check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
