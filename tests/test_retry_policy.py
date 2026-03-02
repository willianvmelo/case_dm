from pathlib import Path
import httpx

from app.models import TransactionRequest, TransactionStatus
from app.partner_client import PartnerClient
from app.repository import SqliteTransactionRepository
from app.service import TransactionService


def test_retry_pending_sends_when_partner_recovers(tmp_path: Path):
    db_file = tmp_path / "test.db"
    repo = SqliteTransactionRepository(str(db_file))

    # relógio controlado
    fake_now = {"t": 1000.0}

    # 1) Primeiro: parceiro fora (500)
    def handler_fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "down"})

    fail_client = httpx.Client(transport=httpx.MockTransport(handler_fail), timeout=1.0)
    failing_partner = PartnerClient(base_url="http://partner", client=fail_client)

    service = TransactionService(repo, failing_partner, now_fn=lambda: fake_now["t"])
    service.create_transaction(TransactionRequest(external_id="x2", valor=10, kind="debit"))

    rec = repo.get_by_external_id("x2")
    assert rec.status == TransactionStatus.pending
    assert rec.next_retry_at is not None

    # 2) Depois: parceiro recupera (200)
    def handler_ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"transaction_id": 123})

    ok_client = httpx.Client(transport=httpx.MockTransport(handler_ok), timeout=1.0)
    service.partner = PartnerClient(base_url="http://partner", client=ok_client)

    # ainda não está due
    assert service.retry_pending_once() == 0

    # avança o tempo para depois do next_retry_at
    fake_now["t"] = rec.next_retry_at + 0.1
    assert service.retry_pending_once() == 1

    rec2 = repo.get_by_external_id("x2")
    assert rec2.status == TransactionStatus.sent
    assert rec2.partner_transaction_id == 123