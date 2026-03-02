import sqlite3
from dataclasses import dataclass
from typing import Optional

from app.models import TransactionKind, TransactionStatus


@dataclass
class TransactionRecord:
    transaction_id: int
    external_id: str
    valor: float
    kind: TransactionKind
    partner_transaction_id: Optional[int]
    status: TransactionStatus
    attempts: int
    last_error: Optional[str]
    next_retry_at: Optional[float]


class SqliteTransactionRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id TEXT NOT NULL UNIQUE,
                    valor REAL NOT NULL,
                    kind TEXT NOT NULL,
                    partner_transaction_id INTEGER,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    next_retry_at REAL
                );
                """
            )

            # migração best-effort para bases antigas (se a coluna já existir, ignora)
            try:
                conn.execute("ALTER TABLE transactions ADD COLUMN next_retry_at REAL;")
            except sqlite3.OperationalError:
                pass

    def get_by_external_id(self, external_id: str) -> Optional[TransactionRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM transactions WHERE external_id = ?",
                (external_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def create(self, external_id: str, valor: float, kind: TransactionKind) -> TransactionRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO transactions (external_id, valor, kind, status, attempts, next_retry_at)
                VALUES (?, ?, ?, ?, 0, NULL)
                """,
                (external_id, float(valor), kind.value, TransactionStatus.pending.value),
            )
            row = conn.execute(
                "SELECT * FROM transactions WHERE external_id = ?",
                (external_id,),
            ).fetchone()
            return self._row_to_record(row)

    def set_partner_sent(self, external_id: str, partner_transaction_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE transactions
                SET partner_transaction_id = ?,
                    status = ?,
                    last_error = NULL,
                    next_retry_at = NULL
                WHERE external_id = ?
                """,
                (int(partner_transaction_id), TransactionStatus.sent.value, external_id),
            )

    def mark_send_failure(self, external_id: str, error: str, next_retry_at: float, max_attempts: int) -> None:
        """
        Incrementa attempts, grava last_error e aplica:
          - se attempts atingir max_attempts => status FAILED e next_retry_at NULL
          - senão => status PENDING e next_retry_at definido
        """
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE transactions
                SET
                  attempts = attempts + 1,
                  last_error = ?,
                  status = CASE WHEN (attempts + 1) >= ? THEN ? ELSE ? END,
                  next_retry_at = CASE WHEN (attempts + 1) >= ? THEN NULL ELSE ? END
                WHERE external_id = ?
                """,
                (
                    error,
                    int(max_attempts),
                    TransactionStatus.failed.value,
                    TransactionStatus.pending.value,
                    int(max_attempts),
                    float(next_retry_at),
                    external_id,
                ),
            )

    def list_pending_due(self, now_ts: float) -> list[TransactionRecord]:
        """
        Lista pendências que já estão 'due' para tentar novamente:
          - status PENDING
          - next_retry_at é NULL (nunca agendado) OU <= now
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM transactions
                WHERE status = ?
                  AND (next_retry_at IS NULL OR next_retry_at <= ?)
                """,
                (TransactionStatus.pending.value, float(now_ts)),
            ).fetchall()
            return [self._row_to_record(r) for r in rows]

    def _row_to_record(self, row: sqlite3.Row) -> TransactionRecord:
        next_retry_at = row["next_retry_at"]
        return TransactionRecord(
            transaction_id=int(row["transaction_id"]),
            external_id=str(row["external_id"]),
            valor=float(row["valor"]),
            kind=TransactionKind(row["kind"]),
            partner_transaction_id=(
                int(row["partner_transaction_id"]) if row["partner_transaction_id"] is not None else None
            ),
            status=TransactionStatus(row["status"]),
            attempts=int(row["attempts"]),
            last_error=(str(row["last_error"]) if row["last_error"] is not None else None),
            next_retry_at=(float(next_retry_at) if next_retry_at is not None else None),
        )