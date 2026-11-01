# VaaniVerify - SAFL submission draft

**Team Bifrost** is a solo submission by **Kunal Sharma**, **Indraprastha Institute of Information Technology Delhi**, participating **online**. **VaaniVerify** is the project name. The prototype has one disclosed live-model regression. Private contact details are intentionally omitted from this public copy and supplied separately in the submission form.

## 1. Team information

| Field | Answer |
|---|---|
| Team name | Team Bifrost |
| Primary contact name | Kunal Sharma |
| Registered contact email | TEAM TO FILL PRIVATELY |
| Phone / WhatsApp with country code | TEAM TO FILL PRIVATELY |
| Team size | 1 |

## 2. Team members

| Field | Member 1 / primary contact |
|---|---|
| Full name | Kunal Sharma |
| Email | TEAM TO FILL PRIVATELY |
| Institution / organisation | Indraprastha Institute of Information Technology Delhi |
| Participation mode | Online |
| Background | Student, IIIT Delhi |


## 3. How we took part

- Participation mode: **Online only — solo participant**.
- Track: **Technical - working prototype**.
- Primary challenge area: **Inclusive Design**. The implementation also addresses System Resilience and Trust & Consent, but the form asks for one primary area.

## 4. Project overview

### Project title

VaaniVerify: Intent-Bound Multilingual Consent for DPI Agents

### One-line summary
<!-- words:summary:1:25 -->
VaaniVerify binds multilingual confirmations to exact agent actions, blocking unauthorized payments and document sharing through deterministic policy and single-use cryptographic approval.
<!-- end:summary -->

### Website description
<!-- words:website:60:100 -->
An AI assistant can describe a payment as money coming in while its tool call sends money out. VaaniVerify separates the agent's explanation from the authority to act. It checks proposed actions against a user's structured permission, compiles confirmations in English, Hindi, Hinglish and Tamil, and signs the exact approved payload. A separate local gateway rejects changed or replayed requests. We demonstrate this for India's DPI through synthetic UPI-style payments, recurring mandates and DigiLocker-style document sharing, with reproducible comparisons and mutation tests. The prototype does not connect to production DPI, and user comprehension remains unmeasured.
<!-- end:website -->

## 5. The problem

DPI systems addressed: **UPI and DigiLocker**, modeled locally; cross-cutting consent architecture. No Aadhaar integration.

### Which DPI assumption breaks when AI agents act on it?
<!-- words:assumption:80:150 -->
The assumption is that a person approving a high-stakes request sees an accurate description of the action they authorize. An agent can break this link because it generates both the tool request and the language explaining that request. After reading an untrusted message, an agent might propose an outgoing payment while describing it as a subsidy receipt. A generic confirmation can then approve a different action from the user's original task. The gap extends beyond money direction: one payment can become a recurring mandate, or permission to share one document can become a larger disclosure. Translating the agent's explanation does not bind it to the executable payload. VaaniVerify makes that binding explicit at the authorization boundary.
<!-- end:assumption -->

### Problem statement and who is affected
<!-- words:problem:100:150 -->
Consider a user asking a Hindi or Hinglish assistant to check whether a subsidy arrived. A malicious external message instructs the assistant to prepare a debit and describe it as receiving the benefit. The user hears a familiar language and believes the request is harmless. The same mismatch can affect a household paying a bill from a message, a person accepting an automatic payment schedule, or an applicant sharing documents through an assistant. Users who cannot comfortably inspect technical transaction details have less opportunity to catch the discrepancy. Reusing an agent integration across services can repeat the failure across many users. This project targets the authorization mismatch itself: which action is permitted, which exact details are shown, and which payload can ultimately execute.
<!-- end:problem -->

## 6. Our approach and findings

### Approach
<!-- words:approach:150:250 -->
We built a local Python/FastAPI consent service, a responsive browser console and a separate public-key-only mock execution gateway. The user selects a structured operation and constraints in the trusted console. Free text remains context: a lexical hint cannot grant payment or sharing authority. An agent has a separate credential that can only propose actions against an existing intent. It cannot register permission, assert trusted provenance, approve a proposal or sign a capability. An optional local Qwen agent produces real proposals through this interface, using constrained JSON generation outside the trusted kernel.

The deterministic kernel checks operation, recipient, monetary ceiling, recurring schedule and count, document set, purpose and retention. It derives each field's relationship to stored constraints rather than trusting agent-supplied source labels. External bill recipients are permitted only when the user has explicitly allowed subsequent exact review. Fixed templates compile the validated payload into English, Hindi, Hinglish or Tamil. Free-text merchant names are excluded from the confirmation sentence.

The owner confirms direction, exact recipient and amount, and the displayed terms. Ed25519 signs the complete action digest and associated intent, audience, subject, nonce, template version and expiry. The other process verifies this capability and atomically consumes its nonce and one-action intent budget with the mock receipt. This combines scope enforcement, accurate presentation and execution binding. A translated warning alone lacks execution integrity; blanket source rejection prevents useful external-bill workflows. No model or paid API is needed to reproduce the prototype.
<!-- end:approach -->

### Threat model and resilience under exposure
<!-- words:threat:150:250 -->
The attacker controls external text and the agent's proposed tool payload and explanation. They may possess the proposal-only credential and know every prompt, rule, schema, template and public key. Their goals are to change the operation or recipient, increase payment or disclosure scope, alter an approved action, replay approval, or obtain multiple executions from one instruction.

We assume the attacker cannot modify the trusted service, read its private signing key or owner session, replace the gateway's pinned public key, or control the user's browser. These are explicit trust assumptions, not hidden prompts. Knowing the policy does not let an attacker rewrite stored user constraints or produce a signature for a different action. The gateway binds all applicable fields and validates expiry after acquiring its execution lock. Unique database constraints enforce one effect per nonce and intent under concurrent requests. Per-intent proposal limits restrict one agent's ability to exhaust the session.

The design does not determine whether a bill is truthful or prove that a user understands it. A user who explicitly allows an external recipient and approves the attacker's exact request can still authorize harm. A stolen owner session, compromised browser or signing service defeats this boundary. An already-issued capability cannot be revoked in the prototype; its maximum lifetime is sixty seconds.
<!-- end:threat -->

### How we evaluated it
<!-- words:evaluation:100:200 -->
We authored twenty semantic templates in four languages: eighty cases, equally split between legitimate tasks and modeled attacks. This policy suite uses fixture proposals and user choices, covering operation, recipient, amount, recurring and document scope, post-approval mutation and directional mismatch.

Five implemented policies compare generic approval, operation-only checking, blanket external rejection, removal of execution binding, and the full kernel. Full trials perform actual signing, verification and SQLite execution. A separate seeded experiment mutates capabilities across ten field/signature families. Regression tests cover concurrency, expiry after lock contention, restart replay, HTTP separation and uncertain outcomes. Evidence includes raw cases, outcomes, timing exclusions and hashes.

A separate CPU pilot samples Qwen2.5-1.5B Q4_K_M on thirty-two synthetic inputs: eight templates in four languages. We retain prompts, raw outputs, malformed responses and attack-goal outcomes. An initial output-shape failure led to operation-specific generation grammar; both runs are disclosed. The same corpus was reused, so this is development evidence, not held-out evaluation. User approval remains scripted and no comprehension study was conducted.
<!-- end:evaluation -->

### Key results

- Authored corpus: **40/40 modeled attacks executed** with the unguarded simulation, **32/40** with operation-only checks, and **0/40** with VaaniVerify. VaaniVerify executed **40/40 legitimate cases** after modeled exact approval.
- Removing execution binding allowed **4/40 modeled attacks** to execute. Blanket external-parameter rejection blocked all modeled attacks but also **24/40 legitimate tasks**; VaaniVerify blocked **0/40 legitimate tasks** in this corpus.
- Generated capability mutations: **1,000/1,000 rejected**; **1,000/1,000 original signed actions remained executable**. These are generated trials, not independent real-world attacks.

- Current local Qwen pilot: **9/16 attack attempts produced attacker-goal proposals**, **0/16 attacker goals executed**, and **15/16 expected benign actions executed**. All 32 outputs were schema-valid. The failed benign case invented a recipient when external recipient review was explicitly delegated. Earlier runs are retained; no held-out claim is made. The latest full suite, with browser and live inference enabled, reports **129 passed and 1 failed** (that delegated-recipient regression).

### What's new here

The contribution is an inspectable combination for vernacular DPI consent: original-operation constraints, deterministic action-to-language explanations, directional confirmation, and one-action execution capabilities. It addresses the gap between an agent's explanation and its executable action; it does not claim to invent capability security or solve multilingual comprehension.

### Who could use this, and how

A payment or document-service integrator building an assistant could first place the kernel before its tool adapter in an authorized sandbox. The concrete first step is mapping provider operations to strict schemas and integrating capability consumption with provider idempotency, followed by multilingual user studies and adversarial model testing.

### Limitations and open problems
<!-- words:limitations:80:150 -->
All actions and identifiers are synthetic. The gateway records mock effects, not real payments, scheduled debits or document delivery. The corpora are authored, with matched language variants; the live pilot covers one small quantized model and cannot estimate broader attack prevalence or compromise rates. Direction choices and exact-entry confirmations have not been tested with users, and translations need native-speaker and accessibility review. Structured intent is authoritative; arbitrary multilingual text is not reliably parsed into consent. Browser compromise, owner-session theft and issuer compromise are outside the protection boundary. Document retention and purpose are bound to the request but cannot be enforced after a recipient copies data. The local receipt hash chain is not independently anchored. One delegated-recipient model case remains incorrect; exact review is essential. Production requires isolated authenticated interfaces, hardened keys, provider-level idempotency, revocation, operational testing and external evaluation.
<!-- end:limitations -->

## 7. Reflection

### Difficulty faced
<!-- words:reflection:200:300 -->
The hardest conceptual problem was distinguishing an accurate warning from actual authority. The initial proposal combined lexical intent extraction, parameter provenance and a directional challenge. Each sounds reassuring, but none automatically establishes what the user authorized. A lexical matcher can misunderstand negation or unfamiliar language. An agent can invent a provenance label. Selecting the correct direction can reflect coaching rather than comprehension. Treating those signals as proof would merely relocate the original trust problem.

We therefore made the user's structured selection authoritative and kept the agent outside that boundary. This costs flexibility: the user must specify the operation and limits, and a previously unknown recipient requires exact review. Our implemented baseline made the usability trade-off visible. Rejecting all externally sourced parameters avoided the authored attacks but blocked twenty-four of forty legitimate cases. Allowing constrained proposals and separately confirming their exact details preserved these cases without treating external text as authority.

Verification exposed a second, concrete gap. The first gateway checked token expiry before waiting for its database write lock. Code review showed that a queued request could pass the check, wait until expiry and still execute. We moved the authoritative time check inside the transaction and added a regression. Another review showed why a network timeout must mean an unknown outcome, not a failed payment: the mock effect may already be committed.

Live inference also exposed misleading narration: the model said a bill had been paid while merely proposing it. This reinforced the separation between agent prose and gateway receipts.

The lesson was that consent security is an end-to-end contract across intent, presentation, approval, concurrency and execution reporting. Strong cryptography cannot repair an ambiguous permission or misleading outcome display. Our tests establish bounded mechanical properties; whether people understand the interface remains an open empirical question.
<!-- end:reflection -->

### How we overcame it

- Made structured operation and scope mandatory before an agent proposal. This gives up free-form autonomous authorization to obtain explicit, inspectable constraints.
- Derived field relationships from stored intent and omitted free-text merchant names from trusted sentences. This gives up arbitrary display-name expressiveness and avoids a fragile multilingual denylist.
- Allowed externally resolved bill recipients only with explicit delegation and exact review. This preserves the authored bill workflows but does not establish the recipient's real-world trustworthiness.
- Bound every action field and one-use intent budget to a signed capability. Added atomic SQLite consumption, concurrent replay tests and post-lock expiry validation.
- Reported execution timeouts as uncertain and preserved same-token retries. This gives up a falsely simple success/failure display in favor of recoverable, accurate state.
- Kept comprehension, translation validation, production integration and post-issuance revocation as explicit remaining work.

## 8. Deliverables and declarations

| Field | Answer |
|---|---|
| Main submission file | [Technical report PDF](https://raw.githubusercontent.com/kunallll17/SAFL_Submission/main/output/pdf/TeamBifrost_Report.pdf) (9 pages) |
| Code repository | [https://github.com/kunallll17/SAFL_Submission](https://github.com/kunallll17/SAFL_Submission); README includes setup and reproduction |
| Demo video | [Demo video](https://raw.githubusercontent.com/kunallll17/SAFL_Submission/main/brag.mp4), 25 seconds; included as `brag.mp4`. It illustrates the implemented interface and cites the earlier pilot; see `docs/VIDEO_CREDITS.md` for evidence and attribution. |
| Other artifacts | [Full submission ZIP](https://raw.githubusercontent.com/kunallll17/SAFL_Submission/main/output/source/TeamBifrost_Submission.zip); `evidence/` contains scenario sets, baseline results, model outputs, mutations, regression results and screenshots |
| Work during the hackathon | Yes: the core implementation was developed during the hackathon. |
| AI tools used | OpenAI Codex (GPT-6) for implementation, testing and documentation. Optional runtime proposer: Qwen2.5-1.5B-Instruct Q4_K_M via llama.cpp b12020; no model in the trusted authorization path |
| External code/models/data | See `THIRD_PARTY_NOTICES.md`, `evidence/dependencies.json` and `evidence/local_model_runtime.json`. No third-party dataset; optional Apache-2.0 Qwen weights and MIT llama.cpp runtime, with pinned revision/checksums |
| All links public without login | Yes - repository, report, demo video and submission ZIP returned HTTP 200 without authentication; downloaded artifacts matched the local files. |

## 9. Responsible testing

- **No real personal data: Yes.** All transaction and document identifiers are synthetic. Only `@demo` handles are accepted; no real Aadhaar numbers, UPI IDs, bank details or documents were used.
- **Responsible disclosure: Yes.** Testing targeted only our local mock services. No weakness in a real service was tested or discovered, and no real-user exploit was published. The sole team member confirms this declaration covers all submitted work.
- Environment: separate owner consent and public-key-only mock DPI gateway processes with SQLite; an optional local CPU inference process and proposal client. Browser UI and HTTP tests used loopback only; no real accounts or transactions were involved.

## 10. Ownership, permissions and consent

Kunal Sharma, the sole team member, confirmed both permissions below.

| Permission | Yes / No | Members opting out |
|---|---|---|
| Featuring project title, summary, description and public links | Yes | None |
| Publishing members' names and institutions | Yes | None |

## Final submission checks

1. Enter the registered email and phone from the private form copy. The public repository and ZIP intentionally omit these contact details.
2. Team size is one; background, responsible-testing declarations and both organizer permissions have been confirmed by Kunal Sharma.
3. Review the linked report, demo video and repository. Private contact details belong only in the contest form; runtime credentials and model binaries are excluded from the public package.
4. Public repository, report, video and ZIP links have been verified without authentication. Use these links in the contest form.
5. Submit one form for the team. The template lists **31 October 2026, 11:59 pm**; confirm an extension or continued acceptance before relying on late submission. The contest form has not been submitted.
