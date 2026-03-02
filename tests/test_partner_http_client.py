import httpx
import pytest

from app.partner_client import PartnerClient, PartnerUnavailable
from app.models import TransactionKind


def test_partner_client_success():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"transaction_id": 777})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, timeout=1.0)

    partner = PartnerClient(base_url="http://partner", client=client)
    res = partner.send(external_id="e1", valor=10, kind=TransactionKind.credit)
    assert res.transaction_id == 777


def test_partner_client_500_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "down"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, timeout=1.0)

    partner = PartnerClient(base_url="http://partner", client=client)
    with pytest.raises(PartnerUnavailable):
        partner.send(external_id="e1", valor=10, kind=TransactionKind.debit)