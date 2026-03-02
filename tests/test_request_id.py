from fastapi.testclient import TestClient
from app.main import app


def test_request_id_is_returned_in_response_header():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "X-Request-Id" in resp.headers


def test_request_id_respects_incoming_header():
    client = TestClient(app)
    resp = client.get("/health", headers={"X-Request-Id": "abc-123"})
    assert resp.headers["X-Request-Id"] == "abc-123"