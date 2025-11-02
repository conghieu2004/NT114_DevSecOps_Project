import types
import app.api.scores as scores_api
from app.main import app as flask_app

def test_progress_non_testing_branch_success(monkeypatch):
    # Bật nhánh non-testing và mock DB trả count=5
    flask_app.config.update(TESTING=False)
    class QStub:
        def filter_by(self, **kw):
            class C:
                def count(self): 
                    return 5
            return C()
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QStub()), raising=False)

    client = flask_app.test_client()
    r = client.get("/api/v1/scores/progress/2")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "success"
    assert body["totalAttempts"] == 5

def test_progress_non_testing_branch_db_error(monkeypatch):
    # Bật nhánh non-testing và mock DB ném lỗi -> fallback 0
    flask_app.config.update(TESTING=False)
    class QStub:
        def filter_by(self, **kw):
            class C:
                def count(self): 
                    raise RuntimeError("db down")
            return C()
    monkeypatch.setattr(scores_api, "Score", types.SimpleNamespace(query=QStub()), raising=False)

    client = flask_app.test_client()
    r = client.get("/api/v1/scores/progress/3")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "success"
    assert body["totalAttempts"] == 0

    # Trả lại trạng thái test để không ảnh hưởng test khác
    flask_app.config.update(TESTING=True)