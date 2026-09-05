import requests

from frontend.api_client import ApiClient


class FakeResponse:
    def __init__(self, ok=True, status_code=200, payload=None):
        self.ok = ok
        self.status_code = status_code
        self._payload = payload or {"code": status_code, "msg": "success", "data": None}

    def json(self):
        return self._payload


def test_api_client_wraps_successful_response(monkeypatch):
    client = ApiClient("http://example.com/")

    def fake_request(method, url, timeout, **kwargs):
        assert method == "GET"
        assert url == "http://example.com/api/health"
        assert timeout == 10
        return FakeResponse(payload={"code": 200, "msg": "success", "data": {"ok": True}})

    monkeypatch.setattr(client.session, "request", fake_request)

    result = client.get("/api/health")

    assert result.ok is True
    assert result.status_code == 200
    assert result.msg == "success"
    assert result.data == {"ok": True}


def test_api_client_wraps_request_error(monkeypatch):
    client = ApiClient("http://example.com")

    def fake_request(method, url, timeout, **kwargs):
        raise requests.ConnectionError("backend down")

    monkeypatch.setattr(client.session, "request", fake_request)

    result = client.get("/api/health")

    assert result.ok is False
    assert result.status_code == 0
    assert "request failed" in result.msg
    assert result.data is None