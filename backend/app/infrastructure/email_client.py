class EmailClient:
    def send_verification_email(self, email: str, token: str):
        link = f"https://yourapp.com/verify?token={token}"
        self.send_email(
            to=email,
            subject="Verify your email",
            body=f"Click to verify your email: {link}",
        )

    def send_password_reset_email(self, email: str, token: str):
        link = f"https://yourapp.com/reset-password?token={token}"
        self.send_email(
            to=email,
            subject="Reset your password",
            body=f"Reset your password: {link}",
        )

    def send_email(self, to: str, subject: str, body: str):
        # Placeholder implementation
        # TODO: Implement actual email sending logic (SMTP, SendGrid, etc.)
        print(f"Email sent to {to}: {subject}")
