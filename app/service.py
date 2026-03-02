from app.models import TransactionRequest, TransactionResponse
from app.partner_client import PartnerClient
from app.repository import InMemoryTransactionRepository


class TransactionService:
    def __init__(self, repo: InMemoryTransactionRepository, partner: PartnerClient) -> None:
        self.repo = repo
        self.partner = partner

    def create_transaction(self, req: TransactionRequest) -> TransactionResponse:
        existing = self.repo.get_by_external_id(req.external_id)
        if existing:
            return TransactionResponse(
                transaction_id=existing.transaction_id,
                partner_transaction_id=existing.partner_transaction_id,
            )

        rec = self.repo.create(req.external_id, req.valor, req.kind)

        # Por enquanto envia sincrono
        partner_res = self.partner.send(external_id=req.external_id, valor=req.valor, kind=req.kind)
        self.repo.set_partner_id(req.external_id, partner_res.transaction_id)

        updated = self.repo.get_by_external_id(req.external_id)
        return TransactionResponse(
            transaction_id=updated.transaction_id,
            partner_transaction_id=updated.partner_transaction_id,
        )