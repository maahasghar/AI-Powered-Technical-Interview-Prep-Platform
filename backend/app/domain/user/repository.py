from app.domain.auth.models import User
from app.domain.user.models import UserProfile


class UserRepository:
    def __init__(self, db):
        self.db = db

    def get_by_id(self, user_id: int):
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def create_user(self, email: str, password_hash: str, is_verified: bool = False):
        user = User(email=email, password_hash=password_hash, is_verified=is_verified)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: int, **kwargs):
        user = self.get_by_id(user_id)
        if user:
            for key, value in kwargs.items():
                setattr(user, key, value)
            self.db.commit()
            self.db.refresh(user)
        return user

    def mark_verified(self, user_id: int):
        user = self.get_by_id(user_id)
        if user:
            user.is_verified = True
            self.db.commit()
            self.db.refresh(user)
        return user

    def get_profile(self, user_id: int):
        return self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    def create_profile(
        self,
        user_id: int,
        full_name: str = None,
        bio: str = None,
        avatar_url: str = None,
    ):
        profile = UserProfile(
            user_id=user_id, full_name=full_name, bio=bio, avatar_url=avatar_url
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_profile(self, user_id: int, **kwargs):
        profile = self.get_profile(user_id)
        if profile:
            for key, value in kwargs.items():
                setattr(profile, key, value)
            self.db.commit()
            self.db.refresh(profile)
        return profile
