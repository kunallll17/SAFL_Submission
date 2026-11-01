import json
import secrets
import sys

from vaaniverify import agent_client


def test_proposal_adapter_output_is_portable_json(tmp_path, monkeypatch, capsys):
    proposal = tmp_path / "proposal.json"
    proposal.write_text(json.dumps({"action": {"operation": "READ_STATUS"}}), encoding="utf-8")
    key = tmp_path / "agent-key.txt"
    key.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["agent_client", "--intent-id", "synthetic-intent-id", "--proposal", str(proposal), "--key-file", str(key)])
    calls = []

    class Response:
        def json(self):
            return {"status": "AWAITING_APPROVAL", "confirmation": "₹500 पैसा जाएगा"}

        def raise_for_status(self):
            pass

    def post(url, **kwargs):
        calls.append(url)
        return Response()

    monkeypatch.setattr(agent_client.httpx, "post", post)
    agent_client.main()
    output = capsys.readouterr().out
    output.encode("ascii")
    assert json.loads(output)["confirmation"] == "₹500 पैसा जाएगा"
    assert calls == ["http://127.0.0.1:8765/api/agent/proposals"]
