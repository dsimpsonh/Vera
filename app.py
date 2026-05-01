import hashlib
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


# -----------------------------
# CONFIG
# -----------------------------

st.set_page_config(
    page_title="Vera — Approval Tracker",
    page_icon="V",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CERT_DIR = DATA_DIR / "certificates"
DB_PATH = DATA_DIR / "vera.db"
LOGO_PATH = BASE_DIR / "vera_logo.png"

MAX_FILE_MB = 10

for path in [DATA_DIR, UPLOAD_DIR, CERT_DIR]:
    path.mkdir(parents=True, exist_ok=True)


# -----------------------------
# STYLE
# -----------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #FDFCF9;
    color: #1A1A1A;
}

h1, h2, h3 {
    font-family: 'Playfair Display', serif;
    letter-spacing: -0.5px;
}

input, textarea {
    border: 1px solid #D9D6CF !important;
    background: #FFFFFF !important;
}

div.stButton > button {
    border: 1px solid #1A1A1A;
    background: transparent;
    color: #1A1A1A;
    padding: 10px 16px;
    font-weight: 500;
}

div.stButton > button:hover {
    background: #1A1A1A;
    color: #FFFFFF;
}

button[kind="primary"] {
    border: none !important;
    background-color: #E86C5D !important;
    color: white !important;
}

button[kind="primary"]:hover {
    background-color: #d85c4e !important;
}

.block-container {
    max-width: 980px;
}

.vera-card {
    background: #FFFFFF;
    border: 1px solid #D9D6CF;
    padding: 28px;
    margin: 18px 0;
}

.client-frame {
    background: #FFFFFF;
    border: 1px solid #D9D6CF;
    padding: 28px;
    margin-top: 20px;
}

.meta-line {
    color: #6E6A63;
    font-size: 14px;
}

.seal {
    border: 2px solid #1A1A1A;
    background: #FFFFFF;
    padding: 28px;
    text-align: center;
    margin-top: 24px;
}

.seal-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.2rem;
    letter-spacing: 0.12em;
}

.stSuccess {
    border-left: 3px solid #2F7A65;
}
</style>
""", unsafe_allow_html=True)


def render_logo():
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=140)


# -----------------------------
# DB
# -----------------------------

def db():
    return sqlite3.connect(DB_PATH)


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_email TEXT,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS versions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version_id TEXT NOT NULL,
                approved_at TEXT NOT NULL,
                approval_hash TEXT NOT NULL,
                certificate_path TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(version_id) REFERENCES versions(id)
            )
        """)


init_db()


# -----------------------------
# HELPERS
# -----------------------------

def now():
    return datetime.now().isoformat(timespec="seconds")


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def clean_optional_email(email):
    if email is None or email.strip() == "":
        return None

    email = email.strip()

    if "@" not in email or "." not in email:
        raise ValueError("El email no parece válido. Corrígelo o deja el campo vacío.")

    return email


def validate_file(uploaded_file):
    if uploaded_file is None:
        raise ValueError("Sube una imagen antes de continuar.")

    size_mb = uploaded_file.size / (1024 * 1024)

    if size_mb > MAX_FILE_MB:
        raise ValueError(f"La imagen pesa {size_mb:.1f}MB. Máximo permitido: {MAX_FILE_MB}MB.")


def save_image(uploaded_file, project_id, version_id):
    image = Image.open(uploaded_file).convert("RGB")

    max_width = 1600
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, int(image.height * ratio)))

    image_path = UPLOAD_DIR / f"{project_id}_{version_id}.jpg"
    image.save(image_path, "JPEG", quality=82, optimize=True)

    return str(image_path)


def make_hash(project_id, version_id, approved_at):
    raw = f"{project_id}|{version_id}|{approved_at}|vera"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()[:24]


def base_url():
    return st.secrets.get("APP_BASE_URL", "http://localhost:8501")


def build_link(project_id):
    return f"{base_url()}/?project_id={project_id}"


# -----------------------------
# REPOSITORY
# -----------------------------

def create_project(project_name, client_name, client_email, uploaded_file, note):
    project_id = new_id("project")
    version_id = new_id("version")
    created_at = now()
    image_path = save_image(uploaded_file, project_id, version_id)

    with db() as conn:
        conn.execute(
            """
            INSERT INTO projects (id, project_name, client_name, client_email, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, project_name, client_name, client_email, created_at),
        )

        conn.execute(
            """
            INSERT INTO versions (id, project_id, version_number, image_path, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (version_id, project_id, 1, image_path, note, created_at),
        )

    return project_id


def add_version(project_id, uploaded_file, note):
    version_id = new_id("version")
    created_at = now()

    with db() as conn:
        latest = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) FROM versions WHERE project_id = ?",
            (project_id,),
        ).fetchone()[0]

        version_number = latest + 1
        image_path = save_image(uploaded_file, project_id, version_id)

        conn.execute(
            """
            INSERT INTO versions (id, project_id, version_number, image_path, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (version_id, project_id, version_number, image_path, note, created_at),
        )


def get_project(project_id):
    with db() as conn:
        conn.row_factory = sqlite3.Row

        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

        if not project:
            return None

        versions = conn.execute(
            """
            SELECT * FROM versions
            WHERE project_id = ?
            ORDER BY version_number DESC
            """,
            (project_id,),
        ).fetchall()

        approval = conn.execute(
            """
            SELECT * FROM approvals
            WHERE project_id = ?
            ORDER BY approved_at DESC
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()

    return {
        "project": dict(project),
        "versions": [dict(v) for v in versions],
        "approval": dict(approval) if approval else None,
    }


def list_projects():
    with db() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT p.*,
                   COUNT(v.id) AS version_count,
                   MAX(v.created_at) AS last_updated
            FROM projects p
            LEFT JOIN versions v ON p.id = v.project_id
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """).fetchall()

    return [dict(row) for row in rows]


# -----------------------------
# PDF
# -----------------------------

def generate_certificate(project, version, approval_hash, approved_at):
    certificate_path = CERT_DIR / f"certificate_{project['id']}_{version['id']}.pdf"

    c = canvas.Canvas(str(certificate_path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 24)
    c.drawString(72, height - 90, "Vera Approval Certificate")

    c.setFont("Helvetica", 12)
    c.drawString(72, height - 140, f"Project: {project['project_name']}")
    c.drawString(72, height - 165, f"Client: {project['client_name']}")
    c.drawString(72, height - 190, f"Version: V{version['version_number']}")
    c.drawString(72, height - 215, f"Approved at: {approved_at}")
    c.drawString(72, height - 240, f"Approval hash: {approval_hash}")

    c.line(72, height - 280, width - 72, height - 280)

    c.setFont("Helvetica-Bold", 20)
    c.drawString(72, height - 325, "STATUS: APPROVED")

    c.setFont("Helvetica", 9)
    c.drawString(72, 72, "Generated by Vera MVP.")

    c.save()

    return str(certificate_path)


def approve_latest(project, version):
    approved_at = now()
    approval_id = new_id("approval")
    approval_hash = make_hash(project["id"], version["id"], approved_at)

    certificate_path = generate_certificate(
        project=project,
        version=version,
        approval_hash=approval_hash,
        approved_at=approved_at,
    )

    with db() as conn:
        conn.execute(
            """
            INSERT INTO approvals (
                id, project_id, version_id, approved_at, approval_hash, certificate_path
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                project["id"],
                version["id"],
                approved_at,
                approval_hash,
                certificate_path,
            ),
        )

    return {
        "approved_at": approved_at,
        "approval_hash": approval_hash,
        "certificate_path": certificate_path,
    }


# -----------------------------
# VIEWS
# -----------------------------

def render_studio():
    render_logo()
    st.title("Vera")
    st.caption("Comparte una versión. Cierra con claridad.")

    tab_create, tab_history = st.tabs(["Nuevo envío", "Historial"])

    with tab_create:
        with st.form("create_project_form", clear_on_submit=False):
            project_name = st.text_input("Nombre del proyecto")
            client_name = st.text_input("Nombre del cliente")
            client_email = st.text_input("Email del cliente opcional")
            note = st.text_area("Nota de la versión")
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

            submitted = st.form_submit_button("Generar link de aprobación")

        if submitted:
            try:
                if not project_name.strip():
                    raise ValueError("Añade el nombre del proyecto.")
                if not client_name.strip():
                    raise ValueError("Añade el nombre del cliente.")

                validate_file(uploaded_file)
                clean_email = clean_optional_email(client_email)

                with st.spinner("Creando proyecto y generando link..."):
                    project_id = create_project(
                        project_name=project_name.strip(),
                        client_name=client_name.strip(),
                        client_email=clean_email,
                        uploaded_file=uploaded_file,
                        note=note.strip(),
                    )

                link = build_link(project_id)

                st.success("Todo listo. Comparte este enlace con tu cliente.")
                st.code(link)
                st.link_button("Simular vista cliente", link)

            except ValueError as error:
                st.warning(str(error))
            except Exception as error:
                st.error("Vera no pudo completar la acción.")
                st.caption(str(error))

    with tab_history:
        projects = list_projects()

        if not projects:
            st.info("Aún no hay proyectos.")
            return

        for project in projects:
            with st.expander(f"{project['project_name']} — {project['client_name']}"):
                st.write(f"Creado: {project['created_at']}")
                st.write(f"Versiones: {project['version_count']}")
                st.code(build_link(project["id"]))
                st.link_button(
                    "Ver como cliente",
                    build_link(project["id"]),
                    key=f"client_view_{project['id']}",
                )

                with st.form(f"version_form_{project['id']}", clear_on_submit=True):
                    version_note = st.text_area("Nota para nueva versión")
                    new_file = st.file_uploader(
                        "Subir nueva versión",
                        type=["png", "jpg", "jpeg", "webp"],
                        key=f"file_{project['id']}",
                    )
                    add_submitted = st.form_submit_button("Añadir versión")

                if add_submitted:
                    try:
                        validate_file(new_file)
                        with st.spinner("Guardando nueva versión..."):
                            add_version(project["id"], new_file, version_note.strip())
                        st.success("Nueva versión añadida.")
                        st.rerun()
                    except ValueError as error:
                        st.warning(str(error))


def render_client(project_id):
    render_logo()

    data = get_project(project_id)

    if data is None:
        st.error("Este link no corresponde a ningún proyecto disponible.")
        st.info("Para esta demo, crea primero un proyecto desde la vista de Sofía.")
        return

    project = data["project"]
    versions = data["versions"]
    approval = data["approval"]

    if not versions:
        st.error("Este proyecto no tiene ninguna versión para revisar.")
        return

    latest_version = versions[0]

    st.title("Revisión privada")
    st.caption("Vera · Approval tracker")

    st.markdown('<div class="client-frame">', unsafe_allow_html=True)

    left, right = st.columns([1.2, 2])

    with left:
        st.markdown("### Detalles")
        st.write(f"**Proyecto:** {project['project_name']}")
        st.write(f"**Cliente:** {project['client_name']}")
        st.write(f"**Versión:** V{latest_version['version_number']}")
        st.markdown(
            f"<p class='meta-line'>Creado: {project['created_at']}</p>",
            unsafe_allow_html=True,
        )

        if latest_version.get("note"):
            st.markdown("### Nota de la ilustradora")
            st.write(latest_version["note"])

    with right:
        image_path = latest_version.get("image_path")
        if image_path and Path(image_path).exists():
            st.image(image_path, use_container_width=True)
        else:
            st.warning("No se encontró la imagen de esta versión.")

    st.markdown("</div>", unsafe_allow_html=True)

    if approval:
        st.success("Esta versión ya fue aprobada.")

        st.markdown(
            f"""
            <div class="seal">
                <div class="seal-title">APROBADO</div>
                <p>Fecha: {approval["approved_at"]}</p>
                <p>Hash: {approval["approval_hash"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        certificate_path = approval.get("certificate_path")

        if certificate_path and Path(certificate_path).exists():
            with open(certificate_path, "rb") as pdf:
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
            with st.spinner("Sellando aprobación y generando certificado..."):
                approval_result = approve_latest(project, latest_version)

            st.balloons()
            st.success("Versión aprobada.")

            st.markdown(
                f"""
                <div class="seal">
                    <div class="seal-title">APROBADO</div>
                    <p>Fecha: {approval_result["approved_at"]}</p>
                    <p>Hash: {approval_result["approval_hash"]}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with open(approval_result["certificate_path"], "rb") as pdf:
                st.download_button(
                    "Descargar certificado PDF",
                    data=pdf,
                    file_name="vera_approval_certificate.pdf",
                    mime="application/pdf",
                )


# -----------------------------
# ENTRY
# -----------------------------

project_id = st.query_params.get("project_id")

if project_id:
    render_client(project_id)
else:
    render_studio()
