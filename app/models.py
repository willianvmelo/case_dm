from enum import Enum
from pydantic import BaseModel, Field


class TransactionKind(str, Enum):
    credit = "credit"
    debit = "debit"


class TransactionRequest(BaseModel):
    external_id: str = Field(..., min_length=1)
    valor: float = Field(..., gt=0)
    kind: TransactionKind


class TransactionResponse(BaseModel):
    transaction_id: int
    partner_transaction_id: int | None = None