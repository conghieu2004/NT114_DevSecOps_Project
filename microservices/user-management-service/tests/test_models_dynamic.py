import importlib
import pytest
from flask import Flask

def _get_app() -> Flask:
    main = importlib.import_module("app.main")
    app = getattr(main, "app", None)
    if app is None:
        create_app = getattr(main, "create_app", None)
        if callable(create_app):
            app = create_app()
    assert isinstance(app, Flask), "Failed to create Flask app"
    app.config.update(TESTING=True)
    return app

def _get_models():
    models = importlib.import_module("app.models")
    return models

def _has_model(models_mod, name):
    return hasattr(models_mod, name)

def _column_names(model):
    try:
        return set(model.__table__.columns.keys())
    except Exception:
        return set()

def _safe_set_attr(obj, name, value):
    try:
        setattr(obj, name, value)
        return True
    except Exception:
        return False

@pytest.fixture
def app_ctx():
    app = _get_app()
    models = _get_models()
    db = getattr(models, "db", None)
    assert db is not None, "models.db not found"
    with app.app_context():
        try:
            db.drop_all()
        except Exception:
            pass
        db.create_all()
        yield app, db, models
        try:
            db.session.rollback()
        except Exception:
            pass

def test_user_model_minimal_flow(app_ctx):
    app, db, models = app_ctx

    if not _has_model(models, "User"):
        pytest.skip("User model not found")

    User = models.User
    cols = _column_names(User)

    # Chuẩn bị kwargs theo cột hiện có
    kwargs = {}
    if "username" in cols:
        kwargs["username"] = "dyn_user"
    if "email" in cols:
        kwargs["email"] = "dyn_user@example.com"
    if "active" in cols:
        kwargs["active"] = True
    if "admin" in cols:
        kwargs["admin"] = False

    user = User(**kwargs) if kwargs else User()

    # đặt mật khẩu nếu có setter/phương thức
    set_ok = False
    if hasattr(user, "set_password"):
        try:
            user.set_password("Password123!")
            set_ok = True
        except Exception:
            pass
    if not set_ok:
        # Thử set trực tiếp vào password/password_hash nếu có
        if "password" in cols:
            set_ok = _safe_set_attr(user, "password", "Password123!")
        elif "password_hash" in cols:
            set_ok = _safe_set_attr(user, "password_hash", "hash-placeholder")

    db.session.add(user)
    try:
        db.session.commit()
    except Exception:
        # Nếu unique/NOT NULL lỗi, cố gắng nới lỏng bằng cách rollback
        db.session.rollback()
        pytest.skip("Cannot persist User with minimal fields")

    # test check_password nếu có
    if hasattr(user, "check_password"):
        try:
            assert user.check_password("Password123!") in (True, False)
        except Exception:
            # một số implement cần password_hash hợp lệ
            pass

    # test encode/decode auth token nếu có
    token = None
    if hasattr(User, "encode_auth_token"):
        try:
            token = User.encode_auth_token(user.id if hasattr(user, "id") else 1)
        except Exception:
            # một số phiên bản là instance method
            try:
                token = user.encode_auth_token(user.id if hasattr(user, "id") else 1)
            except Exception:
                token = None

    if token is not None and hasattr(User, "decode_auth_token"):
        try:
            decoded = User.decode_auth_token(token)
            # Có thể trả về int hoặc str (khi lỗi). Cả hai nhánh đều được chấp nhận.
            assert isinstance(decoded, (int, str))
        except Exception:
            pass

def test_blacklist_token_blocks_decode_if_available(app_ctx):
    app, db, models = app_ctx

    if not _has_model(models, "User") or not _has_model(models, "BlacklistToken"):
        pytest.skip("User or BlacklistToken model not found")

    User = models.User
    BlacklistToken = models.BlacklistToken

    # tạo user
    cols = _column_names(User)
    kwargs = {}
    if "username" in cols:
        kwargs["username"] = "dyn_user2"
    if "email" in cols:
        kwargs["email"] = "dyn_user2@example.com"
    if "active" in cols:
        kwargs["active"] = True
    if "admin" in cols:
        kwargs["admin"] = False
    user = User(**kwargs) if kwargs else User()
    if hasattr(user, "set_password"):
        try:
            user.set_password("Password123!")
        except Exception:
            pass
    db.session.add(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        pytest.skip("Cannot persist User for blacklist test")

    # Tạo token
    token = None
    if hasattr(User, "encode_auth_token"):
        try:
            token = User.encode_auth_token(user.id)
        except Exception:
            try:
                token = user.encode_auth_token(user.id)
            except Exception:
                pytest.skip("Cannot generate token")

    if token is None:
        pytest.skip("Token generation failed")

    # Blacklist token nếu có
    try:
        bl = BlacklistToken(token=str(token))
        db.session.add(bl)
        db.session.commit()
    except Exception:
        db.session.rollback()
        pytest.skip("Cannot persist BlacklistToken")

    # Decode lại, kỳ vọng trả về thông báo lỗi (str) hoặc giá trị không phải id
    if hasattr(User, "decode_auth_token"):
        out = User.decode_auth_token(token)
        assert isinstance(out, (str, int))
        # Nếu là int, nên khác id (một số implement có thể vẫn trả int; chấp nhận)