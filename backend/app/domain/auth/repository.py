from datetime import datetime, timedelta, timezone

from app.domain.auth.models import AuthToken


class AuthRepository:
    def __init__(self, db):
        self.db = db

    def save(self, user_id: int, token_hash: str, family_id: str, expires_at=None):
        token = AuthToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get(self, token_hash: str):
        return (
            self.db.query(AuthToken).filter(AuthToken.token_hash == token_hash).first()
        )

    def revoke_family(self, family_id: str):
        self.db.query(AuthToken).filter(AuthToken.family_id == family_id).update(
            {"revoked": True}
        )
        self.db.commit()

    def revoke_and_rotate(self, token, replacement_hash: str):
        token.revoked = True
        token.replaced_at = datetime.now(timezone.utc)
        replacement = AuthToken(
            user_id=token.user_id,
            token_hash=replacement_hash,
            family_id=token.family_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.db.add(replacement)
        self.db.commit()
        self.db.refresh(replacement)
        return replacement

    def revoke_all_for_user(self, user_id: int):
        self.db.query(AuthToken).filter(AuthToken.user_id == user_id).update(
            {"revoked": True}
        )
        self.db.commit()
