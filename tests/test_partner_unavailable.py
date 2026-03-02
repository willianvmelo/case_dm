from pathlib import Path

import httpx

from app.models import TransactionRequest, TransactionStatus
from app.partner_client import PartnerClient
from app.repository import SqliteTransactionRepository
from app.service import TransactionService


def test_when_partner_fails_transaction_becomes_pending(tmp_path: Path):
    db_file = tmp_path / "test.db"
    repo = SqliteTransactionRepository(str(db_file))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "down"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, timeout=1.0)
    partner = PartnerClient(base_url="http://partner", client=http_client)

    service = TransactionService(repo, partner)

    res = service.create_transaction(TransactionRequest(external_id="x1", valor=10, kind="credit"))
    assert res.status == TransactionStatus.pending
    assert res.partner_transaction_id is None


def test_retry_pending_sends_when_partner_recovers(tmp_path: Path):
    db_file = tmp_path / "test.db"
    repo = SqliteTransactionRepository(str(db_file))

    # 1) Primeiro: parceiro fora (500)
    def handler_fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "down"})

    fail_transport = httpx.MockTransport(handler_fail)
    fail_client = httpx.Client(transport=fail_transport, timeout=1.0)
    failing_partner = PartnerClient(base_url="http://partner", client=fail_client)

    service = TransactionService(repo, failing_partner)
    service.create_transaction(TransactionRequest(external_id="x2", valor=10, kind="debit"))

    rec = repo.get_by_external_id("x2")
    assert rec.status == TransactionStatus.pending

    # 2) Depois: parceiro recupera (200)
    def handler_ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"transaction_id": 123})

    ok_transport = httpx.MockTransport(handler_ok)
    ok_client = httpx.Client(transport=ok_transport, timeout=1.0)
    service.partner = PartnerClient(base_url="http://partner", client=ok_client)

    sent = service.retry_pending_once()
    assert sent == 1

    rec2 = repo.get_by_external_id("x2")
    assert rec2.status == TransactionStatus.sent
    assert rec2.partner_transaction_id == 123