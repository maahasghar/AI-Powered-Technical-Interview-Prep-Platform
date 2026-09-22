from __future__ import annotations

from app.audit import record_audit
from app.domain.auth.models import AuthToken, User
from app.domain.auth.token_models import AccountToken
from app.domain.submissions.models import Submission
from app.feedback.models import Feedback


class UserService:
    def __init__(self, user_repo):
        self.user_repo = user_repo

    def get_user(self, user_id: int):
        return self.user_repo.get_by_id(user_id)

    def get_user_by_email(self, email: str):
        return self.user_repo.get_by_email(email)

    def update_user(self, user_id: int, **kwargs):
        return self.user_repo.update_user(user_id, **kwargs)

    def get_user_profile(self, user_id: int):
        return self.user_repo.get_profile(user_id)

    def create_user_profile(
        self,
        user_id: int,
        full_name: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
    ):
        return self.user_repo.create_profile(user_id, full_name, bio, avatar_url)

    def update_user_profile(self, user_id: int, **kwargs):
        return self.user_repo.update_profile(user_id, **kwargs)

    def delete_account(self, user_id: int):
        session = self.user_repo.db.session
        user = session.get(User, user_id)
        if user is None:
            return False
        record_audit(
            session,
            "ACCOUNT_DELETED",
            actor_user_id=user_id,
            metadata={"retention": "user-owned records deleted"},
        )
        submission_ids = [
            submission_id
            for (submission_id,) in session.query(Submission.id)
            .filter(Submission.user_id == user_id)
            .all()
        ]
        if submission_ids:
            session.query(Feedback).filter(
                Feedback.submission_id.in_(submission_ids)
            ).delete(synchronize_session=False)
        session.query(Submission).filter(Submission.user_id == user_id).delete(
            synchronize_session=False
        )
        session.query(AuthToken).filter(AuthToken.user_id == user_id).delete(
            synchronize_session=False
        )
        session.query(AccountToken).filter(AccountToken.user_id == user_id).delete(
            synchronize_session=False
        )
        from app.domain.user.models import UserProfile

        session.query(UserProfile).filter(UserProfile.user_id == user_id).delete(
            synchronize_session=False
        )
        session.delete(user)
        session.commit()
        return True
