import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


class EmailClient:
    def send_verification_email(self, email: str, token: str):
        link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        self.send_email(
            to=email,
            subject="Verify your email",
            body=f"Click to verify your email: {link}",
        )

    def send_password_reset_email(self, email: str, token: str):
        link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        self.send_email(
            to=email,
            subject="Reset your password",
            body=f"Reset your password: {link}",
        )

    def send_email(self, to: str, subject: str, body: str):
        if settings.EMAIL_DELIVERY_MODE == "console":
            print(f"Email queued for {to}: {subject}")
            return

        if settings.EMAIL_DELIVERY_MODE != "smtp" or not settings.SMTP_HOST:
            raise RuntimeError("Email delivery is not configured")

        message = EmailMessage()
        message["From"] = settings.EMAIL_FROM
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls(context=context)
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
