import hashlib

import httpx
import pytest

from scripts import local_model
from vaaniverify import evaluate_model
from vaaniverify.local_agent import ModelFailure


def test_corrupt_full_download_is_quarantined_and_next_attempt_recovers(tmp_path, monkeypatch):
    monkeypatch.setattr(local_model, "CACHE", tmp_path)
    asset = {"name": "tiny.gguf", "url": "https://models.invalid/tiny", "bytes": 3,
             "sha256": hashlib.sha256(b"abc").hexdigest()}
    (tmp_path / "tiny.gguf.part").write_bytes(b"bad")
    with pytest.raises(RuntimeError, match="Rerun setup"):
        local_model.download(asset)
    assert len(list(tmp_path.glob("*.bad-*"))) == 1
    real_client = httpx.Client
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, content=b"abc")

    monkeypatch.setattr(local_model.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs))
    assert local_model.download(asset).read_bytes() == b"abc"
    assert len(calls) == 1
    assert "range" not in calls[0].headers


def test_model_service_failure_does_not_replace_real_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluate_model, "ROOT", tmp_path)
    output = tmp_path / "existing.json"
    output.write_text('{"previous":"real evidence"}', encoding="utf-8")

    def unavailable(*args, **kwargs):
        raise ModelFailure("offline", stage="infrastructure")

    monkeypatch.setattr(evaluate_model, "generate", unavailable)
    with pytest.raises(RuntimeError, match="not overwritten"):
        evaluate_model.run_pilot(output)
    assert output.read_text(encoding="utf-8") == '{"previous":"real evidence"}'
