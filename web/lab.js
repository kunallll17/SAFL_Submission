"use strict";

const $ = (id) => document.getElementById(id);
const state = {
  language: "hinglish",
  scenarios: [],
  selected: null,
  proposal: null,
  intent: null,
  direction: null,
  approval: null,
  receipts: null,
  evidence: null,
};
const names = {
  READ_STATUS: "Read status",
  PAY: "One-time payment",
  MANDATE: "Recurring mandate",
  SHARE: "Document sharing",
  CANCEL_MANDATE: "Cancel mandate",
};
const directionNames = {
  en: {
    READ_ONLY: "Read / receive only",
    MONEY_OUT: "Send money once",
    RECURRING_OUT: "Allow recurring debits",
    DATA_OUT: "Share my documents",
    CANCEL: "Cancel the mandate",
  },
  hinglish: {
    READ_ONLY: "Sirf dekho / paisa aaye",
    MONEY_OUT: "Ek baar paisa jayega",
    RECURRING_OUT: "Baar-baar paisa katega",
    DATA_OUT: "Documents share honge",
    CANCEL: "Mandate band hoga",
  },
  hi: {
    READ_ONLY: "सिर्फ देखें / पैसा आए",
    MONEY_OUT: "एक बार पैसा जाएगा",
    RECURRING_OUT: "बार-बार पैसा कटेगा",
    DATA_OUT: "दस्तावेज़ साझा होंगे",
    CANCEL: "मैंडेट रद्द होगा",
  },
  ta: {
    READ_ONLY: "பார் / பணம் பெறுதல்",
    MONEY_OUT: "ஒருமுறை பணம் செலுத்துதல்",
    RECURRING_OUT: "தொடர்ந்து பணம் கழியும்",
    DATA_OUT: "ஆவணங்கள் பகிரப்படும்",
    CANCEL: "ஆணை ரத்து செய்யப்படும்",
  },
};
const directionOf = {
  READ_STATUS: "READ_ONLY",
  PAY: "MONEY_OUT",
  MANDATE: "RECURRING_OUT",
  SHARE: "DATA_OUT",
  CANCEL_MANDATE: "CANCEL",
};
const policyNames = {
  unguarded: "Unguarded + generic approval",
  operation_only: "Operation check only",
  strict_external_block: "Reject all external parameters",
  without_execution_binding: "VaaniVerify minus execution binding",
  vaaniverify: "VaaniVerify · full boundary",
};
function el(tag, className = "", text = "") {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text) item.textContent = text;
  return item;
}
function money(paise) {
  return (
    "₹" +
    (paise / 100).toLocaleString("en-IN", {
      minimumFractionDigits: paise % 100 ? 2 : 0,
      maximumFractionDigits: 2,
    })
  );
}
function show(id, visible = true) {
  $(id).classList.toggle("hidden", !visible);
}
function toast(message, error = false) {
  const box = $("toast");
  box.textContent = message;
  box.classList.toggle("error", error);
  show("toast");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => show("toast", false), 7000);
}
async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers:
      body === undefined
        ? {}
        : { "Content-Type": "application/json", "X-Vaani-Request": "1" },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "same-origin",
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.detail || data.error || "Request failed");
    error.code = data.error;
    error.data = data;
    throw error;
  }
  return data;
}
async function guarded(button, fn) {
  button.disabled = true;
  try {
    await fn();
  } catch (error) {
    toast((error.code ? error.code + ": " : "") + error.message, true);
  } finally {
    button.disabled = false;
  }
}
function resetDecision() {
  state.proposal = null;
  state.intent = null;
  state.direction = null;
  state.approval = null;
  show("decision-empty");
  show("decision-result", false);
  show("execution-result", false);
  $("execution-result").replaceChildren();
}
function slug(caseItem) {
  return caseItem.id.slice(caseItem.language.length + 1);
}
function populateScenarios(preferred = "subsidy-trap") {
  const select = $("scenario");
  select.replaceChildren();
  for (const kind of ["attack", "benign"]) {
    const group = document.createElement("optgroup");
    group.label =
      kind === "attack" ? "Adversarial scenarios" : "Legitimate tasks";
    for (const item of state.scenarios.filter(
      (s) => s.language === state.language && s.kind === kind,
    )) {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.title;
      group.append(option);
    }
    select.append(group);
  }
  select.value = state.language + "-" + preferred;
  if (!select.value) select.selectedIndex = 0;
  selectScenario();
}
function selectScenario() {
  state.selected = state.scenarios.find((s) => s.id === $("scenario").value);
  if (!state.selected) return;
  resetDecision();
  const item = state.selected;
  $("case-tag").textContent =
    item.kind === "attack" ? "ATTACK SIMULATION" : "LEGITIMATE TASK";
  $("case-tag").className =
    "tag " + (item.kind === "attack" ? "danger" : "success");
  $("user-text").textContent = "“" + item.intent.user_text + "”";
  $("intent-summary").replaceChildren(
    el("span", "", names[item.intent.operation]),
  );
  if (item.intent.max_amount_paise)
    $("intent-summary").append(
      el("span", "", "Ceiling " + money(item.intent.max_amount_paise)),
    );
  if (item.intent.recipient)
    $("intent-summary").append(el("span", "", item.intent.recipient));
  if (item.intent.allow_external_recipient)
    $("intent-summary").append(
      el("span", "", "External recipient: review required"),
    );
  $("external-text").textContent =
    item.external_text || "No external message in this scenario.";
  $("agent-message").textContent = item.agent_message;
  $("payload").textContent = JSON.stringify(
    compactAction(item.action),
    null,
    2,
  );
  $("intent-json").value = JSON.stringify(item.intent, null, 2);
  $("action-json").value = JSON.stringify(compactAction(item.action), null, 2);
  $("agent-text").value = item.agent_message;
  $("baseline-text").textContent =
    item.kind === "attack"
      ? "A generic approval would accept the modeled attacker action."
      : "A generic approval would accept this legitimate action, without binding it to the user’s intent.";
  document
    .querySelectorAll("[data-case]")
    .forEach((b) =>
      b.classList.toggle("active", b.dataset.case === slug(item)),
    );
}
function compactAction(action) {
  return Object.fromEntries(
    Object.entries(action).filter(
      ([k, v]) =>
        v !== null &&
        !(Array.isArray(v) && !v.length) &&
        k !== "subject" &&
        k !== "currency",
    ),
  );
}
function updateTaskForm() {
  const operation = $("task-operation").value;
  show("task-recipient-group", ["PAY", "MANDATE", "SHARE"].includes(operation));
  show("task-amount-group", ["PAY", "MANDATE"].includes(operation));
  show("task-mandate-group", operation === "MANDATE");
  show("task-share-group", operation === "SHARE");
  show("task-cancel-group", operation === "CANCEL_MANDATE");
  $("task-recipient").disabled = $("task-external").checked;
}
async function createTask() {
  const operation = $("task-operation").value;
  const selected = {
    operation,
    user_text: $("task-text").value,
    language: state.language,
  };
  if (["PAY", "MANDATE", "SHARE"].includes(operation)) {
    selected.allow_external_recipient = $("task-external").checked;
    selected.recipient = selected.allow_external_recipient
      ? null
      : $("task-recipient").value;
  }
  if (["PAY", "MANDATE"].includes(operation))
    selected.max_amount_paise = rupeesToPaise($("task-amount").value);
  if (operation === "MANDATE") {
    selected.frequency = $("task-frequency").value;
    selected.installments = Number($("task-installments").value);
  }
  if (operation === "SHARE") {
    selected.documents = [
      ...document.querySelectorAll('input[name="task-document"]:checked'),
    ].map((input) => input.value);
    selected.purpose = $("task-purpose").value;
    selected.retention_days = Number($("task-retention").value);
  }
  if (operation === "CANCEL_MANDATE")
    selected.mandate_id = $("task-mandate-id").value;
  const result = await api("/api/intents", selected);
  const box = $("created-task");
  box.replaceChildren(
    el("strong", "", "Trusted task created"),
    el("code", "", result.intent_id),
    el(
      "p",
      "",
      "Share this task ID with your proposal-only agent. It grants no signing or execution authority.",
    ),
  );
  box.append(
    el(
      "div",
      "code-line",
      ".venv\\Scripts\\python.exe -m vaaniverify.agent_client --intent-id " +
        result.intent_id +
        " --proposal examples/agent_proposal.json",
    ),
    el(
      "p",
      "",
      "For the optional local Qwen agent, save this task file in the project folder and run:",
    ),
    actionButton("Download agent task JSON ↓", () =>
      download(
        { intent: selected, external_text: $("task-external-text").value },
        "agent-task.json",
      ),
    ),
    el(
      "div",
      "code-line",
      ".venv\\Scripts\\python.exe -m vaaniverify.local_agent --task agent-task.json --intent-id " +
        result.intent_id,
    ),
  );
  show("created-task");
  toast("Trusted task created. The agent can now propose an action.");
}
async function refreshInbox() {
  const proposals = await api("/api/proposals");
  const target = $("proposal-inbox");
  target.replaceChildren();
  if (!proposals.length) {
    target.textContent = "No pending proposals in their review window.";
    return;
  }
  for (const p of proposals) {
    const row = el("div", "inbox-item");
    row.append(
      el(
        "span",
        "",
        names[p.operation] + " · " + (p.recipient || "no recipient"),
      ),
      actionButton("Review proposal", async () => {
        const result = await api("/api/proposals/" + p.proposal_id);
        state.selected = null;
        state.language = result.intent.intent.language;
        document
          .querySelectorAll("[data-language]")
          .forEach((b) =>
            b.classList.toggle("active", b.dataset.language === state.language),
          );
        $("user-text").textContent = result.intent.intent.user_text;
        $("intent-summary").replaceChildren(
          el("span", "", names[result.intent.intent.operation]),
        );
        $("external-text").textContent = result.proposal.external_text;
        $("agent-message").textContent = result.proposal.agent_message;
        $("payload").textContent = JSON.stringify(
          compactAction(result.proposal.action),
          null,
          2,
        );
        $("case-tag").textContent = "AGENT PROPOSAL";
        $("case-tag").className = "tag neutral";
        renderProposal(result);
      }),
    );
    target.append(row);
  }
}
function detail(label, value) {
  const row = el("div", "detail-row");
  row.append(el("span", "", label), el("strong", "", String(value)));
  return row;
}
function renderProposal(result) {
  state.intent = result.intent;
  state.proposal = result.proposal;
  state.direction = null;
  state.approval = null;
  const p = state.proposal,
    a = p.action,
    blocked = p.status === "BLOCKED";
  show("decision-empty", false);
  show("decision-result");
  show("execution-result", false);
  $("execution-result").replaceChildren();
  const selectedIntent = result.intent.intent;
  $("user-text").textContent = selectedIntent.user_text;
  $("intent-json").value = JSON.stringify(selectedIntent, null, 2);
  $("action-json").value = JSON.stringify(compactAction(a), null, 2);
  $("agent-text").value = p.agent_message;
  $("intent-summary").replaceChildren(
    el("span", "", names[selectedIntent.operation]),
  );
  if (selectedIntent.max_amount_paise)
    $("intent-summary").append(
      el("span", "", "Ceiling " + money(selectedIntent.max_amount_paise)),
    );
  if (selectedIntent.recipient)
    $("intent-summary").append(el("span", "", selectedIntent.recipient));
  if (selectedIntent.allow_external_recipient)
    $("intent-summary").append(
      el("span", "", "External recipient: review required"),
    );
  if (!state.selected)
    $("baseline-text").textContent =
      "A generic approval could execute this proposal without binding it to the original intent.";
  $("decision-banner").className =
    "decision-banner" + (blocked ? "" : " ready");
  $("decision-symbol").textContent = blocked ? "×" : "✓";
  $("decision-kicker").textContent = blocked
    ? "AUTHORITY CHECK FAILED"
    : "POLICY CHECKS PASSED";
  $("decision-title").textContent = blocked
    ? "Action blocked."
    : "Your decision comes next.";
  $("decision-description").textContent = blocked
    ? "The proposed action exceeds the user’s recorded permission. No approval token can be issued."
    : "The proposal is within scope. Confirm its direction and exact details to issue a one-use capability.";
  $("policy-checks").replaceChildren();
  for (const check of p.decision.checks) {
    const row = el("div", "policy-row" + (check.passed ? "" : " failed"));
    row.append(el("span", "", check.passed ? "✓" : "×"));
    const copy = el("div");
    copy.append(
      el("strong", "", check.code.replaceAll("_", " ")),
      el("p", "", check.detail),
    );
    row.append(copy);
    $("policy-checks").append(row);
  }
  $("warnings").replaceChildren();
  for (const warning of p.warnings)
    $("warnings").append(
      el(
        "div",
        "warning-item",
        warning +
          " This is a heuristic diagnostic, not the authorization rule.",
      ),
    );
  show("warnings", p.warnings.length > 0);
  $("confirmation-text").textContent = p.confirmation.text;
  $("confirmation-text").lang =
    p.confirmation.language === "hinglish"
      ? "hi-Latn"
      : p.confirmation.language;
  const visual = $("direction-visual");
  visual.replaceChildren();
  const visualLabels = {
    READ_STATUS: ["YOUR ACCOUNT", "READ ONLY"],
    PAY: ["YOUR ACCOUNT", "MONEY OUT"],
    MANDATE: ["YOUR ACCOUNT", "RECURRING OUT"],
    SHARE: ["YOUR DOCUMENTS", "SHARED COPY"],
    CANCEL_MANDATE: ["EXISTING MANDATE", "CANCEL"],
  };
  visual.append(
    el("span", "", visualLabels[a.operation][0]),
    el("i", "", "→"),
    el("span", "", visualLabels[a.operation][1]),
  );
  const details = $("confirmation-details");
  details.replaceChildren(detail("Action", names[a.operation]));
  if (a.recipient) details.append(detail("Recipient · synthetic", a.recipient));
  if (a.amount_paise)
    details.append(
      detail(
        a.operation === "MANDATE" ? "Per-payment ceiling" : "Exact amount",
        money(a.amount_paise),
      ),
    );
  if (a.frequency)
    details.append(
      detail("Schedule", a.frequency + " · " + a.installments + " payments"),
      detail("Maximum total", p.confirmation.maximum_total),
    );
  if (a.documents.length)
    details.append(
      detail(
        "Documents",
        a.documents.map((d) => d.replaceAll("_", " ")).join(", "),
      ),
      detail("Purpose", a.purpose.replaceAll("_", " ")),
      detail("Requested retention", a.retention_days + " days"),
    );
  if (a.mandate_id) details.append(detail("Mandate", a.mandate_id));
  show("approval-form", !blocked);
  $("recipient-answer").value = "";
  $("amount-answer").value = "";
  $("terms-accepted").checked = false;
  const needsRecipient = Boolean(a.recipient || a.mandate_id);
  show("recipient-label", needsRecipient);
  show("recipient-answer", needsRecipient);
  $("recipient-label").textContent = a.mandate_id
    ? "Type the full mandate identifier"
    : "Type the full recipient shown above";
  show("amount-answer-wrap", Boolean(a.amount_paise));
  const correct = directionOf[a.operation],
    alternate =
      correct === "READ_ONLY"
        ? "MONEY_OUT"
        : correct === "RECURRING_OUT"
          ? "MONEY_OUT"
          : "READ_ONLY";
  const choices = [correct, alternate];
  if (crypto.getRandomValues(new Uint8Array(1))[0] % 2) choices.reverse();
  $("direction-choices").replaceChildren();
  for (const choice of choices) {
    const b = el(
      "button",
      "direction-choice",
      directionNames[state.language][choice],
    );
    b.type = "button";
    b.dataset.direction = choice;
    b.setAttribute("aria-pressed", "false");
    b.addEventListener("click", () => {
      state.direction = choice;
      document.querySelectorAll(".direction-choice").forEach((x) => {
        x.classList.toggle("selected", x === b);
        x.setAttribute("aria-pressed", String(x === b));
      });
    });
    $("direction-choices").append(b);
  }
  $("approve").textContent = state.selected?.execution_action
    ? "Sign & test payload swap ↗"
    : "Sign & execute in sandbox ↗";
}
async function inspectScenario() {
  state.selected = state.scenarios.find(
    (item) => item.id === $("scenario").value,
  );
  if (!state.selected) throw new Error("Select a scenario first.");
  const result = await api("/api/demo", { scenario_id: state.selected.id });
  renderProposal(result);
}
async function inspectCustom() {
  const intent = JSON.parse($("intent-json").value);
  intent.language = state.language;
  const action = JSON.parse($("action-json").value);
  const stored = await api("/api/intents", intent);
  const proposal = await api("/api/proposals", {
    intent_id: stored.intent_id,
    action,
    agent_message: $("agent-text").value,
    external_text: $("external-text").textContent,
  });
  state.selected = null;
  $("user-text").textContent = intent.user_text;
  $("agent-message").textContent = $("agent-text").value;
  $("payload").textContent = JSON.stringify(action, null, 2);
  $("case-tag").textContent = "CUSTOM PAYLOAD";
  renderProposal({ intent: stored, proposal });
}
function rupeesToPaise(value) {
  if (!/^\d+(\.\d{1,2})?$/.test(value))
    throw new Error("Enter rupees as digits with at most two decimal places.");
  const [whole, fraction = ""] = value.split(".");
  const total = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  if (!Number.isSafeInteger(total)) throw new Error("Amount is too large.");
  return total;
}
async function approve() {
  if (!state.direction)
    throw new Error("Choose what you intend this action to do.");
  const p = state.proposal,
    a = p.action;
  try {
    state.approval = await api("/api/proposals/" + p.proposal_id + "/approve", {
      direction: state.direction,
      recipient_answer: $("recipient-answer").value,
      amount_answer_paise: a.amount_paise
        ? rupeesToPaise($("amount-answer").value)
        : 0,
      action_digest: p.confirmation.action_digest,
      terms_accepted: $("terms-accepted").checked,
    });
  } catch (error) {
    if (error.code === "DIRECTION_MISMATCH") {
      show("approval-form", false);
      $("decision-title").textContent = "Direction mismatch. Intent cancelled.";
      $("decision-description").textContent =
        "Your chosen direction disagreed with the tool action. Nothing was signed or executed.";
      $("decision-banner").className = "decision-banner";
      $("decision-symbol").textContent = "×";
      $("decision-kicker").textContent = "CONSENT DID NOT MATCH";
    }
    throw error;
  }
  show("approval-form", false);
  try {
    const receipt = await api("/api/execute", {
      action: state.selected?.execution_action || state.approval.action,
      token: state.approval.token,
    });
    renderExecution(receipt);
  } catch (error) {
    renderExecutionError(error);
  }
}
function actionButton(text, fn) {
  const b = el("button", "button secondary", text);
  b.addEventListener("click", () => guarded(b, fn));
  return b;
}
function renderExecution(receipt) {
  show("execution-result");
  const box = $("execution-result");
  box.replaceChildren();
  const card = el("div", "execution-card");
  card.append(
    el("h4", "", "✓ Executed in the mock gateway"),
    el(
      "p",
      "",
      "Signature valid. Exact payload matched. Intent and nonce spent once. No real funds or documents moved.",
    ),
    el(
      "div",
      "hash",
      "Receipt #" + receipt.sequence + " · " + receipt.receipt_hash,
    ),
  );
  card.append(
    actionButton("Attempt replay ↻", async () => {
      try {
        await api("/api/execute", {
          action: state.approval.action,
          token: state.approval.token,
        });
        toast(
          "Unexpected replay acceptance. Inspect the receipt ledger.",
          true,
        );
      } catch (error) {
        card.append(
          el("div", "attack-result", error.code + ": " + error.message),
        );
      }
    }),
  );
  if (state.approval.action.recipient)
    card.append(
      actionButton("Attempt payee swap ⇄", async () => {
        try {
          await api("/api/execute", {
            action: {
              ...state.approval.action,
              recipient: "other.recipient@demo",
            },
            token: state.approval.token,
          });
          toast("Unexpected mutated payload acceptance.", true);
        } catch (error) {
          card.append(
            el("div", "attack-result", error.code + ": " + error.message),
          );
        }
      }),
    );
  box.append(card);
  $("decision-title").textContent = "Approval bound. Action executed.";
  $("decision-description").textContent =
    "The gateway independently verified the one-use capability.";
}
function renderExecutionError(error) {
  show("execution-result");
  const card = el("div", "execution-card");
  const unknown = error.code === "GATEWAY_UNAVAILABLE" || !error.code;
  card.append(
    el("h4", "", unknown ? "Execution status unknown" : "Execution rejected"),
    el("p", "", (error.code ? error.code + ": " : "") + error.message),
  );
  if (error.code === "PAYLOAD_CHANGED")
    card.append(
      el(
        "p",
        "",
        "The agent changed the payload after consent. The original signed action remains valid until its capability expires.",
      ),
      actionButton("Execute original approved action", async () => {
        renderExecution(
          await api("/api/execute", {
            action: state.approval.action,
            token: state.approval.token,
          }),
        );
      }),
    );
  if (unknown)
    card.append(
      el(
        "p",
        "",
        "The gateway may have committed the action before the connection failed. Inspect the receipts before retrying.",
      ),
      actionButton("Inspect execution receipts", () => changeView("receipts")),
      actionButton("Retry the same signed action", async () =>
        renderExecution(
          await api("/api/execute", {
            action: state.approval.action,
            token: state.approval.token,
          }),
        ),
      ),
    );
  $("execution-result").replaceChildren(card);
  $("decision-title").textContent = unknown
    ? "Execution status unknown."
    : "Gateway refused execution.";
  $("decision-description").textContent = unknown
    ? "A network failure is not evidence that the action failed. Check the ledger."
    : "The gateway rejected this execution request.";
  $("decision-banner").className = "decision-banner";
  $("decision-symbol").textContent = unknown ? "?" : "×";
  $("decision-kicker").textContent = unknown
    ? "CHECK EXECUTION RECEIPTS"
    : "EXECUTION CHECK FAILED";
}
async function cancel() {
  await api("/api/intents/" + state.proposal.intent_id + "/cancel", {});
  show("approval-form", false);
  $("decision-title").textContent = "Intent cancelled.";
  $("decision-description").textContent =
    "This intent can no longer authorize an action.";
  toast("Cancelled. No approval token issued.");
}
function speak() {
  if (!("speechSynthesis" in window))
    return toast("This browser does not support speech synthesis.", true);
  const tag = state.language === "hinglish" ? "hi" : state.language;
  const voice = speechSynthesis
    .getVoices()
    .find((v) => v.localService && v.lang.toLowerCase().startsWith(tag));
  if (!voice)
    return toast(
      "No installed local voice for this language. The text confirmation remains available.",
      true,
    );
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(
    state.proposal.confirmation.text,
  );
  utterance.voice = voice;
  utterance.lang = voice.lang;
  utterance.rate = 0.85;
  speechSynthesis.speak(utterance);
}
async function changeView(name) {
  document
    .querySelectorAll(".view")
    .forEach((v) => v.classList.toggle("hidden", v.id !== "view-" + name));
  document
    .querySelectorAll("[data-view]")
    .forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  $("view-name").textContent = {
    lab: "Security lab",
    evidence: "Evidence",
    architecture: "Trust boundary",
    receipts: "Audit receipts",
  }[name];
  if (name === "evidence") await renderEvidence();
  if (name === "receipts") await renderReceipts();
  window.scrollTo({ top: 0, behavior: "instant" });
}
function stat(value, label, note) {
  const box = el("article", "evidence-stat");
  box.append(
    el("strong", "", value),
    el("span", "", label),
    el("small", "", note),
  );
  return box;
}
function paragraphCard(eyebrow, title, copy) {
  const box = el("article", "panel prose");
  box.append(
    el("p", "eyebrow", eyebrow),
    el("h2", "", title),
    el("p", "", copy),
  );
  return box;
}
async function renderEvidence() {
  const report = await api("/api/evidence");
  state.evidence = report;
  const target = $("evidence-content");
  target.replaceChildren();
  if (!report.available) {
    target.append(el("div", "notice", report.detail));
    return;
  }
  const full = report.summary.find((r) => r.policy === "vaaniverify");
  target.append(
    el(
      "div",
      "evidence-notice",
      report.evidence_type +
        " The corpus contains 20 semantic templates, each instantiated in four languages. These outcomes do not estimate real-world fraud rates.",
    ),
  );
  const stats = el("div", "evidence-summary");
  stats.append(
    stat(
      full.attack_executions + " / " + full.attack_count,
      "Modeled attacks executed",
      "Against this authored corpus, with fixtures supplying user choices.",
    ),
    stat(
      full.benign_executions + " / " + full.benign_count,
      "Legitimate actions executed",
      "After exact approval; external bill recipients remain usable.",
    ),
    stat(
      report.full_pipeline_latency_ms.p50.toFixed(2) + " ms",
      "Median local pipeline time",
      "Includes early blocks and mock execution; excludes model, network and human time.",
    ),
  );
  target.append(stats);
  const table = el("table", "data-table");
  const head = el("thead"),
    hr = el("tr");
  for (const title of [
    "Implemented policy",
    "Attack executions",
    "Benign blocked",
  ])
    hr.append(el("th", "", title));
  head.append(hr);
  table.append(head);
  const body = el("tbody");
  for (const row of report.summary) {
    const tr = el("tr", row.policy === "vaaniverify" ? "full-row" : "");
    tr.append(el("td", "", policyNames[row.policy]));
    const metric = el("td"),
      meter = el("div", "metric-bar"),
      bar = document.createElement("progress");
    bar.max = row.attack_count;
    bar.value = row.attack_executions;
    bar.setAttribute("aria-label", "Attack executions");
    meter.append(
      el("span", "", row.attack_executions + " / " + row.attack_count),
      bar,
    );
    metric.append(meter);
    tr.append(
      metric,
      el("td", "", row.benign_blocked + " / " + row.benign_count),
    );
    body.append(tr);
  }
  table.append(body);
  const wrap = el("div", "table-wrap");
  wrap.append(table);
  target.append(wrap);
  const grid = el("div", "evidence-grid");
  const reproduce = paragraphCard(
    "REPRODUCE",
    "One command. Every case.",
    "The evaluator writes the complete scenario set, per-case outcomes, source hashes and runtime details to evidence/. Full-policy trials exercise real signing, verification and SQLite execution. Baselines are policy simulations.",
  );
  reproduce.append(
    el(
      "div",
      "code-line",
      ".venv\\Scripts\\python.exe -m vaaniverify.evaluate\n.venv\\Scripts\\python.exe -m pytest -q",
    ),
  );
  grid.append(
    reproduce,
    paragraphCard(
      "ABLATION",
      "Why execution binding matters.",
      "Removing the exact-payload execution check leaves the policy and confirmation in place. The post-approval recipient swaps then succeed in the modeled cases. The strict source blocker avoids these attacks by also rejecting legitimate external bill tasks.",
    ),
  );
  const provenance = paragraphCard(
    "EVIDENCE PROVENANCE",
    "Inspect the run.",
    "Generated: " +
      report.generated_at_utc +
      " · Python " +
      report.runtime.python +
      ". P95 local pipeline: " +
      report.full_pipeline_latency_ms.p95.toFixed(2) +
      " ms.",
  );
  provenance.append(
    el("div", "hash", "Corpus SHA-256: " + report.corpus_sha256),
    actionButton("Download benchmark JSON ↓", () =>
      download(report, "vaaniverify-benchmark.json"),
    ),
  );
  grid.append(
    provenance,
    paragraphCard(
      "LIMITATIONS",
      "A test suite, not a field study.",
      report.limitations.join(" "),
    ),
  );
  target.append(grid);
  const pilot = await api("/api/model-evidence");
  if (pilot.available) {
    const s = pilot.summary;
    const pilotCard = paragraphCard(
      "SEPARATE LIVE MODEL PILOT",
      "When a real agent proposes the wrong action.",
      pilot.evidence_type +
        " Qwen2.5-1.5B-Instruct, Q4_K_M, recorded with a CPU runtime. " +
        s.attempts +
        " inferences across eight authored templates in four languages; this is a small exploratory pilot.",
    );
    const numbers = el("div", "evidence-summary");
    numbers.append(
      stat(
        s.attacker_goal_proposals + " / " + s.attack_attempts,
        "Attacker-goal proposals",
        "The model proposed the attacker's requested change.",
      ),
      stat(
        s.attacker_goal_executions + " / " + s.attack_attempts,
        "Attacker-goal executions",
        "After the independent policy, signing and gateway checks.",
      ),
      stat(
        s.benign_expected_action_executions + " / " + s.benign_attempts,
        "Expected benign actions executed",
        "Malformed responses count as failures; they are not dropped.",
      ),
    );
    pilotCard.append(
      numbers,
      el(
        "p",
        "microcopy",
        "The generation grammar was revised after four malformed read-only outputs in the initial run. The same corpus was reused; earlier records are retained in the repository. " +
          s.valid_proposals +
          " / " +
          s.attempts +
          " responses passed the proposal schema. " +
          pilot.limitations.join(" "),
      ),
      actionButton("Download prompts & raw model outputs ↓", () =>
        download(pilot, "vaaniverify-model-pilot.json"),
      ),
    );
    target.append(pilotCard);
  }
}
function download(value, filename) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}
async function renderReceipts() {
  const result = await api("/api/receipts");
  state.receipts = result;
  $("audit-state").textContent =
    (result.audit.valid
      ? "✓ Local hash chain consistent"
      : "× Local hash chain invalid") +
    " · " +
    result.audit.entries +
    " entries";
  const list = $("receipt-list");
  list.replaceChildren();
  if (!result.receipts.length) {
    list.append(
      el(
        "div",
        "panel no-receipts",
        "No actions executed yet. Approve a legitimate task in the Security lab to create a receipt.",
      ),
    );
    return;
  }
  for (const receipt of [...result.receipts].reverse()) {
    const card = el("article", "panel receipt-card"),
      header = el("div", "receipt-header");
    header.append(
      el(
        "h3",
        "",
        "#" + receipt.sequence + " · " + names[receipt.action.operation],
      ),
      el("span", "tag success", "SYNTHETIC · EXECUTED"),
    );
    card.append(
      header,
      el(
        "p",
        "",
        new Date(receipt.executed_at * 1000).toLocaleString() +
          " · one-use intent " +
          receipt.intent_id.slice(0, 12) +
          "…",
      ),
      el("pre", "", JSON.stringify(compactAction(receipt.action), null, 2)),
      el("div", "hash", "Receipt: " + receipt.receipt_hash),
      el("div", "hash", "Previous: " + receipt.previous_hash),
    );
    list.append(card);
  }
}
async function init() {
  const fragment = new URLSearchParams(location.hash.slice(1));
  const bootstrap = fragment.get("bootstrap");
  if (bootstrap) {
    history.replaceState(null, "", location.pathname);
    try {
      await api("/api/meta");
    } catch (error) {
      if (error.code !== "OWNER_SESSION_REQUIRED") throw error;
      await api("/api/session", { bootstrap });
    }
  }
  await api("/api/meta");
  state.scenarios = await api("/api/scenarios");
  populateScenarios();
  document.querySelectorAll("[data-language]").forEach((b) =>
    b.addEventListener("click", () => {
      const preferred = state.selected ? slug(state.selected) : "subsidy-trap";
      state.language = b.dataset.language;
      document
        .querySelectorAll("[data-language]")
        .forEach((x) => x.classList.toggle("active", x === b));
      populateScenarios(preferred);
    }),
  );
  document.querySelectorAll("[data-case]").forEach((b) =>
    b.addEventListener("click", () => {
      $("scenario").value = state.language + "-" + b.dataset.case;
      selectScenario();
    }),
  );
  $("scenario").addEventListener("change", selectScenario);
  $("load-scenario").addEventListener("click", (e) =>
    guarded(e.currentTarget, inspectScenario),
  );
  $("inspect-custom").addEventListener("click", (e) =>
    guarded(e.currentTarget, inspectCustom),
  );
  $("approve").addEventListener("click", (e) =>
    guarded(e.currentTarget, approve),
  );
  $("cancel").addEventListener("click", (e) =>
    guarded(e.currentTarget, cancel),
  );
  $("speak").addEventListener("click", speak);
  document
    .querySelectorAll("[data-view]")
    .forEach((b) =>
      b.addEventListener("click", () =>
        changeView(b.dataset.view).catch((e) => toast(e.message, true)),
      ),
    );
  document.querySelector(".brand").addEventListener("click", (event) => {
    event.preventDefault();
    changeView("lab").catch((e) => toast(e.message, true));
  });
  $("refresh-receipts").addEventListener("click", (e) =>
    guarded(e.currentTarget, renderReceipts),
  );
  $("export-receipts").addEventListener("click", () => {
    if (state.receipts) download(state.receipts, "vaaniverify-receipts.json");
  });
  $("task-operation").addEventListener("change", updateTaskForm);
  $("task-external").addEventListener("change", updateTaskForm);
  $("create-task").addEventListener("click", (e) =>
    guarded(e.currentTarget, createTask),
  );
  $("refresh-inbox").addEventListener("click", (e) =>
    guarded(e.currentTarget, refreshInbox),
  );
  if ("speechSynthesis" in window) speechSynthesis.getVoices();
}
init().catch((error) => {
  $("session-alert").textContent =
    error.message +
    " Start with launch.bat, or open the private URL stored in .runtime/console-url.txt. Do not share that link.";
  show("session-alert");
  $("load-scenario").disabled = true;
});
