import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status, HTTPException

from app.context import request_id_ctx
from app.logging_utils import setup_logging
from app.middleware import RequestIdMiddleware

from app.partner_client import PartnerClient
from app.repository import SqliteTransactionRepository
from app.service import TransactionService
from app.models import (
    TransactionRequest,
    TransactionResponse,
    TransactionStatus,
    TransactionStatusResponse,
)


def get_request_id() -> str | None:
    return request_id_ctx.get()


# Logging (configure once on import)
setup_logging(get_request_id)


# Dependencies / singletons
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
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="Transactions API",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(RequestIdMiddleware)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/transaction", response_model=TransactionResponse)
async def create_transaction(payload: TransactionRequest, response: Response):
    result = service.create_transaction(payload)
    if result.status == TransactionStatus.pending:
        response.status_code = status.HTTP_202_ACCEPTED
    return result


@app.get("/transaction/{external_id}", response_model=TransactionStatusResponse)
async def get_transaction_status(external_id: str):
    rec = repo.get_by_external_id(external_id)
    if not rec:
        raise HTTPException(status_code=404, detail="transaction not found")

    return TransactionStatusResponse(
        transaction_id=rec.transaction_id,
        external_id=rec.external_id,
        valor=rec.valor,
        kind=rec.kind,
        partner_transaction_id=rec.partner_transaction_id,
        status=rec.status,
        attempts=rec.attempts,
        last_error=rec.last_error,
    )