#approval_page.py

if st.button("SELLAR Y APROBAR VERSIÓN", use_container_width=True):
    with st.spinner("Sellando aprobación y generando PDF..."):
        approval = approve_project(project_id)

    st.success("Versión aprobada.")
    st.balloons()

    st.markdown("### Sello digital")
    st.code(approval["approval_hash"])

    if approval.get("pdf_path"):
        with open(approval["pdf_path"], "rb") as pdf:
            st.download_button(
                "Descargar certificado PDF",
                data=pdf,
                file_name="vera_approval_certificate.pdf",
                mime="application/pdf",
            )
