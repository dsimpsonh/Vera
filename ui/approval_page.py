from pathlib import Path

import streamlit as st

# Ajusta este import según tu repo real
from logic.approvals import approve_project


def render_approval_page(project_id: str):
    st.title("Vera")
    st.write("Revisión privada para aprobación.")

    if not project_id:
        st.error("No se encontró el proyecto.")
        return

    st.warning("Aprueba solo si esta versión está lista para cerrar.")

    confirmed = st.checkbox("Confirmo que apruebo esta versión.")

    if confirmed:
        if st.button("SELLAR Y APROBAR VERSIÓN", use_container_width=True):
            try:
                with st.spinner("Sellando aprobación y generando PDF..."):
                    approval = approve_project(project_id)

                st.success("Versión aprobada.")
                st.balloons()

                st.markdown("### Sello digital")
                st.code(approval["approval_hash"])

                pdf_path = approval.get("pdf_path") or approval.get("certificate_path")

                if pdf_path and Path(pdf_path).exists():
                    with open(pdf_path, "rb") as pdf:
                        st.download_button(
                            "Descargar certificado PDF",
                            data=pdf,
                            file_name="vera_approval_certificate.pdf",
                            mime="application/pdf",
                        )
                else:
                    st.warning("Aprobación registrada, pero no se encontró el PDF.")

            except Exception as error:
                st.error("Vera no pudo sellar la aprobación.")
                st.caption(str(error))
