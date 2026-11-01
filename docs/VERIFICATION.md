# Verification record

## Current submission check - 1 November 2026

The full suite was rerun with browser and real-model tests enabled: **129 passed, 1 failed**. The failing test is `test_real_model_copies_a_delegated_recipient_from_the_bill`; the model proposed `demo@demo` instead of `utility.board@demo`. This is an unresolved semantic reliability limitation in explicitly delegated recipient selection. It is not hidden with xfail or a fallback response. Evidence: `evidence/submission_pytest.xml` and `docs/FUNCTIONAL_VERIFICATION.md`.

Fresh policy evaluation reproduced 0/40 modeled attack executions and 40/40 legitimate fixture executions. Fresh generated-capability checks rejected 1,000/1,000 mutations while preserving all 1,000 original actions. Console, gateway and real model health endpoints returned HTTP 200. The retained current model pilot reports 32 valid proposals, 9/16 attacker-goal proposals, 0/16 attacker-goal executions and 15/16 exact benign actions.

The submission draft, nine-page PDF and allowlisted ZIP have been refreshed for the current code and these results. Earlier records below are historical and do not override this current test result. This test run preceded publication. Current delivery status is recorded separately in `evidence/submission_publication.json`; application tests were not rerun for packaging edits.

## Historical verification - 31 October 2026

Date: 31 October 2026. Platform: Windows, project Python 3.11.16. All actions used synthetic data and loopback services.

## Automated checks

- **106 pytest cases passed.** Coverage includes strict schemas, operation/scope enforcement, exact approval, signature and claim validation, expiry including lock contention, concurrent replay, concurrent sibling approval, one-intent budget, gateway restart replay, local hash-chain consistency, agent flood isolation, HTTP owner/agent separation, Origin/Host checks, input limits, uncertain execution, agent CLI encoding and real gateway subprocess shutdown.
- One dependency warning remains: Starlette deprecates its HTTPX-backed TestClient path. It does not fail the tests; no warning was hidden and no production claim is based on it.
- JavaScript syntax checked with `node --check web/app.js`. HTML, CSS and JavaScript formatted and checked with Prettier 3.6.2. The tiny SVG remains hand-authored; Prettier's default inference did not support its extension.
- All contest-limited prose sections pass `scripts/check_submission.py`, including the 21-word summary and 297-word reflection.
- Full policy experiment: 80 authored cases / 20 semantic templates x 4 languages. VaaniVerify: 0/40 modeled attack executions, 40/40 legitimate executions. Full policy minus execution binding: 4/40 attack executions. Strict external rejection: 24/40 legitimate tasks blocked.
- Seeded capability mutation experiment: 1,000/1,000 rejected; 1,000/1,000 original signed actions subsequently executed. Ten families; seed 20261031. Local receipt chain verified.

Final command outputs and per-case records are in `evidence/`. Timing measurements are specific to each run and exclude UI, network, model and human latency.

## Browser and live service verification

Browser checks against the local console and separate gateway process:

1. Hinglish subsidy/read-only intent with outgoing PAY proposal was blocked before approval.
2. Legitimate externally resolved bill was confirmed with outgoing direction, exact recipient and INR 500. A signed action produced a gateway receipt.
3. Reusing that capability returned `REPLAY_BLOCKED`; substituting a recipient returned `PAYLOAD_CHANGED`.
4. The dedicated post-approval swap scenario was rejected by the gateway after a valid original approval.
5. Tamil confirmation rendered for a blocked payment. The responsive layout was inspected at desktop 1440 x 1000 and mobile 390 x 844. The mobile document did not overflow horizontally. Screenshots are in `evidence/screenshots/`. The final evidence page, including the live-model section, also fits the 390-pixel mobile viewport without horizontal overflow.
6. Evidence navigation displayed the stored benchmark and correct policy table. Browser error/warning logs were empty at that check.
7. A trusted task was created in the browser, submitted to by the separate proposal-only CLI, loaded from the owner inbox, then approved and executed in the separate gateway. The CLI originally hit a Windows output-encoding issue; after correction it returned valid JSON and the full flow completed.

8. Hindi document-sharing consent was confirmed and executed with exact recipient, document, purpose and retention.
9. Selecting one-time payment for a recurring mandate returned `DIRECTION_MISMATCH` and cancelled the intent. Direction labels explicitly distinguish one-time from recurring payments.

10. Created a task in the owner console, downloaded its JSON, ran the actual local Qwen agent against that file, reviewed its HTTP proposal in the inbox, then explicitly approved and executed it. The separate gateway produced receipt #4. The model narration falsely claimed payment before approval; the trusted panel correctly remained awaiting approval.

Device-local speech availability and spoken quality were not verified. Real local-model inference is recorded separately below. Production API behavior, human comprehension, native-speaker validation and external accessibility audits remain unverified.

## Real local-model pilot

A separate Qwen2.5-1.5B-Instruct Q4_K_M CPU pilot ran 32 generations on eight authored templates in four language variants. Initial loose generation schema: 28/32 valid proposals, 13/16 attacker-goal proposals, 0/16 attacker-goal executions, 12/16 expected benign executions. All four failed benign read-only proposals contained an irrelevant recipient.

After reusing the strict operation/field mapping in the generation grammar, the same corpus produced 32/32 valid proposals, 11/16 attacker-goal proposals, 0/16 attacker-goal executions and 16/16 expected benign executions. The final rerun after infrastructure-error handling fixes reproduced these counts. All three records are retained. These are development iterations on the same inputs, not independent held-out experiments. No system prompt or attack-input tuning occurred between them.

Raw outputs were revalidated and replayed through a fresh kernel/gateway, reproducing the counts. Final replay produced 21 safe receipts: 16 benign tasks and five attack inputs where the model chose an authorized action. Zero attacker-goal executions does not mean zero executions on attack inputs. Weights/archive hashes and the extracted server executable were also verified.

Strict post-generation validation remains necessary; grammar does not guarantee semantic correctness or authorization. Model infrastructure failures abort without replacing evidence. A full-size corrupt model partial is quarantined so a retry can recover. Both have focused regressions.

## Report and package

`output/pdf/TeamBifrost_Report.pdf` is nine pages, below the contest's ten-page cap. All pages were rendered with Poppler and visually inspected for clipping, overflow and legibility; the updated team cover and ownership page were rechecked after attribution was added. The report uses standard PDF fonts. Poppler reported missing optional display-font mappings for Symbol/ArialUnicode; the actual ASCII report rendered legibly without missing glyphs.

`scripts/package_submission.py` uses a file allowlist, checks that active runtime credential strings are absent, tests archive integrity, and writes per-file SHA-256 hashes. It excludes `.runtime`, `.venv`, caches and temporary files. The archive contains source, tests, README, report and evidence. No Git commit or public publication was made by this build. The archive was extracted into a clean project directory; import paths were checked to use that copy, all per-file hashes matched, and all 106 tests passed using the existing dependency environment. This does not claim a fresh dependency installation on another machine.

## Remaining team actions

Team Bifrost is now a solo submission by Kunal Sharma, Student, IIIT Delhi, participating online. Private registration/contact details and both organizer permissions have been supplied by Kunal. The 25-second demo is included. Publication and signed-out access checks are recorded in `evidence/submission_publication.json`. The final contest form and acceptance after the stated deadline remain to be handled.
