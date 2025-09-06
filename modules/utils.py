# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Optional

def ensure_data_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def get_client_ip_hash() -> str:
    return hashlib.sha1(b"na").hexdigest()[:16]

def load_image_bytes(path: str) -> Optional[bytes]:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None
