
# --- Replace or insert into your Export tab content ---
import streamlit as st
from modules import storage

st.subheader("Leads enregistrés (persistants)")
rows = storage.list_leads()

if rows:
    # Gardez votre tableau si vous voulez, sinon utilisez ceci :
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown("### Gestion par ligne")
    st.caption("Supprimez une ligne via le bouton 🗑️ (rafraîchissement auto).")

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

    # Export CSV (utilise la base persistante)
    st.download_button(
        "Télécharger en CSV",
        data=storage.export_csv_bytes(),
        file_name="leads_export.csv",
        mime="text/csv"
    )
else:
    st.info("Aucun lead enregistré pour le moment.")
