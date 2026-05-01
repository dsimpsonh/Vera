import streamlit as st
import sqlite3
import hashlib
import uuid
from pathlib import Path
from datetime import datetime
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Vera — Approval Tracker",
    page_icon="V",
    layout="wide"
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
APPROVAL_DIR = DATA_DIR / "approvals"
DB_PATH = DATA_DIR / "vera.db"

for folder in [DATA_DIR, UPLOAD_DIR, APPROVAL_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# STYLE
# --------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Space+Mono&display=swap');

    .stApp {
        background: #FDFCFB;
        color: #191919;
    }

    h1, h2, h3 {
        font-family: 'Playfair Display', serif;
    }

    p, label, div, button, input, textarea {
        font-family: 'Space Mono', monospace;
    }

    .vera-card {
        background: white;
        border: 1px solid #191919;
        padding: 2rem;
        border-radius: 4px;
        margin-bottom: 1rem;
    }

    .seal {
        border: 3px solid #191919;
        background: #ffffff;
        padding: 2rem;
        text-align: center;
        margin-top: 2rem;
    }

    .seal-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.4rem;
        letter-spacing: 0.12em;
    }

    .small {
        font-size: 0.85rem;
        opacity: 0.75;
    }

    div.stButton > button {
        border: 2px solid #191919;
        background: white;
        color: #191919;
        border-radius: 0;
        padding: 0.8rem 1.2rem;
        font-weight: 700;
    }

    div.stButton > button:hover {
        background: #191919;
        color: white;
        border: 2px solid #191919;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_email TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS versions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version_id TEXT NOT NULL,
                approved_at TEXT NOT NULL,
                approval_hash TEXT NOT NULL,
                client_name TEXT NOT NULL,
                pdf_path TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(version_id) REFERENCES versions(id)
            )
            """
        )


init_db()


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def make_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def make_hash(*parts):
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()


def save_compressed_image(uploaded_file, project_id, version_id):
    image = Image.open(uploaded_file).convert("RGB")

    max_width = 1600
    if image.width > max_width:
        ratio = max_width / image.width
        new_size = (max_width, int(image.height * ratio))
        image = image.resize(new_size)

    path = UPLOAD_DIR / f"{project_id}_{version_id}.jpg"
    image.save(path, format="JPEG", quality=82, optimize=True)

    return str(path)


def create_approval_pdf(project, version, approval_hash, approved_at):
    pdf_id = make_id("pdf")
    pdf_path = APPROVAL_DIR / f"{pdf_id}.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 24)
    c.drawString(72, height - 90, "Vera Approval Certificate")

    c.setFont("Helvetica", 12)
    c.drawString(72, height - 130, f"Project: {project['project_name']}")
    c.drawString(72, height - 155, f"Client: {project['client_name']}")
    c.drawString(72, height - 180, f"Version: {version['version_number']}")
    c.drawString(72, height - 205, f"Approved at: {approved_at}")
    c.drawString(72, height - 230, f"Approval hash: {approval_hash}")

    c.line(72, height - 270, width - 72, height - 270)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, height - 315, "APPROVED")

    c.setFont("Helvetica", 10)
    c.drawString(
        72,
        72,
        "Generated by Vera. This MVP certificate records a timestamped approval trail."
    )

    c.save()
    return str(pdf_path)


def get_base_url():
    return st.query_params.get("base_url", "http://localhost:8501")


# --------------------------------------------------
# DB OPERATIONS
# --------------------------------------------------

def create_project(project_name, client_name, client_email, uploaded_file, note):
    project_id = make_id("project")
    version_id = make_id("version")
    created_at = now_iso()

    image_path = save_compressed_image(uploaded_file, project_id, version_id)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO projects (id, project_name, client_name, client_email, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, project_name, client_name, client_email, created_at)
        )

        conn.execute(
            """
            INSERT INTO versions (id, project_id, version_number, image_path, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (version_id, project_id, 1, image_path, note, created_at)
        )

    return project_id


def add_version(project_id, uploaded_file, note):
    version_id = make_id("version")
    created_at = now_iso()

    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) FROM versions WHERE project_id = ?",
            (project_id,)
        ).fetchone()

        next_version = row[0] + 1
        image_path = save_compressed_image(uploaded_file, project_id, version_id)

        conn.execute(
            """
            INSERT INTO versions (id, project_id, version_number, image_path, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (version_id, project_id, next_version, image_path, note, created_at)
        )


def get_project(project_id):
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row

        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,)
        ).fetchone()

        if not project:
            return None

        versions = conn.execute(
            """
            SELECT * FROM versions
            WHERE project_id = ?
            ORDER BY version_number DESC
            """,
            (project_id,)
        ).fetchall()

        approval = conn.execute(
            """
            SELECT * FROM approvals
            WHERE project_id = ?
            ORDER BY approved_at DESC
            LIMIT 1
            """,
            (project_id,)
        ).fetchone()

    return {
        "project": dict(project),
        "versions": [dict(v) for v in versions],
        "approval": dict(approval) if approval else None
    }


def list_projects():
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT p.*,
                   COUNT(v.id) as version_count,
                   MAX(v.created_at) as last_updated
            FROM projects p
            LEFT JOIN versions v ON p.id = v.project_id
            GROUP BY p.id
            ORDER BY p.created_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def approve_version(project, version):
    approved_at = now_iso()
    approval_id = make_id("approval")

    approval_hash = make_hash(
        project["id"],
        version["id"],
        version["version_number"],
        approved_at,
        project["client_name"]
    )

    pdf_path = create_approval_pdf(
        project=project,
        version=version,
        approval_hash=approval_hash,
        approved_at=approved_at
    )

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO approvals (
                id, project_id, version_id, approved_at,
                approval_hash, client_name, pdf_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                project["id"],
                version["id"],
                approved_at,
                approval_hash,
                project["client_name"],
                pdf_path
            )
        )

    return approval_hash, approved_at, pdf_path


# --------------------------------------------------
# ROUTING
# --------------------------------------------------

project_id = st.query_params.get("project_id")
view = st.query_params.get("view", "studio")


# --------------------------------------------------
# CLIENT VIEW
# --------------------------------------------------

def render_client_view(project_id):
    data = get_project(project_id)

    if not data:
        st.error("Proyecto no encontrado.")
        st.stop()

    project = data["project"]
    versions = data["versions"]
    approval = data["approval"]
    latest_version = versions[0]

    st.title("Vera")
    st.markdown("### Revisión privada para aprobación")

    st.markdown('<div class="vera-card">', unsafe_allow_html=True)
    st.subheader(project["project_name"])
    st.write(f"Cliente: {project['client_name']}")
    st.write(f"Versión actual: V{latest_version['version_number']}")

    if latest_version["note"]:
        st.write(f"Nota de la ilustradora: {latest_version['note']}")

    st.image(latest_version["image_path"], use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if approval:
        st.success("Esta versión ya tiene una aprobación registrada.")

        st.markdown(
            f"""
            <div class="seal">
                <div class="seal-title">APROBADO</div>
                <p>Fecha: {approval["approved_at"]}</p>
                <p>Hash: {approval["approval_hash"]}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if approval.get("pdf_path") and Path(approval["pdf_path"]).exists():
            with open(approval["pdf_path"], "rb") as f:
                st.download_button(
                    "Descargar certificado PDF",
                    data=f,
                    file_name="vera_approval_certificate.pdf",
                    mime="application/pdf"
                )

        return

    st.warning("Revisa la imagen antes de aprobar. Esta acción creará un registro de aprobación.")

    confirm = st.checkbox("Confirmo que apruebo esta versión final.")

    if confirm:
        if st.button("SELLAR Y APROBAR VERSIÓN", use_container_width=True):
            approval_hash, approved_at, pdf_path = approve_version(project, latest_version)

            st.balloons()
            st.success("Versión aprobada y sellada.")

            st.markdown(
                f"""
                <div class="seal">
                    <div class="seal-title">APROBADO</div>
                    <p>Fecha: {approved_at}</p>
                    <p>Hash: {approval_hash}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            with open(pdf_path, "rb") as f:
                st.download_button(
                    "Descargar certificado PDF",
                    data=f,
                    file_name="vera_approval_certificate.pdf",
                    mime="application/pdf"
                )


# --------------------------------------------------
# STUDIO VIEW
# --------------------------------------------------

def render_studio_view():
    st.title("Vera — approval tracker")
    st.write("Manda una revisión. Recibe un trail firmado.")

    tab_new, tab_existing = st.tabs(["Nuevo proyecto", "Proyectos"])

    with tab_new:
        st.markdown('<div class="vera-card">', unsafe_allow_html=True)

        with st.form("new_project_form"):
            project_name = st.text_input("Nombre del proyecto")
            client_name = st.text_input("Cliente")
            client_email = st.text_input("Email del cliente opcional")
            note = st.text_area("Nota para esta versión")
            uploaded_file = st.file_uploader(
                "Sube la ilustración",
                type=["png", "jpg", "jpeg", "webp"]
            )

            submitted = st.form_submit_button("Generar link de aprobación")

        st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            if not project_name or not client_name or not uploaded_file:
                st.error("Falta nombre del proyecto, cliente o imagen.")
            else:
                new_project_id = create_project(
                    project_name=project_name,
                    client_name=client_name,
                    client_email=client_email,
                    uploaded_file=uploaded_file,
                    note=note
                )

                approval_link = f"{get_base_url()}?project_id={new_project_id}"

                st.success("Proyecto creado.")
                st.write("Link privado de aprobación:")
                st.code(approval_link)

                st.link_button("Abrir vista cliente", approval_link)

    with tab_existing:
        projects = list_projects()

        if not projects:
            st.info("Todavía no hay proyectos.")
            return

        for project in projects:
            with st.expander(f"{project['project_name']} — {project['client_name']}"):
                st.write(f"Creado: {project['created_at']}")
                st.write(f"Versiones: {project['version_count']}")

                approval_link = f"{get_base_url()}?project_id={project['id']}"
                st.code(approval_link)

                with st.form(f"add_version_{project['id']}"):
                    note = st.text_area("Nota de nueva versión")
                    uploaded_file = st.file_uploader(
                        "Subir nueva versión",
                        type=["png", "jpg", "jpeg", "webp"],
                        key=f"upload_{project['id']}"
                    )

                    submitted = st.form_submit_button("Añadir versión")

                if submitted:
                    if not uploaded_file:
                        st.error("Sube una imagen para crear una nueva versión.")
                    else:
                        add_version(project["id"], uploaded_file, note)
                        st.success("Nueva versión añadida.")
                        st.rerun()


# --------------------------------------------------
# APP ENTRY
# --------------------------------------------------

if project_id:
    render_client_view(project_id)
else:
    render_studio_view()
