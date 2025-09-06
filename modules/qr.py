# -*- coding: utf-8 -*-
from __future__ import annotations
import re, io
from typing import Dict, Optional
import numpy as np  # type: ignore
import cv2  # type: ignore

def decode_qr_from_bytes(img_bytes: bytes) -> Optional[str]:
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
    res = {"first_name":"","last_name":"","email":"","phone":"","company":"","job":"","url":""}
    if not payload:
        return res
    t = payload.strip()
    if t.upper().startswith("MECARD:"):
        body = t[7:]
        parts = body.split(";")
        fields = {}
        for p in parts:
            if ":" in p:
                k,v = p.split(":",1)
                fields[k.upper()] = v
        n = fields.get("N","")
        if n:
            last, first = (n.split(",",1)+[""])[:2]
            res["last_name"] = last.strip(); res["first_name"] = first.strip()
        res["phone"] = fields.get("TEL","").strip()
        res["email"] = fields.get("EMAIL","").strip()
        res["company"] = fields.get("ORG","").strip()
        res["job"] = fields.get("TITLE","").strip()
        res["url"] = fields.get("URL","").strip()
        return res
    if "BEGIN:VCARD" in t.upper():
        for line in t.splitlines():
            u = line.strip()
            if u.upper().startswith("N:"):
                parts = (u.split(":",1)[1].split(";")+["",""])[:2]
                res["last_name"], res["first_name"] = parts[0].strip(), parts[1].strip()
            elif u.upper().startswith("FN:"):
                if not res["first_name"] and not res["last_name"]:
                    fn = u.split(":",1)[1].strip()
                    if " " in fn: res["first_name"], res["last_name"] = fn.split(" ",1)
                    else: res["first_name"] = fn
            elif u.upper().startswith("TEL"):
                res["phone"] = u.split(":",1)[1].strip()
            elif u.upper().startswith("EMAIL"):
                res["email"] = u.split(":",1)[1].strip()
            elif u.upper().startswith("ORG:"):
                res["company"] = u.split(":",1)[1].strip()
            elif u.upper().startswith("TITLE:"):
                res["job"] = u.split(":",1)[1].strip()
            elif u.upper().startswith("URL:"):
                res["url"] = u.split(":",1)[1].strip()
        return res
    if t.lower().startswith("mailto:"):
        res["email"] = t[7:]; return res
    if t.lower().startswith("tel:"):
        res["phone"] = t[4:]; return res
    if t.lower().startswith(("http://","https://")):
        res["url"] = t; return res
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", t)
    if m: res["email"] = m.group(0)
    return res
