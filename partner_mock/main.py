from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import time

app = FastAPI(title="Partner Mock Bank")

class PartnerRequest(BaseModel):
    external_id: str = Field(..., min_length=1)
    valor: float = Field(..., gt=0)
    kind: str = Field(..., pattern="^(credit|debit)$")

@app.post("/bank_partner_request")
async def bank_partner_request(payload: PartnerRequest, fail: bool = False, delay_ms: int = 0):
    """
    fail=true  -> simula indisponibilidade (HTTP 503)
    delay_ms=N -> simula lentidão (sleep N ms)
    """
    if delay_ms > 0:
        time.sleep(delay_ms / 1000)

    if fail:
        raise HTTPException(status_code=503, detail="partner unavailable (mock)")

    # gera um id determinístico (pra facilitar debug) baseado no external_id
    tx_id = abs(hash(payload.external_id)) % 1_000_000
    return {"transaction_id": tx_id}