import logging

from app.models import TransactionRequest, TransactionResponse, TransactionStatus
from app.partner_client import PartnerClient, PartnerUnavailable
from app.repository import SqliteTransactionRepository

logger = logging.getLogger("transactions")


class TransactionService:
    def __init__(self, repo: SqliteTransactionRepository, partner: PartnerClient) -> None:
        self.repo = repo
        self.partner = partner

    def create_transaction(self, req: TransactionRequest) -> TransactionResponse:
        existing = self.repo.get_by_external_id(req.external_id)
        if existing:
            return TransactionResponse(
                transaction_id=existing.transaction_id,
                partner_transaction_id=existing.partner_transaction_id,
                status=existing.status,
            )

        rec = self.repo.create(req.external_id, req.valor, req.kind)
        logger.info("transaction_created", extra={"external_id": req.external_id, "transaction_id": rec.transaction_id})

        try:
            partner_res = self.partner.send(external_id=req.external_id, valor=req.valor, kind=req.kind)
            self.repo.set_partner_sent(req.external_id, partner_res.transaction_id)
            logger.info("partner_send_ok", extra={"external_id": req.external_id, "partner_transaction_id": partner_res.transaction_id})
        except PartnerUnavailable as e:
            self.repo.mark_pending_error(req.external_id, str(e))
            logger.warning("partner_send_failed", extra={"external_id": req.external_id, "error": str(e)})

        updated = self.repo.get_by_external_id(req.external_id)
        return TransactionResponse(
            transaction_id=updated.transaction_id,
            partner_transaction_id=updated.partner_transaction_id,
            status=updated.status,
        )

    def retry_pending_once(self) -> int:
        """
        Tenta reenviar 1 ciclo de pendências. Retorna quantas foram enviadas com sucesso.
        Mantemos isso síncrono e simples pra facilitar unit test.
        """
        sent = 0
        for rec in self.repo.list_pending():
            try:
                partner_res = self.partner.send(external_id=rec.external_id, valor=rec.valor, kind=rec.kind)
                self.repo.set_partner_sent(rec.external_id, partner_res.transaction_id)
                sent += 1
                logger.info("retry_send_ok", extra={"external_id": rec.external_id, "partner_transaction_id": partner_res.transaction_id})
            except PartnerUnavailable as e:
                self.repo.mark_pending_error(rec.external_id, str(e))
                logger.warning("retry_send_failed", extra={"external_id": rec.external_id, "error": str(e)})
        return sent