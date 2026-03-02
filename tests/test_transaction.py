from fastapi.testclient import TestClient
from app.main import app

def test_create_transaction_returns_ids():
    client = TestClient(app)
    resp = client.post("/transaction", json={"external_id": "ext-1", "valor": 10, "kind": "credit"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["transaction_id"] == 1
    assert body["partner_transaction_id"] == 123

def test_idempotency_by_external_id():
    client = TestClient(app)

    r1 = client.post("/transaction", json={"external_id": "ext-2", "valor": 10, "kind": "debit"})
    r2 = client.post("/transaction", json={"external_id": "ext-2", "valor": 999, "kind": "credit"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == r2.json()

def test_validation_valor_must_be_positive():
    client = TestClient(app)
    resp = client.post("/transaction", json={"external_id": "ext-3", "valor": 0, "kind": "credit"})
    assert resp.status_code == 422

def test_returns_202_when_partner_unavailable(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app, partner

    partner.should_fail = True
    client = TestClient(app)
    resp = client.post("/transaction", json={"external_id": "ext-202", "valor": 10, "kind": "credit"})
    assert resp.status_code == 202
    assert resp.json()["status"] == "PENDING"    