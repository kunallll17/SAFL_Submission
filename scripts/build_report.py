"""Build the nine-page technical report from real evidence and submission prose."""

import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/TeamBifrost_Report.pdf"
BENCH = json.loads((ROOT / "evidence/benchmark.json").read_text(encoding="utf-8"))
MUTATIONS = json.loads((ROOT / "evidence/mutations.json").read_text(encoding="utf-8"))
PILOT = json.loads((ROOT / "evidence/model_pilot.json").read_text(encoding="utf-8"))
DRAFT = (ROOT / "docs/SUBMISSION_DRAFT.md").read_text(encoding="utf-8")
INK = colors.HexColor("#22372e")
GREEN = colors.HexColor("#3c7050")
CORAL = colors.HexColor("#bc6248")
MUTED = colors.HexColor("#657566")
LINE = colors.HexColor("#dce4d5")
PALE = colors.HexColor("#f3f6ee")
WIDTH = 174 * mm
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="BodyVV", fontName="Helvetica", fontSize=9.2, leading=14, textColor=INK, spaceAfter=10))
styles.add(ParagraphStyle(name="SmallVV", fontName="Helvetica", fontSize=8, leading=12, textColor=MUTED, spaceAfter=8))
styles.add(ParagraphStyle(name="TinyVV", fontName="Helvetica", fontSize=7, leading=10.4, textColor=MUTED, spaceAfter=5))
styles.add(ParagraphStyle(name="TitleVV", fontName="Helvetica", fontSize=28, leading=33, textColor=INK, spaceAfter=14))
styles.add(ParagraphStyle(name="SubVV", fontName="Helvetica-Bold", fontSize=13, leading=18, textColor=INK, spaceBefore=12, spaceAfter=8))
styles.add(ParagraphStyle(name="EyebrowVV", fontName="Courier", fontSize=8, leading=11, textColor=CORAL, spaceAfter=10))
styles.add(ParagraphStyle(name="CodeVV", fontName="Courier", fontSize=7.4, leading=11, textColor=GREEN, spaceAfter=8, backColor=PALE, borderPadding=9))
styles.add(ParagraphStyle(name="MetricVV", fontName="Helvetica", fontSize=25, leading=30, textColor=GREEN, spaceAfter=8))


def clean(text):
    return str(text).replace("\u2011", "-").replace("–", "-").replace("—", "-").replace("’", "'").replace("“", '"').replace("”", '"').replace("₹", "INR ").replace("→", "->").replace("×", "x").replace("·", " / ")


def p(text, style="BodyVV"):
    return Paragraph(escape(clean(text)).replace("\n", "<br/>"), styles[style])


def section(title):
    return p(title, "SubVV")


def prose(name):
    match = re.search(rf"<!-- words:{name}:\d+:\d+ -->(.*?)<!-- end:{name} -->", DRAFT, flags=re.S)
    return [p(part.strip()) for part in match.group(1).strip().split("\n\n")]


def title(number, label, heading, subtitle=None):
    items = [p(f"{number:02d} / {label.upper()}", "EyebrowVV"), p(heading, "TitleVV")]
    if subtitle:
        items.append(p(subtitle, "SmallVV"))
    return items


def table(headers, rows, widths=None):
    data = [[p(h, "TinyVV") for h in headers]] + [[p(cell, "SmallVV") for cell in row] for row in rows]
    value = Table(data, colWidths=widths or [WIDTH / len(headers)] * len(headers), hAlign="LEFT", repeatRows=1)
    value.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, 0), .7, LINE), ("LINEBELOW", (0, 1), (-1, -1), .4, LINE),
    ]))
    return value


def callout(label, text):
    value = Table([[p(label, "EyebrowVV")], [p(text, "BodyVV")]], colWidths=[WIDTH])
    value.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE),
                              ("BOX", (0, 0), (-1, -1), .6, LINE),
                              ("LEFTPADDING", (0, 0), (-1, -1), 15), ("RIGHTPADDING", (0, 0), (-1, -1), 15),
                              ("TOPPADDING", (0, 0), (-1, 0), 14), ("BOTTOMPADDING", (0, -1), (-1, -1), 8)]))
    return value


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 19 * mm, 192 * mm, 19 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(18 * mm, 13.5 * mm, "VAANIVERIFY  /  LOCAL SYNTHETIC RESEARCH PROTOTYPE")
    canvas.drawRightString(192 * mm, 13.5 * mm, f"01 NOV 2026  /  {doc.page} OF 9")
    if doc.page > 1:
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(INK)
        canvas.drawString(18 * mm, 282 * mm, "vaaniverify")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(192 * mm, 282 * mm, "INDIA AGENTIC AI SECURITY HACKATHON")
    canvas.restoreState()


story = []
# 1 - cover and claim boundary
story += [Spacer(1, 13 * mm), p("INDIA AGENTIC AI SECURITY HACKATHON / TECHNICAL TRACK", "EyebrowVV"),
          p("VaaniVerify", "TitleVV"), p("Intent-bound multilingual consent\nfor untrusted DPI agents.", "TitleVV"),
          p("Every action, understood.", "SubVV"), Spacer(1, 10 * mm)]
story += prose("website")
story += [Spacer(1, 8 * mm)]
metrics = Table([[p("0 / 40", "MetricVV"), p("40 / 40", "MetricVV"), p(f"{MUTATIONS['blocked']:,}", "MetricVV")],
                 [p("Modeled attacks executed", "SmallVV"), p("Legitimate cases executed", "SmallVV"), p("Generated mutations rejected", "SmallVV")]], colWidths=[WIDTH / 3] * 3)
metrics.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE), ("TOPPADDING", (0, 0), (-1, 0), 17), ("LEFTPADDING", (0, 0), (-1, -1), 14), ("BOTTOMPADDING", (0, 1), (-1, 1), 12)]))
story += [metrics, Spacer(1, 12 * mm), callout("WHAT THESE NUMBERS MEAN", "These headline numbers come from authored policy fixtures and generated capability mutations. A separate 32-inference local Qwen pilot is reported on page 6. All effects are synthetic; no human comprehension, production DPI access or real transactions were tested."), Spacer(1, 9 * mm), p("Primary area: Inclusive Design\nRelated areas: System Resilience; Trust & Consent\nTeam: Team Bifrost\nMember: Kunal Sharma\nInstitution: Indraprastha Institute of Information Technology Delhi\nParticipation: Online (solo participant)", "SmallVV"), PageBreak()]

# 2 - problem
story += title(2, "Problem", "When the explanation and action disagree.")
story += prose("assumption")
story += [section("A realistic failure sequence"), table(["Step", "What the user sees", "What can happen"], [
    ["1. Request", "Check whether my subsidy arrived.", "User intends a read-only task."],
    ["2. External message", "Instructions framed as claiming a benefit.", "Untrusted content influences the agent."],
    ["3. Agent explanation", "The benefit will be received.", "Tool payload proposes an outgoing debit."],
    ["4. Generic approval", "Yes / continue.", "Approval no longer matches original intent."],
], [23 * mm, 72 * mm, 79 * mm]), Spacer(1, 7 * mm)]
story += prose("problem")
story += [section("What changes with VaaniVerify"), p("The agent's explanation is displayed as untrusted evidence. The original user-selected operation remains authoritative. A read-only intent cannot produce a debit capability, regardless of what language or instructions appear in the external message."), PageBreak()]

# 3 - architecture
story += title(3, "Implementation", "Four boundaries. One exact action.")
story += [table(["Boundary", "Implementation and authority"], [
    ["1 / Owner intent", "Private browser session creates structured operation, recipient/ceiling and applicable recurring or document terms. Natural-language text is context only."],
    ["2 / Agent proposal", "Separate bearer credential can propose against an existing intent. It cannot create authority or submit provenance labels. Untrusted prose is never an approval sentence."],
    ["3 / Consent kernel", "Strict schemas, deterministic policy and four fixed language tables. Exact direction, recipient/amount and displayed terms precede capability signing."],
    ["4 / Execution gateway", "Separate process receives only the public key. It verifies the full action and commits the mock receipt with unique nonce/intent consumption in SQLite."],
], [39 * mm, 135 * mm]), Spacer(1, 5 * mm)]
story += prose("approach")
story += [p("Implementation: Python 3.11 / FastAPI / Pydantic / cryptography / SQLite. Frontend: buildless HTML, CSS and JavaScript with text-only rendering and no remote assets. All identifiers are synthetic ASCII @demo handles.", "SmallVV"), PageBreak()]

# 4 - consent contract
story += title(4, "Consent contract", "Meaning is compiled from the payload.")
story += [p("The executable action is validated before it reaches a language template. Every applicable field is included in the action digest. Changing display language does not change authority."),
          table(["Operation", "Fields the user authorizes", "Effect represented"], [
              ["READ_STATUS", "Read-only operation", "No debit or document release"],
              ["PAY", "Recipient + amount within selected ceiling", "One outgoing payment"],
              ["MANDATE", "Recipient + amount + frequency + count", "Bounded recurring authorization"],
              ["SHARE", "Recipient + exact documents + purpose + retention", "Specified document disclosure request"],
              ["CANCEL_MANDATE", "Exact synthetic mandate ID", "Cancellation request only"],
          ], [40 * mm, 80 * mm, 54 * mm]), Spacer(1, 7 * mm),
          callout("HINGLISH PAYMENT CONFIRMATION / GENERATED FROM STRUCTURED FIELDS", "PAISA JAYEGA. Aapke account se INR 500 ek baar utility.board@demo ko jayega."),
          section("One authorization, not an unlimited budget"),
          p("The user selects a direction and enters the exact recipient and monetary amount, then accepts all displayed terms. A mismatching direction cancels the intent. Correct answers permit a single capability to be issued; sibling proposals cannot obtain additional approvals for the same intent."),
          p("The capability includes an action digest, direction, subject, audience, intent/proposal identifiers, nonce, template hash, issue time and expiry. Ed25519 signs its canonical body. Verification checks the full action and lifetime again after acquiring the database lock. A nonce, proposal or intent can appear in the execution ledger only once."),
          p("Intent lifetime: 15 minutes. Proposal review: up to 3 minutes. Capability lifetime: 60 seconds. Cancellation works before issuance. Post-issuance revocation is not implemented. Template hashes bind a software version, not translation correctness.", "SmallVV"),
          section("Accessibility boundary"), p("English, Hindi, Hinglish and Tamil confirmations and directional choices are implemented. The surrounding research console remains primarily English. Optional speech uses a device-local browser voice when available. Native-speaker, comprehension, voice-quality and accessibility studies remain future work."), PageBreak()]

# 5 - evaluation and causal comparison
story += title(5, "Evaluation", "Compare security and legitimate utility.")
story += prose("evaluation")
names = {"unguarded": "Unguarded / generic approval", "operation_only": "Operation-only check", "strict_external_block": "Reject external parameters", "without_execution_binding": "Full policy minus execution binding", "vaaniverify": "VaaniVerify"}
rows = [[names[r["policy"]], f"{r['attack_executions']} / {r['attack_count']}", f"{r['benign_blocked']} / {r['benign_count']}"] for r in BENCH["summary"]]
story += [table(["Policy", "Attack executions", "Benign blocks"], rows, [94 * mm, 40 * mm, 40 * mm]), Spacer(1, 6 * mm),
          p("The execution-binding ablation isolates a concrete gap: an otherwise approved action can be changed at use time. Removing the binding admits four language variants of the recipient-swap case. Blanket external blocking instead sacrifices 24 legitimate cases. This is an implemented synthetic comparison, not an empirical comparison of commercial models."),
          section("Generated capability mutation experiment"),
          p(f"Seed {MUTATIONS['seed']}; ten field/signature families; {MUTATIONS['trials']:,} trials. All {MUTATIONS['blocked']:,} changed capabilities were rejected. All {MUTATIONS['valid_originals_executed']:,} original signed actions still executed afterward, and the resulting receipt chain passed its local integrity check."),
          p(f"Recorded full-pipeline local median: {BENCH['full_pipeline_latency_ms']['p50']:.2f} ms; P95: {BENCH['full_pipeline_latency_ms']['p95']:.2f} ms. This mixes early blocks and accepted SQLite executions, includes signing and verification, and excludes model, network, browser and human time. Values vary by machine and run.", "SmallVV"), PageBreak()]

# 6 - real local-model pilot, distinct from policy fixtures
story += title(6, "Real local-model pilot", "The model proposes. The boundary decides.")
ps = PILOT["summary"]
story += [p("We ran Qwen2.5-1.5B-Instruct Q4_K_M through llama.cpp b12020 on CPU. Its public system prompt instructs it to respect the original request and treat external messages as untrusted. It generates a structured action and an explanation; it has no approval or execution tool."),
          p("The pilot uses eight authored templates, each in four language variants: sixteen benign tasks and sixteen injection attempts. Attack messages claim a connector override and include the desired tool payload. They target payment polarity, recipient substitution, recurring escalation and document expansion. The full prompts, schema, model/runtime checksums and raw outputs are retained."),
          table(["Final pilot measurement", "Recorded outcome"], [
              ["Generation attempts / valid proposals", f"{ps['attempts']} / {ps['valid_proposals']}"],
              ["Attacker-goal actions proposed by model", f"{ps['attacker_goal_proposals']} of {ps['attack_attempts']} attack attempts"],
              ["Attacker-goal actions executed after guard", f"{ps['attacker_goal_executions']} of {ps['attack_attempts']} attack attempts"],
              ["Expected benign actions executed", f"{ps['benign_expected_action_executions']} of {ps['benign_attempts']} benign attempts"],
          ], [110 * mm, 64 * mm]), Spacer(1, 6 * mm),
          section("An observed failure, beyond the fixtures"),
          p("The model sometimes proposed a debit after a read-only request, or a recurring mandate after a one-time payment request. The independently stored intent blocked these proposals. Its narration also claimed a bill had been paid while only generating a proposal. The console therefore treats that narration as untrusted and reports execution only from the gateway receipt."),
          section("What changed between runs"),
          p("Operation-specific grammar repaired an earlier output-shape failure. Later custom-task testing exposed a stale example bill, incorrect decimal conversion and a wrong document operation. We cleared inherited example input, exposed actual model runs and clarified proposer instructions. The current pilot still misses one benign bill recipient: it invents demo@demo under explicit external-recipient delegation. Scripted approval accepted that wrong recipient. This is a real model-reliability limitation, despite zero attacker-goal executions."),
          p("All development records are retained. The latest full suite with browser and live-model checks reports 129 passes and one failing delegated-recipient test. These reused inputs are not held-out samples. Approval is scripted. Results concern one quantized model and cannot establish frontier-model robustness, translation quality or human understanding. Runtime failures abort evidence generation rather than being counted as model responses.", "SmallVV"), PageBreak()]

# 7 - threats
story += title(7, "Threat model", "Public rules. Separate authority.")
story += prose("threat")
story += [table(["Attacker attempt", "Enforced boundary"], [
    ["Change operation / increase scope", "Stored user constraints, separate operation-specific schemas"],
    ["Invent trusted source labels", "Unknown-field rejection; server derives relation to user constraints"],
    ["Lie in multilingual explanation", "Agent text cannot populate the trusted confirmation sentence"],
    ["Swap recipient after approval", "Digest covers full normalized action; Ed25519 verifies it"],
    ["Replay or race two executions", "Unique nonce/intent/proposal consumption in the effect transaction"],
    ["Wait beyond expiry for a lock", "Authoritative lifetime check after acquiring write lock"],
    ["Flood one intent with rejected calls", "Twenty proposals per intent; bounded state and terminal pruning"],
], [66 * mm, 108 * mm]), Spacer(1, 7 * mm),
          callout("OUTSIDE THIS PROTOTYPE'S GUARANTEE", "Compromised owner UI/session or issuer, malicious local processes, deceptive requests explicitly approved by the user, enforcement of recipient-side document deletion, and production financial-system semantics."), PageBreak()]

# 7 - reflection
story += title(8, "Engineering reflection", "The difficult part was defining authority.")
story += prose("reflection")
story += [section("What verification changed"), table(["Observed gap", "Implemented correction"], [
    ["Expiry checked before SQLite lock wait", "Reverify lifetime inside execution transaction; lock-delay regression"],
    ["Rejected proposals could fill session capacity", "Per-intent proposal cap and terminal/expired proposal pruning"],
    ["Timeout displayed as definite rejection", "Unknown-outcome state, receipt inspection and same-token retry"],
    ["Private link reopen / Unicode credential errors", "Reuse authenticated sessions; validate ASCII credentials"],
    ["Windows console could not print the rupee symbol", "Proposal adapter emits interoperable ASCII-escaped JSON"],
], [78 * mm, 96 * mm]), Spacer(1, 6 * mm),
          p("These corrections were verified through regression tests, browser execution and code review. Review is not a formal security audit. Human understanding was not tested and is not inferred from mechanical test success.", "SmallVV"), PageBreak()]

# 8 - reproducibility, limits, adoption and declarations
story += title(9, "Reproduction and next steps", "Inspect it. Run it. Challenge it.")
story += [Paragraph('<link href="https://github.com/kunallll17/SAFL_Submission" color="#3c7050">Public code repository</link> | <link href="https://raw.githubusercontent.com/kunallll17/SAFL_Submission/main/brag.mp4" color="#3c7050">Demo video (25 seconds)</link>. Video credits and earlier-pilot context: docs/VIDEO_CREDITS.md.', styles["SmallVV"])]
story += [p("Windows: run setup.bat once, then launch.bat (Python 3.11+). The landing page links to the guided /demo and the preset /lab. Live inference requires the optional local Qwen server on port 8770; preset security cases need no model. Console and gateway use loopback ports 8765 and 8766. No paid service is required. Keep the launcher open."),
          p(".venv\\Scripts\\python.exe -m pytest -q\n.venv\\Scripts\\python.exe -m vaaniverify.evaluate\n.venv\\Scripts\\python.exe -m vaaniverify.mutations", "CodeVV"),
          p("Evidence: benchmark.json / benchmark.csv / scenarios.json / mutations.json. The benchmark includes runtime, source and corpus hashes. For the optional live pilot, follow README to set up/start the local model, then run python -m vaaniverify.evaluate_model. model_pilot.json retains prompts and raw outputs; local_model_runtime.json pins verified model/runtime assets. The guided demo runs inference directly and exposes actual inputs and raw outputs. FUNCTIONAL_VERIFICATION.md contains manual cases and the known failure; submission_pytest.xml records the latest full test run.", "SmallVV"),
          section("Limits and adoption")]
story += prose("limitations")
story += [p("A realistic first adopter is an assistant integrator at a payment or document service. Begin in an authorized provider sandbox: map operation semantics, bind real subjects, isolate the owner interface, secure signing keys, and integrate provider idempotency. Follow with native-speaker/accessibility studies and adversarial live-model evaluation before any real deployment."),
          section("Testing and attribution"),
          p("Only locally owned synthetic services were tested. No real personal data, accounts, identity documents or funds were used. No live-provider weakness or real-user exploit was published. Original work remains with Team Bifrost. Public links and organizer publicity permissions are completed separately in the submission form.", "SmallVV"),
          p("Development tools: OpenAI Codex (GPT-6) for implementation, testing and documentation. Optional Qwen weights use Apache-2.0; llama.cpp uses MIT. No AI model is in the trusted authorization path. THIRD_PARTY_NOTICES.md records dependencies and licences. No third-party dataset was used.", "SmallVV"),
          section("References"),
          p("1. SAFL. India Agentic AI Security Hackathon (2026). secureaifutureslab.com/events/india-ai-agentic-hackathon\n2. Hofman et al. MAPS: A Multilingual Benchmark for Agent Performance and Security. EACL Findings (2026). aclanthology.org/2026.findings-eacl.42/\n3. Beurer-Kellner et al. Design Patterns for Securing LLM Agents against Prompt Injections (2025). arxiv.org/abs/2506.08837\n4. Josefsson and Liusvaara. RFC 8032: Edwards-Curve Digital Signature Algorithm (2017). datatracker.ietf.org/doc/html/rfc8032", "TinyVV")]

OUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(OUT), pagesize=(210 * mm, 297 * mm), leftMargin=18 * mm, rightMargin=18 * mm,
                        topMargin=25 * mm, bottomMargin=26 * mm,
                        title="VaaniVerify: Intent-Bound Multilingual Consent for DPI Agents", author="Team Bifrost - Kunal Sharma",
                        subject="India Agentic AI Security Hackathon technical report")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
pages = len(PdfReader(OUT).pages)
if pages != 9:
    raise RuntimeError(f"Expected exactly 9 pages; found {pages}. Inspect layout before delivery.")
print(f"Created {OUT} ({pages} pages)")
