import importlib
import inspect
import os
import pytest

# Dùng SQLite in-memory cho toàn bộ test để tránh kết nối Postgres thật
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("FLASK_DEBUG", "0")

# Chặn create_all để không cố kết nối DB khi import app
try:
    from flask_sqlalchemy import SQLAlchemy

    def _no_create_all(self, bind="__all__", app=None):
        return None

    SQLAlchemy.create_all = _no_create_all
except Exception:
    pass

def _patch_user_init():
    try:
        models = importlib.import_module("app.models")
        User = getattr(models, "User", None)
        if not User or getattr(User, "_ci_init_patched", False):
            return
        orig = User.__init__
        def patched(self, *args, **kwargs):
            try:
                sig = inspect.signature(orig)
                if "password" in sig.parameters and "password" not in kwargs:
                    kwargs["password"] = "TestP@ssw0rd!"
            except Exception:
                kwargs.setdefault("password", "TestP@ssw0rd!")
            return orig(self, *args, **kwargs)
        User.__init__ = patched  # type: ignore
        User._ci_init_patched = True  # type: ignore
    except Exception:
        pass

@pytest.fixture(scope="session", autouse=True)
def ci_user_init_patch():
    _patch_user_init()