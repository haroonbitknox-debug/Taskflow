import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode

from app.core.config import settings


class EmailConfigurationError(Exception):
    pass


class EmailDeliveryError(Exception):
    pass


def validate_email_configuration() -> None:
    if not settings.mail_is_configured:
        raise EmailConfigurationError("Mail provider is not configured.")
    if settings.mail_starttls == settings.mail_use_ssl:
        raise EmailConfigurationError("Configure exactly one secure SMTP transport.")


def send_password_reset_email(recipient: str, token: str) -> None:
    validate_email_configuration()

    reset_url = (
        f"{settings.app_base_url}/reset-password?"
        f"{urlencode({'token': token})}"
    )
    message = EmailMessage()
    message["Subject"] = "Reset your TaskFlow password"
    message["From"] = settings.mail_from
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your TaskFlow password.\n\n"
        f"Use this link within {settings.password_reset_token_expire_minutes} minutes:\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )

    context = ssl.create_default_context()
    try:
        if settings.mail_use_ssl:
            with smtplib.SMTP_SSL(
                settings.mail_host,
                settings.mail_port,
                context=context,
                timeout=15,
            ) as server:
                _authenticate(server)
                server.send_message(message)
        else:
            with smtplib.SMTP(
                settings.mail_host,
                settings.mail_port,
                timeout=15,
            ) as server:
                server.ehlo()
                if settings.mail_starttls:
                    server.starttls(context=context)
                    server.ehlo()
                _authenticate(server)
                server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError from exc


def _authenticate(server: smtplib.SMTP | smtplib.SMTP_SSL) -> None:
    if settings.mail_username:
        password = (
            settings.mail_password.get_secret_value()
            if settings.mail_password is not None
            else ""
        )
        server.login(settings.mail_username, password)
