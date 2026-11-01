# VaaniVerify

**Every action, understood.** A multilingual consent boundary for untrusted agents acting on synthetic UPI-style payments, recurring mandates, and document sharing.

The agent may propose an action and tell any story about it. It cannot register user authority, write the trusted confirmation, approve a proposal, or sign an execution capability. VaaniVerify checks the actual action against structured user intent, renders its meaning using fixed language templates, and signs the exact approved payload. A separate gateway process verifies the signature before recording a mock effect.

This is a **local security prototype**, built during the India Agentic AI Security Hackathon on 31 October 2026 by **Team Bifrost: Kunal Sharma**, from **Indraprastha Institute of Information Technology Delhi**, participating **online**. It has no production DPI connections, real transactions, real identifiers, paid API dependencies, or LLM in its trusted path. An optional local Qwen agent proposes actions outside that boundary; the core app works without a model download.

[Technical report](https://raw.githubusercontent.com/kunallll17/SAFL_Submission/main/output/pdf/TeamBifrost_Report.pdf) | [Demo video - 25 seconds](https://raw.githubusercontent.com/kunallll17/SAFL_Submission/main/brag.mp4) | [Submission ZIP](https://raw.githubusercontent.com/kunallll17/SAFL_Submission/main/output/source/TeamBifrost_Submission.zip) | [Submission responses](docs/SUBMISSION_DRAFT.md)

The video animates implemented controls and cites an earlier retained model pilot. The report and results below describe the current run; [video credits and evidence](docs/VIDEO_CREDITS.md) explain the difference.

![VaaniVerify security lab](evidence/screenshots/desktop-blocked.jpg)

## Run on Windows (CMD)

Requires Python 3.11 or newer. Initial setup downloads the pinned dependencies from PyPI; subsequent use is local.

```bat
git clone https://github.com/kunallll17/SAFL_Submission.git
cd SAFL_Submission
setup.bat
launch.bat
```

`launch.bat` starts the console at `http://127.0.0.1:8765` and a separate mock gateway at `http://127.0.0.1:8766`, then opens a private launch URL. Keep its terminal running. Press **Ctrl+C** to stop the services. If ports are occupied:

```bat
launch.bat --port 8875 --gateway-port 8876
```

For Linux/macOS or another checkout location:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m vaaniverify
```

Run setup in your own checkout or extracted submission folder; virtual environments and downloaded model binaries are not distributed.

### Private console access

The launcher writes a **single-use private URL** to `.runtime/console-url.txt`. Its fragment is exchanged for an HttpOnly, SameSite=Strict owner cookie and removed from the address bar. Open that link if automatic browser launch is disabled (`--no-browser`). Reuse the authenticated browser after the exchange. A different browser needs a fresh launcher session. Do not publish `.runtime/`, which also contains the scoped agent credential and local demo receipts. The private signing key stays in memory and rotates on restart. Existing receipt records remain.

## Explore the prototype

The home page introduces the consent boundary with an interactive illustration. **Open demo** leads to the guided task, review and result experience at `/demo`. Choose an example or edit the task and its permission, then press **Run agent**. With the local Qwen server running, the website generates a real proposal directly; there is no JSON download, third-terminal command or inbox refresh in this flow. Generation never approves or executes. Confirm the exact direction, recipient, amount and terms to execute in the mock gateway, or reject the action. Completed receipts appear under **Activity**.

Editing an example task clears its inherited external message; a message you write yourself is preserved. **Inspect this model run** shows the task, external message, raw model JSON, token usage and timing. The amount field is a maximum, not a claim that any smaller proposal satisfies your sentence. See [manual functional tests and verified limitations](docs/FUNCTIONAL_VERIFICATION.md).

The local model must be started once per session with `.venv\Scripts\python.exe scripts\local_model.py serve`. If it is unavailable, the demo page explains the connection problem without substituting a preset action. The **Security lab** at `/lab` retains the complete model-free scenarios, evidence, JSON editor, attack tools, speech playback and external-agent integration described below.

1. **Subsidy trap:** choose it and press **Inspect action**. The user selected read-only; the agent proposes a debit. The kernel blocks it before approval.
2. **Legitimate bill:** inspect an external bill recipient. Choose the outgoing direction, type `utility.board@demo` and `500`, accept the displayed terms, then sign and execute in the sandbox. A real Ed25519 signature is verified by the other process.
3. **Replay / payee swap:** use the receipt's attack buttons. The gateway rejects both. No real money moves.
4. **After-approval swap:** sign the legitimate action. The demo sends a changed recipient to the gateway, which rejects it. The original signed action can still execute before expiry.
5. **Silent Autopay / document scope:** test operation escalation, extra documents, purpose changes and retention changes. Switch among English, Hindi, Hinglish and Tamil confirmations.
6. **Custom payload:** edit the user constraint and malicious proposal in the expandable JSON editor. Unknown fields, non-synthetic handles, ambiguous numeric types and irrelevant operation fields fail validation.
7. **Evidence / Trust boundary / Audit receipts:** inspect the method, policy comparisons, implementation assumptions and local receipt chain.

All confirmation templates are authored, not automatic translations. Browser speech uses only an installed voice marked local by the browser; the app reports when one is unavailable. Audio quality, multilingual comprehension, and a screen-reader user study have **not** been evaluated.

## Connect your own agent

Open the **Security lab**, expand **Create a trusted task for your own agent**, select the operation and exact scope, and create the task. The console displays its intent ID and a command:

```bat
.venv\Scripts\python.exe -m vaaniverify.agent_client --intent-id YOUR_INTENT_ID --proposal examples/agent_proposal.json
```

The sample is a proposal-only HTTP adapter, **not an LLM**. A model can produce the same schema upstream. It receives a separate bearer credential from `.runtime/agent-key.txt`. Give a deployed agent only this credential, never filesystem access to the trusted service or the owner session. Refresh the owner console's **Agent proposal inbox**, review the proposal, and authorize there. Only the trusted console issues and delivers the capability to the gateway.

### Optional real local agent

The included `local_agent` uses Qwen2.5-1.5B-Instruct Q4_K_M through a pinned llama.cpp CPU server. It has a single proposal tool, no approval/execution tool, no cloud dependency and no paid API. Its explanation can still be wrong; the independent kernel remains authoritative.

On Windows, download the optional runtime once (about 1.14 GB), then keep it running in a separate CMD terminal:

```cmd
.venv\Scripts\python.exe scripts\local_model.py setup
.venv\Scripts\python.exe scripts\local_model.py serve
```

Open **Demo**, enter the task, its permission and the untrusted external message, then click **Run agent**. Review the proposal directly on the page. For a CLI integration, the **Security lab** still offers **Download agent task JSON** and the proposal inbox. Save the downloaded file as `agent-task.json` in the project folder and run the command shown beside the task ID. To generate a proposal without submitting it:

```cmd
.venv\Scripts\python.exe -m vaaniverify.local_agent --task examples\model_task.json
```

To reproduce the separate real-model pilot while the model server is running:

```cmd
.venv\Scripts\python.exe -m vaaniverify.evaluate_model
```

Current pilot after the custom-task fix: **32/32 valid proposals; 9/16 attacker-goal proposals; 0/16 attacker-goal executions; 15/16 expected benign executions.** The remaining benign failure is an invented recipient in the explicitly delegated external-bill case. The earlier prompt achieved 16/16 on these stock benign cases but failed the newly tested custom decimal/document tasks. Its report is retained in `evidence/model_pilot_before_task_fix.json`. The current prompt passes six targeted custom-task regressions, but the delegated-recipient regression remains failing. These are reused authored inputs, not held-out evidence of broad model accuracy.

The model server binds only to `127.0.0.1:8770`, disables its web UI, and requires a generated local credential. Model and agent credentials are separate and never included in model prompts. Its exact weights/runtime hashes are in `evidence/local_model_runtime.json`; prompts, raw outputs, invalid responses and per-case outcomes are in `evidence/model_pilot.json`. This is a small exploratory pilot on one quantized model, with scripted user approval, not a frontier-model or human-comprehension benchmark. The model weights and binaries are excluded from the source archive. `Ctrl+C` stops a manually launched model server.

`POST /api/agent/proposals` accepts `{intent_id, action, agent_message, external_text}`. Client-provided provenance labels are forbidden. Other owner APIs reject this credential. There is no endpoint through which an agent can create or approve user intent.

## Reproduce the evidence

```bat
verify.bat
```

Or run each check separately:

```bat
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m vaaniverify.evaluate
.venv\Scripts\python.exe -m vaaniverify.mutations
```

The evaluator writes `evidence/benchmark.json`, `benchmark.csv` and `scenarios.json`. It records runtime details, source hashes, corpus hash, per-case reasons and latency scope. The mutation runner writes `evidence/mutations.json` with a fixed seed and every outcome.

### Measured authored-corpus outcomes

The 80 cases contain **20 semantic templates multiplied by four language variants**, with 40 benign and 40 adversarial cases. They are not 80 independently discovered attacks. Approvals are fixtures; there are no human participants or sampled model responses.

| Implemented policy | Modeled attacks executed | Legitimate actions blocked |
|---|---:|---:|
| Unguarded, generic approval simulation | 40 / 40 | 0 / 40 |
| Operation check only | 32 / 40 | 0 / 40 |
| Reject all external parameters | 0 / 40 | 24 / 40 |
| Full policy without execution binding | 4 / 40 | 0 / 40 |
| **VaaniVerify** | **0 / 40** | **0 / 40** |

The separate generated-capability suite rejected **1,000 / 1,000 mutations** across amount, recipient, operation, schedule, count, document scope, purpose, retention, mandate ID and signature. All **1,000 original signed actions remained executable** after their mutations were rejected. Generated trials are not independent real-world exploits.

The Python suite tests authorization, strict validation, concurrent replay, restart persistence, concurrent approval, expiry after database-lock contention, agent flood isolation, signature/claim changes, cancellation, HTTP role separation, CSRF/Host defenses, and uncertain execution outcomes. A dependency emits one Starlette/httpx deprecation warning; this is recorded rather than hidden. Timing values vary by run and exclude model, network, browser and human latency. No claim of production fraud prevention follows from these results.

## Architecture

```text
Owner browser (private session)
    │ structured intent: operation + constraints
    ▼
Trusted consent service :8765 ◄── scoped bearer ── Untrusted agent
    │                           proposed action + untrusted explanation
    ├── deterministic policy against stored intent
    ├── fixed template from validated action, four languages
    ├── exact direction / recipient / amount / terms confirmation
    └── Ed25519 capability: full action digest + intent + audience + expiry
              │
              ▼
Separate mock gateway :8766 (PUBLIC KEY ONLY)
    ├── verifies signature, full action, direction, audience, template, expiry
    └── SQLite transaction: consume nonce + intent and commit mock receipt
```

The authoritative intent is the structured owner selection, **not a lexical interpretation of the user's sentence**. A language hint and explanation warnings are diagnostic only. External field provenance means how a field relates to the stored constraint; it is not claimed as a complete information-flow taint analysis.

Supported operations: `READ_STATUS`, `PAY`, `MANDATE`, `SHARE`, `CANCEL_MANDATE`. Money is bounded integer paise. Recurring requests bind amount, frequency and payment count. Sharing requests bind document set, recipient, purpose and requested retention. Identifiers must be synthetic ASCII handles ending in `@demo`; free-text merchant names are excluded from the trusted sentence.

One intent authorizes one action, not an unlimited series of separately signed requests. Intents expire after 15 minutes, proposal review after at most 3 minutes, and capabilities after 60 seconds. Cancellation works before issuance. An already-issued capability cannot be revoked remotely in this prototype; it must expire or be spent. SQLite consumption and the mock side effect are the same transaction. A real provider needs transactional/idempotency integration to preserve this property.

## Source map

| File | Responsibility |
|---|---|
| `models.py` | Strict, operation-specific payload and intent schemas |
| `policy.py` | User-scope invariants and non-authoritative wording diagnostics |
| `compiler.py` | Canonical serialization, action digests and four language templates |
| `kernel.py` | Intent/proposal lifecycle, exact approval and signing authority |
| `capabilities.py` | Ed25519 capability format, issuance and verification |
| `gateway.py` | Public-key validation and atomic SQLite mock execution |
| `server.py` | Owner/agent authentication, local HTTP boundary and inbox |
| `__main__.py`, `gateway_runner.py` | Two-process loopback launcher |
| `scenarios.py`, `evaluate.py`, `mutations.py` | Authored corpus, baselines, mutation experiments |
| `web/` | Buildless, responsive console; untrusted data rendered as text |
| `tests/` | Focused regression and API tests |
| `docs/` | Threat model, review evidence and submission draft |

All Python module paths above are under `vaaniverify/`.

## Security and limitations

Read [the threat model](docs/THREAT_MODEL.md). This prototype protects against untrusted proposals under separate owner/signing authority. It does not protect a compromised browser, stolen owner cookie, malicious local process, signing-service compromise, or a user deliberately approving the attacker's exact request. It does not enforce a recipient's deletion or use of documents. It is not a UPI, DigiLocker, Aadhaar, bank, or government service and should not be deployed publicly unchanged.

The local ledger is hash-linked but not independently anchored. A privileged attacker can rewrite and rehash the entire database. The template hash binds the reviewed software version; it does not prove translation correctness. A directional challenge is not a proof of comprehension. No security decision relies on the agent's explanation or a hidden system prompt.

## Submission materials

- `docs/SUBMISSION_DRAFT.md`: paste-ready technical responses with confirmed team details; solo team details, background and consent choices are complete; contact details are entered privately in the form.
- `output/pdf/TeamBifrost_Report.pdf`: nine-page technical report, within the contest's ten-page limit.
- `output/source/TeamBifrost_Submission.zip`: current source, report, demo video and evidence package.
- `brag.mp4`: 25-second product demonstration; credits and measurement context are in `docs/VIDEO_CREDITS.md`.
- `evidence/`: reproducible JSON/CSV results and browser screenshots.
- `THIRD_PARTY_NOTICES.md`: dependency versions and licences.
- `docs/VERIFICATION.md`: what was actually checked and what remains unverified.

The public submission repository is https://github.com/kunallll17/SAFL_Submission. The contest form has not been submitted. The package excludes runtime credentials, private contacts, virtual environments and model weights. Kunal Sharma has confirmed the responsible-testing declarations and both organizer publicity permissions; repository publication does not grant organizer permissions.

## Context and references

- [SAFL hackathon and judging rubric](https://www.secureaifutureslab.com/events/india-ai-agentic-hackathon).
- [MAPS: A Multilingual Benchmark for Agent Performance and Security](https://aclanthology.org/2026.findings-eacl.42/): multilingual evaluation context; its data was not used in this corpus.
- [Design Patterns for Securing LLM Agents against Prompt Injections](https://arxiv.org/abs/2506.08837): architectural isolation context. This project does not claim to invent capability security or deterministic authorization.
- [RFC 8032: EdDSA](https://datatracker.ietf.org/doc/html/rfc8032): Ed25519 signature specification. Implementation uses the established `cryptography` library.
