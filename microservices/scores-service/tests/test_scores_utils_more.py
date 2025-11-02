import types
from flask import Flask
import app.utils as utils_mod

def test_is_admin_exception_path():
    class Odd:
        def get(self, k, d=None):
            raise RuntimeError("cannot get")
    assert utils_mod.is_admin(Odd()) is False

def test_authenticate_header_bearer_without_token():
    app = Flask(__name__)
    @utils_mod.authenticate
    def _inner(user_data):
        return {"ok": True}
    with app.test_request_context("/", method="GET", headers={"Authorization": "Bearer"}):
        resp = _inner()
        assert isinstance(resp, tuple)
        assert resp[1] in (401,)

def test_verify_token_with_user_service_200_but_wrong_shape(monkeypatch):
    class FakeResp:
        status_code = 200
        def json(self):
            return {"status": "success", "data": "not-a-dict"}
    monkeypatch.setattr(utils_mod, "requests", types.SimpleNamespace(get=lambda *a, **k: FakeResp()))
    assert utils_mod.verify_token_with_user_service("token") is None