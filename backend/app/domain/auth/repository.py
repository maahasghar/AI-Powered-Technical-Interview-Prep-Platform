from app.domain.auth.models import AuthToken


class AuthRepository:
    def __init__(self, db):
        self.db = db

    def save(self, user_id: int, refresh_token: str, expires_at=None):
        token = AuthToken(
            user_id=user_id, refresh_token=refresh_token, expires_at=expires_at
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get(self, refresh_token: str):
        return (
            self.db.query(AuthToken)
            .filter(AuthToken.refresh_token == refresh_token)
            .first()
        )

    def revoke(self, refresh_token: str):
        self.db.query(AuthToken).filter(
            AuthToken.refresh_token == refresh_token
        ).update({"revoked": True})
        self.db.commit()
