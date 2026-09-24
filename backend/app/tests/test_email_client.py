from unittest.mock import Mock

import httpx
import pytest
from app.core.config import settings
from app.infrastructure.email_client import EmailClient, EmailDeliveryError
from pydantic import SecretStr


@pytest.fixture
def resend_post(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", SecretStr("re_test_secret"))
    monkeypatch.setattr(settings, "EMAIL_FROM", "Prep <no-reply@example.com>")
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.example.com/")
    post = Mock(return_value=httpx.Response(200, json={"id": "email-id"}))
    monkeypatch.setattr("app.infrastructure.email_client.httpx.post", post)
    return post


@pytest.mark.parametrize(
    "method,path,subject",
    [
        ("send_verification_email", "verify-email", "Verify your email"),
        ("send_password_reset_email", "reset-password", "Reset your password"),
    ],
)
def test_account_emails_use_resend(resend_post, method, path, subject):
    getattr(EmailClient(), method)("user@example.com", "account-token")
    args, kwargs = resend_post.call_args
    assert args == ("https://api.resend.com/emails",)
    assert kwargs["headers"]["Authorization"] == "Bearer re_test_secret"
    assert kwargs["timeout"] == settings.EMAIL_TIMEOUT_SECONDS
    payload = kwargs["json"]
    assert payload["from"] == "Prep <no-reply@example.com>"
    assert payload["to"] == ["user@example.com"]
    assert payload["subject"] == subject
    assert f"https://app.example.com/{path}?token=account-token" in payload["text"]


def test_console_mode_does_not_send_or_log_tokens(resend_post, monkeypatch, caplog):
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "console")
    with caplog.at_level("INFO"):
        EmailClient().send_verification_email("user@example.com", "private-token")
    resend_post.assert_not_called()
    assert "skipped" in caplog.text
    assert "private-token" not in caplog.text


@pytest.mark.parametrize("mode,key", [("resend", ""), ("smtp", "re_test_secret")])
def test_missing_configuration_does_not_send(resend_post, monkeypatch, mode, key):
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", mode)
    monkeypatch.setattr(settings, "RESEND_API_KEY", SecretStr(key))
    with pytest.raises(EmailDeliveryError, match="not configured"):
        EmailClient().send_email("user@example.com", "subject", "private-token")
    resend_post.assert_not_called()


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_provider_rejections_are_safe(resend_post, caplog, status):
    resend_post.return_value = httpx.Response(status, text="private-token")
    with pytest.raises(EmailDeliveryError) as error:
        EmailClient().send_email("user@example.com", "subject", "private-token")
    assert str(status) in caplog.text
    assert "private-token" not in caplog.text + str(error.value)
    assert "re_test_secret" not in caplog.text + str(error.value)
    assert resend_post.call_count == 1


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ReadTimeout])
def test_network_errors_are_safe(resend_post, caplog, error_type):
    resend_post.side_effect = error_type("private-token")
    with pytest.raises(EmailDeliveryError, match="unavailable"):
        EmailClient().send_email("user@example.com", "subject", "private-token")
    assert "private-token" not in caplog.text
    assert resend_post.call_count == 1


def test_registration_delivery_failure_returns_503(monkeypatch):
    from app.api.v1.routers.auth_router import get_auth_service
    from app.main import app
    from fastapi.testclient import TestClient

    service = Mock()
    service.register.side_effect = EmailDeliveryError("private-provider-details")
    monkeypatch.setitem(app.dependency_overrides, get_auth_service, lambda: service)
    monkeypatch.setattr("app.api.v1.routers.auth_router._limit", lambda *args: None)
    response = TestClient(app).post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password"},
    )
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Email delivery is temporarily unavailable. Please try again later."
    }
