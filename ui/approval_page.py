from pathlib import Path

import streamlit as st

from logic.approvals import get_project, approve_project


def render_approval_page(project_id: str):
    st.title("Vera")
    st.caption("Vista privada de aprobación")

    if not project_id:
        st.error("No se encontró el proyecto.")
        return

    data = get_project(project_id)

    if not data:
        st.error("Este link no corresponde a ningún proyecto disponible.")
        st.info("Para esta demo, primero crea el proyecto desde la vista de Sofía.")
        return

    project = data["project"]
    versions = data["versions"]
    approval = data.get("approval")

    if not versions:
        st.error("Este proyecto no tiene imagen asociada.")
        return

    latest_version = versions[0]

    st.markdown("---")

    st.subheader(project["project_name"])
    st.write(f"Cliente: {project['client_name']}")
    st.write(f"Versión: V{latest_version.get('version_number', 1)}")

    image_path = latest_version.get("image_path")

    if image_path and Path(image_path).exists():
        st.image(image_path, use_container_width=True)
    else:
        st.warning("No se encontró la imagen de esta versión.")

    st.markdown("---")

    if approval:
        st.success("Esta versión ya fue aprobada.")

        st.markdown("### Sello digital")
        st.code(approval.get("approval_hash"))

        st.write(f"Aprobado el: {approval.get('approved_at')}")

        pdf_path = approval.get("pdf_path") or approval.get("certificate_path")

        if pdf_path and Path(pdf_path).exists():
            with open(pdf_path, "rb") as pdf:
                st.download_button(
                    "Descargar certificado PDF",
                    data=pdf,
                    file_name="vera_approval_certificate.pdf",
                    mime="application/pdf",
                )

        return

    st.info("Revisa la imagen. Si todo está correcto, puedes aprobar esta versión.")

    confirmed = st.checkbox("He revisado esta versión y está lista para aprobar.")

    if confirmed:
        if st.button("Aprobar esta versión", type="primary", use_container_width=True):
            try:
                with st.spinner("Sellando aprobación y generando certificado..."):
                    approval_result = approve_project(project_id)

                st.success("Versión aprobada.")
                st.balloons()

                st.markdown("### Sello digital")
                st.code(approval_result["approval_hash"])

                pdf_path = approval_result.get("pdf_path") or approval_result.get("certificate_path")

                if pdf_path and Path(pdf_path).exists():
                    with open(pdf_path, "rb") as pdf:
                        st.download_button(
                            "Descargar certificado PDF",
                            data=pdf,
                            file_name="vera_approval_certificate.pdf",
                            mime="application/pdf",
                        )

            except Exception as error:
                st.error("Vera no pudo completar la aprobación.")
                st.caption(str(error))
