# -*- coding: utf-8 -*-
from __future__ import annotations
import base64
import io
import textwrap
from typing import Optional
from PIL import Image


def _fold_line(line: str, width: int = 74) -> str:
    """Fold long vCard lines at ~74 characters with CRLF + space continuation (RFC 2426)."""
    if len(line) <= width:
        return line
    chunks = textwrap.wrap(line, width)
    return chunks[0] + "\r\n " + "\r\n ".join(chunks[1:])


def _jpeg_base64(photo_bytes: bytes) -> str:
    """Ensure JPEG (square, max 800px, quality ~85), return base64 string."""
    img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    img.thumbnail((800, 800))
    w, h = img.size
    side = max(w, h)
    canvas = Image.new("RGB", (side, side), (255, 255, 255))
    canvas.paste(img, ((side - w) // 2, (side - h) // 2))
    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=85, optimize=True)
    return base64.b64encode(out.getvalue()).decode("ascii")


def build_vcard_bytes(
    fn: str,
    n_last: str,
    n_first: str,
    org: str,
    title: str,
    tel: str,
    email: str,
    url: str,
    adr_street: str,
    adr_city: str,
    adr_pc: str,
    adr_country: str,
    photo_bytes: Optional[bytes] = None,
) -> bytes:
    """Build a vCard 3.0 compatible with iOS/Android."""
    url_norm = url if url.startswith(("http://", "https://")) else "https://" + url
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{n_last};{n_first};;;",
        f"FN:{fn}",
        f"ORG:{org}",
        f"TITLE:{title}",
        f"TEL;TYPE=CELL,VOICE:{tel}",
        f"EMAIL;TYPE=INTERNET,WORK:{email}",
        f"URL:{url_norm}",
        f"ADR;TYPE=WORK:;;{adr_street};{adr_city};;{adr_pc};{adr_country}",
    ]
    if photo_bytes:
        jpg_b64 = _jpeg_base64(photo_bytes)
        photo_line = f"PHOTO;ENCODING=b;TYPE=JPEG:{jpg_b64}"
        lines.append(_fold_line(photo_line))
    lines.append("END:VCARD")
    vcard = "\r\n".join(lines) + "\r\n"  # CRLF
    return vcard.encode("utf-8")
