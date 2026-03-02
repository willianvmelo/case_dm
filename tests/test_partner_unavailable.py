from pathlib import Path

from app.models import TransactionRequest, TransactionStatus
from app.partner_client import PartnerClient
from app.repository import SqliteTransactionRepository
from app.service import TransactionService


def test_when_partner_fails_transaction_becomes_pending(tmp_path: Path):
    db_file = tmp_path / "test.db"
    repo = SqliteTransactionRepository(str(db_file))
    partner = PartnerClient(should_fail=True)
    service = TransactionService(repo, partner)

    res = service.create_transaction(TransactionRequest(external_id="x1", valor=10, kind="credit"))
    assert res.status == TransactionStatus.pending
    assert res.partner_transaction_id is None


def test_retry_pending_sends_when_partner_recovers(tmp_path: Path):
    db_file = tmp_path / "test.db"
    repo = SqliteTransactionRepository(str(db_file))

    failing_partner = PartnerClient(should_fail=True)
    service = TransactionService(repo, failing_partner)

    service.create_transaction(TransactionRequest(external_id="x2", valor=10, kind="debit"))
    rec = repo.get_by_external_id("x2")
    assert rec.status == TransactionStatus.pending

    
    service.partner = PartnerClient(should_fail=False)
    sent = service.retry_pending_once()

    assert sent == 1
    rec2 = repo.get_by_external_id("x2")
    assert rec2.status == TransactionStatus.sent
    assert rec2.partner_transaction_id == 123