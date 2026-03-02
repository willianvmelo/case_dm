import httpx
from dataclasses import dataclass

from app.models import TransactionKind


class PartnerUnavailable(Exception):
    pass


@dataclass(frozen=True)
class PartnerResult:
    transaction_id: int


class PartnerClient:
    def __init__(self, base_url: str, timeout_s: float = 2.0, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self._client = client or httpx.Client(timeout=timeout_s)

    def send(self, *, external_id: str, valor: float, kind: TransactionKind) -> PartnerResult:
        
        url = f"{self.base_url}/bank_partner_request"

        payload = {"external_id": external_id, "valor": valor, "kind": kind.value}

        try:
            resp = self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return PartnerResult(transaction_id=int(data["transaction_id"]))
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            raise PartnerUnavailable(str(e)) from e
        except httpx.HTTPStatusError as e:
            
            raise PartnerUnavailable(f"partner http error: {e.response.status_code}") from e
        except (KeyError, ValueError, TypeError) as e:
            raise PartnerUnavailable(f"invalid partner response: {e}") from e