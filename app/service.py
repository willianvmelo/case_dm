import logging
import time

from app.models import TransactionRequest, TransactionResponse, TransactionStatus
from app.partner_client import PartnerClient, PartnerUnavailable

logger = logging.getLogger("transactions")


class TransactionService:
    def __init__(
        self,
        repo,
        partner: PartnerClient,
        *,
        max_attempts: int = 10,
        backoff_cap_s: int = 60,
        now_fn=time.time,
    ) -> None:
        self.repo = repo
        self.partner = partner
        self.max_attempts = max_attempts
        self.backoff_cap_s = backoff_cap_s
        self.now_fn = now_fn

    def _next_delay_s(self, attempt_number: int) -> int:
        # attempt_number começa em 1
        return int(min(self.backoff_cap_s, 2 ** attempt_number))

    def create_transaction(self, req: TransactionRequest) -> TransactionResponse:
        existing = self.repo.get_by_external_id(req.external_id)
        if existing:
            return TransactionResponse(
                transaction_id=existing.transaction_id,
                partner_transaction_id=existing.partner_transaction_id,
                status=existing.status,
            )

        rec = self.repo.create(req.external_id, req.valor, req.kind)
        logger.info(
            "transaction_created",
            extra={"external_id": req.external_id, "transaction_id": rec.transaction_id},
        )

        try:
            partner_res = self.partner.send(
                external_id=req.external_id, valor=req.valor, kind=req.kind
            )
            self.repo.set_partner_sent(req.external_id, partner_res.transaction_id)
            logger.info(
                "partner_send_ok",
                extra={
                    "external_id": req.external_id,
                    "partner_transaction_id": partner_res.transaction_id,
                },
            )
        except PartnerUnavailable as e:
            rec_now = self.repo.get_by_external_id(req.external_id)
            attempt_number = rec_now.attempts + 1
            delay = self._next_delay_s(attempt_number)
            next_retry_at = self.now_fn() + delay

            self.repo.mark_send_failure(
                req.external_id,
                str(e),
                next_retry_at=next_retry_at,
                max_attempts=self.max_attempts,
            )
            logger.warning(
                "partner_send_failed",
                extra={
                    "external_id": req.external_id,
                    "error": str(e),
                    "attempt": attempt_number,
                },
            )

       
        updated = self.repo.get_by_external_id(req.external_id)
        return TransactionResponse(
            transaction_id=updated.transaction_id,
            partner_transaction_id=updated.partner_transaction_id,
            status=updated.status,
        )

    def retry_pending_once(self) -> int:
        sent = 0
        now_ts = self.now_fn()

        for rec in self.repo.list_pending_due(now_ts):
            # segurança extra
            if rec.status != TransactionStatus.pending:
                continue

            try:
                partner_res = self.partner.send(
                    external_id=rec.external_id, valor=rec.valor, kind=rec.kind
                )
                self.repo.set_partner_sent(rec.external_id, partner_res.transaction_id)
                sent += 1
                logger.info(
                    "retry_send_ok",
                    extra={
                        "external_id": rec.external_id,
                        "partner_transaction_id": partner_res.transaction_id,
                    },
                )
            except PartnerUnavailable as e:
                attempt_number = rec.attempts + 1
                delay = self._next_delay_s(attempt_number)
                next_retry_at = now_ts + delay

                self.repo.mark_send_failure(
                    rec.external_id,
                    str(e),
                    next_retry_at=next_retry_at,
                    max_attempts=self.max_attempts,
                )
                logger.warning(
                    "retry_send_failed",
                    extra={
                        "external_id": rec.external_id,
                        "error": str(e),
                        "attempt": attempt_number,
                    },
                )

        return sent