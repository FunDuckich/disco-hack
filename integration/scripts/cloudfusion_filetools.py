#!/usr/bin/env python3
"""
Dolphin → демон CloudFusion: публичная ссылка, сброс локального кэша, pin, QR.

Переменные окружения:
  CLOUDFUSION_API_BASE — URL демона (по умолчанию http://127.0.0.1:8000).

Команды:
  share <file>   — публичная ссылка (в буфер + уведомление)
  drop <file>    — POST .../drop_local_cache
  pin <file>     — закрепить в кэше (LRU не вытеснит)
  unpin <file>
  qr <file>      — ссылка + PNG QR (если установлен qrencode)

Сообщение об ошибке для файла вне маунта / без демона совпадает с ожидаемым в UI Dolphin.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request


def _api_base() -> str:
    return os.environ.get("CLOUDFUSION_API_BASE", "http://127.0.0.1:8000").rstrip("/")


def _notify(title: str, body: str) -> None:
    if shutil.which("notify-send"):
        subprocess.Popen(
            ["notify-send", "-a", "CloudFusion", title, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif shutil.which("kdialog"):
        subprocess.Popen(
            ["kdialog", "--passivepopup", f"{title}\n{body}", "8"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _user_fail(path: str, extra: str | None = None) -> int:
    base = os.path.basename(path) or path
    msg = f"Not a CloudFusion file or daemon not running: {base}"
    if extra:
        msg = f"{msg} ({extra})"
    print(msg, file=sys.stderr)
    _notify("CloudFusion", msg)
    return 1


def _http_json(method: str, url: str, body: dict | None = None, timeout: float = 120.0) -> tuple[int, dict | list | str]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw:
                return resp.status, {}
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(err).get("detail", err)
        except json.JSONDecodeError:
            detail = err or str(e)
        return e.code, {"detail": detail}
    except urllib.error.URLError as e:
        return -1, {"detail": str(e.reason)}
    except Exception as e:
        return -1, {"detail": str(e)}


def _daemon_ok() -> bool:
    code, _ = _http_json("GET", f"{_api_base()}/health", None, timeout=4.0)
    return code == 200


def _resolve(path: str) -> tuple[dict | None, int]:
    if not _daemon_ok():
        return None, _user_fail(path, "daemon unreachable")
    code, data = _http_json(
        "POST",
        f"{_api_base()}/api/files/resolve_local",
        {"local_path": os.path.abspath(path)},
        timeout=30.0,
    )
    if code != 200 or not isinstance(data, dict):
        detail = data.get("detail", data) if isinstance(data, dict) else str(data)
        return None, _user_fail(path, str(detail)[:200])
    return data, 0


def _publish_url(path: str) -> tuple[str | None, int]:
    if not _daemon_ok():
        return None, _user_fail(path)
    code, data = _http_json(
        "POST",
        f"{_api_base()}/api/files/publish",
        {"local_path": os.path.abspath(path)},
        timeout=120.0,
    )
    if code != 200:
        detail = data.get("detail", data) if isinstance(data, dict) else str(data)
        return None, _user_fail(path, str(detail)[:200])
    if not isinstance(data, dict) or data.get("status") != "ok":
        return None, _user_fail(path, str(data))
    return (data.get("url") or "") or None, 0


def cmd_share(path: str) -> int:
    public, err = _publish_url(path)
    if err:
        return err
    if public:
        print(public)
        _notify("CloudFusion: ссылка", public)
        if shutil.which("wl-copy"):
            subprocess.run(["wl-copy"], input=public.encode(), check=False)
        elif shutil.which("xclip"):
            subprocess.run(["xclip", "-selection", "clipboard"], input=public.encode(), check=False)
    return 0


def cmd_drop(path: str) -> int:
    meta, err = _resolve(path)
    if err:
        return err
    assert meta is not None
    if meta.get("is_dir"):
        return _user_fail(path, "is a directory")
    fid = int(meta["file_id"])
    code, data = _http_json(
        "POST",
        f"{_api_base()}/api/files/{fid}/drop_local_cache",
        None,
        timeout=60.0,
    )
    if code != 200:
        detail = data.get("detail", data) if isinstance(data, dict) else str(data)
        return _user_fail(path, str(detail)[:200])
    _notify("CloudFusion", "Локальный кэш сброшен")
    return 0


def cmd_pin(path: str, pinned: bool) -> int:
    meta, err = _resolve(path)
    if err:
        return err
    assert meta is not None
    if meta.get("is_dir"):
        return _user_fail(path, "is a directory")
    fid = int(meta["file_id"])
    code, data = _http_json(
        "POST",
        f"{_api_base()}/api/files/{fid}/pin",
        {"pinned": pinned},
        timeout=30.0,
    )
    if code != 200:
        detail = data.get("detail", data) if isinstance(data, dict) else str(data)
        return _user_fail(path, str(detail)[:200])
    _notify("CloudFusion", "Закрепление обновлено" if pinned else "Снято закрепление")
    return 0


def cmd_qr(path: str) -> int:
    url, err = _publish_url(path)
    if err:
        return err
    if not url:
        return _user_fail(path, "no public url")
    print(url)
    qrencode = shutil.which("qrencode")
    if not qrencode:
        _notify("CloudFusion", "Установите qrencode для QR")
        return 0
    fd, png = tempfile.mkstemp(prefix="cf-qr-", suffix=".png")
    os.close(fd)
    try:
        subprocess.run([qrencode, "-o", png, "-s", "8", url], check=True, timeout=30)
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", png], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            _notify("CloudFusion QR", png)
    except Exception as e:
        _notify("CloudFusion QR", str(e))
        return 1
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "usage: cloudfusion_filetools.py <share|drop|pin|unpin|qr> <file>",
            file=sys.stderr,
        )
        return 2
    cmd = sys.argv[1].lower().strip()
    path = sys.argv[2]
    if cmd == "share":
        return cmd_share(path)
    if cmd == "drop":
        return cmd_drop(path)
    if cmd == "pin":
        return cmd_pin(path, True)
    if cmd == "unpin":
        return cmd_pin(path, False)
    if cmd == "qr":
        return cmd_qr(path)
    print("unknown command:", cmd, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
