"""Ed25519 issuance and strict verification, with public-key-only verification."""

import base64
import json
import secrets
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from pydantic import Field, ValidationError

from .compiler import TEMPLATE_HASH, canonical, digest
from .models import Action, DIRECTIONS, Direction, StrictModel

AUDIENCE = "vaaniverify-mock-dpi-v1"
TOKEN_TTL = 60


class SecurityError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


class Claims(StrictModel):
    version: int = Field(strict=True, ge=1, le=1)
    audience: str
    subject: str
    intent_id: str
    proposal_id: str
    action_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    template_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    direction: Direction
    nonce: str = Field(pattern=r"^[a-f0-9]{48}$")
    issued_at: int = Field(strict=True)
    expires_at: int = Field(strict=True)


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def unb64(value: str) -> bytes:
    if not value or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in value):
        raise ValueError("Invalid base64url")
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)


def issue(key: Ed25519PrivateKey, action: Action, intent_id: str, proposal_id: str, now: int | None = None) -> str:
    issued = int(time.time()) if now is None else now
    claims = Claims(version=1, audience=AUDIENCE, subject=action.subject, intent_id=intent_id,
                    proposal_id=proposal_id, action_digest=digest(action.model_dump(mode="json")),
                    template_hash=TEMPLATE_HASH, direction=DIRECTIONS[action.operation],
                    nonce=secrets.token_hex(24), issued_at=issued, expires_at=issued + TOKEN_TTL)
    payload = canonical(claims.model_dump(mode="json"))
    return f"{b64(payload)}.{b64(key.sign(payload))}"


def verify(key: Ed25519PublicKey, token: str, action: Action, now: int | None = None) -> Claims:
    try:
        if len(token) > 12000:
            raise ValueError("Oversized token")
        encoded, signature = token.split(".")
        payload = unb64(encoded)
        key.verify(unb64(signature), payload)
        raw = json.loads(payload)
        claims = Claims.model_validate(raw)
        if canonical(claims.model_dump(mode="json")) != payload:
            raise ValueError("Noncanonical claims")
    except (ValueError, TypeError, ValidationError, InvalidSignature, UnicodeDecodeError) as exc:
        raise SecurityError("INVALID_TOKEN", "Capability is malformed or its signature is invalid.") from exc
    current = int(time.time()) if now is None else now
    if claims.audience != AUDIENCE or claims.subject != action.subject:
        raise SecurityError("WRONG_AUDIENCE", "Capability belongs to another gateway or subject.")
    if claims.issued_at > current or claims.expires_at <= current or not 0 < claims.expires_at - claims.issued_at <= TOKEN_TTL:
        raise SecurityError("TOKEN_EXPIRED", "Capability is expired, future-dated, or has an invalid lifetime.")
    if claims.template_hash != TEMPLATE_HASH:
        raise SecurityError("TEMPLATE_MISMATCH", "Confirmation template version is not accepted.")
    if claims.action_digest != digest(action.model_dump(mode="json")) or claims.direction != DIRECTIONS[action.operation]:
        raise SecurityError("PAYLOAD_CHANGED", "The execution payload differs from the approved action.")
    return claims
