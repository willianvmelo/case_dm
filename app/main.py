import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status

from app.models import TransactionRequest, TransactionResponse, TransactionStatus
from app.partner_client import PartnerClient
from app.repository import SqliteTransactionRepository
from app.service import TransactionService

logging.basicConfig(level=logging.INFO)

db_path = os.getenv("DB_PATH", "app.db")
repo = SqliteTransactionRepository(db_path=db_path)

partner_url = os.getenv("PARTNER_URL", "http://localhost:9000")
partner = PartnerClient(base_url=partner_url)

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