# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from typing import Dict, Optional, Tuple, List

import numpy as np  # type: ignore
import cv2  # type: ignore

def _try_decode(detector: cv2.QRCodeDetector, img) -> Tuple[Optional[str], Optional[np.ndarray]]:
    # Try single decode
    data, pts, _ = detector.detectAndDecode(img)
    if data:
        return data.strip(), pts
    # Try multi decode
    try:
        retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
        if retval and decoded_info:
            for s in decoded_info:
                if s:
                    return s.strip(), points
    except Exception:
        pass
    return None, None

def decode_qr_from_ndarray(img) -> Optional[str]:
    """
    Robust QR decode from a BGR ndarray. Tries multiple preprocess steps.
    """
    detector = cv2.QRCodeDetector()
    # 1) Raw
    data, _ = _try_decode(detector, img)
    if data: return data
    # 2) Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    data, _ = _try_decode(detector, gray)
    if data: return data
    # 3) CLAHE (contrast)
    try:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        eq = clahe.apply(gray)
        data, _ = _try_decode(detector, eq)
        if data: return data
    except Exception:
        pass
    # 4) Adaptive threshold
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 2)
    data, _ = _try_decode(detector, th)
    if data: return data
    # 5) Resize (upscale)
    h, w = gray.shape[:2]
    if max(h, w) < 1200:
        big = cv2.resize(gray, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
        data, _ = _try_decode(detector, big)
        if data: return data
    # 6) Center crop
    ch, cw = int(h*0.6), int(w*0.6)
    y0, x0 = (h - ch)//2, (w - cw)//2
    crop = gray[y0:y0+ch, x0:x0+cw]
    data, _ = _try_decode(detector, crop)
    if data: return data
    return None

def decode_qr_from_bytes(img_bytes: bytes) -> Optional[str]:
    try:
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        return decode_qr_from_ndarray(img)
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
