from app.domain.auth.password import hash_password, verify_password


def test_hash_password():
    password = "securepassword"
    hashed = hash_password(password)

    assert hashed != password
    assert isinstance(hashed, str)


def test_verify_password_success():
    password = "securepassword"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_failure():
    hashed = hash_password("securepassword")

    assert verify_password("wrongpassword", hashed) is False
