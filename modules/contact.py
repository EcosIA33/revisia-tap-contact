# -*- coding: utf-8 -*-
from __future__ import annotations
import base64, io, textwrap
from typing import Optional
from PIL import Image

def _fold_line(line: str, width: int = 74) -> str:
    if len(line) <= width:
        return line
    chunks = textwrap.wrap(line, width)
    return chunks[0] + "\r\n " + "\r\n ".join(chunks[1:])

def _jpeg_base64(photo_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    img.thumbnail((800, 800))
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode("ascii")

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
    url_norm = (url or "").replace(";", "\\;").replace(",", "\\,")
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
        lines.append(_fold_line(f"PHOTO;ENCODING=b;TYPE=JPEG:{jpg_b64}"))
    lines.append("END:VCARD")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")
