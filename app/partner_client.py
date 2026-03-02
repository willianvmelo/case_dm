from dataclasses import dataclass
from app.models import TransactionKind


class PartnerUnavailable(Exception):
    pass


@dataclass(frozen=True)
class PartnerResult:
    transaction_id: int


class PartnerClient:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def send(self, *, external_id: str, valor: float, kind: TransactionKind) -> PartnerResult:
        
        if self.should_fail:
            raise PartnerUnavailable("partner is unavailable")
        return PartnerResult(transaction_id=123)