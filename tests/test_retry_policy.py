from pathlib import Path
import httpx

from app.models import TransactionRequest, TransactionStatus
from app.partner_client import PartnerClient
from app.repository import SqliteTransactionRepository
from app.service import TransactionService


def test_retry_respects_next_retry_at(tmp_path: Path):
    db_file = tmp_path / "test.db"
    repo = SqliteTransactionRepository(str(db_file))

    # parceiro falha
    def handler_fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "down"})

    fail_client = httpx.Client(transport=httpx.MockTransport(handler_fail), timeout=1.0)
    partner_fail = PartnerClient(base_url="http://partner", client=fail_client)

    fake_now = {"t": 1000.0}
    service = TransactionService(repo, partner_fail, now_fn=lambda: fake_now["t"])

    service.create_transaction(TransactionRequest(external_id="r1", valor=10, kind="credit"))
    rec = repo.get_by_external_id("r1")
    assert rec.status == TransactionStatus.pending
    assert rec.next_retry_at is not None
    assert rec.next_retry_at > fake_now["t"]

    # parceiro recupera mas ainda não venceu o next_retry_at
    def handler_ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"transaction_id": 999})

    ok_client = httpx.Client(transport=httpx.MockTransport(handler_ok), timeout=1.0)
    service.partner = PartnerClient(base_url="http://partner", client=ok_client)

    sent_now = service.retry_pending_once()
    assert sent_now == 0  # não pode tentar ainda

    # avança o tempo para depois do next_retry_at
    fake_now["t"] = rec.next_retry_at + 0.1
    sent_later = service.retry_pending_once()
    assert sent_later == 1

    rec2 = repo.get_by_external_id("r1")
    assert rec2.status == TransactionStatus.sent
    assert rec2.partner_transaction_id == 999


def test_max_attempts_marks_failed(tmp_path: Path):
    db_file = tmp_path / "test.db"
    repo = SqliteTransactionRepository(str(db_file))

    def handler_fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "down"})

    fail_client = httpx.Client(transport=httpx.MockTransport(handler_fail), timeout=1.0)
    partner_fail = PartnerClient(base_url="http://partner", client=fail_client)

    fake_now = {"t": 1000.0}
    service = TransactionService(repo, partner_fail, max_attempts=2, now_fn=lambda: fake_now["t"])

    service.create_transaction(TransactionRequest(external_id="r2", valor=10, kind="debit"))
    rec = repo.get_by_external_id("r2")
    assert rec.status == TransactionStatus.pending

    # força retry ficar due
    fake_now["t"] = rec.next_retry_at + 0.1
    service.retry_pending_once()

    rec2 = repo.get_by_external_id("r2")
    # na 2ª falha (max_attempts=2), vira FAILED
    assert rec2.status == TransactionStatus.failed