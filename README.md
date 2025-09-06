# Tap-to-Contact & Lead Capture (Salon/Congrès)

Mini app Streamlit pour **partager votre carte (.vcf)** et **collecter les leads** en 10 secondes – QR/NFC.

## 1) Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# Éditez .env (identité, coordonnées). Mettez votre photo JPEG dans assets/photo.jpg
```

## 2) Démarrage (smoke test)

```bash
streamlit run app.py
```

Ouvrez l’URL locale fournie. Cliquez sur **"📇 Sauvegarder le contact (.vcf)"** → vérifiez l’ouverture sur iPhone/Android.
Soumettez un lead test → `data/leads.csv` se remplit.

## 3) Déploiement simple

- **Streamlit Community Cloud** : poussez le repo, configurez les **Secrets** (ou `.env` via variables) et déployez.
- **Render** : Web Service Python, commande `streamlit run app.py`, exposition port 8501.
- **Domaine** : mappez `app.votredomaine.fr` → URL finale à programmer dans les tags NFC / QR :
  - `https://app.votredomaine.fr/?utm_source=nfc`
  - `https://app.votredomaine.fr/?utm_source=qr-stand`
  - `https://app.votredomaine.fr/?utm_source=qr-slide`

## 4) NFC & QR

- **NFC** : applis *NFC Tools* / *NXP TagWriter* → Write → URL/URI → collez l’URL ci-dessus (`utm_source=nfc`).
- **QR** : générez le QR avec n’importe quel générateur (ou un simple script Python). Imprimez sur roll-up/badge.

## 5) Google Sheets (optionnel)

Créez un compte de service (JSON), partagez votre Sheet avec l’email de service, mettez:
```
GOOGLE_SERVICE_ACCOUNT_JSON="/chemin/vers/service.json"
GOOGLE_SHEET_ID="ID_DE_VOTRE_SHEET"
```
Les leads seront ajoutés au **CSV** et à **Sheet1**.

## 6) RGPD

- Case consentement obligatoire.
- Leads stockés en CSV local (et éventuellement Google Sheets).
- Mettez votre **Politique de confidentialité** sur votre site et liez-la depuis la page.

## 7) Tests & Qualité

```bash
pytest -q
ruff check .
mypy modules
```

**Critères d’acceptation**
- Aucune erreur au lancement (`streamlit run app.py`).
- Téléchargement `.vcf` lisible sur iPhone/Android (photo incluse si fournie).
- Soumission lead écrit en CSV (et sur Google Sheets si configuré).
- Lint/type-check OK, tests OK.

## 8) Conseils d’usage en salon

- **Imprimez un grand QR** (utm `qr-stand`) + un **sticker NFC** (utm `nfc`) sur la table.
- Mettez l’app **en favori sur votre écran d’accueil** pour montrer le bouton .vcf instantanément.
- Après le salon, exportez `data/leads.csv` → CRM / campagne d’emailing.
