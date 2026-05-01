import streamlit as st

from logic.validators import (
    MAX_FILE_MB,
    clean_optional_email,
    get_file_size_mb,
    validate_image_file,
)

from logic.approvals import create_project, build_approval_link
from external.email_sender import send_client_email


def render_upload_page():
    st.title("Vera")
    st.write("Comparte una versión. Cierra con claridad.")

    st.session_state.setdefault("last_approval_link", None)
    st.session_state.setdefault("last_project_name", None)
    st.session_state.setdefault("last_email_status", None)

    with st.form("upload_form", clear_on_submit=False):
        project_name = st.text_input("Nombre del proyecto")
        client_name = st.text_input("Nombre del cliente")
        client_email = st.text_input("Email del cliente opcional")

        uploaded_file = st.file_uploader(
            "Sube la ilustración",
            type=["png", "jpg", "jpeg", "webp"],
            help=f"Máximo {MAX_FILE_MB}MB",
        )

        if uploaded_file:
            size_mb = get_file_size_mb(uploaded_file)

            if size_mb > MAX_FILE_MB:
                st.error(
                    f"Archivo demasiado grande: {size_mb:.1f}MB. "
                    f"Máximo permitido: {MAX_FILE_MB}MB."
                )
            else:
                st.success(f"Imagen lista: {uploaded_file.name} · {size_mb:.1f}MB")

        submitted = st.form_submit_button("Generar link de aprobación")

    if submitted:
        try:
            if not project_name.strip():
                raise ValueError("Añade el nombre del proyecto.")

            if not client_name.strip():
                raise ValueError("Añade el nombre del cliente.")

            validate_image_file(uploaded_file)
            clean_email = clean_optional_email(client_email)

            with st.spinner("Generando link de aprobación..."):
                project_id = create_project(
                    project_name=project_name.strip(),
                    client_name=client_name.strip(),
                    client_email=clean_email,
                    uploaded_file=uploaded_file,
                )

                approval_link = build_approval_link(project_id)

                email_status = send_client_email(
                    client_email=clean_email,
                    approval_link=approval_link,
                    project_name=project_name.strip(),
                )

            st.session_state.last_approval_link = approval_link
            st.session_state.last_project_name = project_name.strip()
            st.session_state.last_email_status = email_status

        except ValueError as error:
            st.warning(str(error))

        except Exception as error:
            st.error("Vera no pudo completar la acción.")
            st.caption(str(error))

    if st.session_state.last_approval_link:
        st.success("Todo listo. Comparte este enlace con tu cliente.")

        st.markdown("### Link privado")
        st.code(st.session_state.last_approval_link)

        st.link_button(
            "Abrir vista cliente",
            st.session_state.last_approval_link,
        )

        email_status = st.session_state.last_email_status

        if email_status and email_status.get("sent"):
            st.info("Email preparado correctamente.")
        else:
            st.info("Puedes copiar el enlace y enviarlo cuando quieras.")
