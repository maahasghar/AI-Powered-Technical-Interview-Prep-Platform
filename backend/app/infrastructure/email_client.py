from app.domain.auth.service import send_email


class EmailService:
    def send_verification_email(self, email: str, token: str):
        link = f"https://yourapp.com/verify?token={token}"
        send_email(
            to=email,
            subject="Verify your email",
            body=f"Click to verify your email: {link}",
        )
