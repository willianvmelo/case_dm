import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status

from app.models import TransactionRequest, TransactionResponse, TransactionStatus
from app.partner_client import PartnerClient
from app.repository import InMemoryTransactionRepository
from app.service import TransactionService

logging.basicConfig(level=logging.INFO)


repo = InMemoryTransactionRepository()
partner = PartnerClient()
service = TransactionService(repo, partner)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def retry_loop():
        while True:
            service.retry_pending_once()
            await asyncio.sleep(2)

    task = asyncio.create_task(retry_loop())
    yield
    task.cancel()


app = FastAPI(
    title="Transactions API",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/transaction", response_model=TransactionResponse)
async def create_transaction(payload: TransactionRequest, response: Response):
    result = service.create_transaction(payload)
    if result.status == TransactionStatus.pending:
        response.status_code = status.HTTP_202_ACCEPTED
    return result