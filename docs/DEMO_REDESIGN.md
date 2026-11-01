# VaaniVerify demo redesign

The previous interface combined a marketing page, security workbench, agent integration guide and approval form. The primary task was hidden below the fold and required downloading JSON, running a third terminal and refreshing an inbox.

## Direction

- Product: help a person review an agent's actual action before approving it.
- Character: calm, precise, approachable.
- World: payment forms, permission slips and receipts.
- Moments: the user-selected permission and the resulting action, with color reserved for meaningful decisions.
- Signature: an explicit comparison of permission and proposal.

Use the existing vanilla HTML/CSS/JavaScript and Python service. A visual-only cleanup would leave the terminal workflow intact. Replacing the application framework would add unnecessary scope. The chosen implementation provides a dedicated landing page, a guided demo with in-browser local inference at `/demo`, and the complete workbench at `/lab`.

The guided demo flow is task → review → receipt. Show relevant permission fields for the chosen operation, one primary action per step, a readable confirmation and explicit rejection. Keep evidence, raw JSON, attack tools and integration instructions in the security lab. Language selection changes the trusted confirmation; it does not imply full interface translation.

The browser may request generation against a stored owner-created intent. Model output still passes the existing strict schema and kernel policy. Generation cannot sign or execute. Exact recipient, amount, direction and terms confirmation remain mandatory. Inference stays on the existing local Qwen server; errors must never silently fall back to preset results.

Apply spacing, neutral surfaces, restrained icons, shorter copy, readable type, task hierarchy, control details, product-derived visuals and limited motion in that order. No remote fonts, new runtime dependencies or generated imagery.

Verify owner/agent role isolation, generation success and failure, out-of-scope blocking, concurrent inference and cancellation during generation. Exercise the rendered desktop and mobile flow, including a live model proposal and mock execution. Preserve the existing gateway and signing tests.

Design process adapted from **unslop by Damir Sokolovsky**, [heydamir/unslop](https://github.com/heydamir/unslop), licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The task hierarchy is intentionally changed to address the user's explicit UX redesign request.

## Verification — 1 November 2026

- Complete Python suite: **114 passed**, with the existing Starlette/httpx deprecation warning. The Windows process-tree check failed inside the restricted process sandbox and passed when rerun with normal process permissions; the complete suite then passed in that environment.
- An isolated Brave browser exercised a real local Qwen payment proposal, rejected an incorrect confirmation amount, executed the correctly approved mock payment, and displayed the single new receipt in Activity.
- Real local inference also exercised document sharing followed by rejection, and Hindi confirmation followed by a deliberately wrong direction. Both rejection flows ended without execution.
- Controlled browser fixtures verified the blocked-proposal interface and model-unavailable recovery. These are UI failure-path checks, not additional model attack measurements.
- Layout checked at widths 1440, 1280, 1024, 768, 390 and 360 pixels, with no horizontal overflow. Mobile shows one stage at a time. Screenshots: `output/playwright/demo-desktop.png`, `demo-mobile.png`, and `demo-result.png` (the result screenshot predates the final compact spacing adjustment).
- No browser JavaScript errors in the checked flows. JavaScript syntax, duplicate Python definitions, replacement characters, trailing whitespace, and preservation of the original lab JavaScript/CSS were checked.
- The updated service is running on the normal console/gateway ports 8765/8766. The existing local model server remains on 8770. The temporary preview services were stopped. Windows was locked at handoff; no further desktop interaction was attempted after detecting the lock screen.

The redesign does not change the recorded benchmark corpus or regenerate the submission PDF/ZIP. Those existing artifacts describe the earlier interface. It adds no production connection, cloud inference or runtime dependency. Temporary browser verification tools are under ignored `tmp/`.


## Landing page and motion - 1 November 2026

The root page now introduces the product before asking a visitor to set a task. The hero visual derives from the actual consent model: a fixed permission, a proposed payment, and the result of comparing them. Its safe/swap controls are explicitly labelled as an illustration; they do not run inference or create a transaction. The language preview uses the existing authored confirmation strings for English, Hindi, Hinglish and Tamil.

The guided interface was moved intact to `/demo`. The landing page exchanges the private launch fragment for the existing owner cookie, removes the fragment, and waits for that exchange before normal navigation to the demo or lab. Public pages do not confer private API access. The lab's return link points to `/demo`.

Animation uses CSS, IntersectionObserver and the browser's Web Animations API. The illustration is one finite sequence, can be replayed, and stops advancing when offscreen or when the document is hidden. Scroll reveals run once. Reduced motion presents the completed illustration without animation and disables animated scrolling. Static landing content remains readable without JavaScript. The demo adds a running indicator and short stage transitions that honor reduced motion.

Verification for this change:

- Full Python suite: **115 passed**, with the existing Starlette/httpx deprecation warning.
- Isolated Brave checked launch-token exchange, fragment removal, both illustrated outcomes, replay, offscreen pause, all four language previews, and the landing-to-demo handoff with the owner session intact.
- A real local Qwen payment proposal was generated through `/demo` and rejected without execution.
- No horizontal overflow at widths 1440, 1280, 1024, 800, 768, 520, 390 and 360 pixels. Desktop and mobile screenshots were visually inspected.
- Reduced motion showed a completed illustration with zero active animations. JavaScript-disabled landing content remained available. No external requests or JavaScript page errors occurred in the checked flows.
- Landing HTML, CSS, JavaScript and SVG total approximately **36 KB uncompressed**. This is a file-size measurement, not a Lighthouse or real-user performance score. No runtime packages, external fonts, images or animation libraries were added.
- Screenshots: `output/playwright/landing-desktop.png`, `landing-full.png`, and `landing-mobile.png`. The full-page and mobile captures show the recipient-swap example.

Existing submission PDF/ZIP and benchmark results were not regenerated. The illustration is product explanation, not an additional security evaluation.
