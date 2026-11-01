"""Mock execution boundary. Has no approval API and never loads the signing key."""

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .capabilities import SecurityError, verify
from .compiler import canonical, digest
from .models import Action, Execution

ROUTES = {"PAY": "/upi/pay", "MANDATE": "/upi/mandate", "SHARE": "/digilocker/share",
          "READ_STATUS": "/status/read", "CANCEL_MANDATE": "/upi/cancel"}


class Gateway:
    def __init__(self, public_key: Ed25519PublicKey, database: str | Path):
        self.public_key = public_key
        self.database = str(database)
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""CREATE TABLE IF NOT EXISTS receipts (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, nonce TEXT UNIQUE NOT NULL,
                intent_id TEXT UNIQUE NOT NULL, proposal_id TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL, executed_at INTEGER NOT NULL,
                previous_hash TEXT NOT NULL, receipt_hash TEXT NOT NULL)""")

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.database, timeout=10)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def execute(self, action: Action, token: str, expected_operation: str | None = None, now: int | None = None):
        if expected_operation and action.operation != expected_operation:
            raise SecurityError("WRONG_ENDPOINT", "Action cannot execute at this endpoint.")
        # Reject invalid signatures before contending for the database lock.
        verify(self.public_key, token, action, now)
        payload = action.model_dump(mode="json")
        with self.connect() as conn:
            # Nonce consumption and mock side effect are the same transaction.
            conn.execute("BEGIN IMMEDIATE")
            # The lock may have waited past expiry. Recheck at the side-effect boundary.
            claims = verify(self.public_key, token, action, now)
            executed = int(time.time()) if now is None else now
            last = conn.execute("SELECT receipt_hash FROM receipts ORDER BY sequence DESC LIMIT 1").fetchone()
            previous = last[0] if last else "0" * 64
            record = {"nonce": claims.nonce, "intent_id": claims.intent_id, "proposal_id": claims.proposal_id,
                      "action": payload, "executed_at": executed, "previous_hash": previous}
            receipt_hash = digest(record)
            try:
                cur = conn.execute("INSERT INTO receipts (nonce,intent_id,proposal_id,payload,executed_at,previous_hash,receipt_hash) VALUES (?,?,?,?,?,?,?)",
                                   (claims.nonce, claims.intent_id, claims.proposal_id, canonical(payload).decode(), executed, previous, receipt_hash))
            except sqlite3.IntegrityError as exc:
                raise SecurityError("REPLAY_BLOCKED", "This capability or one-action intent has already been spent.") from exc
            return {"status": "EXECUTED", "synthetic": True, "sequence": cur.lastrowid,
                    **record, "receipt_hash": receipt_hash}

    def receipts(self):
        with self.connect() as conn:
            rows = conn.execute("SELECT sequence,nonce,intent_id,proposal_id,payload,executed_at,previous_hash,receipt_hash FROM receipts ORDER BY sequence").fetchall()
        return [{"sequence": r[0], "nonce": r[1], "intent_id": r[2], "proposal_id": r[3],
                 "action": json.loads(r[4]), "executed_at": r[5], "previous_hash": r[6], "receipt_hash": r[7]} for r in rows]

    def audit(self):
        previous = "0" * 64
        records = self.receipts()
        for record in records:
            body = {k: v for k, v in record.items() if k not in {"sequence", "receipt_hash"}}
            if record["previous_hash"] != previous or digest(body) != record["receipt_hash"]:
                return {"valid": False, "entries": len(records), "failed_sequence": record["sequence"]}
            previous = record["receipt_hash"]
        return {"valid": True, "entries": len(records), "head": previous,
                "limitation": "Local hash-chain integrity check; not an independently anchored audit log."}


def create_gateway_app(gateway: Gateway):
    app = FastAPI(title="VaaniVerify mock DPI gateway", docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(SecurityError)
    async def security_error(request, exc):
        return JSONResponse({"error": exc.code, "detail": exc.message}, status_code=403)

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "synthetic", "authority": "public-key verification only"}

    def make_execute(operation):
        def execute(body: Execution):
            return gateway.execute(body.action, body.token, expected_operation=operation)
        return execute

    for operation, path in ROUTES.items():
        app.post(path)(make_execute(operation))
    return app
