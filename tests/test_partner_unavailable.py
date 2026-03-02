from app.models import TransactionRequest, TransactionStatus
from app.partner_client import PartnerClient
from app.repository import InMemoryTransactionRepository
from app.service import TransactionService


def test_when_partner_fails_transaction_becomes_pending():
    repo = InMemoryTransactionRepository()
    partner = PartnerClient(should_fail=True)
    service = TransactionService(repo, partner)

    res = service.create_transaction(TransactionRequest(external_id="x1", valor=10, kind="credit"))
    assert res.status == TransactionStatus.pending
    assert res.partner_transaction_id is None


def test_retry_pending_sends_when_partner_recovers():
    repo = InMemoryTransactionRepository()

    failing_partner = PartnerClient(should_fail=True)
    service = TransactionService(repo, failing_partner)
    service.create_transaction(TransactionRequest(external_id="x2", valor=10, kind="debit"))
    assert repo.get_by_external_id("x2").status == TransactionStatus.pending

    # “recupera” o parceiro
    service.partner = PartnerClient(should_fail=False)
    sent = service.retry_pending_once()

    assert sent == 1
    rec = repo.get_by_external_id("x2")
    assert rec.status == TransactionStatus.sent
    assert rec.partner_transaction_id == 123