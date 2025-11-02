import types
import pytest
from app.models import Score
import app.models as models

class DummySession:
    def __init__(self, commit_exc=None):
        self.added = []
        self.committed = False
        self.rolled_back = False
        self.commit_exc = commit_exc
    def add(self, obj):
        self.added.append(obj)
    def commit(self):
        if self.commit_exc:
            raise self.commit_exc
        self.committed = True
    def rollback(self):
        self.rolled_back = True

def test_score_to_json_shape():
    s = Score(user_id=1, exercise_id=2, answer="print(1)", results=[True, False], user_results=["1", "0"])
    j = s.to_json()
    assert j["user_id"] == 1 and j["exercise_id"] == 2
    assert "created_at" in j and "updated_at" in j

def test_create_score_commits(monkeypatch):
    ds = DummySession()
    monkeypatch.setattr(models, "db", types.SimpleNamespace(session=ds), raising=False)
    sc = Score.create_score(1, 2, answer="a", results=[True], user_results=["ok"])
    assert isinstance(sc, Score)
    assert ds.committed is True and ds.rolled_back is False

def test_create_score_rollback_on_error(monkeypatch):
    ds = DummySession(commit_exc=RuntimeError("fail"))
    monkeypatch.setattr(models, "db", types.SimpleNamespace(session=ds), raising=False)
    with pytest.raises(RuntimeError):
        Score.create_score(1, 2)
    assert ds.rolled_back is True

def test_update_score_success_and_rollback(monkeypatch):
    # success
    ds = DummySession()
    monkeypatch.setattr(models, "db", types.SimpleNamespace(session=ds), raising=False)
    sc = Score(1, 2)
    sc.update_score(answer="b", results=[False], user_results=["res"])
    assert sc.answer == "b" and ds.committed is True
    # rollback on error
    ds2 = DummySession(commit_exc=RuntimeError("boom"))
    monkeypatch.setattr(models, "db", types.SimpleNamespace(session=ds2), raising=False)
    sc2 = Score(3, 4)
    with pytest.raises(RuntimeError):
        sc2.update_score(answer="x")
    assert ds2.rolled_back is True