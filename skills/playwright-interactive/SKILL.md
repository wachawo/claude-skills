---
name: "playwright-interactive"
description: "Persistent browser and Electron interaction via `js_repl` for fast iterative UI debugging."
---

# Playwright Interactive Skill

Use a persistent Playwright `js_repl` session to debug local web or Electron apps, keep the same handles between iterations, and run functional and visual QA without restarting the entire toolchain unless process ownership has actually changed.

## Prerequisites

- `js_repl` must be enabled for this skill.
- If `js_repl` is missing, enable it in `~/.codex/config.toml`:

```toml
[features]
js_repl = true
```

- You can also start a new session with `--enable js_repl` (equivalent to `-c features.js_repl=true`).
- After enabling `js_repl`, start a new Codex session so the tool list refreshes.
- For now, run this workflow with the sandbox disabled: launch Codex with `--sandbox danger-full-access` (or the equivalent configuration for `sandbox_mode=danger-full-access`). This is a temporary requirement while `js_repl` + Playwright support inside the sandbox is still being finalized.
- Run setup from the same project directory you intend to debug.
- Treat `js_repl_reset` as a recovery tool, not routine cleanup. Resetting the kernel destroys your Playwright handles.

## One-time setup

```bash
test -f package.json || npm init -y
npm install playwright
# Web-only, for headed Chromium or mobile emulation:
# npx playwright install chromium
# Electron-only, and only if the target workspace is the app itself:
# npm install --save-dev electron
node -e "import('playwright').then(() => console.log('playwright import ok')).catch((error) => { console.error(error); process.exit(1); })"
```

If you later switch to a different workspace, repeat setup there.

## Main workflow

1. Before testing, build a brief QA inventory:
   - Build the inventory from three sources: user-requested requirements, user-facing functionality or behavior actually implemented, and claims you plan to make in the final response.
   - Anything that appears in any of these three sources must map to at least one QA check before signoff.
   - List the user-facing claims you intend to sign off on.
   - List every meaningful user-facing control, mode toggle, or implemented interactive behavior.
   - List the state or view changes each control or implemented behavior can produce.
   - Use this as the shared coverage list for both functional QA and visual QA.
   - For each "claim or control state" pair, note the intended functional check, the specific state in which the visual check should occur, and the evidence you plan to capture.
   - If a requirement is visually central but subjective, convert it into an observable QA check rather than leaving it implicit.
   - Add at least 2 exploratory or off-happy-path scenarios that could reveal brittle behavior.
2. Run the bootstrap cell once.
3. Start or confirm the necessary dev server in a persistent TTY session.
4. Launch the desired runtime and continue reusing the same Playwright handles.
5. After each code change, reload for renderer-only changes or relaunch for main-process / startup changes.
6. Run functional QA with normal user input.
7. Run a separate visual QA pass.
8. Verify viewport conformance and capture the screenshots needed to support your claims.
9. Clean up the Playwright session only when the task is genuinely complete.

## Bootstrap (run once)

```javascript
var chromium;
var electronLauncher;
var browser;
var context;
var page;
var mobileContext;
var mobilePage;
var electronApp;
var appWindow;

try {
  ({ chromium, _electron: electronLauncher } = await import("playwright"));
  console.log("Playwright loaded");
} catch (error) {
  throw new Error(
    `Could not load playwright from the current js_repl cwd. Run the setup commands from this workspace first. Original error: ${error}`
  );
}
```

Binding rules:

- Use `var` for shared top-level Playwright handles, because subsequent `js_repl` cells reuse them.
- The setup cells below intentionally describe a short happy path. If a handle looks stale, set that binding to `undefined` and re-run the cell rather than scattering recovery logic everywhere.
- Prefer one named handle per surface of interest (`page`, `mobilePage`, `appWindow`) rather than re-discovering pages from a context.

Shared web helpers:

```javascript
var resetWebHandles = function () {
  context = undefined;
  page = undefined;
  mobileContext = undefined;
  mobilePage = undefined;
};

var ensureWebBrowser = async function () {
  if (browser && !browser.isConnected()) {
    browser = undefined;
    resetWebHandles();
  }

  browser ??= await chromium.launch({ headless: false });
  return browser;
};

var reloadWebContexts = async function () {
  for (const currentContext of [context, mobileContext]) {
    if (!currentContext) continue;
    for (const p of currentContext.pages()) {
      await p.reload({ waitUntil: "domcontentloaded" });
    }
  }
  console.log("Reloaded existing web tabs");
};
```

## Choosing a session mode

For web apps, default to an explicit viewport, and treat native window mode as a separate validation pass.

- Use an explicit viewport for routine iterations, breakpoint validation, reproducible screenshots, snapshot diffs, and model-assisted localization. This is the default because it is stable across machines and avoids host window-manager variability.
- When you need deterministic high-DPI behavior, keep an explicit viewport and add `deviceScaleFactor`, rather than switching to native window mode.
- Use native window mode (`viewport: null`) for a separate headed pass when you need to verify launch window size, OS-level DPI behavior, browser chrome interactions, or bugs that may depend on host display configuration.
- For Electron, always assume native window behavior. Electron is launched through Playwright with `noDefaultViewport`, so treat it as a real desktop window and verify size and layout at launch before changing anything.
- When signoff depends on both layout breakpoints and real desktop behavior, do both passes: explicit viewport first for deterministic QA, then native-window validation for environment-specific final checks.
- Treat mode changes as a context reset. Do not reuse a viewport-emulated `context` for a native-window pass or vice versa; close the old `page` and `context`, then create new ones for the new mode.

## Starting or reusing a web session

Desktop and mobile web sessions share the same `browser`, helpers, and QA flow. The main difference is which context and page pair you create.

### Desktop web context

Set `TARGET_URL` for the application you are debugging. For local servers, prefer `127.0.0.1` over `localhost`.

```javascript
var TARGET_URL = "http://127.0.0.1:3000";

if (page?.isClosed()) page = undefined;

await ensureWebBrowser();
context ??= await browser.newContext({
  viewport: { width: 1600, height: 900 },
});
page ??= await context.newPage();

await page.goto(TARGET_URL, { waitUntil: "domcontentloaded" });
console.log("Loaded:", await page.title());
```

If `context` or `page` are stale, set `context = page = undefined` and re-run the cell.

### Mobile web context

Reuse `TARGET_URL` if it already exists; otherwise specify the mobile target directly.

```javascript
var MOBILE_TARGET_URL = typeof TARGET_URL === "string"
  ? TARGET_URL
  : "http://127.0.0.1:3000";

if (mobilePage?.isClosed()) mobilePage = undefined;

await ensureWebBrowser();
mobileContext ??= await browser.newContext({
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
});
mobilePage ??= await mobileContext.newPage();

await mobilePage.goto(MOBILE_TARGET_URL, { waitUntil: "domcontentloaded" });
console.log("Loaded mobile:", await mobilePage.title());
```

If `mobileContext` or `mobilePage` are stale, set `mobileContext = mobilePage = undefined` and re-run the cell.

### Native-window web pass

```javascript
var TARGET_URL = "http://127.0.0.1:3000";

await ensureWebBrowser();

await page?.close().catch(() => {});
await context?.close().catch(() => {});
page = undefined;
context = undefined;

browser ??= await chromium.launch({ headless: false });
context = await browser.newContext({ viewport: null });
page = await context.newPage();

await page.goto(TARGET_URL, { waitUntil: "domcontentloaded" });
console.log("Loaded native window:", await page.title());
```

## Starting or reusing an Electron session

Set `ELECTRON_ENTRY` to `.` when the current workspace is the Electron app itself and `package.json` points `main` at the correct entry file. If you need to target a specific main-process file directly, use a path such as `./main.js`.

```javascript
var ELECTRON_ENTRY = ".";

if (appWindow?.isClosed()) appWindow = undefined;

if (!appWindow && electronApp) {
  await electronApp.close().catch(() => {});
  electronApp = undefined;
}

electronApp ??= await electronLauncher.launch({
  args: [ELECTRON_ENTRY],
});

appWindow ??= await electronApp.firstWindow();

console.log("Loaded Electron window:", await appWindow.title());
```

If `js_repl` is not running from the Electron app workspace, pass `cwd` explicitly at launch.

If the application process looks stale, set `electronApp = appWindow = undefined` and re-run the cell.

If you already have an Electron session but need a fresh process after changing main-process, preload, or startup code, use the restart cell in the next section instead of re-running this one.

## Reusing sessions between iterations

Keep the same session alive whenever possible.

Reload the web renderer:

```javascript
await reloadWebContexts();
```

Reload only the Electron renderer:

```javascript
await appWindow.reload({ waitUntil: "domcontentloaded" });
console.log("Reloaded Electron window");
```

Restart Electron after main-process, preload, or startup changes:

```javascript
await electronApp.close().catch(() => {});
electronApp = undefined;
appWindow = undefined;

electronApp = await electronLauncher.launch({
  args: [ELECTRON_ENTRY],
});

appWindow = await electronApp.firstWindow();
console.log("Relaunched Electron window:", await appWindow.title());
```

If launch requires an explicit `cwd`, include the same `cwd` here.

Default behavior:

- Keep each `js_repl` cell short and focused on a single burst of interaction.
- Reuse existing top-level bindings (`browser`, `context`, `page`, `electronApp`, `appWindow`) rather than redeclaring them.
- If you need isolation, create a new page or new context inside the same browser.
- For Electron, use `electronApp.evaluate(...)` only for main-process inspection or specialized diagnostics.
- Fix errors in helpers in place; do not reset the REPL unless the kernel is genuinely broken.

## Checklists

### Session loop

- Run the `js_repl` bootstrap once, then keep the same Playwright handles alive between iterations.
- Launch the target runtime from the current workspace.
- Make a code change.
- Reload or relaunch using the right path for that change.
- Update the shared QA inventory if exploration revealed an additional control, state, or visible claim.
- Re-run functional QA.
- Re-run visual QA.
- Capture final artifacts only after the current state is the one you are evaluating.

### Reload decision

- Renderer-only change: reload the existing page or Electron window.
- Main-process, preload, or startup change: relaunch Electron.
- New uncertainty about process ownership or startup code: relaunch instead of guessing.

### Functional QA

- Use real user-facing controls for signoff: keyboard, mouse, click, touch, or equivalent Playwright input APIs.
- Verify at least one critical end-to-end flow.
- Confirm the visible result of that flow, not just internal state.
- For real-time or animation-heavy apps, verify behavior under realistic interaction timing.
- Work from the shared QA inventory, not ad-hoc spot checks.
- Cover every obvious visible control at least once before signoff, not just the primary happy path.
- For reversible controls or stateful toggles in the inventory, test the full cycle: original state, changed state, and return to original state.
- After scripted checks pass, run a short exploratory pass with normal input for 30–90 seconds, not following only the planned path.
- If exploration reveals a new state, control, or claim, add it to the shared QA inventory and cover it before signoff.
- `page.evaluate(...)` and `electronApp.evaluate(...)` may inspect or set up state, but do not count as input for signoff.

### Visual QA

- Treat visual QA as separate from functional QA.
- Use the same shared QA inventory defined before testing and updated during QA; do not start visual coverage with a different implicit list.
- Restate user-facing claims and verify each explicitly; do not assume a functional pass proves a visual claim.
- A user-facing claim is not signed off until it has been inspected in the specific state in which it is meant to be perceived.
- Inspect the initial viewport before scrolling.
- Confirm the initial view visually supports the main interface claims; if a key promised element is not clearly perceivable there, treat that as a bug.
- Inspect all required visible regions, not only the main interaction surface.
- Inspect the states and modes already listed in the shared QA inventory, including at least one meaningful post-interaction state when the task is interactive.
- If motion or transitions are part of the experience, inspect at least one in-transition state in addition to the steady-state endpoints.
- If labels, overlays, annotations, guides, or highlights must track changing content, verify that relationship after a corresponding state change.
- For dynamic or interaction-dependent visuals, inspect long enough to judge stability, layering, and readability; do not rely on a single screenshot for signoff.
- For interfaces that may become denser after loading or interaction, inspect the densest realistic state reachable during QA, not just the empty, loading, or collapsed state.
- If the product has a defined minimum supported viewport or window size, run a separate visual QA pass there; otherwise pick a smaller but still realistic size and inspect it explicitly.
- Distinguish presence from execution: if an intended affordance is technically present but not clearly perceivable due to weak contrast, overlap, clipping, or instability, treat that as a visual failure.
- If any required visible region is clipped, cut off, hidden, or pushed outside the viewport in the evaluated state, treat that as a bug, even if page-level scroll metrics look acceptable.
- Look for clipping, overflow, distortion, layout imbalance, inconsistent spacing, alignment issues, illegible text, weak contrast, broken layering, and awkward motion states.
- Evaluate aesthetic quality, not just correctness. The UI should feel intentional, cohesive, and visually pleasant for the task.
- Prefer viewport screenshots for signoff. Use full-page captures only as secondary debugging artifacts, and take a focused screenshot when a region requires closer inspection.
- If motion makes a screenshot ambiguous, briefly wait for the UI to settle, then capture the image you actually intend to evaluate.
- Before signoff, ask explicitly: which visible part of this interface have I not yet inspected up close?
- Before signoff, ask explicitly: which visible defect would most likely embarrass this result if a user looked carefully?

### Signoff

- A functional path passed under normal user input.
- Coverage was explicitly mapped to the shared QA inventory: note which requirements, implemented features, controls, states, and claims were exercised, and explicitly state any intentional exclusions.
- The visual QA pass covered the entire relevant interface.
- Every user-facing claim has a matching visual check and an inspected screenshot artifact from the state and viewport or window size in which the claim matters.
- Viewport conformance checks passed for the intended initial view and any required minimum supported viewport or window size.
- If the product launches in a window, the launch size, placement, and initial layout were verified before any manual resize or move.
- The UI is not merely functional; it is visually cohesive and not aesthetically weak for the task.
- Functional correctness, viewport conformance, and visual quality must each pass on their own; one does not imply the others.
- For interactive products, a short exploratory pass was completed and the response mentions what that pass covered.
- If screenshot review and numeric checks ever disagreed, the discrepancy was investigated before signoff; visible clipping in screenshots is a failure to address, not something metrics can override.
- Include a brief negative confirmation of the main defect classes you checked and did not find.
- Cleanup was performed, or the session was intentionally left alive for further work.

## Screenshot examples

If you plan to deliver a screenshot through `codex.emitImage(...)`, default to the CSS-normalized paths in the next section. These are the canonical examples for screenshots that will be interpreted by the model or used for subsequent coordinate-based actions. Keep raw captures as an exception only for precision-sensitive debugging; raw screenshot exception examples appear after the normalization guidance.

### Screenshots for the model (default)

If you will deliver a screenshot through `codex.emitImage(...)` for model interpretation, normalize it to CSS pixels for the exact region you captured before delivery. This keeps any returned coordinates aligned with Playwright's CSS pixels if the response is later used for clicks, and reduces image payload size and model token cost.

Do not deliver raw native-window screenshots by default. Skip normalization only when you explicitly need device-pixel accuracy, e.g., for debugging Retina or DPI artifacts, inspecting pixel-accurate rendering, or another precision-sensitive case where raw pixels matter more than payload size. For local inspection that will not be delivered to the model, a raw capture is fine.

Do not assume `page.screenshot({ scale: "css" })` is sufficient in native window mode (`viewport: null`). On Chromium with macOS Retina displays, headed native-window screenshots can still come back at device-pixel size even when `scale: "css"` is requested. The same caveat applies to Electron windows launched through Playwright, because Electron operates with `noDefaultViewport`, and `appWindow.screenshot({ scale: "css" })` may still return device-pixel output.

Use separate normalization paths for web pages and Electron windows:

- Web: prefer `page.screenshot({ scale: "css" })` directly. If a native-window Chromium still returns device-pixel output, resize inside the current page through canvas; a scratch page is not required.
- Electron: do not use `appWindow.context().newPage()` or `electronApp.context().newPage()` as a scratch page. Electron contexts do not reliably support that path. Capture in the main process via `BrowserWindow.capturePage(...)`, resize via `nativeImage.resize(...)`, and deliver those bytes directly.

Common helpers and conventions:

```javascript
var emitJpeg = async function (bytes) {
  await codex.emitImage({
    bytes,
    mimeType: "image/jpeg",
    detail: "original",
  });
};

var emitWebJpeg = async function (surface, options = {}) {
  await emitJpeg(await surface.screenshot({
    type: "jpeg",
    quality: 85,
    scale: "css",
    ...options,
  }));
};

var clickCssPoint = async function ({ surface, x, y, clip }) {
  await surface.mouse.click(
    clip ? clip.x + x : x,
    clip ? clip.y + y : y
  );
};

var tapCssPoint = async function ({ page, x, y, clip }) {
  await page.touchscreen.tap(
    clip ? clip.x + x : x,
    clip ? clip.y + y : y
  );
};
```

- Use `page` or `mobilePage` for web, or `appWindow` for Electron, as the `surface`.
- Treat `clip` as CSS pixels from `getBoundingClientRect()` in the renderer.
- Prefer JPEG with `quality: 85` unless lossless precision is specifically required.
- For full-image captures, use the returned `{ x, y }` directly.
- For cropped captures, add the clip origin back when clicking.

### CSS normalization for web

The preferred web path for explicit-viewport contexts, and often for web in general:

```javascript
await emitWebJpeg(page);
```

Mobile web uses the same path; substitute `mobilePage` for `page`:

```javascript
await emitWebJpeg(mobilePage);
```

If the model returns `{ x, y }`, click directly:

```javascript
await clickCssPoint({ surface: page, x, y });
```

Click path for mobile web:

```javascript
await tapCssPoint({ page: mobilePage, x, y });
```

For web screenshots with `clip`, or element screenshots on this normal path, `scale: "css"` usually works directly. Add the region origin back when clicking.

- `await emitWebJpeg(page, { clip })`
- `await emitWebJpeg(mobilePage, { clip })`
- `await clickCssPoint({ surface: page, clip, x, y })`
- `await tapCssPoint({ page: mobilePage, clip, x, y })`
- `await clickCssPoint({ surface: page, clip: box, x, y })` after `const box = await locator.boundingBox()`

Fallback for native web window when `scale: "css"` still comes back at device-pixel size:

```javascript
var emitWebScreenshotCssScaled = async function ({ page, clip, quality = 0.85 } = {}) {
  var NodeBuffer = (await import("node:buffer")).Buffer;
  const target = clip
    ? { width: clip.width, height: clip.height }
    : await page.evaluate(() => ({
        width: window.innerWidth,
        height: window.innerHeight,
      }));

  const screenshotBuffer = await page.screenshot({
    type: "png",
    ...(clip ? { clip } : {}),
  });

  const bytes = await page.evaluate(
    async ({ imageBase64, targetWidth, targetHeight, quality }) => {
      const image = new Image();
      image.src = `data:image/png;base64,${imageBase64}`;
      await image.decode();

      const canvas = document.createElement("canvas");
      canvas.width = targetWidth;
      canvas.height = targetHeight;

      const ctx = canvas.getContext("2d");
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(image, 0, 0, targetWidth, targetHeight);

      const blob = await new Promise((resolve) =>
        canvas.toBlob(resolve, "image/jpeg", quality)
      );

      return new Uint8Array(await blob.arrayBuffer());
    },
    {
      imageBase64: NodeBuffer.from(screenshotBuffer).toString("base64"),
      targetWidth: target.width,
      targetHeight: target.height,
      quality,
    }
  );

  await emitJpeg(bytes);
};
```

For a fallback full-viewport capture, treat the returned `{ x, y }` as direct CSS coordinates:

```javascript
await emitWebScreenshotCssScaled({ page });
await clickCssPoint({ surface: page, x, y });
```

For a fallback cropped capture, add the clip origin back:

```javascript
await emitWebScreenshotCssScaled({ page, clip });
await clickCssPoint({ surface: page, clip, x, y });
```

### CSS normalization for Electron

For Electron, normalize in the main process instead of opening a Playwright scratch page. The helper below returns CSS-scaled bytes for the entire content area or for a clipped region in CSS pixels. Treat `clip` as CSS pixels of the content area, e.g., values taken from `getBoundingClientRect()` in the renderer.

```javascript
var emitElectronScreenshotCssScaled = async function ({ electronApp, clip, quality = 85 } = {}) {
  const bytes = await electronApp.evaluate(async ({ BrowserWindow }, { clip, quality }) => {
    const win = BrowserWindow.getAllWindows()[0];
    const image = clip ? await win.capturePage(clip) : await win.capturePage();

    const target = clip
      ? { width: clip.width, height: clip.height }
      : (() => {
          const [width, height] = win.getContentSize();
          return { width, height };
        })();

    const resized = image.resize({
      width: target.width,
      height: target.height,
      quality: "best",
    });

    return resized.toJPEG(quality);
  }, { clip, quality });

  await emitJpeg(bytes);
};
```

Full Electron window:

```javascript
await emitElectronScreenshotCssScaled({ electronApp });
await clickCssPoint({ surface: appWindow, x, y });
```

Cropped Electron region using CSS pixels from the renderer:

```javascript
var clip = await appWindow.evaluate(() => {
  const rect = document.getElementById("board").getBoundingClientRect();
  return {
    x: Math.round(rect.x),
    y: Math.round(rect.y),
    width: Math.round(rect.width),
    height: Math.round(rect.height),
  };
});

await emitElectronScreenshotCssScaled({ electronApp, clip });
await clickCssPoint({ surface: appWindow, clip, x, y });
```

### Raw screenshot exception examples

Use these only when raw pixels matter more than CSS-coordinate alignment, e.g., for debugging Retina or DPI artifacts, inspecting pixel-accurate rendering, or other precision-sensitive review.

Raw delivery from desktop web:

```javascript
await codex.emitImage({
  bytes: await page.screenshot({ type: "jpeg", quality: 85 }),
  mimeType: "image/jpeg",
  detail: "original",
});
```

Raw delivery from Electron:

```javascript
await codex.emitImage({
  bytes: await appWindow.screenshot({ type: "jpeg", quality: 85 }),
  mimeType: "image/jpeg",
  detail: "original",
});
```

Raw mobile delivery once a mobile web context is already running:

```javascript
await codex.emitImage({
  bytes: await mobilePage.screenshot({ type: "jpeg", quality: 85 }),
  mimeType: "image/jpeg",
  detail: "original",
});
```

## Viewport conformance checks (required)

Do not assume a screenshot is acceptable just because the main widget is visible. Before signoff, explicitly verify that the intended initial view satisfies the product's requirement, using both screenshot review and numeric checks.

- Define the intended initial view before signoff. For scrollable pages, this is the above-the-fold experience. For app-like shells, games, editors, dashboards, or tools, this is the full interactive surface plus the controls and status needed to use it.
- Use screenshots as the primary evidence of conformance. Numeric checks support screenshots; they do not override visible clipping.
- Signoff fails if any required visible region is clipped, cut off, hidden, or pushed outside the viewport in the intended initial view, even if page-level scroll metrics look acceptable.
- Scrolling is acceptable when the product is designed to scroll and the initial view still conveys the main experience and reveals the primary call to action or required starting context.
- For fixed-shell interfaces, scrolling is not an acceptable workaround if it is needed to access part of the main interactive surface or essential controls.
- Do not rely on document scroll metrics alone. Fixed-height shells, internal panels, and hidden-overflow containers can clip required UI while page-level scroll checks still look clean.
- Verify region bounds, not just document bounds. Confirm that every required visible region fits inside the viewport in the starting state.
- For Electron or desktop apps, verify both the launch window size and placement and the renderer's initial visible layout before any manual resize or move.
- Passing viewport conformance checks only proves that the intended initial view is visible without unintended clipping or scrolling. It does not prove that the UI is visually correct or aesthetically successful.

Check for web or renderer:

```javascript
console.log(await page.evaluate(() => ({
  innerWidth: window.innerWidth,
  innerHeight: window.innerHeight,
  clientWidth: document.documentElement.clientWidth,
  clientHeight: document.documentElement.clientHeight,
  scrollWidth: document.documentElement.scrollWidth,
  scrollHeight: document.documentElement.scrollHeight,
  canScrollX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  canScrollY: document.documentElement.scrollHeight > document.documentElement.clientHeight,
})));
```

Check for Electron:

```javascript
console.log(await appWindow.evaluate(() => ({
  innerWidth: window.innerWidth,
  innerHeight: window.innerHeight,
  clientWidth: document.documentElement.clientWidth,
  clientHeight: document.documentElement.clientHeight,
  scrollWidth: document.documentElement.scrollWidth,
  scrollHeight: document.documentElement.scrollHeight,
  canScrollX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  canScrollY: document.documentElement.scrollHeight > document.documentElement.clientHeight,
})));
```

Supplement the numeric check with `getBoundingClientRect()` checks for required visible regions in your specific UI when clipping is a realistic failure mode; document-level metrics alone are not enough for fixed shells.

## Dev server

For local web debugging, keep the app running in a persistent TTY session. Do not rely on one-off background commands from a short-lived shell.

Use the project's normal start command, e.g.:

```bash
npm start
```

Before `page.goto(...)`, verify the chosen port is listening and the app responds.

For Electron debugging, launch the app from `js_repl` via `_electron.launch(...)` so the same session owns the process. If the Electron renderer depends on a separate dev server (e.g., Vite or Next), keep that server running in a persistent TTY session and then restart or reload the Electron app from `js_repl`.

## Cleanup

Run cleanup only when the task is genuinely complete:

- Cleanup is manual. Exiting Codex, closing the terminal, or losing the `js_repl` session does not implicitly trigger `electronApp.close()`, `context.close()`, or `browser.close()`.
- For Electron specifically, assume the app may keep running if you leave the session without first running the cleanup cell.

```javascript
if (electronApp) {
  await electronApp.close().catch(() => {});
}

if (mobileContext) {
  await mobileContext.close().catch(() => {});
}

if (context) {
  await context.close().catch(() => {});
}

if (browser) {
  await browser.close().catch(() => {});
}

browser = undefined;
context = undefined;
page = undefined;
mobileContext = undefined;
mobilePage = undefined;
electronApp = undefined;
appWindow = undefined;

console.log("Playwright session closed");
```

If you plan to exit Codex right after debugging, run the cleanup cell first and wait for the `"Playwright session closed"` log before exiting.

## Common failure modes

- `Cannot find module 'playwright'`: run the one-time setup in the current workspace and verify the import before using `js_repl`.
- Playwright package installed but the browser executable is missing: run `npx playwright install chromium`.
- `page.goto: net::ERR_CONNECTION_REFUSED`: confirm the dev server is still running in a persistent TTY session, double-check the port, and prefer `http://127.0.0.1:<port>`.
- `electron.launch` hangs, times out, or exits immediately: check the local `electron` dependency, confirm the `args` target, and ensure any renderer dev server is already running before launch.
- `Identifier has already been declared`: reuse existing top-level bindings, choose a new name, or wrap the code in `{ ... }`. Use `js_repl_reset` only when the kernel is genuinely stuck.
- `browserContext.newPage: Protocol error (Target.createTarget): Not supported` when working with Electron: do not use `appWindow.context().newPage()` or `electronApp.context().newPage()` as a scratch page; use the Electron-specific screenshot normalization flow in the screenshots-for-the-model section.
- `js_repl` timed out or reset: re-run the bootstrap cell and rebuild the session with shorter, more focused cells.
- Browser launch or network operations fail immediately: confirm the session was started with `--sandbox danger-full-access`, and restart with that flag if needed.
