from __future__ import annotations

import hashlib
import re
from pathlib import Path

_SAFE_RE = re.compile(r"[^A-Za-z0-9._()\- ]+")


def safe_filename(name: str) -> str:
    name = Path(name).name.strip().replace("\x00", "")
    name = _SAFE_RE.sub("_", name)
    if not name:
        return "arquivo"
    return name[:180]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
