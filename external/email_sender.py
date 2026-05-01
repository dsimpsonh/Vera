import smtplib
from email.mime.text import MIMEText
import streamlit as st


def send_client_email(client_email: str | None, approval_link: str, project_name: str):
    if client_email is None or client_email.strip() == "":
        return {
            "sent": False,
            "reason": "No email provided",
        }

    smtp_host = st.secrets.get("SMTP_HOST")
    smtp_port = int(st.secrets.get("SMTP_PORT", 587))
    smtp_user = st.secrets.get("SMTP_USER")
    smtp_password = st.secrets.get("SMTP_PASSWORD")
    from_email = st.secrets.get("FROM_EMAIL", smtp_user)

    if not all([smtp_host, smtp_user, smtp_password, from_email]):
        return {
            "sent": False,
            "reason": "SMTP not configured",
        }

    subject = f"Aprobación pendiente: {project_name}"

    body = f"""
Hola,

Sofía te ha enviado una versión para aprobar en Vera.

Proyecto: {project_name}

Puedes revisar y aprobar la imagen aquí:
{approval_link}

Gracias,
Vera
"""

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = client_email.strip()

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, [client_email.strip()], message.as_string())

    return {
        "sent": True,
        "reason": "Email sent",
        "to": client_email.strip(),
    }
