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
        full_name: str = None,
        bio: str = None,
        avatar_url: str = None,
    ):
        return self.user_repo.create_profile(user_id, full_name, bio, avatar_url)

    def update_user_profile(self, user_id: int, **kwargs):
        return self.user_repo.update_profile(user_id, **kwargs)
