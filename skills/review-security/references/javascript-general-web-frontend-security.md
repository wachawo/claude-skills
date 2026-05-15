# Frontend JavaScript/TypeScript Security Specification (Vanilla Browser JS/TS, modern browsers)

This document is intended as a **security specification** that supports:

1. **Secure-by-default code generation** for new frontend JavaScript/TypeScript (not tied to a specific framework).
2. **Security review / vulnerability hunting** in existing frontend code (both passive "spot issues while working" mode and active "scan the repo and produce a report" mode).

The document is intentionally written as a set of **normative requirements** ("MUST/SHOULD/MAY") plus **audit rules** (what bad patterns look like, how to detect them, and how to fix or mitigate them).

---

## 0) Safety, Boundaries, and Anti-Abuse Constraints (MUST FOLLOW)

* MUST NOT request, output, log, hardcode, or commit secrets (API keys that are supposed to be secret, private keys, passwords, OAuth refresh tokens, session tokens, cookies).
  Notes:

  * Frontend code is inherently observable to end users. If a value must remain secret, it must not be in code shipped to the browser.
  * If the project uses "public" keys (for example, publishable analytics keys), they MUST be treated as non-secret and scoped accordingly.

* MUST NOT "fix" security by disabling protections (for example, weakening CSP via `unsafe-inline`/`unsafe-eval` without justification, removing origin checks for `postMessage`, switching to `innerHTML` for convenience, accepting arbitrary redirects/URLs, or disabling sanitization).

* MUST provide **evidence-based findings** when auditing: cite file paths, code snippets, and relevant HTML/CSP/configuration values that justify the claim.

* MUST be honest about uncertainty:

  * Security headers (CSP, frame-ancestors, etc.) may be set on the server/edge/CDN rather than in repo code. If they are not visible, report it as "not visible here; verify the runtime/edge configuration". (Also note that `<meta http-equiv=...>` only simulates a subset of headers; do not assume other security headers exist just because a meta tag is present.) ([MDN Web Docs][1])

---

## 1) Modes of Operation

### 1.1 Generation Mode (default)

When asked to write new frontend JS/TS code or modify existing code:

* MUST follow every **MUST** requirement in this specification.
* SHOULD follow every **SHOULD** requirement unless the user explicitly states otherwise.
* MUST prefer secure-by-default browser APIs and proven libraries over hand-rolled security code (especially for HTML sanitization).
* MUST avoid introducing new risky sinks (DOM XSS injection sinks such as `innerHTML`, navigation to `javascript:` URLs, dynamic code execution via `eval`/`Function`, unsafe `postMessage`, unsafe loading of third-party scripts, etc.). ([OWASP Cheat Sheet Series][2])

### 1.2 Passive Review Mode (always on while editing)

When working anywhere in a frontend repository (even if the user did not request a security scan):

* MUST "spot" violations of this specification in edited or adjacent code.
* SHOULD raise issues as they arise, with a brief explanation and a safe fix.

### 1.3 Active Audit Mode (explicit scan request)

When the user asks to "scan", "audit", or "hunt for vulnerabilities":

* MUST systematically search the codebase for violations of this specification.
* MUST output findings in a structured format (see §2.3).

Recommended audit order:

1. HTML entry points (`index.html`, server-rendered templates), script/style includes, and any CSP delivery mechanism (header vs. meta). ([W3C][3])
2. DOM XSS sinks (`innerHTML`, `document.write`, `insertAdjacentHTML`, event-handler attributes) and their data sources (URL params/hash, storage, postMessage, API responses). ([OWASP Cheat Sheet Series][2])
3. Navigation/redirect handling (`window.location*`, link targets, URL allowlists), including the dangers of `javascript:` URLs. ([MDN Web Docs][4])
4. Cross-origin communication (`postMessage`, iframe-embedding patterns, sandboxing). ([MDN Web Docs][5])
5. Sensitive data storage (localStorage/sessionStorage) and trust assumptions. ([OWASP Cheat Sheet Series][6])
6. Third-party scripts / tag managers / CDNs, integrity controls (SRI), and policy controls (CSP). ([OWASP Cheat Sheet Series][7])
7. DOM clobbering gadgets and unsafe reliance on named `window`/`document` properties. ([OWASP Cheat Sheet Series][8])

---

## 2) Definitions and Review Guidance

### 2.1 Untrusted Input (treated as attacker-controlled by default)

Examples:

* Data derived from URLs: `location.href`, `location.search`, `location.hash`, `document.baseURI`, `new URLSearchParams(location.search)`, routing fragments. ([OWASP Cheat Sheet Series][2])
* DOM content that may contain user markup (comments, profiles, CMS content, markdown-to-HTML output, etc.), particularly when injected dynamically. ([OWASP Cheat Sheet Series][2])
* `postMessage` event data (`event.data`) and metadata (`event.origin`) from other windows/frames. ([MDN Web Docs][5])
* Browser storage: `localStorage`, `sessionStorage`, IndexedDB (contents may be attacker-influenced via XSS or local machine access; never assume "trusted"). ([OWASP Cheat Sheet Series][6])
* Any data from network calls (even from "your own API"), because it may contain stored attacker content that becomes dangerous only when injected into the DOM. ([OWASP Cheat Sheet Series][2])

### 2.2 Dangerous Sink (DOM XSS / code-execution sink)

A sink is any API/operation that may execute scripts or interpret attacker-controlled strings as HTML/JS/URL in a security-sensitive way. High-signal sinks:

* HTML parsing/insertion: `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `document.writeln`. ([OWASP Cheat Sheet Series][2])
* Dynamic code execution: `eval`, `new Function`, `setTimeout("...")`, `setInterval("...")`. ([MDN Web Docs][10])
* Navigation to script-bearing URLs (for example, `javascript:`) via setters such as `Location.href`/`window.location` (and via link `href` attributes when attacker-controlled). ([MDN Web Docs][4])
* Setting event-handler attributes from strings, for example `setAttribute("onclick", "...")`. ([OWASP Cheat Sheet Series][2])

### 2.3 Required Audit-Finding Format

For each issue found, output:

* Rule ID:
* Severity: Critical / High / Medium / Low
* Location: file path + function/class/module + line(s)
* Evidence: exact code/config snippet
* Impact: what can go wrong, who can exploit it
* Fix: safe change (preferably a minimal diff)
* Mitigation: defense-in-depth if an immediate fix is difficult
* False positive notes: what to verify when uncertain

---

## 3) Secure Baseline: Minimum Production Configuration (MUST in production)

This is the minimum baseline that prevents common frontend JS/TS misconfigurations. Some items live "in the repo" (HTML/JS); some may live on the server/edge.

### 3.1 Baseline Content Security Policy (CSP) (SHOULD; MUST for high-risk applications)

* SHOULD deliver CSP via HTTP response headers when possible.
* MAY deliver CSP via an HTML `<meta http-equiv="Content-Security-Policy" ...>` when headers cannot be set (for example, pure-static-hosting limitations). ([MDN Web Docs][1])
* When using CSP via `<meta http-equiv>`, MUST understand the limitations:

  * The policy applies only to content that follows the meta element (so it must appear very early, before any scripts/resources you want it to govern). ([W3C][3])
  * The following directives are **not supported** in a policy delivered via meta and will be ignored: `report-uri`, `frame-ancestors`, and `sandbox`. ([W3C][3])
  * "Report-only" CSP cannot be set via a meta element. ([W3C][3])

Practical baseline goals:

* Avoid the script sources `unsafe-inline` and `unsafe-eval` (they substantially weaken CSP's value against XSS). ([MDN Web Docs][10])
* Prefer nonce/hash-based script policies if inline scripts are needed. ([MDN Web Docs][10])
* Consider enabling Trusted Types enforcement where possible. ([MDN Web Docs][11])

### 3.2 Third-Party Script Baseline (SHOULD)

* SHOULD minimize third-party script execution and treat it as having privileges equivalent to first-party JS (it runs with your origin's privileges). ([OWASP Cheat Sheet Series][7])
* SHOULD use Subresource Integrity (SRI) for third-party scripts/styles served from a CDN. ([MDN Web Docs][12])

### 3.3 Cross-Window Communication Baseline (SHOULD)

* SHOULD restrict `postMessage` communications to explicit origins and validate both the origin and the message shape. ([MDN Web Docs][5])

---

## 4) Rules (generation + audit)

Each rule contains: required practice, insecure patterns, detection hints, and remediation.

### JS-XSS-001: Do not inject untrusted HTML into the DOM (avoid `innerHTML` and similar)

Severity: Critical if attacker-controlled input can be shown to reach these APIs; otherwise Medium


Required:

* MUST treat `innerHTML`, `outerHTML`, and `insertAdjacentHTML` as dangerous sinks when their input may contain untrusted data. ([OWASP Cheat Sheet Series][2])
* MUST prefer safe DOM APIs that do not parse HTML:

  * `textContent` for text. ([OWASP Cheat Sheet Series][2])
  * `document.createElement`, `appendChild`, `setAttribute` for non-event-handler attributes. ([OWASP Cheat Sheet Series][2])
* If HTML insertion is genuinely required, SHOULD sanitize via a well-vetted HTML sanitizer and seriously consider applying Trusted Types to constrain usage to audited code paths. ([MDN Web Docs][11])

Insecure patterns:

* `el.innerHTML = userInput`
* `el.insertAdjacentHTML('beforeend', userInput)`
* `el.outerHTML = userInput`

Detection hints:

* Look for: `.innerHTML`, `.outerHTML`, `insertAdjacentHTML(`.
* Trace the source of the inserted string: URL params/hash, postMessage, storage, API responses, DOM attributes. ([OWASP Cheat Sheet Series][2])

Fix:

* Replace with `textContent` for plain text. ([OWASP Cheat Sheet Series][2])
* For structured UI, build DOM nodes explicitly.
* For "rich text" requirements:

  * Sanitize via an allowlist-based sanitizer.
  * Prefer returning safe "components" rather than arbitrary HTML strings.
  * Use Trusted Types enforcement so that only `TrustedHTML` reaches sinks where supported. ([MDN Web Docs][11])

Mitigation:

* Deploy a strict CSP and consider Trusted Types enforcement (`require-trusted-types-for 'script'`). ([MDN Web Docs][10])

False-positive notes:

* If the string is provably constant or composed entirely from trusted constants, it may be safe. Still prefer the safer APIs.

---

### JS-XSS-002: Avoid `document.write` / `document.writeln` (XSS + document-clobbering hazards)

Severity: Critical if attacker-controlled input can be shown to reach these APIs; otherwise Medium

Required:

* MUST avoid `document.write()` and `document.writeln()` in production code (they are XSS vectors and can be exploited via crafted HTML, even if some browsers in some situations block injected `<script>`). ([MDN Web Docs][13])
* If legacy use is unavoidable, MUST ensure untrusted input does not reach these APIs and SHOULD apply Trusted Types (`TrustedHTML`) where supported. ([MDN Web Docs][14])

Insecure patterns:

* `document.write(userInput)`
* `document.writeln(getParam('q'))`

Detection hints:

* Look for `document.write(`, `document.writeln(`. ([OWASP Cheat Sheet Series][2])

Fix:

* Replace with DOM manipulations (`createElement`, `appendChild`) or safe text insertion (`textContent`). ([OWASP Cheat Sheet Series][2])

Mitigation:

* A strict CSP + Trusted Types enforcement reduces blast radius if a sink remains. ([MDN Web Docs][10])

---

### JS-XSS-003: Do not execute code from strings (`eval`, `new Function`, string-form timeouts)

Severity: Critical if attacker-controlled input can be shown to reach these APIs; otherwise Medium

Required:

* MUST NOT pass untrusted data to:

  * `eval()`
  * `new Function(...)`
  * `setTimeout("...")` / `setInterval("...")` with string arguments ([MDN Web Docs][10])
* SHOULD avoid these APIs entirely in modern frontend code; refactor to non-eval logic. ([MDN Web Docs][10])
* MUST NOT "fix CSP breakage" by adding `unsafe-eval` unless there is a documented and reviewed justification with compensating controls. ([MDN Web Docs][10])

Insecure patterns:

* `eval(userInput)`
* `new Function("return " + userInput)()`
* `setTimeout(userInput, 0)` where userInput is a string

Detection hints:

* Look for `eval(`, `new Function`, `setTimeout("`, `setInterval("`.
* Look for the construction of code strings for later use.

Fix:

* Replace dynamic code with:

  * structured data + explicit branching/handlers,
  * `JSON.parse` instead of `eval` for JSON. ([OWASP Cheat Sheet Series][2])

Mitigation:

* A CSP that blocks eval-level APIs by default and avoidance of `unsafe-eval`. ([MDN Web Docs][10])
* Consider Trusted Types for controlled cases, but treat it as a hardening layer rather than a license to keep eval patterns. ([MDN Web Docs][10])

---

### JS-XSS-004: Do not set event-handler attributes from strings (for example, `setAttribute("onclick", "...")`)

Severity: High

Required:

* MUST NOT use `setAttribute("on...", string)` or similar patterns with untrusted data; this turns strings into executable code in the event-handler context. ([OWASP Cheat Sheet Series][2])
* SHOULD prefer `addEventListener` with function references.

Insecure patterns:

* `el.setAttribute("onclick", userInput)`
* `el.onclick = userControlledString` (string assignment)

Detection hints:

* Look for `.setAttribute("on`, `.onclick =`, `.onmouseover =`, etc.
* Trace whether the right-hand side may be influenced by URL/hash/storage/postMessage. ([OWASP Cheat Sheet Series][2])

Fix:

* Replace with `addEventListener("click", () => { ... })`.
* If dynamic dispatch is required, use an allowlist mapping from identifiers to functions (no eval-strings). ([OWASP Cheat Sheet Series][2])

---

### JS-URL-001: Sanitize and allowlist URLs before navigation (especially `window.location` / `location.replace`)

Severity: Low (High if the attacker can be shown to fully control the URL)

IMPORTANT: This may produce many false positives. Perform additional analysis to determine whether the URL is fully attacker-controlled. If not, this is at best an informational finding.

NOTE: Redirecting to any given URL may be important functionality. If that is the feature's purpose, at minimum verify the scheme even if the origin can vary.

Required:

* MUST treat any assignment to navigation targets as security-sensitive:

  * `window.location = ...`
  * `location.href = ...`
  * `location.assign(...)`
  * `location.replace(...)` ([MDN Web Docs][4])
* MUST prevent navigation to `javascript:` URLs (and to other script-bearing/active schemes in general), particularly when the input is derived from URL params, storage, or messages. ([MDN Web Docs][4]). Allow only `http:` and `https:`.
* SHOULD validate/allowlist the destination. A safe baseline:

  * Allow only same-origin relative paths, OR
  * Allow only a strict allowlist of origins and protocols (typically `https:` and optionally `http:` for localhost dev). ([OWASP Cheat Sheet Series][8])

Insecure patterns:

* `location.replace(getParam("next"))`
* `window.location = userSuppliedUrl`
* `location.assign(window.redirectTo || "/")` where `redirectTo` may be "clobbered" or attacker-set ([OWASP Cheat Sheet Series][8])

Detection hints:

* Look for `window.location`, `location.href`, `location.assign`, `location.replace`.
* Look for typical redirect parameters: `next`, `returnTo`, `redirect`, `url`, `continue`.
* Look for literal `javascript:` usage. ([MDN Web Docs][4])

Fix:

* Parse and validate via `new URL(value, location.origin)`, then enforce:

  * `url.protocol` is in `{ "https:" }` (and include `http:` only in explicit dev-only code paths),
  * `url.origin` equals `location.origin` for internal redirects, or is in a strict allowlist for external ones,
  * optionally allow only specific path prefixes. ([MDN Web Docs][4])
* On validation failure, redirect to a safe default (home/dashboard).

Mitigation:

* Deploy a strict CSP and Trusted Types enforcement to reduce the impact of DOM XSS sinks, but note that Trusted Types alone do not prevent every possible unsafe-navigation scenario. ([W3C][15])

False-positive notes:

IMPORTANT: This may produce many false positives. Perform additional analysis to determine whether the URL is fully attacker-controlled. If not, this is at best an informational finding.

* Some applications intentionally support external redirects (SSO, payment flows). They MUST be on an allowlist and documented.

---

### JS-URL-002: Sanitize URLs before injecting into DOM URL contexts (`href`, `src`, etc.)

Severity: Low (High if the attacker can be shown to fully control the URL)

IMPORTANT: This may produce many false positives. Perform additional analysis to determine whether the URL is fully attacker-controlled. If not, this is at best an informational finding.

Required:

* MUST treat setting URL-bearing DOM attributes/properties as security-sensitive, particularly:

  * `a.href`, `img.src`, `script.src`, `iframe.src`, `form.action`, `link.href`.
* MUST prevent script-bearing schemes (`javascript:` and other active schemes) when the values may be attacker-influenced. ([MDN Web Docs][4])
* SHOULD prefer property assignments (for example, `a.href = url.toString()`) after parsing and validation, rather than string concatenation.

Insecure patterns:

* `link.href = getParam("u")`
* `el.setAttribute("href", userInput)` without validation
* URL construction via concatenation with untrusted parts

Detection hints:

* Look for `.href =`, `.src =`, `.action =`, `setAttribute("href"`, `setAttribute("src"`.
* Look for `javascript:` / `data:` usage in URLs. ([MDN Web Docs][4])

IMPORTANT: This may produce many false positives. Perform additional analysis to determine whether the URL is fully attacker-controlled. If not, this is at best an informational finding.

Fix:

* Use `new URL(...)` and validate:

  * a protocol allowlist
  * never pass user values into `<script src>` (treat that as code execution). ([OWASP Cheat Sheet Series][8])

---

### JS-CSP-001: Use CSP; meta delivery is acceptable

Severity: Medium-High (depending on threat model; High when handling untrusted content)

NOTE: The most important header to set is the CSP `script-src`. All other directives are less important and can usually be omitted in favor of development convenience.

Required:

* SHOULD deploy CSP as the primary defense-in-depth against XSS. ([MDN Web Docs][10])
* MAY provide CSP via `<meta http-equiv="Content-Security-Policy" ...>` when headers are unavailable. ([MDN Web Docs][1])
* If CSP is delivered via meta, MUST:

  * place it early (before scripts/resources you want to govern), and
  * not rely on directives that are unsupported in meta (`report-uri`, `frame-ancestors`, `sandbox`). ([W3C][3])
* MUST avoid adding `unsafe-inline` as a "quick fix" for CSP issues unless explicitly required and reviewed (it negates much of CSP's purpose). ([MDN Web Docs][10])
* MUST avoid adding `unsafe-eval` unless explicitly required and reviewed (it permits eval-level APIs that are commonly exploited). ([MDN Web Docs][10])

Insecure patterns:

* CSP completely absent (HTML repo or server/edge) for an application that renders untrusted content.
* CSP includes `script-src 'unsafe-inline'` and/or `script-src 'unsafe-eval'` without strong justification. ([MDN Web Docs][10])
* CSP delivered via meta but includes `frame-ancestors` (which will be ignored in meta). ([W3C][3])

Detection hints:

* In HTML, look for `<meta http-equiv="Content-Security-Policy"`.
* In server/edge configs, look for the `Content-Security-Policy` header.
* If CSP is meta-only, verify it appears before any `<script>` tags you want it to govern. ([W3C][3])

Fix:

* Prefer header delivery of CSP at the server/edge.
* If you are restricted to meta, keep a strong CSP allowlist and document the limitations; implement clickjacking protection (for example, `frame-ancestors`) at the server/edge rather than via meta. ([W3C][3])

---

### JS-CSP-002: Prefer a strict CSP (nonce/hash); avoid inline/eval patterns in code

Severity: Medium

NOTE: The most important header to set is the CSP `script-src`. All other directives are less important and can usually be omitted in favor of development convenience.

Required:

* SHOULD design frontend code to operate under a strict CSP:

  * avoid inline scripts and inline event handlers,
  * avoid eval-level APIs (see JS-XSS-003),
  * allow scripts via nonce or hash where necessary. ([MDN Web Docs][10])

Insecure patterns:

* Many inline script blocks and inline `onclick="..."` handlers.
* Libraries that require `unsafe-eval`.

Detection hints:

* Look for `<script>` blocks with inline code, `onclick="`, `onload="`, etc.
* Look for CSP directives that contain `unsafe-inline` or `unsafe-eval`. ([MDN Web Docs][10])

Fix:

* Move inline scripts to external JS files (same-origin).
* Use nonces/hashes for unavoidable inline blocks. ([MDN Web Docs][10])

---

### JS-TT-001: Use Trusted Types to reduce DOM XSS surface area (where supported)

Severity: Low

Required:

* SHOULD consider enabling Trusted Types enforcement via CSP `require-trusted-types-for 'script'` to make many DOM XSS sinks reject "raw" strings. ([MDN Web Docs][11])
* When using Trusted Types, SHOULD also apply the CSP `trusted-types` directive to constrain the policies that may be created (this reduces policy sprawl and improves auditability). ([MDN Web Docs][16])
* MUST keep Trusted Types policy code small, carefully reviewed, and the only path through which trusted values reach sinks. ([W3C][15])

Insecure patterns:

* "Trusted Types are enabled" but the policy simply returns input unchanged (no sanitization/validation).
* Many ad-hoc policies created throughout the codebase without restrictions.
* The belief that Trusted Types alone prevent all unsafe navigations or all classes of XSS. (They target DOM injection sinks; they are not a universal sandbox.) ([W3C][15])

Detection hints:

* Look for CSP directives: `require-trusted-types-for` and `trusted-types`.
* In code, look for `trustedTypes.createPolicy(` and inspect the policy implementations. ([MDN Web Docs][11])

Fix:

* Add a small set of well-vetted policies (for example, a `createHTML` that sanitizes).
* Restrict the allowed policies via `trusted-types <policyName...>`.
* Migrate sinks so that they require `TrustedHTML` / `TrustedScriptURL` where appropriate. ([MDN Web Docs][11])

---

### JS-MSG-001: `postMessage` must use strict origin validation and an explicit targetOrigin

Severity: Medium (High if dangerous behavior can be invoked via postMessage)

Required:

* When sending messages, MUST set an explicit `targetOrigin` (not `*`) to avoid sending data to an unexpected origin after window redirects or origin changes. ([MDN Web Docs][5])
* When receiving messages, MUST:

  * Validate `event.origin` with an exact comparison against an allowlist of expected origins (no substring matching). ([OWASP Cheat Sheet Series][6])
  * Validate `event.source` where appropriate (the expected window reference). ([MDN Web Docs][5])
  * Validate the structure of `event.data` (schema/shape) and treat it purely as data (never evaluate as code or inject into the DOM via `innerHTML`). ([OWASP Cheat Sheet Series][6])

Insecure patterns:

* `otherWindow.postMessage(payload, "*")`
* `window.addEventListener("message", (e) => { doSomething(e.data) })` without an `origin` check
* `if (e.origin.includes("trusted.com"))` (substring checks)
* `el.innerHTML = e.data` ([OWASP Cheat Sheet Series][6])

Detection hints:

* Look for `postMessage(`, `addEventListener("message"`, `onmessage =`.
* Audit every handler for an explicit `event.origin` allowlist check. ([OWASP Cheat Sheet Series][6])

Fix:

* Define an allowlist:

  * `const ALLOWED = new Set(["https://app.example.com", "https://accounts.example.com"]);`
  NOTE: For development convenience, you may use the current page's origin `window.location.origin` as a safe default origin.
* On receive:

  * `if (!ALLOWED.has(event.origin)) return;`
  * Validate `event.data` with a strict schema and reject unknown/extra fields.
* On send:

  * use the exact expected origin string as `targetOrigin`. ([OWASP Cheat Sheet Series][6])

Mitigation:

* Combine with a strict CSP and avoid DOM sinks in message-handling paths. ([MDN Web Docs][10])

---

### JS-STORAGE-001: Web Storage is not a safe place for secrets (and is attacker-influenced)

Severity: Low

Required:

* MUST NOT store sensitive secrets or session identifiers in `localStorage` (or `sessionStorage`) if compromise is meaningful; a single XSS is enough to exfiltrate everything in storage. ([OWASP Cheat Sheet Series][6])
* MUST treat values read from storage as untrusted input (attackers can load malicious values into storage via XSS). ([OWASP Cheat Sheet Series][6])
* SHOULD prefer cookies set by the server with `HttpOnly` for session identifiers (JS cannot set `HttpOnly`, so avoid storing session IDs in JS-accessible storage). ([OWASP Cheat Sheet Series][6])
* SHOULD avoid hosting multiple unrelated applications on the same origin if they rely on storage isolation (storage is shared per origin). ([OWASP Cheat Sheet Series][6])

Insecure patterns:

* `localStorage.setItem("access_token", token)`
* `localStorage.setItem("session", sessionId)`
* The assumption that `localStorage` is "trusted because same-origin".

Detection hints:

* Look for `localStorage.getItem`, `localStorage.setItem`, `sessionStorage.*`.
* Flag storage keys named `token`, `jwt`, `session`, `auth`, `refresh`. ([OWASP Cheat Sheet Series][6])

Fix:

* Use server-managed sessions or short-lived tokens issued and rotated safely, with careful XSS protection (CSP/Trusted Types) and minimal exposure to JS.
* If storage is required for non-sensitive state, keep it non-auth and validate/escape before use.

---

### JS-SUPPLY-001: Third-party JavaScript is a major supply-chain risk; minimize and control it

Severity: Low

Required:

* MUST treat third-party JS as having the same privileges as first-party JS (it can execute arbitrary code in your origin and read DOM data). ([OWASP Cheat Sheet Series][7])
* SHOULD minimize third-party scripts and prefer:

  * self-hosting / mirroring scripts,
  * strict CSP allowlists,
  * SRI for any CDN scripts,
  * continuous monitoring for unexpected changes. ([OWASP Cheat Sheet Series][7])

Insecure patterns:

* Loading arbitrary remote scripts from many vendors without review.
* Using tag managers that may dynamically inject scripts without integrity controls.
* Allowing scripts from broad wildcards in CSP (for example, `script-src *`). ([MDN Web Docs][10])

Detection hints:

* In HTML, look for `<script src="https://...">` and `tag manager` snippets.
* In CSP source lists, look for `script-src` wildcards or excessively broad domains.
* Look for dynamic script injection: `document.createElement("script")`, `script.src = ...`, `appendChild(script)`. ([OWASP Cheat Sheet Series][8])

Fix:

* Remove unnecessary third-party tags.
* Self-host or mirror scripts where possible.
* Tighten CSP `script-src` to the minimum set of trusted sources.
* Add SRI for CDN scripts/styles. ([OWASP Cheat Sheet Series][7])

---

### JS-SRI-001: Use Subresource Integrity (SRI) for third-party scripts/styles

Severity: Low

Required:

* SHOULD use SRI so that browsers load third-party resources only when they match an expected cryptographic hash. ([MDN Web Docs][12])
* MUST update SRI hashes whenever the underlying resource changes (pin versions; avoid "latest" URLs).

Insecure patterns:

* `<script src="https://cdn.example.com/lib.js"></script>` without `integrity`.
* Loading `latest` or unpinned third-party resources.

Detection hints:

* Look for `<script src="https://` and `<link rel="stylesheet" href="https://` without `integrity=`.
* Verify that `integrity` is present and that strong hashes are used (sha256/384/512). ([MDN Web Docs][12])

Fix:

* Add `integrity="sha384-..."` (or appropriate) and ensure the correct CORS mode where required.
* Prefer self-hosting for critical libraries.

---

### FS-DOMC-001: Prevent DOM clobbering (do not rely on named `window`/`document` properties)

Severity: Medium-High (can become Critical if it allows script loading or `javascript:` navigation)

Required:

* MUST NOT rely on implicit globals or `window.someName` / `document.someName` lookups that can be "clobbered" by injected HTML elements with matching `id`/`name`. ([OWASP Cheat Sheet Series][8])
* MUST avoid patterns such as `let x = window.redirectTo || "/safe"; location.assign(x);` where `redirectTo` may be "clobbered" to an `<a>` element whose `href` is attacker-controlled (including `javascript:`). ([OWASP Cheat Sheet Series][8])
* SHOULD use explicit variable declarations, local scoping, and explicit DOM queries (`getElementById`) instead of named-property access. ([OWASP Cheat Sheet Series][8])
* If the application injects user markup (even sanitized), SHOULD ensure sanitization strategies account for `id`/`name` collisions. ([OWASP Cheat Sheet Series][8])

Insecure patterns:

* `const cfg = window.config || {};` used for security-sensitive URLs.
* `const redirect = window.redirectTo || "/"; location.assign(redirect);` ([OWASP Cheat Sheet Series][8])
* Loading scripts from `window.*` configuration values without strict validation.

Detection hints:

* Look for `window.` and `document.` used as configuration stores (especially `||` fallback patterns).
* Look for `location.assign/replace` usage with variables sourced from `window`/`document` properties.
* Look for dynamic script creation (`createElement('script')`) where `.src` comes from a non-local variable. ([OWASP Cheat Sheet Series][8])

Fix:

* Store configuration in module-scoped constants (not on `window`/`document`) and pass it explicitly.
* Validate any URL-like configuration via a protocol/origin allowlist (see FEJS-URL-001). ([OWASP Cheat Sheet Series][8])
* Consider hardening: sanitization, CSP, and (in limited cases) freezing sensitive objects, but treat this as defense-in-depth rather than a replacement for safe coding patterns. ([OWASP Cheat Sheet Series][8])

---

## 5) Practical Scanning Heuristics (how to "hunt")

When actively scanning, use these high-signal patterns:

* DOM XSS sinks:

  * `.innerHTML`, `.outerHTML`, `insertAdjacentHTML(`
  * `document.write(`, `document.writeln(` ([OWASP Cheat Sheet Series][2])

* Dangerous navigation/URL sinks:

  * `window.location`, `location.href`, `location.assign`, `location.replace`
  * `javascript:` literals (and other suspicious schemes such as `data:text/html`) ([MDN Web Docs][4])

* Code execution from strings:

  * `eval(`, `new Function`, `setTimeout("`, `setInterval("` ([MDN Web Docs][10])

* Event-handler string injection:

  * `.setAttribute("on`, `.onclick =`, `.onload =` with strings ([OWASP Cheat Sheet Series][2])

* `postMessage`:

  * `postMessage(` with `"*"` as the targetOrigin
  * `addEventListener("message"` without strict `event.origin` allowlist checks ([MDN Web Docs][5])

* Storage:

  * `localStorage.setItem(` / `getItem(`, `sessionStorage.*`
  * keys containing `token`, `jwt`, `session`, `auth`, `refresh` ([OWASP Cheat Sheet Series][6])

* CSP and related:

  * `Content-Security-Policy` header configuration (server/edge)
  * `<meta http-equiv="Content-Security-Policy" ...>`
  * CSP containing `unsafe-inline` or `unsafe-eval`
  * `require-trusted-types-for` / `trusted-types` directives ([MDN Web Docs][1])

* Third-party scripts:

  * `<script src="https://...">` without `integrity=`
  * tag-manager snippets and dynamic-script-injection paths ([MDN Web Docs][12])


* DOM clobbering gadgets:

  * `window.<name> || ...` and `document.<name> || ...` patterns
  * security-sensitive use of `window`/`document` properties as configuration sources ([OWASP Cheat Sheet Series][8])

Always try to confirm:

* data origin (untrusted vs. trusted),
* sink type (HTML parsing, navigation, code execution, message handling, storage),
* the presence of defensive controls (CSP, Trusted Types, sanitizers, strict allowlists, schema validation).

---

## 6) Sources (accessed 2026-01-27)

Primary standards / platform documentation:

* W3C Content Security Policy Level 2 (HTML `<meta>` delivery limitations; directives unsupported in meta CSP): `https://www.w3.org/TR/CSP2/` ([W3C][3])
* MDN: CSP guide (strict CSP, nonce/hash, `unsafe-inline`/`unsafe-eval`, eval blocking): `https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP` ([MDN Web Docs][10])
* MDN: `<meta http-equiv>` (CSP via meta and warnings about security headers in meta): `https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/http-equiv` ([MDN Web Docs][1])
* MDN: `frame-ancestors` (and the note that it is unsupported in `<meta>`): `https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors` ([MDN Web Docs][18])

DOM XSS and dangerous sinks:

* OWASP: DOM Based XSS Prevention Cheat Sheet (dangerous sinks + safe patterns such as `textContent`): `https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][2])
* MDN: `innerHTML` (security considerations): `https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML` ([MDN Web Docs][19])
* MDN: `insertAdjacentHTML` (security considerations): `https://developer.mozilla.org/en-US/docs/Web/API/Element/insertAdjacentHTML` ([MDN Web Docs][20])
* MDN: `document.write()` / `document.writeln()` (security considerations): `https://developer.mozilla.org/en-US/docs/Web/API/Document/write` and `https://developer.mozilla.org/en-US/docs/Web/API/Document/writeln` ([MDN Web Docs][13])

URL-scheme hazards:

* MDN: `javascript:` URLs (execution upon navigation; not recommended; references to `window.location`): `https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Schemes/javascript` ([MDN Web Docs][4])

Trusted Types:

* W3C: Trusted Types specification (DOM XSS sinks include `Element.innerHTML` and `Location.href` setters; goals and limitations): `https://www.w3.org/TR/trusted-types/` ([W3C][15])
* MDN: `require-trusted-types-for` directive: `https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/require-trusted-types-for` ([MDN Web Docs][11])
* MDN: `trusted-types` directive: `https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/trusted-types` ([MDN Web Docs][16])

Cross-window messaging:

* MDN: `window.postMessage` (security guidance: specify targetOrigin; validate origin): `https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage` ([MDN Web Docs][5])
* OWASP: HTML5 Security Cheat Sheet (Web Messaging recommendations: explicit origin, strict checks, no `innerHTML`): `https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][6])

Third-party scripts and integrity:

* OWASP: Third Party JavaScript Management Cheat Sheet (risks and defenses, including SRI/mirroring): `https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][7])
* MDN: Subresource Integrity overview: `https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Subresource_Integrity` ([MDN Web Docs][12])
* W3C: Subresource Integrity specification: `https://www.w3.org/TR/sri-2/` ([W3C][21])

DOM clobbering:

* OWASP: DOM Clobbering Prevention Cheat Sheet (named-property access risk; attack examples with `location.assign` and `javascript:`): `https://cheatsheetseries.owasp.org/cheatsheets/DOM_Clobbering_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][8])

[1]: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/http-equiv "https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/http-equiv"
[2]: https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html"
[3]: https://www.w3.org/TR/CSP2/ "Content Security Policy Level 2"
[4]: https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Schemes/javascript "javascript: URLs - URIs | MDN"
[5]: https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage "https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage"
[6]: https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html"
[7]: https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html"
[8]: https://cheatsheetseries.owasp.org/cheatsheets/DOM_Clobbering_Prevention_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/DOM_Clobbering_Prevention_Cheat_Sheet.html"
[9]: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel/noopener "https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel/noopener"
[10]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP "https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP"
[11]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/require-trusted-types-for "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/require-trusted-types-for"
[12]: https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Subresource_Integrity "https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Subresource_Integrity"
[13]: https://developer.mozilla.org/en-US/docs/Web/API/Document/write "https://developer.mozilla.org/en-US/docs/Web/API/Document/write"
[14]: https://developer.mozilla.org/en-US/docs/Web/API/Document/writeln "https://developer.mozilla.org/en-US/docs/Web/API/Document/writeln"
[15]: https://www.w3.org/TR/trusted-types/ "https://www.w3.org/TR/trusted-types/"
[16]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/trusted-types "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/trusted-types"
[18]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors"
[19]: https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML "https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML"
[20]: https://developer.mozilla.org/en-US/docs/Web/API/Element/insertAdjacentHTML "https://developer.mozilla.org/en-US/docs/Web/API/Element/insertAdjacentHTML"
[21]: https://www.w3.org/TR/sri-2/ "https://www.w3.org/TR/sri-2/"
