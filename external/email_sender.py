def send_client_email(client_email, approval_link, project_name):
    if client_email is None or client_email.strip() == "":
        return {"sent": False, "reason": "No email provided"}

    return {"sent": True, "reason": "Email ready"}
