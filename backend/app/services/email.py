import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
import structlog

log = structlog.get_logger()


async def send_verification_email(to_email: str, token: str, frontend_url: str) -> None:
    verify_url = f"{frontend_url}/auth/verify-email?token={token}"
    await _send_email(
        to=to_email,
        subject="Verify your Stipple account",
        body=f"Click to verify your email:\n{verify_url}\n\nThis link expires in 24 hours.",
        html_body=(
            f"<p>Click to verify your email:</p>"
            f'<p><a href="{verify_url}">{verify_url}</a></p>'
            f"<p>This link expires in 24 hours.</p>"
        ),
        token=token,
        token_type="verify",
        to_email=to_email,
    )


async def send_password_reset_email(to_email: str, token: str, frontend_url: str) -> None:
    reset_url = f"{frontend_url}/auth/reset-password?token={token}"
    await _send_email(
        to=to_email,
        subject="Reset your Stipple password",
        body=f"Click to reset your password:\n{reset_url}\n\nThis link expires in 1 hour.",
        html_body=(
            f"<p>Click to reset your password:</p>"
            f'<p><a href="{reset_url}">{reset_url}</a></p>'
            f"<p>This link expires in 1 hour.</p>"
        ),
        token=token,
        token_type="reset",
        to_email=to_email,
    )


async def _send_email(
    to: str,
    subject: str,
    body: str,
    html_body: str,
    token: str,
    token_type: str,
    to_email: str,
) -> None:
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    if not smtp_password or smtp_password.startswith("SG.placeholder"):
        # Dev mode: no email is sent and no token is stored anywhere.
        # The database already holds only the SHA-256 hash — the raw token
        # exists only in memory for the duration of the request.
        # To test the verification flow, capture the token from your test
        # script at the point it is generated, or query the email_tokens
        # table and use the hash to locate the matching token in your test.
        log.info(
            "dev_email_skipped",
            token_type=token_type,
            recipient=to_email,
            instruction=(
                "No token is stored outside the database. "
                "Capture the raw token from your test script, or query "
                "email_tokens WHERE used_at IS NULL ORDER BY created_at DESC."
            ),
        )
        return

    smtp_host = os.getenv("SMTP_HOST", "smtp.sendgrid.net")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "apikey")
    email_from = os.getenv("EMAIL_FROM", "noreply@example.com")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = to
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    await aiosmtplib.send(
        msg,
        hostname=smtp_host,
        port=smtp_port,
        username=smtp_user,
        password=smtp_password,
        start_tls=True,
    )
