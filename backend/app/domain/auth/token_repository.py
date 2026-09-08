from datetime import datetime, timezone

from app.domain.auth.token_models import AccountToken
from sqlalchemy import func


class AccountTokenRepository:
    def __init__(self, db):
        self.db = db

    def create(self, user_id, token_hash, token_type, expires_at):
        token = AccountToken(
            user_id=user_id,
            token_hash=token_hash,
            token_type=token_type,
            expires_at=expires_at,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_active(self, token_hash, token_type):
        return (
            self.db.query(AccountToken)
            .filter(
                AccountToken.token_hash == token_hash,
                AccountToken.token_type == token_type,
                AccountToken.used_at.is_(None),
            )
            .first()
        )

    def invalidate_unused(self, user_id, token_type):
        self.db.query(AccountToken).filter(
            AccountToken.user_id == user_id,
            AccountToken.token_type == token_type,
            AccountToken.used_at.is_(None),
        ).update({AccountToken.used_at: func.now()})
        self.db.commit()

    def mark_used(self, token):
        token.used_at = datetime.now(timezone.utc)
        self.db.commit()
