
# --- Persistence bootstrap (minimal, keeps your UI) ---
from modules import storage
try:
    DB_PATH = storage.init_db()  # default: data/leads.db
except Exception as e:
    # Optional fallback if your code folder is read-only (e.g., /mount/src/...)
    import tempfile, os
    tmp_dir = os.path.join(tempfile.gettempdir(), "revisia_data")
    os.makedirs(tmp_dir, exist_ok=True)
    DB_PATH = storage.init_db(os.path.join(tmp_dir, "leads.db"))
    # (Optionnel) informer dans votre UI:
    try:
        import streamlit as st
        st.sidebar.warning(f"Stockage déplacé vers {DB_PATH} (cause: {e}). "
                           "Définissez LEADS_DB_PATH pour choisir un autre chemin.")
    except Exception:
        pass
