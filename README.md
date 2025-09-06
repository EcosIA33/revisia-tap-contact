# Tap-to-Contact — Édition Salon

- QR en en-tête (image `assets/qr.png` ou QR dynamique via `QR_TARGET_URL`).
- Scanner QR (caméra arrière) pour pré-remplir les leads.
- Export **CSV** et **Excel .xlsx** au format **Table** (filtres, en-têtes figées).

## Lancer
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Config (.env)
```
SHOW_QR_IN_HEADER=true
QR_TARGET_URL="https://.../ton.vcf"  # sinon l'appli affiche assets/qr.png
SHOW_DOWNLOAD_BUTTON=false
```


### Caméra / Scanner
- Le scanner Live propose **à chaque fois** le choix **Arrière** ou **Avant**.
- Si la capture ne démarre pas, sélectionnez l’autre option.
- L’accès caméra nécessite **HTTPS** (ou `localhost`).
- En alternative, utilisez le **Mode photo** puis laissez l’appli décoder le QR.
