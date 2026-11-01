"""Trusted consent state machine; transport authentication lives in server.py."""

import copy
import secrets
import threading
import time
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .capabilities import SecurityError, issue
from .compiler import compile_action, digest
from .models import Action, Approval, DIRECTIONS, Intent, ProposalInput
from .policy import advisory_polarity, evaluate_policy, explanation_warnings


@dataclass
class IntentRecord:
    value: Intent
    expires_at: int
    state: str = "OPEN"


class Kernel:
    def __init__(self, signing_key: Ed25519PrivateKey | None = None, clock=time.time):
        self.signing_key = signing_key or Ed25519PrivateKey.generate()
        self.clock = clock
        self.intents: dict[str, IntentRecord] = {}
        self.proposals: dict[str, dict] = {}
        self.lock = threading.RLock()

    def create_intent(self, intent: Intent):
        with self.lock:
            if len(self.intents) >= 2000:
                raise SecurityError("SESSION_LIMIT", "Restart the local demo to clear its bounded session state.")
            intent_id = secrets.token_hex(16)
            expires_at = int(self.clock()) + 900
            self.intents[intent_id] = IntentRecord(intent, expires_at)
            return {"intent_id": intent_id, "intent": intent.model_dump(mode="json"),
                    "intent_digest": digest(intent.model_dump(mode="json")), "expires_at": expires_at,
                    "text_hint": advisory_polarity(intent.user_text), "authority": "structured user selection"}

    def active_intent(self, intent_id):
        record = self.intents.get(intent_id)
        if record is None:
            raise SecurityError("UNKNOWN_INTENT", "No trusted user intent exists with that identifier.")
        if record.state != "OPEN":
            raise SecurityError("INTENT_CLOSED", "This one-action intent is already used or cancelled.")
        if int(self.clock()) >= record.expires_at:
            raise SecurityError("INTENT_EXPIRED", "The user's intent has expired. Create a new intent.")
        return record

    def propose(self, proposal: ProposalInput):
        with self.lock:
            record = self.active_intent(proposal.intent_id)
            # An agent cannot allocate new trusted intents. Cap its work per intent
            # so rejected proposals cannot consume the whole owner's session.
            related = [p for p in self.proposals.values() if p["intent_id"] == proposal.intent_id]
            if len(related) >= 20:
                raise SecurityError("INTENT_PROPOSAL_LIMIT", "This intent has reached its proposal limit. The owner must create a new intent.")
            if len(self.proposals) >= 5000:
                stale = [key for key, value in self.proposals.items()
                         if value["status"] != "AWAITING_APPROVAL" or value["expires_at"] <= int(self.clock())]
                for key in stale[:1000]:
                    del self.proposals[key]
                if len(self.proposals) >= 5000:
                    raise SecurityError("SESSION_LIMIT", "Too many live proposals. Cancel existing intents before continuing.")
            decision = evaluate_policy(record.value, proposal.action)
            proposal_id = secrets.token_hex(16)
            result = {"proposal_id": proposal_id, "intent_id": proposal.intent_id,
                      "status": "AWAITING_APPROVAL" if decision["allowed"] else "BLOCKED",
                      "action": proposal.action.model_dump(mode="json"),
                      "agent_message": proposal.agent_message, "external_text": proposal.external_text,
                      "decision": decision, "confirmation": compile_action(proposal.action, record.value.language),
                      "warnings": explanation_warnings(proposal.agent_message, proposal.action),
                      "expires_at": min(record.expires_at, int(self.clock()) + 180)}
            self.proposals[proposal_id] = result
            # Return independent snapshots: callers cannot mutate security state.
            return copy.deepcopy(result)

    def approve(self, proposal_id: str, proof: Approval):
        with self.lock:
            proposal = self.proposals.get(proposal_id)
            if not proposal or proposal["status"] != "AWAITING_APPROVAL":
                raise SecurityError("NOT_APPROVABLE", "Proposal is blocked, closed, or unknown.")
            record = self.active_intent(proposal["intent_id"])
            if int(self.clock()) >= proposal["expires_at"]:
                raise SecurityError("PROPOSAL_EXPIRED", "Review window expired. Request a new proposal.")
            action = Action.model_validate(proposal["action"])
            if proof.direction != DIRECTIONS[action.operation]:
                proposal["status"] = "REJECTED"
                record.state = "CANCELLED"
                raise SecurityError("DIRECTION_MISMATCH", "Selected direction does not match the action. Intent cancelled.")
            if (proof.recipient_answer != (action.recipient or action.mandate_id or "")
                    or proof.amount_answer_paise != (action.amount_paise or 0)
                    or proof.action_digest != digest(action.model_dump(mode="json"))
                    or not proof.terms_accepted):
                raise SecurityError("EXACT_CONFIRMATION_REQUIRED", "Confirm the exact recipient, amount, and displayed terms.")
            # Re-evaluate against immutable intent before minting.
            if not evaluate_policy(record.value, action)["allowed"]:
                raise SecurityError("POLICY_CHANGED", "Action is outside the user's authority.")
            token = issue(self.signing_key, action, proposal["intent_id"], proposal_id, now=int(self.clock()))
            proposal["status"] = "APPROVED"
            record.state = "CONSUMED"
            for sibling in self.proposals.values():
                if sibling["intent_id"] == proposal["intent_id"] and sibling["status"] == "AWAITING_APPROVAL":
                    sibling["status"] = "SUPERSEDED"
            return {"token": token, "action": action.model_dump(mode="json"), "expires_in_seconds": 60,
                    "proposal_id": proposal_id, "status": "APPROVED"}

    def cancel(self, intent_id):
        with self.lock:
            record = self.active_intent(intent_id)
            record.state = "CANCELLED"
            for proposal in self.proposals.values():
                if proposal["intent_id"] == intent_id and proposal["status"] == "AWAITING_APPROVAL":
                    proposal["status"] = "CANCELLED"
            return {"status": "CANCELLED", "intent_id": intent_id}
