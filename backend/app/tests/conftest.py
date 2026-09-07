import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault(
    "DATABASE_URL",
    os.getenv("TEST_DATABASE_URL", "postgresql://app:app@localhost:5432/app_test"),
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.domain.auth.models import User
from app.domain.problems.models import Problem
from app.infrastructure.db import Base, get_db_session
from app.main import app
from app.core.security import create_access_token, hash_password


TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL, future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = Session(test_engine)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def user_factory(db_session):
    def create_user(
        email="test@example.com",
        password="password",
        role="user",
        is_verified=True,
    ):
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_verified=is_verified,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return create_user


@pytest.fixture
def problem_factory(db_session):
    def create_problem(
        title="Two Sum",
        difficulty=1,
        categories=None,
        description="Find two numbers that add to a target.",
        test_cases="[]",
    ):
        problem = Problem(
            title=title,
            difficulty=difficulty,
            categories=categories or ["two-pointers"],
            description=description,
            test_cases=test_cases,
        )
        db_session.add(problem)
        db_session.commit()
        db_session.refresh(problem)
        return problem

    return create_problem


def auth_headers(user):
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}
