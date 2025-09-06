# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional, Dict, List
import cv2  # type: ignore
import numpy as np  # type: ignore
import re

def _decode_qr_variants(img: np.ndarray) -> Optional[str]:
    """Try multiple preprocessing to improve decoding on noisy prints."""
    det = cv2.QRCodeDetector()
    # variants to try
    variants: List[np.ndarray] = []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    variants.append(gray)
    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
    variants.append(clahe)
    # Sharpen
    blur = cv2.GaussianBlur(gray, (0,0), 2.0)
    sharp = cv2.addWeighted(gray, 1.6, blur, -0.6, 0)
    variants.append(sharp)
    # Thresholds
    variants.append(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY,31,5))
    variants.append(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,3))
    _, otsu = cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    variants.append(otsu)
    # Try each
    for v in variants:
        data, points, _ = det.detectAndDecode(v)
        if data:
            return data
    return None

def decode_qr_from_bytes(b: bytes) -> Optional[str]:
    """Decode QR from image bytes (PNG/JPG)."""
    arr = np.frombuffer(b, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    return _decode_qr_variants(img)

def parse_contact_from_qr(text: str) -> Dict[str,str]:
    """Parse minimal contact info from common QR payloads (vCard, MECARD, mailto, tel, heuristics)."""
    res = {
        "first_name":"",
        "last_name":"",
        "email":"",
        "phone":"",
        "company":"",
        "job":"",
        "url":"",
    }
    if not text:
        return res
    t = text.strip()
    upper = t.upper()

    # vCard basic fields
    if upper.startswith("BEGIN:VCARD"):
        kv = {}
        for ln in [x.strip() for x in t.splitlines() if ":" in x]:
            k, v = ln.split(":",1)
            key = k.split(";")[0].upper()
            kv[key] = v.strip()
        if "N" in kv:
            parts = [p.strip() for p in kv["N"].split(";")]
            if parts:
                res["last_name"] = parts[0]
            if len(parts)>1:
                res["first_name"] = parts[1]
        if "FN" in kv and not (res["first_name"] or res["last_name"]):
            words = kv["FN"].split()
            if len(words)>=2:
                res["first_name"], res["last_name"] = words[0], " ".join(words[1:])
            else:
                res["first_name"] = kv["FN"]
        res["email"] = kv.get("EMAIL","")
        res["phone"] = kv.get("TEL","")
        res["company"] = kv.get("ORG","")
        res["job"] = kv.get("TITLE","")
        res["url"] = kv.get("URL","")
        return res

    # MECARD:N:Nom,Prénom;TEL:...;EMAIL:...;ORG:...;;
    if upper.startswith("MECARD:"):
        fields = dict()
        for pair in t[7:].split(";"):
            if ":" in pair:
                k,v = pair.split(":",1)
                fields[k.upper()] = v
        if "N" in fields:
            name = fields["N"]
            parts = [p.strip() for p in name.split(",")]
            if len(parts)==2:
                res["last_name"], res["first_name"] = parts[0], parts[1]
            else:
                res["first_name"] = name
        res["email"] = fields.get("EMAIL","")
        res["phone"] = fields.get("TEL","")
        res["company"] = fields.get("ORG","")
        return res

    # Simple schemes
    if t.lower().startswith("mailto:"):
        res["email"] = t[7:].strip(); return res
    if t.lower().startswith("tel:"):
        res["phone"] = t[4:].strip(); return res
    if t.lower().startswith(("http://","https://")):
        res["url"] = t.strip(); return res

    # Heuristic email extraction
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", t)
    if m:
        res["email"] = m.group(0)
    return res
