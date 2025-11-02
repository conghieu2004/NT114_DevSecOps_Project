import types
from sqlalchemy import exc
import pytest
from app.main import app
import app.api.exercises as exercises_api

def _req_ctx(path="/", method="POST", json=None):
    return app.test_request_context(path, method=method, json=json)

def test_validate_code_invalid_payload(client):
    route = None
    for rule in app.url_map.iter_rules():
        if "/validate_code" in rule.rule:
            route = rule.rule
            break
    if not route:
        pytest.skip("no validate_code route")
    # thiếu key -> 400
    r1 = client.post(route, json={"answer": "print(1)"})
    assert r1.status_code in (400,)
    r2 = client.post(route, json={"exercise_id": 1})
    assert r2.status_code in (400,)
    r3 = client.post(route, json=None)
    # Một số cấu hình Flask trả 415 khi thiếu Content-Type application/json
    assert r3.status_code in (400, 415)

def test_add_exercise_non_admin_unwrapped(monkeypatch):
    with _req_ctx("/", method="POST", json={"title":"t","body":"b","difficulty":1,"test_cases":[1],"solutions":[1]}):
        resp = exercises_api.add_exercise.__wrapped__({"username":"u","admin":False})
    assert isinstance(resp, tuple)
    assert resp[1] in (401,)

def test_add_exercise_missing_required_fields_unwrapped(monkeypatch):
    # thiếu solutions -> 400 "Missing required fields"
    with _req_ctx("/", method="POST", json={"title":"t","body":"b","difficulty":1,"test_cases":[1]}):
        resp = exercises_api.add_exercise.__wrapped__({"username":"u","admin":True})
    assert isinstance(resp, tuple)
    assert resp[1] in (400,)

def test_update_exercise_no_fields_to_update_unwrapped(monkeypatch):
    # {} => tất cả field None -> 400 "No fields to update in payload!"
    with _req_ctx("/5", method="PUT", json={}):
        resp = exercises_api.update_exercise.__wrapped__({"username":"u","admin":True}, "5")
    assert isinstance(resp, tuple)
    assert resp[1] in (400,)