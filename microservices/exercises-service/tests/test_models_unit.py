import types
import pytest
from app.models import Exercise
import app.models as models

class DummySession:
    def __init__(self, fail_commit=False):
        self.added = []
        self.committed = False
        self.rolled_back = False
        self.fail_commit = fail_commit

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        if self.fail_commit:
            raise RuntimeError("commit failed")
        self.committed = True

    def rollback(self):
        self.rolled_back = True

def test_create_exercise_commits(monkeypatch):
    ds = DummySession(fail_commit=False)
    monkeypatch.setattr(models, "db", types.SimpleNamespace(session=ds), raising=False)
    ex = Exercise.create_exercise("T", "B", 1, [], [])
    assert hasattr(ex, "title")
    assert ds.committed is True
    assert ds.rolled_back is False

def test_create_exercise_rollback_on_error(monkeypatch):
    ds = DummySession(fail_commit=True)
    monkeypatch.setattr(models, "db", types.SimpleNamespace(session=ds), raising=False)
    with pytest.raises(RuntimeError):
        Exercise.create_exercise("T", "B", 1, [], [])
    assert ds.rolled_back is True

def test_update_exercise_success(monkeypatch):
    ds = DummySession(fail_commit=False)
    monkeypatch.setattr(models, "db", types.SimpleNamespace(session=ds), raising=False)
    ex = Exercise("t", "b", 1, [], [])
    ex.id = 10
    ex.update_exercise(title="new-title")
    assert ex.title == "new-title"
    assert ds.committed is True

def test_update_exercise_rollback_on_error(monkeypatch):
    ds = DummySession(fail_commit=True)
    monkeypatch.setattr(models, "db", types.SimpleNamespace(session=ds), raising=False)
    ex = Exercise("t", "b", 1, [], [])
    ex.id = 11
    with pytest.raises(RuntimeError):
        ex.update_exercise(title="will-fail")
    assert ds.rolled_back is True