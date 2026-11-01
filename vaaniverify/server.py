"""Owner console and least-privilege proposal API. Loopback demo only."""

import json
import secrets
import threading
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from .capabilities import SecurityError, b64
from .compiler import TEMPLATE_HASH
from .gateway import Gateway, ROUTES
from .kernel import Kernel
from .local_agent import AgentTask, ModelFailure, generate
from .models import Approval, Execution, Intent, ProposalInput, StrictModel
from .scenarios import SCENARIOS

ROOT = Path(__file__).resolve().parents[1]


class SessionRequest(StrictModel):
    bootstrap: str = Field(min_length=30, max_length=200, pattern=r"^[A-Za-z0-9_-]+$")


class ScenarioRequest(StrictModel):
    scenario_id: str = Field(max_length=100)


class InferenceRequest(StrictModel):
    external_text: str = Field(default="", max_length=4000)


def create_app(kernel: Kernel, gateway: Gateway, bootstrap: str, agent_key: str,
               origin="http://127.0.0.1:8765", gateway_url="http://127.0.0.1:8766", execution_transport=None):
    app = FastAPI(title="VaaniVerify", docs_url=None, redoc_url=None, openapi_url=None)
    session = secrets.token_urlsafe(32)
    bootstrap_used = False
    inference_lock = threading.Lock()
    host = origin.split("://", 1)[1]

    @app.middleware("http")
    async def browser_boundary(request: Request, call_next):
        if request.headers.get("host") != host:
            return JSONResponse({"error": "INVALID_HOST", "detail": "Use the local console address."}, status_code=400)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            # Agent API is bearer-authenticated, and never accepts browser cookies.
            if not request.url.path.startswith("/api/agent/"):
                if request.headers.get("origin") != origin or request.headers.get("x-vaani-request") != "1":
                    return JSONResponse({"error": "ORIGIN_REJECTED", "detail": "Use the trusted console to approve actions."}, status_code=403)
            if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
                return JSONResponse({"error": "JSON_REQUIRED"}, status_code=415)
            parts, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 32768:
                    return JSONResponse({"error": "REQUEST_TOO_LARGE"}, status_code=413)
                parts.append(chunk)
            request._body = b"".join(parts)
        response = await call_next(request)
        response.headers.update({
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "DENY", "Cache-Control": "no-store",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        })
        return response

    @app.exception_handler(SecurityError)
    async def security_error(request, exc):
        return JSONResponse({"error": exc.code, "detail": exc.message},
                            status_code=503 if exc.code == "GATEWAY_UNAVAILABLE" else 403)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, exc):
        # Exclude input values and nonserializable exception contexts from API errors.
        errors = [{"field": ".".join(map(str, error["loc"])), "message": error["msg"]} for error in exc.errors()]
        return JSONResponse({"error": "INVALID_INPUT", "detail": "The action does not match the accepted schema.", "fields": errors}, status_code=422)

    def owner(request: Request):
        value = request.cookies.get("vv_owner", "")
        if not value or not value.isascii() or not secrets.compare_digest(value, session):
            raise SecurityError("OWNER_SESSION_REQUIRED", "Open the private console link created by launch.bat.")

    def agent(request: Request):
        value = request.headers.get("authorization", "")
        if not value.isascii() or not secrets.compare_digest(value, "Bearer " + agent_key):
            raise SecurityError("AGENT_KEY_REQUIRED", "The agent proposal API requires its scoped bearer credential.")

    @app.get("/")
    def index():
        return FileResponse(ROOT / "web" / "index.html")

    @app.get("/demo")
    def demo():
        return FileResponse(ROOT / "web" / "demo.html")

    @app.get("/lab")
    def lab():
        return FileResponse(ROOT / "web" / "lab.html")

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "local-synthetic", "version": "0.1.0"}

    @app.post("/api/session")
    def create_session(body: SessionRequest):
        nonlocal bootstrap_used
        with kernel.lock:
            if bootstrap_used or not secrets.compare_digest(body.bootstrap, bootstrap):
                raise SecurityError("INVALID_BOOTSTRAP", "This private launch link is invalid or already exchanged. Use the existing browser session or restart the launcher.")
            bootstrap_used = True
        response = JSONResponse({"authenticated": True})
        response.set_cookie("vv_owner", session, httponly=True, samesite="strict", max_age=14400, path="/")
        return response

    @app.get("/api/meta", dependencies=[Depends(owner)])
    def metadata():
        return {"mode": "synthetic", "template_hash": TEMPLATE_HASH,
                "public_key": b64(kernel.signing_key.public_key().public_bytes_raw()),
                "languages": ["en", "hi", "hinglish", "ta"], "case_count": len(SCENARIOS),
                "execution_boundary": "separate public-key-only gateway", "gateway_url": gateway_url}

    @app.get("/api/scenarios", dependencies=[Depends(owner)])
    def scenarios():
        return SCENARIOS

    @app.post("/api/intents", dependencies=[Depends(owner)])
    def create_intent(body: Intent):
        return kernel.create_intent(body)

    @app.get("/api/model/status", dependencies=[Depends(owner)])
    def model_status():
        try:
            response = httpx.get("http://127.0.0.1:8770/health", timeout=2, trust_env=False)
            ready = response.status_code == 200 and (ROOT / ".runtime/model-key.txt").is_file()
        except httpx.HTTPError:
            ready = False
        return {"ready": ready, "busy": inference_lock.locked(), "name": "Qwen2.5 · on this device"}

    @app.post("/api/intents/{intent_id}/generate", dependencies=[Depends(owner)])
    def generate_proposal(intent_id: str, body: InferenceRequest):
        # The owner starts inference; the model receives only the stored scope
        # and untrusted text. It still has no signing or execution authority.
        if not inference_lock.acquire(blocking=False):
            return JSONResponse({"error": "MODEL_BUSY", "detail": "The local agent is working on another request. Try again shortly."}, status_code=409)
        try:
            with kernel.lock:
                record = kernel.active_intent(intent_id)
                task = AgentTask(intent=record.value, external_text=body.external_text)
            result = generate(task)
            # Rechecks expiry/cancellation after inference, outside the kernel lock.
            proposal = kernel.propose(ProposalInput(intent_id=intent_id, action=result.proposal.action,
                                                   agent_message=result.proposal.agent_message,
                                                   external_text=body.external_text))
            return {"intent": {"intent_id": intent_id, "intent": task.intent.model_dump(mode="json")},
                    "proposal": proposal, "inference": {"model": result.model, "elapsed_ms": result.elapsed_ms,
                                                        "usage": result.usage, "raw_output": result.raw_text}}
        except ModelFailure as exc:
            unavailable = exc.stage == "infrastructure"
            return JSONResponse({"error": "MODEL_UNAVAILABLE" if unavailable else "MODEL_OUTPUT_INVALID",
                                 "detail": "The local model is not responding. Check that its server is running, then retry." if unavailable
                                 else "The model did not produce a valid action. Nothing was approved or executed. You can retry."},
                                status_code=503 if unavailable else 502)
        except OSError:
            return JSONResponse({"error": "MODEL_UNAVAILABLE", "detail": "The local model is not configured. Start the local model server, then retry."}, status_code=503)
        finally:
            inference_lock.release()

    @app.get("/api/proposals", dependencies=[Depends(owner)])
    def proposal_inbox():
        with kernel.lock:
            pending = [value for value in kernel.proposals.values()
                       if value["status"] == "AWAITING_APPROVAL" and value["expires_at"] > int(kernel.clock())]
            return [{"proposal_id": p["proposal_id"], "operation": p["action"]["operation"],
                     "recipient": p["action"]["recipient"], "expires_at": p["expires_at"]} for p in pending[-50:]]

    @app.get("/api/proposals/{proposal_id}", dependencies=[Depends(owner)])
    def read_proposal(proposal_id: str):
        import copy
        with kernel.lock:
            proposal = kernel.proposals.get(proposal_id)
            if not proposal:
                raise SecurityError("UNKNOWN_PROPOSAL", "This proposal is no longer available.")
            record = kernel.intents[proposal["intent_id"]]
            return {"intent": {"intent_id": proposal["intent_id"], "intent": record.value.model_dump(mode="json")},
                    "proposal": copy.deepcopy(proposal)}

    @app.post("/api/proposals", dependencies=[Depends(owner)])
    def propose(body: ProposalInput):
        return kernel.propose(body)

    @app.post("/api/agent/proposals", dependencies=[Depends(agent)])
    def agent_propose(body: ProposalInput):
        return kernel.propose(body)

    @app.post("/api/demo", dependencies=[Depends(owner)])
    def run_demo(body: ScenarioRequest):
        case = next((s for s in SCENARIOS if s["id"] == body.scenario_id), None)
        if not case:
            raise SecurityError("UNKNOWN_SCENARIO", "Select an available synthetic scenario.")
        intent = kernel.create_intent(Intent.model_validate(case["intent"]))
        proposal = kernel.propose(ProposalInput(intent_id=intent["intent_id"], action=case["action"],
                                               agent_message=case["agent_message"], external_text=case["external_text"]))
        return {"intent": intent, "proposal": proposal, "scenario_id": case["id"]}

    @app.post("/api/proposals/{proposal_id}/approve", dependencies=[Depends(owner)])
    def approve(proposal_id: str, body: Approval):
        return kernel.approve(proposal_id, body)

    @app.post("/api/intents/{intent_id}/cancel", dependencies=[Depends(owner)])
    def cancel(intent_id: str):
        return kernel.cancel(intent_id)

    @app.post("/api/execute", dependencies=[Depends(owner)])
    def execute(body: Execution):
        if execution_transport:
            return execution_transport(body.action, body.token)
        try:
            response = httpx.post(gateway_url + ROUTES[body.action.operation], json=body.model_dump(mode="json"), timeout=5, trust_env=False)
            result = response.json()
            if response.status_code != 200:
                raise SecurityError(result.get("error", "GATEWAY_REJECTED"), result.get("detail", "Gateway refused this action."))
            return result
        except (httpx.HTTPError, ValueError) as exc:
            raise SecurityError("GATEWAY_UNAVAILABLE", "The mock gateway could not confirm execution. Inspect the ledger before retrying; reuse the same token.") from exc

    @app.get("/api/receipts", dependencies=[Depends(owner)])
    def receipts():
        return {"receipts": gateway.receipts(), "audit": gateway.audit()}

    @app.get("/api/evidence", dependencies=[Depends(owner)])
    def evidence():
        path = ROOT / "evidence" / "benchmark.json"
        if not path.exists():
            return {"available": False, "detail": "Run python -m vaaniverify.evaluate to generate measured evidence."}
        return {"available": True, **json.loads(path.read_text(encoding="utf-8"))}

    @app.get("/api/model-evidence", dependencies=[Depends(owner)])
    def model_evidence():
        path = ROOT / "evidence" / "model_pilot.json"
        if not path.exists():
            return {"available": False, "detail": "The optional local-model pilot has not been run."}
        return {"available": True, **json.loads(path.read_text(encoding="utf-8"))}

    app.mount("/assets", StaticFiles(directory=ROOT / "web"), name="assets")
    return app
