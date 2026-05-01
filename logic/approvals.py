#approvals.py

import hashlib
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from data.db import get_connection
from external.certificates import generate_certificate


# -----------------------------
# HELPERS
# -----------------------------

def _now():
    return datetime.now().isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _make_hash(project_id: str, version_id: str, approved_at: str) -> str:
    raw = f"{project_id}|{version_id}|{approved_at}|vera"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()[:24]


def _get_base_url():
    # fallback para local
    return "http://localhost:8501"


# -----------------------------
# CREATE PROJECT
# -----------------------------

def create_project(
    project_name: str,
    client_name: str,
    client_email: str | None,
    uploaded_file,
) -> str:
    """
    Crea proyecto + primera versión.
    """

    conn = get_connection()

    project_id = _new_id("project")
    version_id = _new_id("version")

    created_at = _now()

    # guardar imagen
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    image_path = upload_dir / f"{project_id}_{version_id}.jpg"

    from PIL import Image

    image = Image.open(uploaded_file).convert("RGB")

    max_width = 1600
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, int(image.height * ratio)))

    image.save(image_path, "JPEG", quality=82, optimize=True)

    # DB inserts
    conn.execute(
        """
        INSERT INTO projects (id, project_name, client_name, client_email, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_id, project_name, client_name, client_email, created_at),
    )

    conn.execute(
        """
        INSERT INTO versions (id, project_id, version_number, image_path, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (version_id, project_id, 1, str(image_path), created_at),
    )

    conn.commit()
    conn.close()

    return project_id


# -----------------------------
# BUILD LINK
# -----------------------------

def build_approval_link(project_id: str) -> str:
    base = _get_base_url()
    return f"{base}?project_id={project_id}"


# -----------------------------
# GET PROJECT DATA
# -----------------------------

def get_project(project_id: str):
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    project = conn.execute(
        "SELECT * FROM projects WHERE id = ?",
        (project_id,),
    ).fetchone()

    if not project:
        conn.close()
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

    conn.close()

    return {
        "project": dict(project),
        "versions": [dict(v) for v in versions],
        "approval": dict(approval) if approval else None,
    }


# -----------------------------
# APPROVE PROJECT
# -----------------------------

def approve_project(project_id: str):
    """
    Aprueba la última versión del proyecto.
    """

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    project = conn.execute(
        "SELECT * FROM projects WHERE id = ?",
        (project_id,),
    ).fetchone()

    if not project:
        conn.close()
        raise ValueError("Proyecto no encontrado")

    latest_version = conn.execute(
        """
        SELECT * FROM versions
        WHERE project_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()

    if not latest_version:
        conn.close()
        raise ValueError("No hay versiones para aprobar")

    approved_at = _now()
    approval_id = _new_id("approval")

    approval_hash = _make_hash(
        project_id,
        latest_version["id"],
        approved_at,
    )

    # generar PDF
    certificate_path = generate_certificate(
        project=dict(project),
        version=dict(latest_version),
        approval_hash=approval_hash,
        approved_at=approved_at,
    )

    conn.execute(
        """
        INSERT INTO approvals (
            id,
            project_id,
            version_id,
            approved_at,
            approval_hash,
            certificate_path
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            approval_id,
            project_id,
            latest_version["id"],
            approved_at,
            approval_hash,
            certificate_path,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "approval_hash": approval_hash,
        "approved_at": approved_at,
        "pdf_path": certificate_path,
    }
