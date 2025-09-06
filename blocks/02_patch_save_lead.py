
# --- Patch inside your existing _save_lead(...) ---
# Signature typique:
# def _save_lead(first_name, last_name, email, phone, company, job, source, consent):
from modules import storage

def _save_lead(first_name, last_name, email, phone, company, job, source, consent):
    # ... votre logique actuelle (validation, nettoyage, enregistrement en session, etc.) ...

    # Ajout persistance (idempotent par email) :
    storage.upsert_lead(first_name, last_name, email, phone, company, job, source, consent)

    # ... retour/notifications selon votre modèle ...
