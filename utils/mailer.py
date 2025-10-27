import os
import smtplib
from typing import List, Optional, Tuple
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


def send_email(to_email: str, subject: str, html_body: str, attachments: Optional[List[Tuple[str, bytes]]] = None) -> bool:
    """Send an email using SMTP settings from environment.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML body content
        attachments: Optional list of (filename, file_bytes)

    Env vars supported:
        SMTP_HOST (default: smtp.gmail.com)
        SMTP_PORT (default: 587)
        SMTP_USER, SMTP_PASSWORD (required)
        SMTP_USE_TLS (default: true)
        SMTP_USE_SSL (default: false)
        SMTP_FROM (optional; uses SMTP_USER when not set)
    """
    try:
        host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
        from_email = os.getenv("SMTP_FROM") or user

        if not user or not password:
            raise RuntimeError("SMTP_USER or SMTP_PASSWORD not configured")

        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Attach files
        for fname, fbytes in (attachments or []):
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(fbytes)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{fname}"')
            msg.attach(part)

        if use_ssl:
            server = smtplib.SMTP_SSL(host, port)
        else:
            server = smtplib.SMTP(host, port)
            if use_tls:
                server.starttls()
        server.login(user, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception:
        return False
