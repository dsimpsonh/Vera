import streamlit as st
import pandas as pd
import hashlib
import uuid
from datetime import datetime
from pathlib import Path

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="Vera — Tracker de Aprobación",
    page_icon="🖋️",
    layout="wide"
)

LOG_PATH = Path("approval_logs.csv")


# -----------------------------
# STYLES
# -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=Space+Mono&display=swap');

.stApp {
    background-color: #FDFCFB;
    color: #1E1E1E;
}

h1, h2, h3 {
    font-family: 'Playfair Display', serif;
}

p, label, div, button {
    font-family: 'Space Mono', monospace;
}

.gallery-card {
    border: 1px solid #1E1E1E;
    padding: 2rem;
    border-radius: 2px;
    background: white;
}

.seal {
    border: 2px solid #1E1E1E;
    padding: 2rem;
    text-align: center;
    margin-top: 2rem;
    background: #fff;
}

.seal-title {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    letter-spacing: 2px;
}

.approve-button button {
    width: 100%;
    min-height: 90px;
    font-size: 1.2rem;
    border: 2px solid #1E1E1E;
}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# SESSION STATE
# -----------------------------
if "projects" not in st.session_state:
    st.session_state.projects = {}

if "approved_projects" not in st.session_state:
    st.session_state.approved_projects = {}


# -----------------------------
# HELPERS
# -----------------------------
def generate_project_id(project_name: str, client_name: str) -> str:
    base = f"{project_name}-{client_name}-{uuid.uuid4()}"
    return hashlib.sha256(base.encode()).hexdigest()[:10]


def generate_fake_hash(project_id: str) -> str:
    timestamp = datetime.utcnow().isoformat()
    raw = f"{project_id}-{timestamp}-vera"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()


def save_approval_log(project_id: str, project_name: str, client_name: str, approval_hash: str):
    log_entry = {
        "project_id": project_id,
        "project_name": project_name,
        "client_name": client_name,
        "approved_at": datetime.now().isoformat(timespec="seconds"),
        "approval_hash": approval_hash
    }

    if LOG_PATH.exists():
        df = pd.read_csv(LOG_PATH)
        df = pd.concat([df, pd.DataFrame([log_entry])], ignore_index=True)
    else:
        df = pd.DataFrame([log_entry])

    df.to_csv(LOG_PATH, index=False)


def get_current_base_url() -> str:
    return "http://localhost:8501"


# -----------------------------
# ROUTING
# -----------------------------
query_params = st.query_params
project_id = query_params.get("project_id", None)


# -----------------------------
# VISTA CLIENTE
# -----------------------------
if project_id:
    st.title("Vera")
    st.markdown("### Galería de aprobación privada")

    project = st.session_state.projects.get(project_id)

    if not project:
        st.error("No se encontró este proyecto en la sesión actual.")
        st.info("Para esta demo sin base de datos, primero debes crear el proyecto desde la vista de Sofía.")
        st.stop()

    st.markdown('<div class="gallery-card">', unsafe_allow_html=True)

    st.subheader(project["project_name"])
    st.caption(f"Cliente: {project['client_name']}")

    st.image(project["image"], use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")

    with st.container():
        st.markdown('<div class="approve-button">', unsafe_allow_html=True)

        approved = st.button("SELLAR Y APROBAR VERSIÓN")

        st.markdown("</div>", unsafe_allow_html=True)

    if approved:
        approval_hash = generate_fake_hash(project_id)
        approved_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        st.session_state.approved_projects[project_id] = {
            "approved_at": approved_at,
            "approval_hash": approval_hash
        }

        save_approval_log(
            project_id=project_id,
            project_name=project["project_name"],
            client_name=project["client_name"],
            approval_hash=approval_hash
        )

        st.balloons()

    if project_id in st.session_state.approved_projects:
        approval = st.session_state.approved_projects[project_id]

        st.markdown(f"""
        <div class="seal">
            <div class="seal-title">APROBADO</div>
            <p>Versión sellada digitalmente</p>
            <p><strong>Fecha:</strong> {approval["approved_at"]}</p>
            <p><strong>Hash:</strong> {approval["approval_hash"]}</p>
        </div>
        """, unsafe_allow_html=True)


# -----------------------------
# VISTA SOFÍA
# -----------------------------
else:
    st.title("Vera")
    st.markdown("### Tracker de aprobación para ilustradoras")
    st.write("Sube una ilustración, crea un proyecto y genera un enlace privado para aprobación del cliente.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<div class="gallery-card">', unsafe_allow_html=True)

        project_name = st.text_input("Nombre del Proyecto")
        client_name = st.text_input("Cliente")

        uploaded_image = st.file_uploader(
            "Sube la imagen de la ilustración",
            type=["png", "jpg", "jpeg", "webp"]
        )

        generate_link = st.button("Generar Link de Aprobación")

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        if uploaded_image:
            st.image(uploaded_image, caption="Vista previa", use_container_width=True)
        else:
            st.info("La imagen aparecerá aquí como vista previa.")

    if generate_link:
        if not project_name or not client_name or not uploaded_image:
            st.warning("Completa el nombre del proyecto, cliente e imagen antes de generar el link.")
        else:
            new_project_id = generate_project_id(project_name, client_name)

            st.session_state.projects[new_project_id] = {
                "project_name": project_name,
                "client_name": client_name,
                "image": uploaded_image.getvalue()
            }

            approval_url = f"{get_current_base_url()}?project_id={new_project_id}"

            st.success("Link de aprobación generado.")

            st.code(approval_url, language="text")

            st.markdown(
                f"[Abrir vista cliente]({approval_url})",
                unsafe_allow_html=True
            )

    st.divider()

    st.caption("Demo MVP sin base de datos. Los proyectos viven en st.session_state durante la sesión activa.")
