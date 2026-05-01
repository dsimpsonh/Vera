
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pathlib import Path


def generate_certificate(project, version, approval_hash, approved_at):
    output_dir = Path("data/certificates")
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / f"{project['id']}_{version['id']}.pdf"

    c = canvas.Canvas(str(file_path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 22)
    c.drawString(72, height - 90, "Vera Approval Certificate")

    c.setFont("Helvetica", 12)
    c.drawString(72, height - 140, f"Project: {project['project_name']}")
    c.drawString(72, height - 165, f"Client: {project['client_name']}")
    c.drawString(72, height - 190, f"Version: {version['version_number']}")
    c.drawString(72, height - 215, f"Approved at: {approved_at}")
    c.drawString(72, height - 240, f"Hash: {approval_hash}")

    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, height - 300, "STATUS: APPROVED")

    c.save()

    return str(file_path)
