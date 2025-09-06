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

### Astuces / Config caméra
- **Caméra arrière forcée** en live scan (WebRTC). Vous pouvez la désactiver via `FORCE_REAR_CAMERA=false` dans `.env` si besoin.
- Sur **mobile**, l'accès caméra nécessite **HTTPS** (ou `localhost`). Hébergez l'app derrière un domaine en HTTPS pour que le scanner fonctionne.
