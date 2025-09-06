# RevisIA — Tap Contact (Salon) · PATCHED5

Modifications demandées :  
1) Suppression de la capture vidéo dans **Scanner un QR** ; on ne garde que l'import d'image.  
2) Persistance des leads **même après fermeture** : toute saisie/édition dans l'onglet *Export & gestion* est enregistrée dans `data/leads.csv`.  
3) Possibilité de **corriger** (édition directe) et **supprimer par ligne**.

## Installation rapide
```bash
python -m venv .venv && source .venv/bin/activate  # sous Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
## Lancement
```bash
streamlit run app.py
```
## Tests
```bash
pytest -q
ruff check .
mypy .
```

## Données
- Fichier persistant : `data/leads.csv` (créé automatiquement).

## Notes techniques
- Décodage QR via OpenCV (`cv2.QRCodeDetector`) pour éviter les dépendances système.
- Export Excel stylisé (openpyxl).
- Édition & suppression par ligne : via `st.data_editor` + boutons associés, puis sauvegarde.
