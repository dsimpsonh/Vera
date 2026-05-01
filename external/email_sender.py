def send_client_email(client_email: str | None, approval_link: str, project_name: str):
    """
    MVP-safe email sender.

    For now, email is optional. If no email is provided, Vera should still
    generate the approval link and continue the demo flow.
    """

    if client_email is None or client_email.strip() == "":
        return {
            "sent": False,
            "reason": "No email provided",
        }

    # SMTP real can be added later.
    # For demo, we return success without crashing.

    return {
        "sent": True,
        "reason": "Email ready",
        "to": client_email.strip(),
        "project_name": project_name,
        "approval_link": approval_link,
    }
