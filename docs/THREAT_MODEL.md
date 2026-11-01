# Threat model and security contract

## Assets and attacker

Assets: user-selected scope, recipient and monetary limits, recurring terms, document-sharing scope, approval integrity, single execution and an inspectable local receipt.

The attacker may control an external message, the full agent explanation, every proposed tool argument, and a proposal-only agent credential. They may know the full source, templates, policy, schemas and public key. They may submit conflicting proposals, tamper with execution requests, forge signatures, replay valid capabilities, and send concurrent requests. External content in this demo is authored synthetic data; no live service is targeted.

The attacker cannot read the owner session, private launch secret or issuer memory, modify the server/gateway installation or its public key, or control the trusted browser. Access to the same operating-system account, filesystem or process memory defeats the intended service separation. The local mock is not an OS security sandbox.

## Trust boundaries

1. **Owner to intent store:** a private bootstrap exchanged for a same-origin HttpOnly cookie authenticates the console. Mutations additionally require the exact Origin, a custom header and JSON. The server validates Host to reduce DNS rebinding. The demo serves on loopback HTTP; production needs HTTPS, independent origins, real account authentication and hardened session management.
2. **Agent to proposal store:** a different bearer credential grants only proposal submission against an existing intent. It cannot create intent, enumerate the owner inbox, approve, or retrieve signing secrets. The action schema forbids client provenance labels, unknown fields and free-text merchant display names.
3. **Intent to confirmation:** structured user fields determine authority. Agent wording is never used to broaden it. In-scope external recipient resolution still needs an exact independent confirmation. Every displayed confirmation is compiled from the canonical validated action using fixed templates.
4. **Approval to execution:** the issuer signs the canonical capability body with Ed25519. A separate process receives only its public key. The capability binds the action digest (including every applicable field), subject, audience, direction, intent ID, proposal ID, nonce, template hash, issuance and expiry.
5. **Execution to mock effect:** after obtaining the SQLite write lock, the gateway verifies the capability again and inserts the mock receipt in the same transaction as nonce/intent consumption. UNIQUE constraints enforce one effect per nonce, proposal and intent even across restarts and concurrent requests.

## Enforced invariants

| Invariant | Enforcement | Regression coverage |
|---|---|---|
| Read-only cannot become pay, mandate or share | Exact operation equality | Three escalation variants |
| Pinned recipient cannot change | Stored intent equality | Before/after approval swaps |
| Payment cannot exceed user ceiling | Strict integer comparison | Bound, overflow, bool/string/float rejection |
| One-time consent cannot authorize recurring debit | Separate operation schema | PAY to MANDATE |
| Recurring schedule/count cannot expand | Frequency and installment equality | Scope and signed mutation checks |
| Document consent cannot expand or change purpose | Exact document set, recipient, purpose and retention | Independent field mutations |
| Agent cannot label itself trusted | Unknown-field rejection; server-derived relationship to constraints | Forged provenance input |
| Wrong directional answer cannot sign | Direction check cancels intent | Direction mismatch |
| Several proposals cannot multiply one instruction | Locked intent consumption + gateway UNIQUE(intent_id) | Concurrent sibling approval |
| Approval cannot be reused or mutated | Full-action digest, Ed25519, UNIQUE nonce | Concurrent replay, tamper and restart |
| Queued request cannot outlive capability | Lifetime rechecked after transaction lock | Lock-delay expiry regression |
| Rejected mutations do not spend valid approval | Validation before receipt insertion | 1,000 generated trials |
| Timeout cannot be reported as definite failure | Unknown-outcome UI + receipt inspection + same-token retry | Commit-then-timeout HTTP regression |

## Availability and lifecycle

Each agent-accessible intent is limited to 20 proposals. The owner session holds at most 2,000 intents and 5,000 proposals; terminal/expired proposals are pruned at capacity. This is a bounded demo, not an internet-facing denial-of-service defense. The owner can restart to reset in-memory intents. The ledger persists. Issuer keys rotate on restart, invalidating previous outstanding capabilities.

An intent lives 15 minutes. A proposal is reviewable for up to 3 minutes. Capabilities are valid for 60 seconds. Cancellation prevents issuance; it cannot revoke an already minted capability. If the execution response is lost after commit, the console reports uncertainty and directs the user to receipts. A same-token retry cannot duplicate an effect but may return replay rejection after an earlier success.

## Why public logic does not bypass the checks

Knowing a policy lets the attacker predict rejections, but does not let them change the stored user selection or sign a new payload. A syntactically correct proposal that respects all selected constraints can proceed to the user. This is deliberate: the kernel enforces authorization, not whether an external bill is factually legitimate. If the user explicitly permits an external recipient and approves the attacker's exact details, the kernel cannot infer a different unexpressed intention.

## Explicit non-guarantees

- No proven multilingual natural-language intent extraction; the lexical hint is advisory and incomplete.
- No proof that a direction choice establishes human comprehension. Coaching, habituation and accessibility require user studies.
- No production UPI/DigiLocker integration, real ledger, real mandate scheduling, identity verification or document transfer.
- No enforcement of recipient-side retention or purpose after data release.
- No claim of 100% protection against prompt injection or fraud. Corpus outcomes are bounded synthetic evidence.
- The separate live pilot covers one small quantized model and authored development inputs; it is not a frontier-model benchmark or LLM-as-judge comparison. The five baselines are policy simulations.
- No trusted hardware, attestation, secure key vault, distributed issuer, key rollover protocol or external revocation service.
- No tamper-proof log. The hash chain is locally checkable but unanchored.
- No independently reviewed Tamil/Hindi translation or speech-quality assessment. Template hashes identify versions, not linguistic validity.

## Adoption path

A payment or document-service integrator could first replace the mock side-effect adapter in an authorized sandbox, map provider-specific operation semantics to strict schemas, and place the owner UI on an isolated authenticated origin. Integrate provider idempotency with the capability budget, establish per-account keys or subject binding, externally anchor receipts, and test failure recovery. Next run adversarial model integrations and blinded studies with speakers and accessibility users. Deployment depends on these steps; the current project is not ready for real funds or identity documents.
