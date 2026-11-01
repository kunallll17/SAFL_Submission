"use strict";

const scene = document.getElementById("action-scene");
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const translations = {
  en: "Money leaves your account. Pay ₹500 once to utility.board@demo.",
  hi: "पैसा जाएगा। आपके खाते से ₹500 एक बार utility.board@demo को जाएंगे।",
  hinglish: "PAISA JAYEGA. Aapke account se ₹500 ek baar utility.board@demo ko jayega.",
  ta: "பணம் வெளியே செல்லும். உங்கள் கணக்கிலிருந்து ₹500, utility.board@demo க்கு ஒருமுறை செலுத்தப்படும்.",
};
let timer = null;
let phase = 0;
let inView = false;
let hasPlayed = false;

function finishScene() {
  clearTimeout(timer);
  phase = 4;
  scene.dataset.phase = "4";
  document.getElementById("scene-announcement").textContent = document.getElementById("verdict-title").textContent;
}
function advance() {
  clearTimeout(timer);
  if (document.hidden || !inView || phase >= 4) return;
  timer = setTimeout(() => {
    phase += 1;
    scene.dataset.phase = String(phase);
    if (phase === 4) finishScene(); else advance();
  }, phase === 0 ? 500 : 750);
}
function play() {
  clearTimeout(timer);
  hasPlayed = true;
  phase = 0;
  scene.dataset.phase = "0";
  document.getElementById("scene-announcement").textContent = "";
  if (reducedMotion.matches) finishScene(); else advance();
}
function setCase(value) {
  const swap = value === "swap";
  scene.dataset.case = value;
  document.getElementById("scene-recipient").textContent = swap ? "cashback.claim@demo" : "utility.board@demo";
  document.getElementById("recipient-check").textContent = swap ? "Recipient changed" : "Exact recipient";
  document.getElementById("verdict-title").textContent = swap ? "Blocked before approval" : "Ready for your review";
  document.getElementById("verdict-copy").textContent = swap ? "The recipient changed. Your permission did not." : "Within your permission. Still needs your approval.";
  document.getElementById("verdict-glyph").setAttribute("d", swap ? "m9 9 6 6m0-6-6 6" : "m8 12 3 3 5-6");
  document.querySelectorAll("[data-case][aria-pressed]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.case === value)));
  play();
}

// A single short sequence, not a perpetual animation. Only active while visible.
if (!reducedMotion.matches && "IntersectionObserver" in window) {
  document.documentElement.classList.add("motion-ready");
  const sceneObserver = new IntersectionObserver((entries) => {
    inView = entries[0].isIntersecting;
    if (!inView) clearTimeout(timer);
    else if (!hasPlayed) play();
    else advance();
  }, { threshold: .25 });
  sceneObserver.observe(scene);
  const revealObserver = new IntersectionObserver((entries, observer) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("visible");
      observer.unobserve(entry.target);
    }
  }, { threshold: .1 });
  document.querySelectorAll(".reveal").forEach((item) => revealObserver.observe(item));
} else {
  inView = true;
  finishScene();
}
document.addEventListener("visibilitychange", () => { if (document.hidden) clearTimeout(timer); else advance(); });
reducedMotion.addEventListener("change", () => {
  if (reducedMotion.matches) {
    document.documentElement.classList.remove("motion-ready");
    finishScene();
  }
});
document.getElementById("replay").addEventListener("click", play);
document.querySelectorAll("button[data-case]").forEach((button) => button.addEventListener("click", () => setCase(button.dataset.case)));
document.querySelectorAll("button[data-language]").forEach((button) => button.addEventListener("click", () => {
  const paragraph = document.getElementById("translation");
  paragraph.textContent = translations[button.dataset.language];
  paragraph.lang = button.dataset.language === "hinglish" ? "hi-Latn" : button.dataset.language;
  document.querySelectorAll("button[data-language]").forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
  if (!reducedMotion.matches && paragraph.animate) {
    paragraph.getAnimations().forEach((animation) => animation.cancel());
    paragraph.animate([{ opacity: .2, transform: "translateY(4px)" }, { opacity: 1, transform: "translateY(0)" }], { duration: 250, easing: "ease-out" });
  }
}));

// Exchange the launch fragment here so navigation to /demo keeps the owner session.
// The public landing page never needs private APIs unless a launch token is present.
async function exchangeLaunchLink() {
  const bootstrap = new URLSearchParams(location.hash.slice(1)).get("bootstrap");
  if (!bootstrap) return;
  history.replaceState(null, "", location.pathname);
  try {
    const existing = await fetch("/api/meta", { credentials: "same-origin" });
    if (existing.ok) return;
    if (existing.status !== 403) throw new Error("The local console is unavailable.");
    const result = await fetch("/api/session", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-Vaani-Request": "1" }, body: JSON.stringify({ bootstrap }) });
    if (!result.ok) throw new Error("This launch link has expired or was already used. Open the existing demo session or restart launch.bat.");
  } catch (error) {
    const notice = document.getElementById("session-notice");
    notice.textContent = error.message;
    notice.hidden = false;
  }
}
const sessionReady = exchangeLaunchLink();
// A fast click must not race the session exchange or carry credentials in a URL.
document.querySelectorAll('a[href="/demo"], a[href="/lab"]').forEach((link) => link.addEventListener("click", async (event) => {
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  await sessionReady;
  location.assign(link.getAttribute("href"));
}));
