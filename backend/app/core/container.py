# core/container.py

from app.infrastructure.db import Database
from app.infrastructure.redis import RedisClient
from app.infrastructure.email_client import EmailClient

from app.domain.auth.repository import AuthRepository
from app.domain.auth.service import AuthService

from app.domain.user.repository import UserRepository
from app.domain.user.service import UserService

from app.domain.problems.repository import ProblemsRepository
from app.domain.problems.service import ProblemsService

from app.domain.submissions.repository import SubmissionsRepository
from app.domain.submissions.service import SubmissionsService


class Container:
    def __init__(self):
        # Infrastructure layer
        self.db = Database()
        self.redis = RedisClient()
        self.email_client = EmailClient()

        # Repositories
        self.auth_repository = AuthRepository(self.db)
        self.user_repository = UserRepository(self.db)
        self.problems_repository = ProblemsRepository(self.db)
        self.submissions_repository = SubmissionsRepository(self.db)

        # Services
        self.auth_service = AuthService(self.auth_repository, self.redis, self.email_client)
        self.user_service = UserService(self.user_repository)
        self.problems_service = ProblemsService(self.problems_repository)
        self.submissions_service = SubmissionsService(self.submissions_repository)


# Create a single global container instance
container = Container()
