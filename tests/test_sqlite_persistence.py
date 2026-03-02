from pathlib import Path

from app.models import TransactionRequest, TransactionStatus
from app.partner_client import PartnerClient
from app.repository import SqliteTransactionRepository
from app.service import TransactionService


def test_sqlite_persists_transaction(tmp_path: Path):
    db_file = tmp_path / "test.db"
    repo = SqliteTransactionRepository(str(db_file))
    service = TransactionService(repo, PartnerClient(should_fail=False))

    res1 = service.create_transaction(TransactionRequest(external_id="p1", valor=10, kind="credit"))
    assert res1.status == TransactionStatus.sent

    
    repo2 = SqliteTransactionRepository(str(db_file))
    service2 = TransactionService(repo2, PartnerClient(should_fail=False))

    res2 = service2.create_transaction(TransactionRequest(external_id="p1", valor=999, kind="debit"))
    assert res2.transaction_id == res1.transaction_id
    assert res2.partner_transaction_id == res1.partner_transaction_id
    assert res2.status == res1.status