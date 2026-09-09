from .conftest import auth_headers


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_route(client, user_factory):
    user_factory()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password"},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_register_route(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "password"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert response.json()["is_verified"] is False


def test_refresh_route(client, user_factory):
    user = user_factory()
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "password"},
    )

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_response.json()["refresh_token"]},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_authenticated_user_can_access_profile(client, user_factory):
    user = user_factory()

    response = client.get(
        "/api/v1/users/me",
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()["id"] == user.id
    assert response.json()["email"] == user.email


def test_refresh_token_rotates_and_reuse_revokes_family(client, user_factory):
    user = user_factory()
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "password"},
    )
    original_refresh_token = login_response.json()["refresh_token"]

    rotation_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )
    replacement_refresh_token = rotation_response.json()["refresh_token"]

    reused_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )
    replacement_after_reuse_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": replacement_refresh_token},
    )

    assert rotation_response.status_code == 200
    assert replacement_refresh_token != original_refresh_token
    assert reused_response.status_code == 401
    assert replacement_after_reuse_response.status_code == 401


def test_logout_revokes_refresh_token_family(client, user_factory):
    user = user_factory()
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "password"},
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    refresh_after_logout_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert logout_response.status_code == 200
    assert refresh_after_logout_response.status_code == 401
