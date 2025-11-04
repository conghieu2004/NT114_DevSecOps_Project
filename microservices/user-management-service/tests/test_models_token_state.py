from datetime import datetime, timedelta, timezone
import jwt
import pytest
from flask import Flask
from app.models import User


@pytest.fixture
def app_ctx():
    app = Flask("models-test")
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        TOKEN_EXPIRATION_DAYS=0,
        TOKEN_EXPIRATION_SECONDS=30,
    )
    with app.app_context():
        yield app


def test_user_create_and_password_hash_and_json(app_ctx):
    u = User(username="alice", email="alice@example.com", password="P@ssw0rd!")
    assert isinstance(u.password, str) and len(u.password) > 0

    # to_json coverage (không cần commit DB)
    j = u.to_json()
    assert j["username"] == "alice"
    assert j["email"] == "alice@example.com"


def test_encode_and_decode_token_success(app_ctx):
    u = User(username="bob", email="bob@example.com", password="Secret123!")
    token = u.encode_auth_token(1)
    assert token

    uid = User.decode_auth_token(token)
    assert uid == 1


def test_decode_token_error_branches(app_ctx):
    # Expired token
    past = datetime.now(timezone.utc) - timedelta(seconds=10)
    payload_expired = {"sub": "1", "iat": past, "exp": past}
    token_expired = jwt.encode(payload_expired, app_ctx.config["SECRET_KEY"], algorithm="HS256")
    msg = User.decode_auth_token(token_expired)
    assert isinstance(msg, str)

    # Invalid token format
    msg2 = User.decode_auth_token("invalid.token.string")
    assert isinstance(msg2, str)

    # Invalid user_id in token
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    payload_bad_sub = {"sub": "not-an-int", "iat": datetime.now(timezone.utc), "exp": future}
    token_bad = jwt.encode(payload_bad_sub, app_ctx.config["SECRET_KEY"], algorithm="HSHS256".replace("SHS", "S"))
    msg3 = User.decode_auth_token(token_bad)
    assert isinstance(msg3, str)


def test_deactivate_and_reactivate_user(app_ctx):
    u = User(username="eve", email="eve@example.com", password="Xyz#12345")
    u.deactivate_user()
    assert u.active is False
    u.reactivate_user()
    assert u.active is True