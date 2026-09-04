# core/container.py

from app.domain.auth.repository import AuthRepository
from app.domain.auth.service import AuthService
from app.domain.problems.repository import ProblemsRepository
from app.domain.problems.service import ProblemsService
from app.domain.submissions.repository import SubmissionsRepository
from app.domain.submissions.service import SubmissionsService
from app.domain.user.repository import UserRepository
from app.domain.user.service import UserService
from app.infrastructure.db import Database
from app.infrastructure.email_client import EmailClient
from app.infrastructure.redis import RedisClient
from sqlalchemy.orm import Session

# The container owns shared infrastructure clients and builds services with their dependencies.
# Database-backed services receive a request-scoped session from the API layer.

## The container creates and connects the services and tools our application needs.
# It keeps shared clients, such as Redis and email, in one place.
# It creates database-backed services using the current request's database session. These requets are passed in from the API layer.
class Container:
    def __init__(self):
        self.redis = RedisClient()
        self.email_client = EmailClient()

    def get_auth_service(self, session: Session):
        database = Database(session)
        return AuthService(
            AuthRepository(database),
            UserRepository(database),
            self.email_client,
        )

    def get_user_service(self, session: Session):
        database = Database(session)
        return UserService(UserRepository(database))

    def get_problems_service(self, session: Session):
        database = Database(session)
        return ProblemsService(ProblemsRepository(database))

    def get_submissions_service(self, session: Session):
        database = Database(session)
        return SubmissionsService(SubmissionsRepository(database))


# Create a single global container instance
container = Container()
