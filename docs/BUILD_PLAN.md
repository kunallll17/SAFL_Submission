# VaaniVerify build plan

Team Bifrost. Team size: one (solo submission).

## Intended result

A local, zero-paid-API prototype demonstrating that an untrusted agent cannot turn a read/receive task into a payment, create recurring consent from a one-off payment, or alter an approved action. Four deterministic confirmation languages: English, Hindi, Hinglish, Tamil. Synthetic identifiers only, ending in `@demo`; no real DPI integration.

## Design choices

- Python/FastAPI + a buildless HTML/CSS/JS console. This avoids a frontend build dependency and keeps the security code easy to inspect.
- Structured user intent is authoritative. Natural language classification is advisory and never grants write authority. A lexical matcher cannot establish consent reliably.
- The agent can propose actions and explanations. It cannot author provenance, register trusted intent, approve proposals, or mint capabilities. Browser owner sessions and agent bearer credentials have separate permissions.
- Kernel compares operation, amount, recipient, recurring terms, and document scopes with the stored intent. External bill fields can proceed only within an explicitly selected operation and require exact field confirmation in the trusted UI. Agent explanations are displayed as untrusted evidence, never as consent.
- A deterministic compiler renders typed payloads. Untrusted merchant names are omitted from the approval sentence, rather than filtered by a fragile denylist. Identifiers are restricted to synthetic ASCII handles and shown separately.
- Ed25519 capabilities cover canonical typed payloads, direction, intent/proposal IDs, audience, subject, nonce, issue/expiry times, and template hash. The separate mock gateway has only the public key. Atomic SQLite nonce consumption and ledger insertion prevent replay, including concurrent requests and gateway restarts.
- Single-use approvals consume the intent budget; repeat proposals cannot multiply one user's authorization. Expiry and cancellation fail closed.
- Baselines are explicitly implemented policy simulations: unguarded, operation-only, strict external-source rejection. No fabricated LLM judge or fabricated user study.

## Alternatives considered

An LLM security judge adds prompt-injection risk and paid/model setup dependencies without enforcing authorization. A translated warning with a yes/no button leaves parameter mutation and original-intent escalation unresolved. A blanket ban on external parameters prevents legitimate bill payment. The selected design separates intent, exact-action confirmation, and execution binding.

## Delivery sequence

1. Typed models, policy kernel, compiler, signed tokens, atomic mock gateway.
2. Regression tests including scope escalation, forgery, replay, expiry, cancellation, Unicode, taint spoofing, and concurrent execution.
3. Synthetic multilingual scenario corpus, policy baselines, mutation trials, JSON/CSV evidence.
4. Local interactive approval console with adversarial playground, audit receipts, benchmark explorer, language switch and optional device-local speech.
5. Live API/browser verification, reproducible README, threat model, submission answers, <=10-page report PDF, source archive.

## Explicit evidence boundaries

No claim of winning, production readiness, universal language understanding, or proven human comprehension. Choosing a direction is an interaction design hypothesis, not proof a user understands. No automatic translation or speech recognition in the trusted path. Audio availability depends on locally installed browser voices. Synthetic benchmarks measure this kernel, not real-model compromise probability. No public upload, contest submission, or video production is part of this build.
