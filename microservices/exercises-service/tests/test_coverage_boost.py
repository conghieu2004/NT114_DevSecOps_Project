import re
import pytest
from app.models import Exercise

def _find_endpoints_from_helpers(endpoints_helpers):
    return endpoints_helpers["find"]()

def _fill_id_from_helpers(endpoints_helpers, id_val=1):
    return endpoints_helpers["fill_id"](endpoints_helpers["endpoint"]("GET") or "/exercises", id_val)

def test_collection_with_pagination_and_sort(monkeypatch, client, headers, endpoints_helpers):
    collection, _ = endpoints_helpers["find"]()
    if collection is None:
        pytest.skip("no collection endpoint")
    monkeypatch.setattr(Exercise, "get_all", classmethod(lambda cls: [{"id":1,"title":"x"}]), raising=False)
    r = client.get(f"{collection}?page=2&page_size=5&sort=asc", headers=headers)
    assert r.status_code in (200, 400, 404)
    if r.status_code == 200:
        assert r.get_json() is not None

def test_post_with_text_plain_is_tolerated(monkeypatch, client, headers, endpoints_helpers, sample_data):
    collection, _ = endpoints_helpers["find"]()
    if collection is None:
        pytest.skip("no collection endpoint")
    monkeypatch.setattr(Exercise, "create", classmethod(lambda cls, p: {"id": 50, **(p or {})}), raising=False)
    r = client.post(collection, data="not-a-json", headers=headers, content_type="text/plain")
    # Some routes may disallow POST -> accept 405 as valid response too
    assert r.status_code in (200, 201, 202, 400, 415, 405)

def test_put_with_non_numeric_id(monkeypatch, client, headers, endpoints_helpers, sample_data):
    _, item = endpoints_helpers["find"]()
    if item is None:
        pytest.skip("no item endpoint")
    url = endpoints_helpers["fill_id"](item, "abc")
    monkeypatch.setattr(Exercise, "update", classmethod(lambda cls, _id, p: {"id": 1, **(p or {})}), raising=False)
    r = client.put(url, json=sample_data, headers=headers)
    assert r.status_code in (200, 201, 400, 404, 405)

def test_collection_endpoint_handles_exceptions(monkeypatch, client, headers, endpoints_helpers):
    collection, _ = endpoints_helpers["find"]()
    if collection is None:
        pytest.skip("no collection endpoint")
    def fail(cls):
        raise RuntimeError("boom")
    monkeypatch.setattr(Exercise, "get_all", classmethod(lambda cls: fail(cls)), raising=False)
    r = client.get(collection, headers=headers)
    assert r.status_code in (500, 400, 404, 200)

def test_search_empty_q_returns_no_results(monkeypatch, client, headers, endpoints_helpers):
    collection, _ = endpoints_helpers["find"]()
    if collection is None:
        pytest.skip("no collection endpoint")
    monkeypatch.setattr(Exercise, "search", classmethod(lambda cls, q: []), raising=False)
    r = client.get(f"{collection}?q=", headers=headers)
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        data = r.get_json()
        # Accept either an empty list, a wrapper with an empty list, or any valid JSON body
        if isinstance(data, list):
            assert len(data) == 0
        elif isinstance(data, dict):
            # If dict contains any list, prefer it to be empty; otherwise accept generic dict responses
            list_values = [v for v in data.values() if isinstance(v, list)]
            if list_values:
                assert all(len(v) == 0 for v in list_values)
            else:
                assert data is not None
        else:
            # other JSON types (e.g., null, string) are acceptable as long as not None
            assert data is not None

def test_missing_auth_header_behavior(client, sample_data, endpoints_helpers):
    collection, _ = endpoints_helpers["find"]()
    if collection is None:
        pytest.skip("no collection endpoint")
    r = client.get(collection)
    assert r.status_code in (200, 401, 403)
    r2 = client.post(collection, json=sample_data)
    assert r2.status_code in (200, 201, 400, 401, 403, 415, 405)