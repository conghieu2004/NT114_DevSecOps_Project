import types
import app.api.scores as scores_api
from app.main import app as flask_app
import pytest

@pytest.fixture(autouse=True)
def restore_testing_flag():
    # Lưu lại giá trị TESTING hiện tại và khôi phục sau mỗi test
    original = flask_app.config.get("TESTING", True)
    try:
        yield
    finally:
        flask_app.config.update(TESTING=original)

def test_progress_non_testing_branch_zero_attempts(monkeypatch):
    # Nhánh non-testing: DB trả count = 0 -> totalAttempts = 0
    flask_app.config.update(TESTING=False)

    class QStub:
        def filter_by(self, **kw):
            class C:
                def count(self):
                    return 0
            return C()

    monkeypatch.setattr(
        scores_api, "Score", types.SimpleNamespace(query=QStub()), raising=False
    )

    client = flask_app.test_client()
    r = client.get("/api/v1/scores/progress/10")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "success"
    assert body["totalAttempts"] == 0

def test_progress_testing_branch_success_shape():
    # Nhánh testing: không phụ thuộc DB, chỉ xác thực cấu trúc phản hồi thành công
    flask_app.config.update(TESTING=True)
    client = flask_app.test_client()
    r = client.get("/api/v1/scores/progress/5")
    assert r.status_code == 200
    body = r.get_json()
    # Không giả định giá trị cụ thể để tránh phụ thuộc implement,
    # chỉ kiểm tra cấu trúc và kiểu dữ liệu hợp lý
    assert body["status"] == "success"
    assert "totalAttempts" in body
    assert isinstance(body["totalAttempts"], int)

def test_progress_non_testing_branch_negative_user_id(monkeypatch):
    # Nhánh non-testing: user_id âm vẫn xử lý, DB trả count=3
    flask_app.config.update(TESTING=False)

    class QStub:
        def filter_by(self, **kw):
            class C:
                def count(self):
                    return 3
            return C()

    monkeypatch.setattr(
        scores_api, "Score", types.SimpleNamespace(query=QStub()), raising=False
    )

    client = flask_app.test_client()
    r = client.get("/api/v1/scores/progress/-1")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "success"
    assert body["totalAttempts"] == 3