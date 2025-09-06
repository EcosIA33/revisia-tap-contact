# -*- coding: utf-8 -*-
"""
QR scanner amélioré (drop‑in) pour le module d'origine.
- Conserve l'API :
    * decode_qr_from_ndarray(img_bgr) -> Optional[str]
    * decode_qr_from_bytes(b: bytes) -> Optional[str]
    * parse_contact_from_qr(text: str) -> Dict[str,str]
- Ne dépend que d'OpenCV par défaut. Si `pyzbar` et/ou `pyzxing` sont présents,
  ils sont utilisés automatiquement (optionnels, tolérance logo accrue).
"""
from __future__ import annotations
import re
from typing import Dict, Optional, Tuple, List

import numpy as np  # type: ignore
import cv2  # type: ignore
import importlib

# -----------------------------
# Helpers
# -----------------------------

def _try_decode_opencv(img: np.ndarray, logs: List[str]) -> List[str]:
    """Essaye OpenCV en multi puis en single decode."""
    det = cv2.QRCodeDetector()
    texts: List[str] = []
    try:
        ok, decoded_info, points, _ = det.detectAndDecodeMulti(img)
        if ok and decoded_info:
            for s in decoded_info:
                if s:
                    texts.append(s.strip())
            if texts:
                logs.append(f"OpenCV multi OK: {len(texts)} code(s)")
                return texts
    except Exception as e:
        logs.append(f"OpenCV multi error: {e!r}")
    try:
        data, pts, _ = det.detectAndDecode(img)
        if data:
            logs.append("OpenCV single OK")
            return [data.strip()]
    except Exception as e:
        logs.append(f"OpenCV single error: {e!r}")
    return []

def _try_decode_pyzbar(img_gray: np.ndarray, logs: List[str]) -> List[str]:
    """Optionnel : utilise pyzbar si installé (zbar requis)."""
    if not importlib.util.find_spec("pyzbar"):
        logs.append("pyzbar non disponible")
        return []
    try:
        from pyzbar.pyzbar import decode  # type: ignore
        res = decode(img_gray)
        out = [r.data.decode("utf-8", "ignore").strip() for r in res if r.data]
        if out:
            logs.append(f"pyzbar OK: {len(out)} code(s)")
        return out
    except Exception as e:
        logs.append(f"pyzbar error: {e!r}")
        return []

def _try_decode_zxing(img_gray: np.ndarray, logs: List[str]) -> List[str]:
    """Optionnel : ZXing via Java (pyzxing)."""
    if not importlib.util.find_spec("pyzxing"):
        logs.append("pyzxing non disponible")
        return []
    try:
        from pyzxing import BarCodeReader  # type: ignore
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            cv2.imwrite(tmp.name, img_gray)
            tmp_path = tmp.name
        reader = BarCodeReader()
        outputs = reader.decode(tmp_path, possible_formats=["QR_CODE"])
        os.unlink(tmp_path)
        texts: List[str] = []
        for item in outputs or []:
            if isinstance(item, dict) and item.get("parsed"):
                texts.append(str(item["parsed"]).strip())
            elif isinstance(item, dict) and item.get("raw"):
                texts.append(str(item["raw"]).strip())
        if texts:
            logs.append(f"ZXing OK: {len(texts)} code(s)")
        return texts
    except Exception as e:
        logs.append(f"ZXing error: {e!r}")
        return []

def _dedup(texts: List[str]) -> List[str]:
    seen = set(); out = []
    for t in texts:
        t = (t or "").strip()
        if not t: continue
        if t not in seen:
            seen.add(t); out.append(t)
    return out

def _variants_from_bgr(img_bgr: np.ndarray) -> List[np.ndarray]:
    """Génère des variantes robustes contre logos/contrastes faibles."""
    if img_bgr.ndim == 2:
        gray = img_bgr
    else:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    vars: List[np.ndarray] = []

    def add(x): vars.append(x)

    # Base
    add(gray)

    # Contraste
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
    add(clahe)

    # Netteté (unsharp)
    blur = cv2.GaussianBlur(gray, (0,0), 3)
    sharp = cv2.addWeighted(gray, 1.6, blur, -0.6, 0)
    add(sharp)

    # Gamma
    for g in (1.4, 1.8, 2.2):
        inv = 1.0/max(g,1e-6)
        table = ((np.arange(256)/255.0) ** inv * 255.0).clip(0,255).astype("uint8")
        add(cv2.LUT(gray, table))

    # Seuils
    add(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY,31,5))
    add(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,3))
    _, otsu = cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    add(otsu)
    _, otsu_inv = cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    add(otsu_inv)

    # Morphologie sur les binaires
    k = np.ones((3,3), np.uint8)
    add(cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, k, iterations=1))
    add(cv2.morphologyEx(otsu_inv, cv2.MORPH_OPEN, k, iterations=1))

    # Débruitage léger
    add(cv2.fastNlMeansDenoising(gray, h=5))

    # Rotations
    add(cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE))
    add(cv2.rotate(gray, cv2.ROTATE_180))
    add(cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE))

    # Upscale/downscale (utile quand le QR est trop petit ou flou)
    h, w = gray.shape[:2]
    for scale in (0.75, 1.5, 2.0):
        nh, nw = max(32,int(h*scale)), max(32,int(w*scale))
        add(cv2.resize(gray, (nw, nh), interpolation=cv2.INTER_CUBIC))

    # Crop central (supprime des bords non pertinents / logos extérieurs)
    ch, cw = int(h*0.7), int(w*0.7)
    y0, x0 = max(0,(h-ch)//2), max(0,(w-cw)//2)
    add(gray[y0:y0+ch, x0:x0+cw])

    return vars

# -----------------------------
# Public API
# -----------------------------

def decode_qr_from_ndarray(img) -> Optional[str]:
    """
    Robust QR decode from a BGR ndarray. Tries multiple preprocess steps
    and, si disponibles, plusieurs moteurs de lecture.
    """
    logs: List[str] = []
    # Assure format ndarray uint8
    arr = np.array(img)
    if arr.dtype != np.uint8:
        arr = arr.astype(np.uint8, copy=False)

    # Si image RGB/gray, convertit vers BGR attendu par cv2 routines.
    if arr.ndim == 3 and arr.shape[2] == 3:
        bgr = arr
    elif arr.ndim == 2:
        bgr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    else:
        try:
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        except Exception:
            bgr = arr

    # 1) Boucle sur variantes + OpenCV
    for v in _variants_from_bgr(bgr):
        out = _try_decode_opencv(v, logs)
        if out:
            return _dedup(out)[0]

    # 2) pyzbar si dispo (sur quelques variantes binaires et gray)
    for v in _variants_from_bgr(bgr)[:8]:  # limiter le coût
        out = _try_decode_pyzbar(v if v.ndim==2 else cv2.cvtColor(v, cv2.COLOR_BGR2GRAY), logs)
        if out:
            return _dedup(out)[0]

    # 3) ZXing si dispo (sur gray natif)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    out = _try_decode_zxing(gray, logs)
    if out:
        return _dedup(out)[0]

    return None

def decode_qr_from_bytes(b: bytes) -> Optional[str]:
    """Charge des bytes d'image (PNG/JPG) et applique le pipeline."""
    file_bytes = np.asarray(bytearray(b), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        return None
    return decode_qr_from_ndarray(img)

# --- Parsing du contenu QR en champs contact ---

def parse_contact_from_qr(t: str) -> Dict[str, str]:
    """
    Retourne un dict normalisé {first_name,last_name,email,phone,company,job,url}.
    Prend en charge vCard, MeCard, mailto:, tel:, URL, heuristique email.
    """
    res: Dict[str,str] = {
        "first_name":"",
        "last_name":"",
        "email":"",
        "phone":"",
        "company":"",
        "job":"",
        "url":"",
    }
    if not t:
        return res
    t = t.strip()

    upper = t.upper()
    if upper.startswith("BEGIN:VCARD"):
        # Parsing vCard minimaliste
        lines = [x.strip() for x in t.splitlines() if ":" in x]
        kv = {}
        for ln in lines:
            k, v = ln.split(":",1)
            key = k.split(";")[0].upper()
            kv[key] = v.strip()
        # Nom
        if "N" in kv:
            parts = [p.strip() for p in kv["N"].split(";")]
            if parts:
                res["last_name"] = parts[0]
            if len(parts) > 1:
                res["first_name"] = parts[1]
        elif "FN" in kv and not (res["first_name"] or res["last_name"]):
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

    if upper.startswith("MECARD:"):
        body = t[7:]
        kv = {}
        for part in body.split(";"):
            if ":" in part:
                k, v = part.split(":",1)
                kv[k.upper()] = v
        # MECARD:N:Nom Prenom
        n = kv.get("N","").strip()
        if n:
            bits = n.split()
            if len(bits)>=2:
                res["first_name"] = bits[1]; res["last_name"] = bits[0]
            else:
                res["first_name"] = n
        res["email"] = kv.get("EMAIL","")
        res["phone"] = kv.get("TEL","")
        res["company"] = kv.get("ORG","")
        res["job"] = kv.get("TITLE","")
        res["url"] = kv.get("URL","")
        return res

    # mailto:, tel:, URL et heuristiques
    if t.lower().startswith("mailto:"):
        res["email"] = t[7:].strip(); return res
    if t.lower().startswith("tel:"):
        res["phone"] = t[4:].strip(); return res
    if t.lower().startswith(("http://","https://")):
        res["url"] = t.strip(); return res

    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", t)
    if m:
        res["email"] = m.group(0)
    return res
