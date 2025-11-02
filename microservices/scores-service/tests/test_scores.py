import pytest
from app.main import app

class _CompatResponse:
    def __init__(self, resp):
        self._resp = resp
    def json(self):
        return self._resp.get_json()
    def __getattr__(self, name):
        return getattr(self._resp, name)

class _CompatClient:
    def __init__(self, c):
        self._c = c
    def get(self, *a, **k):
        return _CompatResponse(self._c.get(*a, **k))
    def post(self, *a, **k):
        return _CompatResponse(self._c.post(*a, **k))
    def put(self, *a, **k):
        return _CompatResponse(self._c.put(*a, **k))
    def delete(self, *a, **k):
        return _CompatResponse(self._c.delete(*a, **k))

@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield _CompatClient(c)

def test_submit_score_endpoint_success(client):
    # Giả định submission data
    submission_data = {
        "user_id": 1,
        "exercise_id": 10,
        "results": [True, True, False], # Kết quả submission (ví dụ)
        "language": "python"
    }
    
    # Giả định endpoint là /scores/submit
    response = client.post("/api/v1/scores/submit", json=submission_data)
    
    # Kiểm tra response thành công (hoặc 201 Created)
    assert response.status_code == 200 or response.status_code == 201
    assert "score_id" in response.json() 

def test_user_progress_endpoint(client):
    # Kiểm tra endpoint thống kê của người dùng
    user_id = 1
    response = client.get(f"/api/v1/scores/progress/{user_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "totalAttempts" in data
    assert data["totalAttempts"] >= 0 # Kiểm tra dữ liệu hợp lệ