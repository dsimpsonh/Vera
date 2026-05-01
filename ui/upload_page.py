import streamlit as st
from logic.validators import clean_optional_email, validate_image_file, MAX_FILE_MB


def render_upload_page():
    st.title("Vera")
    st.write("Manda una revisión. Recibe un trail firmado.")

    st.session_state.setdefault("last_approval_link", None)

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
            size_mb = uploaded_file.size / (1024 * 1024)
            if size_mb > MAX_FILE_MB:
                st.error(f"Archivo demasiado grande: {size_mb:.1f}MB.")
            else:
                st.success(f"Imagen lista: {uploaded_file.name} · {size_mb:.1f}MB")

        submitted = st.form_submit_button("Send")

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

            st.session_state.last_approval_link = approval_link

        except ValueError as e:
            st.warning(str(e))
        except Exception as e:
            st.error("Vera no pudo completar la acción.")
            st.caption(str(e))

    if st.session_state.last_approval_link:
        st.success("Proyecto creado. Link de aprobación listo.")
        st.markdown("### Link privado")
        st.code(st.session_state.last_approval_link)
        st.link_button("Abrir vista cliente", st.session_state.last_approval_link)
