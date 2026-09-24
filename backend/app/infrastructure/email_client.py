import logging

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Email could not be accepted by the delivery provider."""


class EmailClient:
    def send_verification_email(self, email: str, token: str):
        link = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={token}"
        self.send_email(
            to=email,
            subject="Verify your email",
            body=f"Click to verify your email: {link}",
        )

    def send_password_reset_email(self, email: str, token: str):
        link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
        self.send_email(
            to=email,
            subject="Reset your password",
            body=f"Reset your password: {link}",
        )

    def send_email(self, to: str, subject: str, body: str):
        if settings.EMAIL_DELIVERY_MODE == "console":
            logger.info("Email delivery skipped (console mode): %s", subject)
            return

        api_key = settings.RESEND_API_KEY.get_secret_value().strip()
        if settings.EMAIL_DELIVERY_MODE != "resend" or not api_key:
            logger.error("Set EMAIL_DELIVERY_MODE=resend and RESEND_API_KEY")
            raise EmailDeliveryError("Email delivery is not configured")

        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "from": settings.EMAIL_FROM,
                    "to": [to],
                    "subject": subject,
                    "text": body,
                },
                timeout=settings.EMAIL_TIMEOUT_SECONDS,
            )
        except httpx.RequestError:
            logger.error("Resend email request failed or timed out")
            raise EmailDeliveryError("Email provider is unavailable") from None

        if not response.is_success:
            # Provider bodies may contain recipient details; log only the status.
            logger.error("Resend rejected email (HTTP %s)", response.status_code)
            raise EmailDeliveryError("Email provider rejected the request")
