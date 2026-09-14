"""Exercise browser cookie contracts without requiring a database."""

from unittest.mock import Mock

import pytest
from app.api.v1.routers.auth_router import get_auth_service, router
from app.core.config import settings
from app.domain.auth.exceptions import Unauthorized
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def cookie_client():
    service = Mock()
    service.login.return_value = {
        "access_token": "access",
        "refresh_token": "first-refresh",
        "token_type": "bearer",
    }
    service.refresh_access_token.return_value = {
        "access_token": "new-access",
        "refresh_token": "rotated-refresh",
        "token_type": "bearer",
    }
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_auth_service] = lambda: service
    with TestClient(
        app, base_url="https://testserver", headers={"X-Session-Request": "1"}
    ) as client:
        yield client, service


def test_login_refresh_and_logout_cookie_contract(cookie_client, monkeypatch):
    client, service = cookie_client
    monkeypatch.setattr(settings, "ENV", "production")
    login = client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": "password"}
    )
    assert login.json() == {"access_token": "access", "token_type": "bearer"}
    cookie = login.headers["set-cookie"]
    assert all(
        value in cookie
        for value in ["HttpOnly", "Secure", "SameSite=lax", "Path=/api/v1/auth"]
    )
    assert login.headers["cache-control"] == "no-store"
    refresh = client.post("/api/v1/auth/refresh")
    service.refresh_access_token.assert_called_once_with("first-refresh")
    assert refresh.json() == {"access_token": "new-access", "token_type": "bearer"}
    assert client.cookies["refresh_token"] == "rotated-refresh"
    logout = client.post("/api/v1/auth/logout")
    service.logout.assert_called_once_with("rotated-refresh")
    assert logout.status_code == 200
    assert "Max-Age=0" in logout.headers["set-cookie"]
    assert "refresh_token" not in client.cookies


def test_invalid_refresh_clears_cookie(cookie_client):
    client, service = cookie_client
    service.refresh_access_token.side_effect = Unauthorized()
    result = client.post(
        "/api/v1/auth/refresh", headers={"Cookie": "refresh_token=invalid"}
    )
    assert result.status_code == 401
    assert "Max-Age=0" in result.headers["set-cookie"]


def test_refresh_requires_cookie_not_json_token(cookie_client):
    client, service = cookie_client
    result = client.post("/api/v1/auth/refresh", json={"refresh_token": "body-token"})
    assert result.status_code == 401
    service.refresh_access_token.assert_not_called()


@pytest.mark.parametrize("path", ["login", "refresh", "logout"])
def test_session_endpoints_require_csrf_header_and_trusted_origin(cookie_client, path):
    client, service = cookie_client
    result = client.post(
        f"/api/v1/auth/{path}",
        headers={"Origin": "https://untrusted.example"},
        json={"email": "a@example.com", "password": "password"},
    )
    assert result.status_code == 403
    del client.headers["X-Session-Request"]
    assert (
        client.post(
            f"/api/v1/auth/{path}",
            json={"email": "a@example.com", "password": "password"},
        ).status_code
        == 403
    )
    service.login.assert_not_called()
    service.refresh_access_token.assert_not_called()
    service.logout.assert_not_called()
