"""Seeded capability mutation tests, separate from the authored policy benchmark."""

import argparse
import json
import random
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .capabilities import SecurityError, b64, issue, unb64
from .compiler import digest
from .gateway import Gateway
from .models import Action

FAMILIES = ["amount", "recipient", "operation", "frequency", "installments", "documents", "purpose", "retention", "mandate_id", "signature"]


def run_mutations(per_family=100, seed=20261031):
    rng = random.Random(seed)
    root = Path(__file__).resolve().parents[1]
    scratch = root / "tmp"
    scratch.mkdir(exist_ok=True)
    key = Ed25519PrivateKey.generate()
    rows = []
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="mutation-", dir=scratch) as directory:
        gateway = Gateway(key.public_key(), Path(directory) / "ledger.db")
        for family in FAMILIES:
            for index in range(per_family):
                recipient = f"synthetic-{family}-{index}@demo"
                amount = rng.randint(1, 5_000_000)
                raw = dict(operation="PAY", recipient=recipient, amount_paise=amount)
                if family in {"frequency", "installments"}:
                    raw.update(operation="MANDATE", frequency="MONTHLY", installments=3)
                if family in {"documents", "purpose", "retention"}:
                    raw = dict(operation="SHARE", recipient=recipient, documents=["driving_license"], purpose="employment", retention_days=7)
                if family == "mandate_id":
                    raw = dict(operation="CANCEL_MANDATE", mandate_id=f"mandate-demo-{index+1}")
                original = Action(**raw)
                token = issue(key, original, f"mutation-{family}-{index}", f"proposal-{family}-{index}", now=1000)
                changed = dict(raw)
                if family == "amount": changed["amount_paise"] += rng.randint(1, 1_000_000)
                elif family == "recipient": changed["recipient"] = f"redirect-{index}@demo"
                elif family == "operation": changed.update(operation="MANDATE", frequency="MONTHLY", installments=12)
                elif family == "frequency": changed["frequency"] = "WEEKLY"
                elif family == "installments": changed["installments"] = rng.choice([n for n in range(1, 13) if n != 3])
                elif family == "documents": changed["documents"] = ["driving_license", rng.choice(["address_proof", "degree_certificate"])]
                elif family == "purpose": changed["purpose"] = rng.choice(["education", "identity_check"])
                elif family == "retention": changed["retention_days"] = rng.randint(8, 365)
                elif family == "mandate_id": changed["mandate_id"] = f"mandate-demo-{index+1001}"
                changed_token = token
                if family == "signature":
                    payload, signature = token.split(".")
                    signature_bytes = bytearray(unb64(signature))
                    signature_bytes[rng.randrange(64)] ^= 1 << rng.randrange(8)
                    changed_token = payload + "." + b64(bytes(signature_bytes))
                attack = Action(**changed)
                code, blocked = "EXECUTED", False
                try:
                    gateway.execute(attack, changed_token, now=1000)
                except SecurityError as exc:
                    code, blocked = exc.code, True
                # A rejected mutation must not burn the original valid approval.
                original_ok = False
                try:
                    original_ok = gateway.execute(original, token, now=1000)["status"] == "EXECUTED"
                except SecurityError:
                    pass
                rows.append({"id": f"{family}-{index}", "family": family, "blocked": blocked,
                             "reason": code, "original_still_executes": original_ok,
                             "original_digest": digest(original.model_dump(mode="json")),
                             "mutated_digest": digest(attack.model_dump(mode="json"))})
        audit = gateway.audit()
    return {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "seed": seed,
            "scope": "Generated signed-capability mutation trials. Not independent discovered exploits or model attacks.",
            "trials": len(rows), "blocked": sum(r["blocked"] for r in rows),
            "valid_originals_executed": sum(r["original_still_executes"] for r in rows),
            "families": FAMILIES, "per_family": per_family, "audit": audit,
            "duration_seconds": round(time.perf_counter() - started, 3), "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-family", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261031)
    parser.add_argument("--output", type=Path, default=Path("evidence/mutations.json"))
    args = parser.parse_args()
    if not 1 <= args.per_family <= 1000:
        parser.error("per-family must be between 1 and 1000")
    report = run_mutations(args.per_family, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Generated mutations blocked: {report['blocked']}/{report['trials']}")
    print(f"Original signed actions still executable: {report['valid_originals_executed']}/{report['trials']}")
    print(f"Ledger consistent: {report['audit']['valid']}; seed: {args.seed}")
    if report["blocked"] != report["trials"] or report["valid_originals_executed"] != report["trials"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
