from dataclasses import dataclass
from app.models import TransactionKind


@dataclass(frozen=True)
class PartnerResult:
    transaction_id: int


class PartnerClient:
    def send(self, *, external_id: str, valor: float, kind: TransactionKind) -> PartnerResult:        
        # Por enquanto retorna um id "falso"
        return PartnerResult(transaction_id=123)