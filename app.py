
import os
import streamlit as st

# --- Persistence (SQLite) ---
from modules import storage
DB_PATH = storage.init_db()  # creates/opens data/leads.db by default

st.set_page_config(page_title="RevisIA – Leads", page_icon="🗂️", layout="wide")

# ------ Helpers ------
def _save_lead(first_name, last_name, email, phone, company, job, source, consent):
    """Persist lead in SQLite and return dict (no in-memory dependency)."""
    storage.upsert_lead(first_name, last_name, email, phone, company, job, source, consent)
    return {
        "first_name": first_name or "",
        "last_name": last_name or "",
        "email": (email or "").strip().lower(),
        "phone": phone or "",
        "company": company or "",
        "job": job or "",
        "source": source or "",
        "consent": bool(consent),
    }

def decode_qr_from_bytes(b: bytes):
    """Delegate to your existing modules.qr if available; otherwise no-op."""
    try:
        from modules.qr import decode_qr_from_bytes as _real_decode
        return _real_decode(b)
    except Exception:
        return None

def parse_contact_from_qr(data: str) -> dict:
    """Basic parser for vCard/MeCard fallback. Tries to extract common fields."""
    if not data:
        return {}
    d = {"first_name":"", "last_name":"", "email":"", "phone":"", "company":"", "job":""}
    s = data.strip()

    # vCard rough
    if "BEGIN:VCARD" in s.upper():
        lines = [ln.strip() for ln in s.replace("\r","").split("\n")]
        for ln in lines:
            up = ln.upper()
            if up.startswith("N:"):
                # N:Last;First;...
                try:
                    body = ln.split(":",1)[1]
                    parts = body.split(";")
                    d["last_name"]  = (parts[0] or "").strip()
                    d["first_name"] = (parts[1] or "").strip()
                except Exception:
                    pass
            elif up.startswith("FN:"):
                body = ln.split(":",1)[1].strip()
                if not (d["first_name"] or d["last_name"]):
                    bits = body.split()
                    if len(bits) >= 2:
                        d["first_name"], d["last_name"] = bits[0], " ".join(bits[1:])
                    else:
                        d["first_name"] = body
            elif "EMAIL" in up:
                try:
                    d["email"] = ln.split(":",1)[1].strip()
                except Exception:
                    pass
            elif up.startswith("TEL"):
                try:
                    d["phone"] = ln.split(":",1)[1].strip()
                except Exception:
                    pass
            elif up.startswith("ORG:"):
                d["company"] = ln.split(":",1)[1].strip()
            elif up.startswith("TITLE:"):
                d["job"] = ln.split(":",1)[1].strip()
        return d

    # MeCard rough MECARD:N:Lastname,Firstname;TEL:;EMAIL:;ORG:;TITLE:;
    if s.upper().startswith("MECARD:"):
        try:
            body = s[7:]
            fields = body.split(";")
            for f in fields:
                if not f or ":" not in f:
                    continue
                k, v = f.split(":",1)
                k = k.strip().upper()
                v = v.strip()
                if k == "N":
                    # Last,First
                    parts = [p.strip() for p in v.split(",")]
                    if len(parts) >= 2:
                        d["last_name"], d["first_name"] = parts[0], parts[1]
                    else:
                        d["first_name"] = v
                elif k == "TEL":
                    d["phone"] = v
                elif k == "EMAIL":
                    d["email"] = v
                elif k == "ORG":
                    d["company"] = v
                elif k == "TITLE":
                    d["job"] = v
        except Exception:
            pass
        return d

    # Fallback: try to find email & phone heuristically
    import re
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", s)
    if m:
        d["email"] = m.group(0)
    m = re.search(r"\+?\d[\d\s().-]{6,}", s)
    if m:
        d["phone"] = m.group(0).strip()
    return d

# ------ Sidebar ------
with st.sidebar:
    st.markdown("### Base de données")
    st.caption(f"Chemin DB : `{DB_PATH}`")
    st.caption("Variable d'env optionnelle : `LEADS_DB_PATH`")

st.title("Gestion des leads (scanner & export)")

tab_scan, tab_export = st.tabs(["Scanner un QR (image)", "Export (persistant)"])

# ----------------- Scanner (image uniquement) -----------------
with tab_scan:
    st.header("Scanner un QR (depuis une image)")

    AUTO_SAVE_ON_DECODE = os.getenv('AUTO_SAVE_ON_DECODE','0').lower() in ('1','true','yes','on')
    if "qr_last" not in st.session_state:
        st.session_state.qr_last = None

    auto_save = st.checkbox("Auto-enregistrer dès qu'un QR valide est détecté", value=AUTO_SAVE_ON_DECODE)

    st.subheader("Importer une image de QR")
    img = st.file_uploader("Photo du QR (PNG/JPG)", type=["png","jpg","jpeg"])
    if img is not None:
        data = decode_qr_from_bytes(img.read())
        if data:
            st.info("QR décodé 👍")
            st.code(data, language="text")

            parsed = parse_contact_from_qr(data)
            colA, colB = st.columns(2)
            with colA:
                first = st.text_input("Prénom", value=parsed.get("first_name",""))
                last  = st.text_input("Nom", value=parsed.get("last_name",""))
                email = st.text_input("Email *", value=parsed.get("email",""))
                phone = st.text_input("Téléphone", value=parsed.get("phone",""))
            with colB:
                company = st.text_input("Société", value=parsed.get("company",""))
                job     = st.text_input("Poste/Fonction", value=parsed.get("job",""))
                source  = st.text_input("Source", value="QR")
                consent = st.checkbox("Consentement RGPD", value=True)

            # Auto-save (only once per new content)
            is_new = (data != st.session_state.qr_last)
            if auto_save and is_new and email:
                _save_lead(first, last, email, phone, company, job, source, consent)
                st.session_state.qr_last = data
                st.success("Lead enregistré automatiquement.")

            if st.button("Enregistrer ce lead"):
                _save_lead(first, last, email, phone, company, job, source, consent)
                st.session_state.qr_last = data
                st.success("Lead enregistré.")

        else:
            st.error("Impossible de décoder un QR dans cette image.")

# ----------------- Export (persistant) -----------------
with tab_export:
    st.header("Export (persistant)")
    st.caption("Les leads enregistrés seront conservés même après fermeture de l'application.")

    with st.expander("Ajouter un lead manuellement"):
        with st.form("add_lead_form"):
            col1, col2 = st.columns(2)
            with col1:
                first = st.text_input("Prénom")
                last  = st.text_input("Nom")
                email = st.text_input("Email *")
                phone = st.text_input("Téléphone")
            with col2:
                company = st.text_input("Société")
                job     = st.text_input("Poste/Fonction")
                source  = st.text_input("Source", value="Export")
                consent = st.checkbox("Consentement RGPD", value=True)
            submitted = st.form_submit_button("Enregistrer le lead")
            if submitted:
                try:
                    _save_lead(first, last, email, phone, company, job, source, consent)
                    st.success("Lead enregistré de façon persistante (SQLite).")
                except Exception as e:
                    st.error(f"Enregistrement impossible: {e}")

    st.subheader("Leads enregistrés")
    rows = storage.list_leads()

    if rows:
        # Aperçu tableau rapide
        st.dataframe(rows, use_container_width=True, hide_index=True)

        st.markdown("### Gestion par ligne")
        st.caption("Supprimez une ligne précise via le bouton 🗑️.")

        # Per-line deletion UI
        for r in rows:
            with st.container():
                c1, c2, c3, c4 = st.columns([4,3,3,1])
                with c1:
                    st.write(f"**#{r['id']}** — {r['first_name']} {r['last_name']}")
                with c2:
                    st.write(r.get('email',''))
                with c3:
                    st.write(r.get('company',''))
                with c4:
                    if st.button("🗑️", key=f"del_{r['id']}", help="Supprimer ce lead"):
                        try:
                            storage.delete_lead(int(r["id"]))
                            st.success(f"Lead #{r['id']} supprimé.")
                            st.rerun()
                        except Exception as e:
                            st.warning(f"Suppression impossible: {e}")

        # Export CSV
        csv_bytes = storage.export_csv_bytes()
        st.download_button(
            "Télécharger en CSV",
            data=csv_bytes,
            file_name="leads_export.csv",
            mime="text/csv"
        )
    else:
        st.info("Aucun lead enregistré pour le moment.")
