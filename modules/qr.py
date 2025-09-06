# -*- coding: utf-8 -*-
from __future__ import annotations
import re
import io
from typing import Dict, Tuple, Optional

import numpy as np  # type: ignore
import cv2  # type: ignore


def decode_qr_from_bytes(img_bytes: bytes) -> Optional[str]:
    """Decode QR payload from image bytes using OpenCV. Returns text or None."""
    try:
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(img)
        return data.strip() if data else None
    except Exception:
        return None


def parse_contact_from_qr(payload: str) -> Dict[str, str]:
    """
    Parse common QR payloads to contact fields (best-effort).
    Supports MECARD, vCard (BEGIN:VCARD), and simple URL/mailto/tel fallbacks.
    Returns a dict keys: first_name, last_name, email, phone, company, job, url
    """
    res = {
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "company": "",
        "job": "",
        "url": "",
    }
    if not payload:
        return res

    text = payload.strip()

    # MECARD format: MECARD:N:Last,First;TEL:...;EMAIL:...;ORG:...;TITLE:...;URL:...;;
    if text.upper().startswith("MECARD:"):
        body = text[7:]
        # Split on ; but keep empty last segment
        parts = body.split(";")
        fields = {}
        for p in parts:
            if ":" in p:
                k, v = p.split(":", 1)
                fields[k.upper()] = v
        n = fields.get("N", "")
        if n:
            # "Last,First"
            last, first = (n.split(",", 1) + [""])[:2]
            res["last_name"] = last.strip()
            res["first_name"] = first.strip()
        res["phone"] = fields.get("TEL", "").strip()
        res["email"] = fields.get("EMAIL", "").strip()
        res["company"] = fields.get("ORG", "").strip()
        res["job"] = fields.get("TITLE", "").strip()
        res["url"] = fields.get("URL", "").strip()
        return res

    # vCard
    if "BEGIN:VCARD" in text.upper():
        # Simple line parse
        for line in text.splitlines():
            u = line.strip()
            if u.upper().startswith("N:"):
                nval = u.split(":", 1)[1]
                # N:Last;First;Middle;Prefix;Suffix
                parts = (nval.split(";") + ["", "", "", "", ""])[:5]
                res["last_name"] = parts[0].strip()
                res["first_name"] = parts[1].strip()
            elif u.upper().startswith("FN:"):
                # if no N, try to split FN
                if not res["first_name"] and not res["last_name"]:
                    fn = u.split(":", 1)[1].strip()
                    if " " in fn:
                        first, last = fn.split(" ", 1)
                        res["first_name"] = first
                        res["last_name"] = last
                    else:
                        res["first_name"] = fn
            elif u.upper().startswith("TEL"):
                res["phone"] = u.split(":", 1)[1].strip()
            elif u.upper().startswith("EMAIL"):
                res["email"] = u.split(":", 1)[1].strip()
            elif u.upper().startswith("ORG:"):
                res["company"] = u.split(":", 1)[1].strip()
            elif u.upper().startswith("TITLE:"):
                res["job"] = u.split(":", 1)[1].strip()
            elif u.upper().startswith("URL:"):
                res["url"] = u.split(":", 1)[1].strip()
        return res

    # Simple fallbacks
    if text.lower().startswith("mailto:"):
        res["email"] = text[7:]
        return res
    if text.lower().startswith("tel:"):
        res["phone"] = text[4:]
        return res
    if text.lower().startswith(("http://", "https://")):
        res["url"] = text
        return res

    # Try email regex
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    if m:
        res["email"] = m.group(0)

    return res
