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
