from fastapi import FastAPI

from app.models import TransactionRequest, TransactionResponse
from app.partner_client import PartnerClient
from app.repository import InMemoryTransactionRepository
from app.service import TransactionService

app = FastAPI(title="Transactions API")

repo = InMemoryTransactionRepository()
partner = PartnerClient()
service = TransactionService(repo, partner)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/transaction", response_model=TransactionResponse)
async def create_transaction(payload: TransactionRequest):
    return service.create_transaction(payload)