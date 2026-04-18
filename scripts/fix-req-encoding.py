"""One-off: normalize daemon/requirements.txt to UTF-8 LF (fix UTF-16 / mojibake from editors)."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQ = ROOT / "daemon" / "requirements.txt"


def main() -> int:
    raw = REQ.read_bytes()
    text: str
    if raw.startswith(b"\xff\xfe"):
        text = raw.decode("utf-16-le")
    elif raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16-be")
    elif raw.startswith(b"\xef\xbb\xbf"):
        text = raw.removeprefix(b"\xef\xbb\xbf").decode("utf-8")
    else:
        # UTF-16-LE without BOM: NUL after ASCII in first lines
        if len(raw) > 4 and raw[1] == 0:
            text = raw.decode("utf-16-le")
        else:
            text = raw.decode("utf-8")

    lines = [ln.rstrip("\r") for ln in text.splitlines()]
    # Minor comment fix
    out_lines: list[str] = []
    for ln in lines:
        if "No module named requests" in ln and "'" not in ln.split("named", 1)[-1]:
            ln = ln.replace("No module named requests", "No module named 'requests'")
        out_lines.append(ln)
    body = "\n".join(out_lines) + "\n"
    REQ.write_bytes(body.encode("utf-8"))
    print(REQ, "-> utf-8, lf, lines:", len(out_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
