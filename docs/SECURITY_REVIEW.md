# Review and corrections

31 October 2026. Two code-review passes covered the security kernel, signature format, gateway and benchmark; then HTTP authentication, browser rendering and launcher code. This is a code review, not an external audit or formal proof.

| Finding | Reproduction / consequence | Correction and evidence |
|---|---|---|
| Token expiry before lock acquisition | A competing SQLite writer could delay execution beyond token expiry while the early check remained valid | Reverify after `BEGIN IMMEDIATE`; deterministic lock-delay regression |
| Global proposal exhaustion | One agent could fill the session with rejected proposals under a single intent | Twenty proposals per owner-created intent; terminal/expired eviction; isolation regression |
| Unknown execution reported as rejected | Gateway committed a mock effect, then its response timed out | HTTP 503 with uncertain-outcome detail; UI shows unknown state, receipt inspection and same-token retry; commit-then-timeout regression |
| Reopening a consumed private link | A valid owner session was blocked by unnecessary bootstrap re-exchange | Check existing session before exchanging the fragment; single-use server exchange preserved |
| Non-ASCII credential caused 500 | Unicode input was passed to ASCII-only constant-time comparison | Bootstrap schema and ASCII checks; controlled validation/authorization response |

The review found no authorization bypass in the inspected role separation, strict schemas, full-action signature verification or one-intent budget. Review explicitly excluded compromised owner credentials/processes, translation accuracy, human comprehension and production provider semantics.

Additional issues found during implementation and verification:

- SQLite transaction context managers did not close connections, causing Windows temporary-directory cleanup failures. Added explicit closing while preserving commit/rollback semantics.
- The proposal CLI could not print the rupee symbol under a legacy Windows encoding. It now emits portable ASCII-escaped JSON, with a regression preserving the decoded multilingual content.
- Windows virtual-environment launchers create an interpreter child. Terminating only the launcher could orphan the mock gateway. Cleanup now terminates the owned gateway process tree; an integration test starts the real subprocess and proves its port is released after console shutdown.
- Owner review of external proposals needed a complete inbox flow. Added authenticated list/read endpoints, task creation controls and a CLI adapter. Verified the full flow through the browser and separate gateway.

No real provider or third-party system was targeted. Findings concern this prototype only.

## Optional model integration review

A further read-only review verified separate model/proposal/owner credentials, strict model-output validation, operation-specific generation grammar, owner-only evidence access, safe task export and text-only rendering. No remaining blocking finding was identified. Two robustness findings were fixed: a corrupt full-size partial download now moves to a uniquely named quarantine file so a retry can recover; infrastructure failures abort the pilot without overwriting prior evidence. Regression tests cover both.

The reviewer independently revalidated all three saved model runs, replayed valid outputs through fresh kernels/gateways, checked corpus/prompt/source hashes, verified downloaded asset checksums and the extracted executable, and ran all 106 tests. Final replay: 32 valid proposals, 11/16 attacker-goal proposals, zero attacker-goal executions, 16/16 expected benign executions. This was enforcement replay, not independent model generation. Initial same-corpus development results remain disclosed.
