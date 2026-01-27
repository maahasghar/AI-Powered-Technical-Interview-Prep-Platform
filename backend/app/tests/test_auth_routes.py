def test_login_route(client, mocker):
    mocker.patch(
        "app.core.container.container.auth_service.login",
        return_value={
            "access_token": "abc",
            "refresh_token": "def",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password"},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_refresh_route(client, mocker):
    mocker.patch(
        "app.core.container.container.auth_service.refresh_access_token",
        return_value={"access_token": "newtoken"},
    )

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "def"},
    )

    assert response.status_code == 200
