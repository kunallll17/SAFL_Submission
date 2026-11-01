"""Authority comes from stored user constraints, never from agent-supplied labels."""

import re

from .models import Action, Intent


def evaluate_policy(intent: Intent, action: Action) -> dict:
    checks = []

    def check(code, ok, detail):
        checks.append({"code": code, "passed": ok, "detail": detail})

    check("OPERATION_BOUND", intent.operation == action.operation,
          f"User selected {intent.operation}; agent proposed {action.operation}.")
    if intent.operation == action.operation:
        if action.recipient:
            check("RECIPIENT_BOUND", action.recipient == intent.recipient or intent.allow_external_recipient,
                  "Recipient matches the user constraint." if action.recipient == intent.recipient
                  else "External recipient requires exact approval." if intent.allow_external_recipient
                  else "Recipient differs from the one the user selected.")
        if action.amount_paise:
            check("AMOUNT_CEILING", action.amount_paise <= (intent.max_amount_paise or 0),
                  f"Requested {action.amount_paise} paise; user ceiling {intent.max_amount_paise} paise.")
        for field in ("frequency", "installments", "purpose", "retention_days", "mandate_id"):
            if getattr(action, field) is not None:
                check(f"{field.upper()}_BOUND", getattr(action, field) == getattr(intent, field),
                      f"{field.replace('_', ' ').capitalize()} must match the user's selection.")
        if action.documents:
            check("DOCUMENT_SCOPE", set(action.documents) == set(intent.documents),
                  "Only the exact user-selected document set may be shared.")
    allowed = all(item["passed"] for item in checks)
    provenance = {"operation": "USER_BOUND" if intent.operation == action.operation else "CONFLICT"}
    if action.recipient:
        provenance["recipient"] = "USER_BOUND" if intent.recipient == action.recipient else "EXTERNAL_REQUIRES_REVIEW" if intent.allow_external_recipient else "CONFLICT"
    if action.amount_paise:
        provenance["amount_paise"] = "WITHIN_USER_CEILING" if action.amount_paise <= (intent.max_amount_paise or 0) else "CONFLICT"
    return {"allowed": allowed, "checks": checks, "provenance": provenance,
            "reason": "EXACT_APPROVAL_REQUIRED" if allowed else next(c["code"] for c in checks if not c["passed"])}


def advisory_polarity(text: str) -> str:
    """A deliberately non-authoritative hint, not a multilingual intent parser."""
    value = text.casefold()
    read = any(word in value for word in ("check", "status", "receive", "refund", "aaya", "aayega", "jama", "स्थिति", "जमा", "நிலை"))
    write = any(word in value for word in ("pay", "bhejo", "send", "share", "mandate", "भेज", "கட்டு"))
    return "AMBIGUOUS" if read and write else "READ_OR_RECEIVE" if read else "WRITE_MENTIONED" if write else "UNKNOWN"


def explanation_warnings(message: str, action: Action) -> list[str]:
    """Best-effort diagnostics only; authorization never depends on this heuristic."""
    warnings = []
    if action.operation in {"PAY", "MANDATE"} and advisory_polarity(message) == "READ_OR_RECEIVE":
        warnings.append("Agent wording suggests receiving/checking; the proposed tool moves money out.")
    handles = re.findall(r"[a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+", message)
    if handles and action.recipient and any(h != action.recipient for h in handles):
        warnings.append("The agent explanation names a different recipient.")
    if re.search(r"[\u202a-\u202e\u2066-\u2069]", message):
        warnings.append("The untrusted explanation contains bidirectional control characters.")
    return warnings
