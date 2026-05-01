MAX_FILE_MB = 10


def clean_optional_email(email: str | None) -> str | None:
    if email is None or email.strip() == "":
        return None

    email = email.strip()

    if "@" not in email or "." not in email:
        raise ValueError("El email no parece válido. Corrígelo o deja el campo vacío.")

    return email


def validate_image_file(uploaded_file) -> None:
    if uploaded_file is None:
        raise ValueError("Sube una imagen antes de enviar.")

    size_mb = uploaded_file.size / (1024 * 1024)

    if size_mb > MAX_FILE_MB:
        raise ValueError(f"La imagen pesa {size_mb:.1f}MB. Máximo permitido: {MAX_FILE_MB}MB.")
