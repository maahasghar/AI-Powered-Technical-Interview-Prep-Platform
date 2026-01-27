import pytest
from fastapi.testclient import TestClient

from ..main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_user():
    return {
        "id": 1,
        "email": "test@example.com",
        "hashed_password": "$2b$12$fakehashedpassword",
        "role": "user",
        "is_verified": True,
    }
