import secrets

import pytest
from fastapi.testclient import TestClient

from vaaniverify.gateway import Gateway
from vaaniverify.kernel import Kernel
from vaaniverify.server import create_app

ORIGIN = "http://127.0.0.1:8765"
HEADERS = {"Origin": ORIGIN, "X-Vaani-Request": "1"}


@pytest.fixture
def web(tmp_path):
    kernel = Kernel()
    gateway = Gateway(kernel.signing_key.public_key(), tmp_path / "ledger.db")
    bootstrap, agent_key = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    app = create_app(kernel, gateway, bootstrap, agent_key, execution_transport=gateway.execute)
    client = TestClient(app, base_url=ORIGIN)
    return client, bootstrap, agent_key, kernel, gateway


def login(web):
    client, bootstrap, *_ = web
    response = client.post("/api/session", json={"bootstrap": bootstrap}, headers=HEADERS)
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    return client


def test_public_page_cannot_read_owner_api(web):
    client, *_ = web
    assert client.get("/").status_code == 200
    assert client.get("/api/meta").status_code == 403
    assert client.get("/api/receipts").status_code == 403
    assert client.get("/api/model-evidence").status_code == 403
    assert "frame-ancestors 'none'" in client.get("/").headers["content-security-policy"]


def test_session_exchange_single_use(web):
    client = login(web)
    assert client.get("/api/meta").status_code == 200
    response = client.post("/api/session", json={"bootstrap": web[1]}, headers=HEADERS)
    assert response.status_code == 403
    assert response.json()["error"] == "INVALID_BOOTSTRAP"


def test_non_ascii_bootstrap_is_validation_error_not_server_error(web):
    client = web[0]
    response = client.post("/api/session", json={"bootstrap": "é" * 32}, headers=HEADERS)
    assert response.status_code == 422
    assert response.json()["error"] == "INVALID_INPUT"


@pytest.mark.parametrize("headers", [{}, {"Origin": "https://attacker.invalid", "X-Vaani-Request": "1"}, {"Origin": ORIGIN}])
def test_csrf_and_cross_origin_rejected(web, headers):
    client = login(web)
    response = client.post("/api/demo", json={"scenario_id": "en-known-bill"}, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"] == "ORIGIN_REJECTED"


def test_dns_rebinding_host_rejected(web):
    client, *_ = web
    assert client.get("/health", headers={"Host": "attacker.invalid"}).status_code == 400


def test_agent_credential_cannot_create_intent_or_approve(web):
    client, _, agent_key, *_ = web
    headers = {**HEADERS, "Authorization": "Bearer " + agent_key}
    assert client.post("/api/intents", json={"operation": "READ_STATUS", "user_text": "Read status"}, headers=headers).status_code == 403
    assert client.post("/api/proposals/abc/approve", json={}, headers=headers).status_code == 403
    assert client.get("/api/scenarios", headers=headers).status_code == 403
    assert client.get("/api/model-evidence", headers=headers).status_code == 403


def test_agent_can_only_propose_against_existing_intent(web):
    client = login(web)
    stored = client.post("/api/intents", json={"operation": "READ_STATUS", "user_text": "Read status"}, headers=HEADERS).json()
    client.cookies.clear()
    headers = {"Authorization": "Bearer " + web[2]}
    proposal = {"intent_id": stored["intent_id"], "action": {"operation": "PAY", "recipient": "attacker.demo@demo", "amount_paise": 50000}}
    result = client.post("/api/agent/proposals", json=proposal, headers=headers)
    assert result.status_code == 200
    assert result.json()["status"] == "BLOCKED"
    assert client.post("/api/agent/proposals", json=proposal).status_code == 403
    proposal["provenance"] = {"recipient": "TRUSTED_USER"}
    assert client.post("/api/agent/proposals", json=proposal, headers=headers).status_code == 422


def test_owner_can_review_external_agent_proposal(web):
    client = login(web)
    stored = client.post("/api/intents", json={"operation": "READ_STATUS", "user_text": "Read status"}, headers=HEADERS).json()
    result = client.post("/api/agent/proposals", json={"intent_id": stored["intent_id"], "action": {"operation": "READ_STATUS"}}, headers={"Authorization": "Bearer " + web[2]}).json()
    inbox = client.get("/api/proposals").json()
    assert inbox[0]["proposal_id"] == result["proposal_id"]
    review = client.get("/api/proposals/" + result["proposal_id"]).json()
    assert review["intent"]["intent"]["operation"] == "READ_STATUS"
    assert "token" not in review["proposal"]
    client.cookies.clear()
    assert client.get("/api/proposals", headers={"Authorization": "Bearer " + web[2]}).status_code == 403


def test_live_http_owner_approval_and_execution(web):
    client = login(web)
    result = client.post("/api/demo", json={"scenario_id": "hi-external-bill"}, headers=HEADERS).json()
    p = result["proposal"]
    assert p["status"] == "AWAITING_APPROVAL"
    response = client.post(f"/api/proposals/{p['proposal_id']}/approve", json={"direction": "MONEY_OUT", "recipient_answer": "utility.board@demo", "amount_answer_paise": 50000, "action_digest": p["confirmation"]["action_digest"], "terms_accepted": True}, headers=HEADERS)
    assert response.status_code == 200
    approved = response.json()
    body = {"action": approved["action"], "token": approved["token"]}
    assert client.post("/api/execute", json=body, headers=HEADERS).json()["status"] == "EXECUTED"
    assert client.post("/api/execute", json=body, headers=HEADERS).json()["error"] == "REPLAY_BLOCKED"
    assert client.get("/api/receipts").json()["audit"]["entries"] == 1


def test_schema_errors_do_not_echo_input(web):
    client = login(web)
    response = client.post("/api/intents", json={"operation": "PAY", "user_text": "private-sentinel", "max_amount_paise": True}, headers=HEADERS)
    assert response.status_code == 422
    assert "private-sentinel" not in response.text


def test_body_size_and_json_content_type(web):
    client = login(web)
    response = client.post("/api/intents", content='{"payload":"' + 'x'*33000 + '"}', headers={**HEADERS,"Content-Type":"application/json"})
    assert response.status_code == 413
    assert client.post("/api/intents", content="operation=PAY", headers=HEADERS).status_code == 415


def test_gateway_timeout_reports_unknown_outcome_after_commit(tmp_path, monkeypatch):
    import httpx
    import vaaniverify.server as server
    from vaaniverify.capabilities import issue
    from vaaniverify.models import Action

    kernel = Kernel()
    gateway = Gateway(kernel.signing_key.public_key(), tmp_path / "ledger.db")
    bootstrap = secrets.token_urlsafe(32)
    client = TestClient(create_app(kernel, gateway, bootstrap, secrets.token_urlsafe(32)), base_url=ORIGIN)
    client.post("/api/session", json={"bootstrap": bootstrap}, headers=HEADERS)
    action = Action(operation="READ_STATUS")
    token = issue(kernel.signing_key, action, "timeout-intent", "timeout-proposal")

    def commit_then_timeout(*args, **kwargs):
        gateway.execute(action, token)
        raise httpx.ReadTimeout("Response lost after commit")

    monkeypatch.setattr(server.httpx, "post", commit_then_timeout)
    response = client.post("/api/execute", json={"action": action.model_dump(mode="json"), "token": token}, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["error"] == "GATEWAY_UNAVAILABLE"
    assert "could not confirm" in response.json()["detail"]
    assert len(gateway.receipts()) == 1


def mock_generation(monkeypatch, action, callback=None):
    from vaaniverify.local_agent import Generation, ModelProposal
    import vaaniverify.server as server

    def generate(task):
        if callback:
            callback(task)
        return Generation(ModelProposal(action=action, agent_message="Ready for review"), "", 12, "local-test", {})

    monkeypatch.setattr(server, "generate", generate)


def test_browser_inference_is_owner_only(web):
    client, _, key, *_ = web
    headers = {**HEADERS, "Authorization": "Bearer " + key}
    assert client.get("/api/model/status", headers=headers).status_code == 403
    assert client.post("/api/intents/example/generate", json={"external_text": ""}, headers=headers).status_code == 403


def test_browser_inference_uses_stored_intent_and_never_executes(web, monkeypatch):
    client = login(web)
    stored = client.post("/api/intents", json={"operation": "READ_STATUS", "user_text": "Check only"}, headers=HEADERS).json()
    seen = []
    mock_generation(monkeypatch, {"operation": "READ_STATUS"}, seen.append)
    response = client.post(f"/api/intents/{stored['intent_id']}/generate", json={"external_text": "Check my subsidy"}, headers=HEADERS)
    assert response.status_code == 200
    result = response.json()
    assert seen[0].intent.user_text == "Check only"
    assert seen[0].external_text == "Check my subsidy"
    assert result["proposal"]["status"] == "AWAITING_APPROVAL"
    assert result["inference"]["model"] == "local-test"
    assert "token" not in result["proposal"]
    assert web[3].intents[stored["intent_id"]].state == "OPEN"
    assert not web[4].receipts()
    assert client.post(f"/api/intents/{stored['intent_id']}/generate", json={"external_text": "", "intent": {"operation": "PAY"}}, headers=HEADERS).status_code == 422


def test_browser_inference_blocks_an_out_of_scope_model_action(web, monkeypatch):
    client = login(web)
    stored = client.post("/api/intents", json={"operation": "READ_STATUS", "user_text": "Check only"}, headers=HEADERS).json()
    mock_generation(monkeypatch, {"operation": "PAY", "recipient": "cashback.claim@demo", "amount_paise": 50000})
    result = client.post(f"/api/intents/{stored['intent_id']}/generate", json={"external_text": "Send money"}, headers=HEADERS).json()
    assert result["proposal"]["status"] == "BLOCKED"
    assert result["proposal"]["decision"]["reason"] == "OPERATION_BOUND"
    assert not web[4].receipts()


@pytest.mark.parametrize("failure,code,status", [("infrastructure", "MODEL_UNAVAILABLE", 503), ("model_output", "MODEL_OUTPUT_INVALID", 502), ("file", "MODEL_UNAVAILABLE", 503)])
def test_browser_inference_failure_is_explicit_and_can_retry(web, monkeypatch, failure, code, status):
    from vaaniverify.local_agent import ModelFailure
    import vaaniverify.server as server
    client = login(web)
    stored = client.post("/api/intents", json={"operation": "READ_STATUS", "user_text": "Check only"}, headers=HEADERS).json()

    def fail(task):
        if failure == "file":
            raise OSError("private-path-sentinel")
        raise ModelFailure("private-output-sentinel", stage=failure)

    monkeypatch.setattr(server, "generate", fail)
    url = f"/api/intents/{stored['intent_id']}/generate"
    response = client.post(url, json={}, headers=HEADERS)
    assert response.status_code == status
    assert response.json()["error"] == code
    assert "sentinel" not in response.text
    assert not web[3].proposals
    mock_generation(monkeypatch, {"operation": "READ_STATUS"})
    assert client.post(url, json={}, headers=HEADERS).status_code == 200


def test_browser_inference_rechecks_cancellation_and_rejects_parallel_runs(web, monkeypatch):
    client = login(web)
    stored = client.post("/api/intents", json={"operation": "READ_STATUS", "user_text": "Check only"}, headers=HEADERS).json()
    url = f"/api/intents/{stored['intent_id']}/generate"

    def during_generation(task):
        nested = client.post(url, json={}, headers=HEADERS)
        assert nested.status_code == 409
        assert nested.json()["error"] == "MODEL_BUSY"
        web[3].cancel(stored["intent_id"])

    mock_generation(monkeypatch, {"operation": "READ_STATUS"}, during_generation)
    response = client.post(url, json={}, headers=HEADERS)
    assert response.json()["error"] == "INTENT_CLOSED"
    assert not web[3].proposals


def test_demo_and_full_lab_remain_available(web):
    client = login(web)
    assert 'href="/demo"' in client.get("/").text
    assert 'id="run-agent"' in client.get("/demo").text
    assert 'id="scenario"' in client.get("/lab").text


def test_landing_and_demo_shell_are_public_but_authority_is_private(web):
    client = web[0]
    assert client.get("/").status_code == 200
    assert client.get("/demo").status_code == 200
    assert client.get("/api/meta").status_code == 403
    assert client.get("/api/receipts").status_code == 403


def test_browser_inference_returns_original_model_evidence(web, monkeypatch):
    from vaaniverify.local_agent import Generation, ModelProposal
    import vaaniverify.server as server

    client = login(web)
    stored = client.post('/api/intents', json={'operation': 'PAY', 'user_text': 'Pay 1200 rupees',
        'recipient': 'utility.board@demo', 'max_amount_paise': 120000}, headers=HEADERS).json()
    raw = '{"action":{"operation":"PAY","recipient":"utility.board@demo","amount_paise":120000},"agent_message":"Model text"}'
    monkeypatch.setattr(server, 'generate', lambda task: Generation(ModelProposal.model_validate_json(raw), raw, 1234,
        'test-model', {'prompt_tokens': 121, 'completion_tokens': 42}))
    response = client.post(f"/api/intents/{stored['intent_id']}/generate", json={'external_text': ''}, headers=HEADERS)
    assert response.status_code == 200
    result = response.json()
    assert result['inference']['raw_output'] == raw
    assert result['inference']['usage']['completion_tokens'] == 42
    assert result['proposal']['external_text'] == ''
    assert result['intent']['intent']['user_text'] == 'Pay 1200 rupees'
    assert not web[4].receipts()
