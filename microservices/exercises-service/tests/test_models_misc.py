from app.models import Exercise

def test_model_repr_and_from_json_and_to_json():
    data = {
        "title": "T",
        "body": "B",
        "difficulty": 2,
        "test_cases": ["1+1"],
        "solutions": ["2"],
    }
    ex = Exercise.from_json(data)
    # __repr__
    r = repr(ex)
    assert "Exercise" in r and "difficulty=2" in r
    # to_json basic shape; created_at/updated_at may be None before DB insert
    j = ex.to_json()
    assert j["title"] == "T" and isinstance(j, dict)
    assert "created_at" in j and "updated_at" in j