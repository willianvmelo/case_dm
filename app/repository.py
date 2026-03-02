from dataclasses import dataclass
from typing import Optional

from app.models import TransactionKind


@dataclass
class TransactionRecord:
    transaction_id: int
    external_id: str
    valor: float
    kind: TransactionKind
    partner_transaction_id: Optional[int] = None


class InMemoryTransactionRepository:
    def __init__(self) -> None:
        self._by_external_id: dict[str, TransactionRecord] = {}
        self._next_id = 1

    def get_by_external_id(self, external_id: str) -> Optional[TransactionRecord]:
        return self._by_external_id.get(external_id)

    def create(self, external_id: str, valor: float, kind: TransactionKind) -> TransactionRecord:
        rec = TransactionRecord(
            transaction_id=self._next_id,
            external_id=external_id,
            valor=valor,
            kind=kind,
        )
        self._next_id += 1
        self._by_external_id[external_id] = rec
        return rec

    def set_partner_id(self, external_id: str, partner_transaction_id: int) -> None:
        rec = self._by_external_id[external_id]
        rec.partner_transaction_id = partner_transaction_id