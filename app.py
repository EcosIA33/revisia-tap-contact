#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit app: Tap-to-Contact & Lead Capture + QR Scanner
- Télécharge un .vcf v3.0 (photo JPEG intégrée si fournie)
- Formulaire de collecte leads (CSV local + Google Sheets optionnel)
- Tracking utm_source (NFC/QR)
- Scanner QR en direct (caméra) + pré-remplissage lead
"""
from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import Optional, Dict

import streamlit as st
from dotenv import load_dotenv

from modules.contact import build_vcard_bytes
from modules.storage import Lead, Storage, StorageConfig
from modules.utils import ensure_data_dir, get_client_ip_hash, load_image_bytes
from modules.qr import parse_contact_from_qr

# QR live scanner (WebRTC)
try:
    import av  # noqa: F401  # ensure wheel present
    import cv2  # noqa: F401
    from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase
    QR_ENABLED = True
except Exception:
    QR_ENABLED = False

APP_NAME = "Tap-to-Contact & Lead Capture"

# --- Boot ---
load_dotenv()
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", "logs"))
ensure_data_dir(DATA_DIR)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app")

# --- Config identité (depuis .env) ---
IDENTITY: Dict[str, str] = {
    "FN": os.getenv("FULL_NAME", "Votre Nom"),
    "N_LAST": os.getenv("N_LAST", "Nom"),
    "N_FIRST": os.getenv("N_FIRST", "Prénom"),
    "ORG": os.getenv("ORG", "Votre Société"),
    "TITLE": os.getenv("TITLE", "Fonction"),
    "TEL": os.getenv("TEL", "+33 6 00 00 00 00"),
    "EMAIL": os.getenv("EMAIL", "vous@example.com"),
    "URL": os.getenv("URL", "https://www.exemple.com"),
    "ADR_STREET": os.getenv("ADR_STREET", "10 Rue Exemple"),
    "ADR_CITY": os.getenv("ADR_CITY", "Paris"),
    "ADR_PC": os.getenv("ADR_PC", "75000"),
    "ADR_COUNTRY": os.getenv("ADR_COUNTRY", "France"),
}
PHOTO_PATH = os.getenv("PHOTO_PATH", "assets/photo.jpg")
SHOW_QR_IN_HEADER = os.getenv("SHOW_QR_IN_HEADER", "false").lower() in ("1","true","yes","on")
QR_IMAGE_PATH = os.getenv("QR_IMAGE_PATH", "assets/qr.png")

# --- Storage config ---
storage_cfg = StorageConfig(
    csv_path=DATA_DIR / "leads.csv",
    gsheet_id=os.getenv("GOOGLE_SHEET_ID"),
    gservice_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
)
storage = Storage(storage_cfg)

st.set_page_config(page_title=APP_NAME, page_icon="👋", layout="centered")

# --- Tabs ---
tab_share, tab_scan, tab_export = st.tabs(["📇 Partager ma carte", "📷 Scanner un QR", "📤 Export"])

with tab_share:
    # --- UI ---
    try:
        qp = st.query_params  # type: ignore[attr-defined]
    except Exception:
        try:
            qp = st.experimental_get_query_params()  # type: ignore[attr-defined]
        except Exception:
            qp = {}
    utm_source = (qp.get("utm_source") or ["direct"])[0]

    st.title("Enregistrer mon contact")
    st.caption("Salon / Congrès — approchez, scannez, connectons-nous 🤝")

    # Photo (optionnelle)
    photo_bytes: Optional[bytes] = load_image_bytes(PHOTO_PATH)
    qr_bytes: Optional[bytes] = load_image_bytes(QR_IMAGE_PATH)
    if SHOW_QR_IN_HEADER and qr_bytes:
        st.image(qr_bytes, width=260, caption="Scannez pour ajouter le contact")
    elif photo_bytes:
        st.image(photo_bytes, width=140, caption=IDENTITY["FN"])

    # VCF
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

    st.download_button(
        label="📇 Sauvegarder le contact (.vcf)",
        data=vcard_bytes,
        file_name=f"{IDENTITY['FN'].replace(' ', '_')}.vcf",
        mime="text/vcard"
    )

    st.divider()
    st.header("Laissez-moi votre carte ✍️")

    with st.form("lead_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            first_name = st.text_input("Prénom *", max_chars=64)
        with c2:
            last_name = st.text_input("Nom *", max_chars=64)

        c3, c4 = st.columns(2)
        with c3:
            email = st.text_input("Email *", max_chars=120, placeholder="prenom.nom@entreprise.com")
        with c4:
            phone = st.text_input("Téléphone", max_chars=32, placeholder="+33 6 xx xx xx xx")

        company = st.text_input("Société *", max_chars=120)
        job = st.text_input("Poste", max_chars=120)
        interest = st.selectbox("Intérêt", ["Prise de contact", "Démo", "Devis", "Partenariat", "Autre"])
        consent = st.checkbox("J’accepte d’être recontacté·e par email/téléphone (RGPD)")
        submit = st.form_submit_button("Envoyer")

    if submit:
        if not (first_name and last_name and email and company and consent):
            st.error("Merci de remplir les champs obligatoires (*) et de cocher le consentement RGPD.")
        else:
            lead = Lead(
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                email=email.strip(),
                phone=phone.strip(),
                company=company.strip(),
                job=job.strip(),
                interest=interest,
                utm_source=utm_source,
                ip_hash=get_client_ip_hash(),  # best-effort hash
            )
            ok, msg = storage.save_lead(lead)
            if ok:
                st.success("✅ Merci ! Votre carte est bien enregistrée. On revient vers vous très vite.")
            else:
                st.error(f"Une erreur est survenue : {msg}")
            logger.info("Lead submit: ok=%s source=%s email=%s", ok, utm_source, email)

    st.caption("Astuce : scannez le QR au stand ou approchez un sticker NFC → cette page s’ouvre, "
               "vous enregistrez mon contact et me laissez le vôtre en 10 secondes.")

with tab_scan:
    st.header("Scanner un QR (caméra)")
    st.caption("Scannez les QR code des visiteurs pour pré-remplir leur fiche.")

    if not QR_ENABLED:
        st.warning("Le scanner live nécessite des paquets supplémentaires. "
                   "Installez: streamlit-webrtc, opencv-python-headless, av, aiortc. "
                   "Vous pouvez sinon **importer une photo** du QR ci-dessous.")
    else:
        import cv2  # type: ignore
        from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoTransformerBase

        class QRProcessor(VideoTransformerBase):  # type: ignore[misc]
            def __init__(self) -> None:
                self.detector = cv2.QRCodeDetector()
                self.last_result: Optional[str] = None

            def transform(self, frame):
                img = frame.to_ndarray(format="bgr24")
                try:
                    data, points, _ = self.detector.detectAndDecode(img)
                    if data:
                        self.last_result = data.strip()
                except Exception:
                    pass
                return img

        ctx = webrtc_streamer(
            key="qr-scan",
            mode=WebRtcMode.SENDRECV,
            media_stream_constraints={"video": True, "audio": False},
            video_transformer_factory=QRProcessor,
            async_processing=True,
        )

        if ctx.video_transformer:
            qr_text = ctx.video_transformer.last_result
        else:
            qr_text = None

        if qr_text:
            st.success("QR détecté ✔")
            with st.expander("Voir le contenu du QR scanné"):
                st.code(qr_text, language="text")

            parsed = parse_contact_from_qr(qr_text)
            with st.form("scan_to_lead", clear_on_submit=False):
                c1, c2 = st.columns(2)
                with c1:
                    s_first = st.text_input("Prénom *", value=parsed.get("first_name", ""), max_chars=64)
                with c2:
                    s_last = st.text_input("Nom *", value=parsed.get("last_name", ""), max_chars=64)
                c3, c4 = st.columns(2)
                with c3:
                    s_email = st.text_input("Email *", value=parsed.get("email", ""), max_chars=120)
                with c4:
                    s_phone = st.text_input("Téléphone", value=parsed.get("phone", ""), max_chars=32)
                s_company = st.text_input("Société *", value=parsed.get("company", ""), max_chars=120)
                s_job = st.text_input("Poste", value=parsed.get("job", ""), max_chars=120)
                s_interest = st.selectbox("Intérêt", ["Prise de contact", "Démo", "Devis", "Partenariat", "Autre"])
                s_consent = st.checkbox("J’accepte d’être recontacté·e (RGPD)", value=True)
                s_submit = st.form_submit_button("Enregistrer le lead")

            if s_submit:
                if not (s_first and s_last and s_email and s_company and s_consent):
                    st.error("Champs obligatoires manquants ou consentement non coché.")
                else:
                    lead = Lead(
                        first_name=s_first.strip(),
                        last_name=s_last.strip(),
                        email=s_email.strip(),
                        phone=s_phone.strip(),
                        company=s_company.strip(),
                        job=s_job.strip(),
                        interest=s_interest,
                        utm_source="qr-scan",
                        ip_hash=get_client_ip_hash(),
                    )
                    ok, msg = storage.save_lead(lead)
                    if ok:
                        st.success("✅ Lead enregistré depuis QR.")
                    else:
                        st.error(f"Erreur: {msg}")

    # Fallback: upload d'une photo/scan de QR
    st.subheader("Ou importer une image avec un QR")
    img_file = st.file_uploader("Image (photo du QR, PNG/JPG)", type=["png", "jpg", "jpeg"])
    if img_file is not None:
        from modules.qr import decode_qr_from_bytes
        data = decode_qr_from_bytes(img_file.read())
        if data:
            st.info("QR décodé 👍")
            with st.expander("Voir le contenu du QR importé"):
                st.code(data, language="text")
            parsed = parse_contact_from_qr(data)
            st.write("Champs reconnus : ", parsed)
        else:
            st.error("Impossible de décoder un QR dans cette image.")


with tab_export:
    st.header("Exporter les leads")
    st.caption("Téléchargez vos leads au format CSV ou Excel (.xlsx).")

    import pandas as pd  # type: ignore

    csv_path = DATA_DIR / "leads.csv"
    if not csv_path.exists():
        st.info("Aucun lead enregistré pour le moment.")
    else:
        try:
            df = pd.read_csv(csv_path, dtype=str).fillna("")
            st.dataframe(df, use_container_width=True)
            st.download_button(
                "📄 Télécharger CSV",
                data=csv_path.read_bytes(),
                file_name="leads.csv",
                mime="text/csv",
            )
            # Build Excel in-memory
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Leads")
            st.download_button(
                "📊 Télécharger Excel (.xlsx)",
                data=buf.getvalue(),
                file_name="leads.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            st.error(f"Erreur lors de la lecture/export: {e}")
