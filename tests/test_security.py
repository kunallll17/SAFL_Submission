import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from vaaniverify.capabilities import SecurityError, b64, issue, unb64
from vaaniverify.compiler import TEMPLATE_HASH, canonical, compile_action, digest, rupees
from vaaniverify.gateway import Gateway, create_gateway_app
from vaaniverify.kernel import Kernel
from vaaniverify.models import Action, Approval, DIRECTIONS, Intent, ProposalInput
from vaaniverify.policy import evaluate_policy


def payment(**updates):
    return Action.model_validate({"operation": "PAY", "recipient": "utility.board@demo", "amount_paise": 50000, **updates})


def intent(**updates):
    return Intent.model_validate({"operation": "PAY", "user_text": "Pay my electricity bill", "recipient": "utility.board@demo", "max_amount_paise": 50000, **updates})


def proof_for(proposal, **updates):
    action = Action.model_validate(proposal["action"])
    return Approval.model_validate({"direction": DIRECTIONS[action.operation],
                                   "recipient_answer": action.recipient or action.mandate_id or "",
                                   "amount_answer_paise": action.amount_paise or 0,
                                   "action_digest": digest(action.model_dump(mode="json")),
                                   "terms_accepted": True, **updates})


def ready(kernel, selected=None, action=None):
    stored = kernel.create_intent(selected or intent())
    return kernel.propose(ProposalInput(intent_id=stored["intent_id"], action=action or payment()))


@pytest.fixture
def setup(tmp_path):
    kernel = Kernel(clock=lambda: 1000)
    return kernel, Gateway(kernel.signing_key.public_key(), tmp_path / "ledger.db")


def assert_error(code, fn):
    with pytest.raises(SecurityError) as error:
        fn()
    assert error.value.code == code


def test_legitimate_full_flow(setup):
    kernel, gateway = setup
    proposal = ready(kernel)
    approved = kernel.approve(proposal["proposal_id"], proof_for(proposal))
    receipt = gateway.execute(payment(), approved["token"], now=1000)
    assert receipt["status"] == "EXECUTED"
    assert receipt["synthetic"] is True
    assert gateway.audit()["valid"] is True


@pytest.mark.parametrize("operation,fields", [
    ("PAY", {"recipient": "utility.board@demo", "amount_paise": 50000}),
    ("MANDATE", {"recipient": "utility.board@demo", "amount_paise": 50000, "frequency": "MONTHLY", "installments": 12}),
    ("SHARE", {"recipient": "recruiter.demo@demo", "documents": ["driving_license"], "purpose": "employment", "retention_days": 7}),
])
def test_read_intent_cannot_escalate(operation, fields):
    decision = evaluate_policy(Intent(operation="READ_STATUS", user_text="Check my refund"), Action(operation=operation, **fields))
    assert not decision["allowed"]
    assert decision["reason"] == "OPERATION_BOUND"


@pytest.mark.parametrize("updates,code", [
    ({"recipient": "attacker.demo@demo"}, "RECIPIENT_BOUND"),
    ({"amount_paise": 50001}, "AMOUNT_CEILING"),
    ({"operation": "MANDATE", "frequency": "MONTHLY", "installments": 12}, "OPERATION_BOUND"),
])
def test_payment_scope(updates, code):
    assert evaluate_policy(intent(), payment(**updates))["reason"] == code


def test_external_resolution_requires_exact_approval(setup):
    kernel, gateway = setup
    selected = intent(recipient=None, allow_external_recipient=True)
    proposal = ready(kernel, selected)
    assert proposal["decision"]["provenance"]["recipient"] == "EXTERNAL_REQUIRES_REVIEW"
    assert_error("EXACT_CONFIRMATION_REQUIRED", lambda: kernel.approve(proposal["proposal_id"], proof_for(proposal, recipient_answer="")))
    assert len(gateway.receipts()) == 0
    approved = kernel.approve(proposal["proposal_id"], proof_for(proposal))
    assert gateway.execute(payment(), approved["token"], now=1000)["status"] == "EXECUTED"


def test_agent_cannot_supply_provenance():
    with pytest.raises(ValidationError):
        ProposalInput(intent_id="a" * 32, action=payment(), provenance={"recipient": "TRUSTED_USER"})


@pytest.mark.parametrize("amount", [True, False, "50000", 500.5, -1, 0, 10_000_001])
def test_money_is_bounded_strict_integer(amount):
    with pytest.raises(ValidationError):
        payment(amount_paise=amount)


@pytest.mark.parametrize("recipient", ["real@upi", "refund\u202e@demo", "pаyee@demo", "<script>@demo", "a@demo", "x\n@demo", "x y@demo"])
def test_only_synthetic_ascii_identifiers(recipient):
    with pytest.raises(ValidationError):
        payment(recipient=recipient)


def test_unknown_and_irrelevant_action_fields_rejected():
    with pytest.raises(ValidationError):
        payment(display_name="Cashback received")
    with pytest.raises(ValidationError):
        payment(documents=["address_proof"])
    with pytest.raises(ValidationError):
        Action(operation="READ_STATUS", amount_paise=500)


def test_direction_mismatch_cancels_intent(setup):
    kernel, gateway = setup
    proposal = ready(kernel)
    assert_error("DIRECTION_MISMATCH", lambda: kernel.approve(proposal["proposal_id"], proof_for(proposal, direction="READ_ONLY")))
    assert_error("INTENT_CLOSED", lambda: kernel.propose(ProposalInput(intent_id=proposal["intent_id"], action=payment())))
    assert gateway.receipts() == []


@pytest.mark.parametrize("updates", [{"recipient_answer": "other.demo@demo"}, {"amount_answer_paise": 49999}, {"terms_accepted": False}, {"action_digest": "0" * 64}])
def test_exact_proof_required(setup, updates):
    kernel, _ = setup
    proposal = ready(kernel)
    assert_error("EXACT_CONFIRMATION_REQUIRED", lambda: kernel.approve(proposal["proposal_id"], proof_for(proposal, **updates)))


def test_multiple_proposals_share_one_intent_budget(setup):
    kernel, gateway = setup
    first = ready(kernel)
    second = kernel.propose(ProposalInput(intent_id=first["intent_id"], action=payment()))
    approved = kernel.approve(first["proposal_id"], proof_for(first))
    assert_error("NOT_APPROVABLE", lambda: kernel.approve(second["proposal_id"], proof_for(second)))
    gateway.execute(payment(), approved["token"], now=1000)
    # Even a second valid signature for the same intent fails at the gateway.
    second_token = issue(kernel.signing_key, payment(), first["intent_id"], "another-proposal", now=1000)
    assert_error("REPLAY_BLOCKED", lambda: gateway.execute(payment(), second_token, now=1000))


@pytest.mark.parametrize("updates", [{"amount_paise": 50001}, {"recipient": "attacker.demo@demo"}, {"operation": "MANDATE", "frequency": "WEEKLY", "installments": 12}])
def test_post_approval_mutation_blocked(setup, updates):
    kernel, gateway = setup
    proposal = ready(kernel)
    approved = kernel.approve(proposal["proposal_id"], proof_for(proposal))
    assert_error("PAYLOAD_CHANGED", lambda: gateway.execute(payment(**updates), approved["token"], now=1000))
    assert gateway.receipts() == []


def test_replay_survives_gateway_restart(setup):
    kernel, gateway = setup
    proposal = ready(kernel)
    token = kernel.approve(proposal["proposal_id"], proof_for(proposal))["token"]
    gateway.execute(payment(), token, now=1000)
    restarted = Gateway(kernel.signing_key.public_key(), gateway.database)
    assert_error("REPLAY_BLOCKED", lambda: restarted.execute(payment(), token, now=1000))


def test_concurrent_execution_exactly_once(setup):
    kernel, gateway = setup
    proposal = ready(kernel)
    token = kernel.approve(proposal["proposal_id"], proof_for(proposal))["token"]

    def attempt(_):
        try:
            return gateway.execute(payment(), token, now=1000)["status"]
        except SecurityError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(attempt, range(24)))
    assert outcomes.count("EXECUTED") == 1
    assert outcomes.count("REPLAY_BLOCKED") == 23
    assert gateway.audit()["entries"] == 1


@pytest.mark.parametrize("now", [999, 1060, 10000])
def test_token_time_bounds(setup, now):
    kernel, gateway = setup
    token = issue(kernel.signing_key, payment(), "intent", "proposal", now=1000)
    assert_error("TOKEN_EXPIRED", lambda: gateway.execute(payment(), token, now=now))


def test_wrong_key_and_signature_tamper(setup):
    kernel, gateway = setup
    token = issue(Ed25519PrivateKey.generate(), payment(), "intent", "proposal", now=1000)
    assert_error("INVALID_TOKEN", lambda: gateway.execute(payment(), token, now=1000))
    valid = issue(kernel.signing_key, payment(), "intent", "proposal", now=1000)
    payload, sig = valid.split(".")
    raw = json.loads(unb64(payload))
    raw["action_digest"] = "0" * 64
    assert_error("INVALID_TOKEN", lambda: gateway.execute(payment(), b64(canonical(raw)) + "." + sig, now=1000))


@pytest.mark.parametrize("updates,code", [
    ({"audience": "another-gateway"}, "WRONG_AUDIENCE"),
    ({"subject": "another-user"}, "WRONG_AUDIENCE"),
    ({"template_hash": "0" * 64}, "TEMPLATE_MISMATCH"),
    ({"direction": "READ_ONLY"}, "PAYLOAD_CHANGED"),
    ({"expires_at": 99999}, "TOKEN_EXPIRED"),
])
def test_signed_claim_mismatches_rejected(setup, updates, code):
    kernel, gateway = setup
    token = issue(kernel.signing_key, payment(), "intent", "proposal", now=1000)
    raw = json.loads(unb64(token.split(".")[0]))
    raw.update(updates)
    payload = canonical(raw)
    forged = b64(payload) + "." + b64(kernel.signing_key.sign(payload))
    assert_error(code, lambda: gateway.execute(payment(), forged, now=1000))


def test_cancel_and_expiry(setup):
    kernel, _ = setup
    proposal = ready(kernel)
    kernel.cancel(proposal["intent_id"])
    assert_error("NOT_APPROVABLE", lambda: kernel.approve(proposal["proposal_id"], proof_for(proposal)))
    another = ready(kernel)
    kernel.clock = lambda: 1180
    assert_error("PROPOSAL_EXPIRED", lambda: kernel.approve(another["proposal_id"], proof_for(another)))
    kernel.clock = lambda: 1901
    assert_error("INTENT_EXPIRED", lambda: kernel.propose(ProposalInput(intent_id=another["intent_id"], action=payment())))


def test_proposal_snapshot_cannot_mutate_kernel(setup):
    kernel, _ = setup
    proposal = ready(kernel)
    proposal["action"]["amount_paise"] = 1
    assert kernel.proposals[proposal["proposal_id"]]["action"]["amount_paise"] == 50000


@pytest.mark.parametrize("field,value", [("documents", ["address_proof"]), ("purpose", "identity_check"), ("retention_days", 365), ("recipient", "other.demo@demo")])
def test_document_scope_bound(field, value):
    selected = Intent(operation="SHARE", user_text="Share licence for employment", recipient="recruiter.demo@demo", documents=["driving_license"], purpose="employment", retention_days=7)
    raw = dict(operation="SHARE", recipient="recruiter.demo@demo", documents=["driving_license"], purpose="employment", retention_days=7)
    raw[field] = value
    assert evaluate_policy(selected, Action(**raw))["allowed"] is False


@pytest.mark.parametrize("language", ["en", "hi", "hinglish", "ta"])
@pytest.mark.parametrize("action", [payment(), Action(operation="READ_STATUS"), Action(operation="MANDATE", recipient="utility.board@demo", amount_paise=50000, frequency="MONTHLY", installments=12), Action(operation="SHARE", recipient="recruiter.demo@demo", documents=["driving_license"], purpose="employment", retention_days=7), Action(operation="CANCEL_MANDATE", mandate_id="mandate-demo-1")])
def test_all_operation_language_templates(language, action):
    rendered = compile_action(action, language)
    assert "{" not in rendered["text"]
    assert rendered["template_hash"] == TEMPLATE_HASH
    if action.recipient:
        assert action.recipient in rendered["text"]
    if action.amount_paise:
        assert rupees(action.amount_paise) in rendered["text"]


def test_currency_format_and_canonicalization():
    assert rupees(123456789) == "₹12,34,567.89"
    assert rupees(101) == "₹1.01"
    assert digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2})


def test_hash_chain_detects_local_edit(setup):
    kernel, gateway = setup
    proposal = ready(kernel)
    token = kernel.approve(proposal["proposal_id"], proof_for(proposal))["token"]
    gateway.execute(payment(), token, now=1000)
    with gateway.connect() as conn:
        conn.execute("UPDATE receipts SET executed_at=42")
    assert gateway.audit()["valid"] is False


def test_gateway_http_endpoint_binding(setup):
    from fastapi.testclient import TestClient
    kernel, gateway = setup
    token = issue(kernel.signing_key, payment(), "intent", "proposal")
    client = TestClient(create_gateway_app(gateway))
    response = client.post("/digilocker/share", json={"action": payment().model_dump(mode="json"), "token": token})
    assert response.status_code == 403
    assert response.json()["error"] == "WRONG_ENDPOINT"
    assert client.post("/upi/pay", json={"action": payment().model_dump(mode="json"), "token": token}).status_code == 200


def test_expiry_rechecked_after_database_lock(setup, monkeypatch):
    from contextlib import contextmanager
    import vaaniverify.capabilities as capabilities
    kernel, gateway = setup
    token = issue(kernel.signing_key, payment(), "intent", "proposal", now=1000)
    clock = [1059]
    monkeypatch.setattr(capabilities.time, "time", lambda: clock[0])
    original = gateway.connect

    class LockDelay:
        def __init__(self, conn):
            self.conn = conn

        def execute(self, sql, *args):
            result = self.conn.execute(sql, *args)
            if sql == "BEGIN IMMEDIATE":
                clock[0] = 1060
            return result

    @contextmanager
    def delayed_connection():
        with original() as conn:
            yield LockDelay(conn)

    monkeypatch.setattr(gateway, "connect", delayed_connection)
    assert_error("TOKEN_EXPIRED", lambda: gateway.execute(payment(), token))
    assert gateway.receipts() == []


def test_agent_flood_cannot_exhaust_other_intents(setup):
    kernel, _ = setup
    stored = kernel.create_intent(Intent(operation="READ_STATUS", user_text="Read status"))
    for _ in range(20):
        assert kernel.propose(ProposalInput(intent_id=stored["intent_id"], action=payment()))["status"] == "BLOCKED"
    for _ in range(50):
        assert_error("INTENT_PROPOSAL_LIMIT", lambda: kernel.propose(ProposalInput(intent_id=stored["intent_id"], action=payment())))
    assert ready(kernel)["status"] == "AWAITING_APPROVAL"


def test_concurrent_sibling_approvals_issue_one_token(setup):
    kernel, _ = setup
    first = ready(kernel)
    second = kernel.propose(ProposalInput(intent_id=first["intent_id"], action=payment()))

    def approve_proposal(proposal):
        try:
            return kernel.approve(proposal["proposal_id"], proof_for(proposal))["status"]
        except SecurityError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(approve_proposal, [first, second]))
    assert results.count("APPROVED") == 1
    assert results.count("NOT_APPROVABLE") == 1
