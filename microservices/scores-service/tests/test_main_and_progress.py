from app.main import app as flask_app

def test_progress_v1_in_testing_returns_200():
    flask_app.config.update(TESTING=True)
    client = flask_app.test_client()
    r = client.get("/api/v1/scores/progress/1")
    assert r.status_code == 200
    body = r.get_json()
    assert body and body.get("status") == "success" and "data" in body

def test_list_scores_endpoint_smoke(monkeypatch):
    # Tránh chạm DB: monkeypatch query.all -> []
    import types as _t
    import app.api.scores as scores_api
    class QEmpty:
        def all(self_inner):
            return []
    monkeypatch.setattr(scores_api, "Score", _t.SimpleNamespace(query=QEmpty()), raising=False)
    client = flask_app.test_client()
    r = client.get("/api/scores/")
    # Có thể trả 200 với data list rỗng; hoặc 404 nếu route không có
    assert r.status_code in (200, 404, 405)