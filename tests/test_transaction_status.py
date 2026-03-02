from fastapi.testclient import TestClient
from app.models import TransactionKind
from app.main import app, repo


def test_get_transaction_status_returns_404_when_missing():
    client = TestClient(app)
    resp = client.get("/transaction/does-not-exist")
    assert resp.status_code == 404


def test_get_transaction_status_returns_record():
    # cria direto no repo global do app (não depende do partner HTTP)
    ext = "status-1"
    rec = repo.get_by_external_id(ext)
    if rec is None:
        repo.create(external_id=ext, valor=10, kind=TransactionKind.credit)

    client = TestClient(app)
    resp = client.get(f"/transaction/{ext}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["external_id"] == ext
    assert data["valor"] == 10.0
    assert data["kind"] == "credit"
    assert data["status"] in ("PENDING", "SENT")
    assert "attempts" in data