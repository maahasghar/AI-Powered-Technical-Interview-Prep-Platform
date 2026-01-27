from datetime import datetime, timedelta

import pytest
from app.domain.auth.exceptions import InvalidCredentialsError, InvalidTokenError
from app.domain.auth.service import AuthService


def test_login_success(mocker, mock_user):
    repo = mocker.Mock()
    repo.get_user_by_email.return_value = mock_user

    service = AuthService(repo)

    mocker.patch(
        "app.domain.auth.password.verify_password",
        return_value=True,
    )

    result = service.login("test@example.com", "password")

    assert "access_token" in result
    assert "refresh_token" in result


def test_login_invalid_password(mocker, mock_user):
    repo = mocker.Mock()
    repo.get_user_by_email.return_value = mock_user

    service = AuthService(repo)

    mocker.patch(
        "app.domain.auth.password.verify_password",
        return_value=False,
    )

    with pytest.raises(InvalidCredentialsError):
        service.login("test@example.com", "wrongpassword")


def test_refresh_token_valid(mocker):
    repo = mocker.Mock()
    repo.get_refresh_token.return_value = {
        "token": "validtoken",
        "revoked": False,
        "expires_at": datetime.utcnow() + timedelta(days=1),
    }

    service = AuthService(repo)

    result = service.refresh_access_token("validtoken")

    assert "access_token" in result


def test_refresh_token_revoked(mocker):
    repo = mocker.Mock()
    repo.get_refresh_token.return_value = {
        "token": "revokedtoken",
        "revoked": True,
        "expires_at": datetime.utcnow() + timedelta(days=1),
    }

    service = AuthService(repo)

    with pytest.raises(InvalidTokenError):
        service.refresh_access_token("revokedtoken")
