import app.api.scores as scores_api
from flask import Flask
import pytest

@pytest.fixture()
def client():
    app = Flask("scores_auth")
    app.register_blueprint(scores_api.scores_blueprint, url_prefix="/api/scores")
    return app.test_client()

def test_endpoints_require_auth_on_user_routes(client):
    # các route có @authenticate sẽ trả 401/403 khi thiếu Authorization header
    r1 = client.get("/api/scores/user")
    r2 = client.get("/api/scores/user/1")
    assert r1.status_code in (401, 403)
    assert r2.status_code in (401, 403)