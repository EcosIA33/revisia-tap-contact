#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATCHED5:
- Suppression de la webcam pour le scan QR (import image uniquement)
- Persistance des leads (édition/suppression) dans data/leads.csv
"""
from __future__ import annotations
import os
import io
import logging
from pathlib import Path
from typing import Optional, Dict

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from modules.storage import Storage, StorageConfig, Lead
from modules.qr import decode_qr_from_bytes, parse_contact_from_qr
from modules.contact import build_vcard_bytes

# --- Logs ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("revisia.tap")

# --- Config ---
load_dotenv(override=True)
APP_NAME = os.getenv("APP_NAME", "RevisIA — Tap Contact (Salon)")
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
LEADS_CSV = Path(os.getenv("LEADS_CSV", DATA_DIR / "leads.csv"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

IDENTITY: Dict[str,str] = {
    "FN": os.getenv("FN", "Adrian Rodriguez"),
    "N_LAST": os.getenv("N_LAST", "Rodriguez"),
    "N_FIRST": os.getenv("N_FIRST", "Adrian"),
    "ORG": os.getenv("ORG", "DRIVN"),
    "TITLE": os.getenv("TITLE", "Fondateur"),
    "TEL": os.getenv("TEL", "+33 6 27 16 52 05"),
    "EMAIL": os.getenv("EMAIL", "adrian@drivn.fr"),
    "URL": os.getenv("URL", "https://www.drivn.fr/"),
    "ADR_STREET": os.getenv("ADR_STREET", ""),
    "ADR_CITY": os.getenv("ADR_CITY", ""),
    "ADR_PC": os.getenv("ADR_PC", ""),
    "ADR_COUNTRY": os.getenv("ADR_COUNTRY", "France"),
}

PHOTO_PATH = os.getenv("PHOTO_PATH", "assets/photo.jpg")
SHOW_QR_IN_HEADER = os.getenv("SHOW_QR_IN_HEADER", "true").lower() in ("1","true","yes","on")
QR_IMAGE_PATH = os.getenv("QR_IMAGE_PATH", "assets/qr.png")
QR_TARGET_URL = os.getenv("QR_TARGET_URL", "")  # si défini + 'qrcode' présent, on génère dyn.
SHOW_DOWNLOAD_BUTTON = os.getenv("SHOW_DOWNLOAD_BUTTON", "false").lower() in ("1","true","yes","on")
LOGO_PATH = os.getenv("LOGO_PATH", "assets/logo.png")
SHOW_LOGO = os.getenv("SHOW_LOGO", "true").lower() in ("1","true","yes","on")

# --- Storage ---
storage = Storage(StorageConfig(csv_path=LEADS_CSV))

st.set_page_config(page_title=APP_NAME, page_icon="🎯", layout="centered")

def load_image_bytes(path: str) -> Optional[bytes]:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None

def build_header():
    col1, col2 = st.columns([1,1])
    with col1:
        if SHOW_LOGO and os.path.exists(LOGO_PATH):
            try:
                st.image(LOGO_PATH, width=160)
            except Exception:
                st.warning("Logo non lisible (format invalide). Désactivez SHOW_LOGO ou remplacez le fichier.")
        st.markdown(f"### {IDENTITY['FN']}")
        st.caption(f"{IDENTITY['TITLE']} — {IDENTITY['ORG']}")

        # vCard téléchargeable (optionnel)
        photo_bytes = load_image_bytes(PHOTO_PATH)
        vcard_bytes = build_vcard_bytes(
            fn=IDENTITY["FN"],
            n_last=IDENTITY["N_LAST"],
            n_first=IDENTITY["N_FIRST"],
            org=IDENTITY["ORG"],
            title=IDENTITY["TITLE"],
            tel=IDENTITY["TEL"],
            email=IDENTITY["EMAIL"],
            url=IDENTITY["URL"],
            adr_street=IDENTITY["ADR_STREET"],
            adr_city=IDENTITY["ADR_CITY"],
            adr_pc=IDENTITY["ADR_PC"],
            adr_country=IDENTITY["ADR_COUNTRY"],
            photo_bytes=photo_bytes
        )
        if SHOW_DOWNLOAD_BUTTON:
            st.download_button("📇 Sauvegarder le contact (.vcf)", data=vcard_bytes,
                               file_name=f"{IDENTITY['FN'].replace(' ', '_')}.vcf",
                               mime="text/vcard")
    with col2:
        qr_bytes: Optional[bytes] = None
        # Si demandé, tente de générer un QR à la volée
        if QR_TARGET_URL:
            try:
                import qrcode
                qr = qrcode.QRCode(version=4, box_size=6, border=2)
                qr.add_data(QR_TARGET_URL)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO(); img.save(buf, format="PNG"); qr_bytes = buf.getvalue()
            except Exception:
                qr_bytes = load_image_bytes(QR_IMAGE_PATH)
        else:
            qr_bytes = load_image_bytes(QR_IMAGE_PATH)
        if SHOW_QR_IN_HEADER and qr_bytes:
            try:
                st.image(qr_bytes, width=300, caption=" ")
            except Exception:
                st.warning("Image QR en-tête invalide. Remplacez `assets/qr.png` ou renseignez QR_TARGET_URL dans .env.")


def _lead_form(initial: Optional[Dict[str,str]] = None, key: str = "lead_form"):
    initial = initial or {}
    with st.form(key=key):
        # Saisie manuelle rapide — ordre demandé : Société, Nom, Prénom, Téléphone, Email, Fonction, Intérêt
        company = st.text_input("Société", value=initial.get("company",""))
        last_name = st.text_input("Nom", value=initial.get("last_name",""))
        first_name = st.text_input("Prénom", value=initial.get("first_name",""))
        phone = st.text_input("Téléphone", value=initial.get("phone",""))
        email = st.text_input("Email", value=initial.get("email",""))
        job = st.text_input("Fonction", value=initial.get("job",""))
        interest = st.text_input("Intérêt", value=initial.get("interest","Prise de contact"))
        submitted = st.form_submit_button("💾 Enregistrer le lead")
    if submitted:
        if not (first_name and last_name and email and company):
            st.error("Champs requis manquants (Prénom, Nom, Email, Société).")
        else:
            ok, msg = storage.append_lead(Lead(
                first_name=first_name, last_name=last_name, email=email,
                phone=phone, company=company, job=job,
                interest=interest, utm_source="", ip_hash=""
            ))
            if ok:
                st.success("Lead enregistré.")
            else:
                st.error(f"Erreur: {msg}")

def tab_scan():
    st.subheader("Scanner un QR (image)")
    img = st.file_uploader("Photo du QR", type=["png","jpg","jpeg"], key="qr_upload")
    if img is not None:
        data = decode_qr_from_bytes(img.read())
        if data:
            st.info("QR décodé 👍")
            st.code(data, language="text")
            parsed = parse_contact_from_qr(data)
            st.write("Champs reconnus :", parsed)
            _lead_form(parsed, key="lead_from_qr")
        else:
            st.error("Impossible de décoder un QR dans cette image.")
    st.divider()
    st.subheader("Saisie manuelle rapide")
    _lead_form(key="lead_manual")

def tab_export():
    st.subheader("Export & gestion des leads (persistant)")
    df = storage.load_df()
    st.caption(f"{len(df)} ligne(s) chargée(s) depuis `{LEADS_CSV}`")

    # Sélection pour suppression par ligne
    if not df.empty:
        sel = st.multiselect("Sélectionner des lignes à supprimer", df["id"].tolist(), key="to_delete")
        if sel:
            st.warning(f"{len(sel)} ligne(s) marquée(s) pour suppression.")
            if st.button("🗑️ Supprimer la sélection", type="primary"):
                df = df[~df["id"].isin(sel)].copy()
                ok, msg = storage.overwrite_df(df)
                if ok:
                    st.success("Suppression effectuée.")
                else:
                    st.error(f"Erreur de sauvegarde: {msg}")

    # Édition
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        hide_index=True,
        column_config={"created_at": st.column_config.TextColumn("Créé le", disabled=True),
                       "id": st.column_config.TextColumn("ID", disabled=True)},
        use_container_width=True,
        key="editor",
    )
    if st.button("💾 Enregistrer les modifications"):
        ok, msg = storage.overwrite_df(edited)
        if ok:
            st.success("Modifications enregistrées dans le CSV (persistant).")
        else:
            st.error(f"Erreur: {msg}")

    # Exports
    c1, c2 = st.columns(2)
    with c1:
        csv_bytes = edited.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Télécharger CSV", data=csv_bytes, file_name="leads.csv", mime="text/csv")
    with c2:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            from io import BytesIO
            wb = Workbook(); ws = wb.active; ws.title = "Leads"
            headers = list(edited.columns)
            ws.append(headers)
            # styles
            header_fill = PatternFill("solid", fgColor="1f4e78")
            header_font = Font(color="FFFFFF", bold=True)
            for cell in ws[1]:
                cell.fill = header_fill; cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            for _, row in edited.iterrows():
                ws.append([str(row.get(h,"")) for h in headers])
            ws.freeze_panes = "A2"
            for col in ws.columns:
                max_len = max(len(str(c.value)) if c.value else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(12, max_len+2), 40)
            buf = BytesIO(); wb.save(buf)
            st.download_button("📊 Télécharger Excel (.xlsx)", data=buf.getvalue(),
                               file_name="leads.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"Erreur export: {e}")

def main():
    build_header()
    st.divider()
    tab1, tab2 = st.tabs(["🔍 Scanner un QR", "📤 Export & gestion"])
    with tab1:
        tab_scan()
    with tab2:
        tab_export()

if __name__ == "__main__":
    main()
