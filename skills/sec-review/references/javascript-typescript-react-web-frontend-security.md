# React (JavaScript/TypeScript) Web Frontend Security Specification (React 19.x, TypeScript 5.x)

This document is intended as a **security specification** that supports:

1. **Secure-by-default code generation** for new React code.
2. **Security review and vulnerability hunting** in existing React code (both passive "spot issues while working" mode and active "scan the repo and report findings" mode).

The document is intentionally written as a set of **normative requirements** ("MUST/SHOULD/MAY") together with **audit rules** (what bad patterns look like, how to detect them, and how to fix or mitigate them).

---

## 0) Safety, Boundaries, and Anti-Abuse Constraints (MANDATORY)

* MUST NOT request, output, log, or commit secrets (API keys, OAuth client secrets, private keys, session cookies, JWTs, signing keys).

  * Frontend note: anything sent to the browser is visible to end users and attackers (view source, devtools, proxies); never treat client code or "bundled env variables" as secret. ([create-react-app.dev][1])
* MUST NOT "fix" security by disabling protections (for example, turning off CSP "to make it work", adding `unsafe-inline`/`unsafe-eval` without a documented and constrained plan, disabling CSRF protection when using cookies, broadening CORS, skipping sanitization, or introducing "temporary" workarounds that end up in production). ([OWASP Cheat Sheet Series][2])
* MUST provide **evidence-based findings** when auditing: cite file paths, code snippets, and configuration values that justify the claim.
* MUST be honest about uncertainty: if a defense may be present in the infrastructure (CDN/WAF/reverse proxy), report it as "not visible in application code; verify via runtime headers / edge configuration".
* MUST assume that any data crossing a trust boundary (URL, storage, network, postMessage, third-party scripts) may be attacker-influenced unless proven otherwise (see §2.1).

---

## 1) Modes of Operation

### 1.1 Generation Mode (default)

When asked to write new React code or modify existing code:

* MUST honor every **MUST** requirement of this specification.
* SHOULD honor every **SHOULD** requirement unless the user explicitly states otherwise.
* MUST prefer secure-by-default APIs and proven libraries over hand-rolled security code.
* MUST avoid introducing new risky "sinks" (raw HTML insertion, direct DOM sinks such as `innerHTML`, dynamic code execution, untrusted redirects/navigation, third-party script injection, unsafe token storage, etc.). ([MDN Web Docs][3])

### 1.2 Passive Review Mode (always on while editing)

When working anywhere in a React repository (even if the user did not request a security scan):

* MUST "spot" violations of this specification in edited or adjacent code.
* SHOULD raise issues as they arise, with a brief explanation and a safe fix.

### 1.3 Active Audit Mode (explicit scan request)

When the user asks to "scan", "audit", or "hunt for vulnerabilities":

* MUST systematically search the codebase for violations of this specification.
* MUST output findings in a structured format (see §2.3).

Recommended audit order:

1. Application entry points, build tooling (Vite/Webpack/CRA/Next), deployment configuration, CDN/static hosting.
2. Secret and configuration exposure (env variables, runtime config injection, source maps).
3. Rendering of untrusted data (XSS/DOM XSS), particularly `dangerouslySetInnerHTML`, markdown/HTML renderers, URL attributes.
4. Direct DOM use and dangerous JS execution (`innerHTML`, `eval`, `new Function`, `document.write`, etc.).
5. Authentication and session patterns (token storage, cookies, CSRF interaction, OAuth flows).
6. Network layer (axios/fetch wrappers, dynamic base URLs, credentialed requests, data-exfiltration risks).
7. Navigation and redirect handling (open redirects, `window.location`, `target=_blank`, `window.open`).
8. Third-party scripts/tags/analytics and integrity controls (CSP, SRI).
9. Service worker/PWA behavior (HTTPS, caching rules, update strategy).
10. Security-header posture (CSP, clickjacking protection, nosniff, referrer policy) in the application or at the edge. ([OWASP Cheat Sheet Series][2])

---

## 2) Definitions and Review Guidance

### 2.1 Untrusted Input (treat as attacker-controlled until proven otherwise)

Examples:

* URL data: `window.location`, query parameters, hash fragments, route parameters.
* Any data from browser storage: `localStorage`, `sessionStorage`, `IndexedDB` (including data the application previously wrote -- XSS or extensions can tamper with it). ([OWASP Cheat Sheet Series][4])
* Any data from cross-window messaging: `window.postMessage` payload. ([OWASP Cheat Sheet Series][4])
* Any data from remote APIs, webhooks proxied to the client, GraphQL responses, CMS content, feature-flag services.
* Any stored user content (profiles, comments, rich text, markdown) displayed in the UI.
* Any data produced by third-party scripts or tag managers (treat as untrusted unless control is very strict). ([OWASP Cheat Sheet Series][5])

### 2.2 State-Changing Request (frontend perspective)

A request is state-changing if it can create/update/delete data, change auth/session state, cause side effects (purchase, sending email, dispatching a webhook), or initiate privileged actions.

Frontend note:

* State changes are often initiated by `fetch/axios` calls or form submissions. If authentication is cookie-based, such calls may be relevant to CSRF (§4 REACT-CSRF-001). ([OWASP Cheat Sheet Series][6])

### 2.3 Required Audit-Finding Format

For each issue found, output:

* Rule ID:
* Severity: Critical / High / Medium / Low
* Location: file path + component/function + line(s)
* Evidence: exact code/config snippet
* Impact: what can go wrong, who can exploit it
* Fix: safe change (preferably a minimal diff)
* Mitigation: defense-in-depth if an immediate fix is difficult
* False positive notes: what to verify when uncertain

---

## 3) Secure Baseline: Minimum Production Configuration (MUST in production)

This is the minimum "production baseline" that prevents common React frontend misconfigurations.

### 3.1 Production Build and Configuration Hygiene (MUST)

* MUST ship a production build to production (minified, no dev overlays/tools, with the correct mode flags).
* MUST ensure that build-time configuration does not bake secrets into shipped JS/HTML/CSS. Build-time "environment variables" are not secrets; treat them as public. ([create-react-app.dev][1])
* SHOULD treat source maps as sensitive operational artifacts:

  * Either do not publish them publicly, or publish them only where intended (for example, behind authentication or to an error-reporting provider), since they may reveal code structure and internal URLs.

### 3.2 Browser-Provided Defenses (SHOULD, but a basic expectation for modern apps)

* SHOULD deploy CSP as defense-in-depth against XSS and keep it compatible with your React build (avoid `unsafe-inline` and `unsafe-eval` unless strictly necessary and documented). ([OWASP Cheat Sheet Series][2])
* SHOULD use Subresource Integrity (SRI) for any third-party script/style loaded from a CDN (or self-host it). ([MDN Web Docs][7])
* SHOULD enable clickjacking protection via `frame-ancestors` (CSP) and/or `X-Frame-Options` if framing is not an explicit product requirement. ([MDN Web Docs][8])

### 3.3 High-Risk Feature Baseline (MUST when used)

* If any user HTML/markdown/rich text is rendered:

  * MUST sanitize before insertion and avoid direct DOM sinks. ([OWASP Cheat Sheet Series][9])
* If service worker / PWA features are used:

  * MUST serve them over HTTPS and implement a safe caching/update strategy (a service worker is a powerful request/response proxy). ([MDN Web Docs][10])

---

## 4) Rules (generation + audit)

Each rule contains: required practice, insecure patterns, detection hints, and remediation guidance.

### REACT-CONFIG-001: Never bake secrets into the client bundle (env variables are public)

Severity: Critical (when secrets are exposed)

Required:

* MUST NOT place secrets in React code, in `public/` assets, or in build-time environment variables intended for client consumption.
* MUST assume that any value available to the React application at runtime can be extracted by an attacker.

Insecure patterns:

* Using build-time env variables for secrets:

  * `process.env.REACT_APP_*` containing private keys or credentials.
  * `import.meta.env.VITE_*` containing secrets.
* Hardcoded secrets in JS/TS, committed `.env`, or secrets in `public/config.json` served to all users.

Detection hints:

* Look for:

  * `REACT_APP_`, `VITE_`, `NEXT_PUBLIC_`, `process.env.`, `import.meta.env.`
  * `apiKey`, `secret`, `token`, `private`, `password`, `client_secret`
* Inspect `public/` for runtime-config JSON.

Fix:

* Move secrets server-side (API, BFF, serverless function).
* Use the backend to issue short-lived, scope-limited tokens if the browser must call third-party APIs.

Notes:

* CRA explicitly warns against storing secrets and notes that env variables are baked into the build and visible to anyone who inspects the files. ([create-react-app.dev][1])
* Vite explicitly notes that variables exposed to client code end up in the client bundle and must not contain sensitive information. ([vitejs][11])

---

### REACT-XSS-001: Do not use `dangerouslySetInnerHTML` with untrusted content (sanitize or avoid)

Severity: High (only when attacker-controlled HTML can be shown to reach it)

Required:

* MUST avoid `dangerouslySetInnerHTML` unless absolutely necessary.
* If it must be used:

  * MUST sanitize untrusted HTML with a vetted sanitizer (for example, DOMPurify) using an allowlist-oriented configuration.
  * MUST keep sanitization logic centralized and carefully reviewed.
  * SHOULD add CSP and consider Trusted Types (see REACT-TT-001).

Insecure patterns:

* `<div dangerouslySetInnerHTML={{ __html: userHtml }} />` where `userHtml` comes from API/URL/storage.
* "Sanitization" via regex, ad-hoc stripping, or incomplete allowlists.

Detection hints:

* Grep: `dangerouslySetInnerHTML`, `__html:`
* Trace the origin of the HTML string (API/CMS/URL/localStorage).

Fix:

* Replace with safe rendering:

  * Render structured data as React elements/components instead of HTML strings.
  * If rich text is required, sanitize via DOMPurify (or equivalent) and render the cleaned output.
* Add CSP; remove dangerous sinks where possible.

Notes:

* React explicitly warns that `dangerouslySetInnerHTML` is dangerous and can lead to XSS when misused. ([React][12])
* OWASP explicitly flags `dangerouslySetInnerHTML` without sanitization as a typical framework "escape-hatch" pitfall. ([OWASP Cheat Sheet Series][9])
* DOMPurify describes itself as an XSS sanitizer for HTML/SVG/MathML. ([GitHub][13])

---

### REACT-XSS-002: Rely on React's default escaping; do not bypass it

Severity: High (when bypassed)

Required:

* MUST render untrusted strings via standard JSX interpolation (`{value}`) and React props, which are escaped by default.
* MUST NOT build HTML strings from untrusted data and then insert them into the DOM by any means.
* SHOULD treat any "escape hatch" as high-risk and review it carefully.

Insecure patterns:

* Converting untrusted text to HTML and inserting it:

  * `element.innerHTML = userValue`
  * `document.write(userValue)`
  * `insertAdjacentHTML(..., userValue)`

Detection hints:

* Grep for DOM sinks: `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `DOMParser`, `createContextualFragment`.

Fix:

* Render text content via React (JSX) so that it is escaped.
* If you really need HTML, sanitize and apply REACT-XSS-001 + REACT-TT-001.

Notes:

* The React documentation (JSX) states that React DOM escapes values embedded in JSX before rendering to help prevent injection. ([React][14])

---

### REACT-DOM-001: Avoid DOM XSS sinks in React code (use safe alternatives)

Severity: High

Required:

* MUST avoid direct DOM injection sinks, even outside React rendering, unless they are strictly controlled.
* If a DOM sink is required:

  * MUST ensure inputs are trusted/validated/sanitized.
  * SHOULD apply Trusted Types (REACT-TT-001).

Insecure patterns:

* `someEl.innerHTML = untrusted`
* `document.write(untrusted)`
* `new DOMParser().parseFromString(untrusted, 'text/html')` followed by insertion

Detection hints:

* Grep for: `innerHTML`, `outerHTML`, `document.write`, `DOMParser`, `Range().createContextualFragment`, `insertAdjacentHTML`

Fix:

* Prefer:

  * `textContent` for text insertion.
  * Rendering via React instead of manual DOM manipulation.
  * A vetted sanitizer for any required HTML parsing.

Notes:

* The Trusted Types documentation classifies HTML sinks such as `Element.innerHTML` and `document.write()` as injection sinks capable of executing scripts when fed attacker-controlled input. ([MDN Web Docs][3])
* The OWASP HTML5 guide recommends using `textContent` instead of `innerHTML` when assigning untrusted data. ([OWASP Cheat Sheet Series][4])

---

### REACT-URL-001: Validate and constrain untrusted URLs used in `href`, `src`, navigation, and redirects

Severity: High only when they can be shown to be attacker-controlled

Required:

* MUST treat any URL derived from untrusted input as dangerous.
* MUST maintain an allowlist of schemes and (where applicable) hosts:

  * Typically allow only `https:` (and possibly `http:` for localhost/dev) and relative URLs for in-app navigation.
  * MUST explicitly block `javascript:` and dangerous uses of `data:` unless you have specialized validation and an explicit use case.
* SHOULD prefer same-site relative paths (for example, `/settings`) over absolute URLs.
* MUST validate "returnTo/next/redirect" parameters (see REACT-REDIRECT-001).

Insecure patterns:

* `<img src={userProvidedUrl}>...` (can be used for tracking/exfiltration; also risky when used for scripts/iframes)
* `window.location = next`
* `navigate(next)` where `next` comes from query parameters without validation

Detection hints:

* Look for:

  * `href={`, `src={`, `window.location`, `location.href`, `window.open`, `navigate(`, `redirectTo`, `returnTo`, `next=`
* Trace whether the value originates from URL/query/storage/API.

Fix:

* Implement a shared `safeUrl()` utility:

  * Parse via `new URL(value, base)`
  * Apply scheme and host allowlists (or require same-origin)
  * For redirects: allow only relative paths (starting with `/`) or a strict allowlist of absolute origins.
* Have a safe default when validation fails.

Notes:

* OWASP explicitly notes the risk of React's `dangerouslySetInnerHTML` and states that React cannot safely handle `javascript:` or `data:` URLs without specialized validation. ([OWASP Cheat Sheet Series][9])

---

### REACT-MARKUP-001: Markdown/rich-text rendering must be configured safely

Severity: Medium

Required:

* MUST assume that markdown/rich text may be attacker-controlled if it comes from users or a CMS.
* MUST ensure that raw HTML is not rendered unless sanitized.
* SHOULD prefer markdown renderers that:

  * Disallow raw HTML by default, or
  * Can be configured to disallow raw HTML, or
  * Sanitize HTML output before rendering.

Insecure patterns:

* Rendering markdown with "raw HTML passthrough" enabled (for example, options/plugins that allow HTML).
* Inline rendering of user-provided SVG/MathML/HTML without sanitization.

Detection hints:

* Look for common libraries and dangerous options:

  * `marked`, `markdown-it`, `react-markdown`, `rehype-raw`, `sanitize: false`, `allowDangerousHtml`, etc.
* Look for `dangerouslySetInnerHTML` used with "markdown output".

Fix:

* Disable raw-HTML passthrough.
* Sanitize the output with a vetted sanitizer (for example, DOMPurify) before rendering.

Notes:

* The OWASP XSS guide emphasizes that framework escape hatches require output encoding and/or HTML sanitization. ([OWASP Cheat Sheet Series][9])

---

### REACT-TT-001: Use Trusted Types (with CSP) to harden DOM XSS sinks where possible

Severity: Low

Required:

* SHOULD first consider enabling Trusted Types in report-only mode, then switch to enforce once violations are addressed.
* SHOULD centralize Trusted Types policies and treat them as high-risk code requiring review.
* MUST NOT create permissive policies that simply "pass through" untrusted strings.

Insecure patterns:

* A Trusted Types policy that returns a raw string without sanitization for HTML sinks.
* Many scattered policies throughout the codebase (hard to audit).

Detection hints:

* Look for:

  * `trustedTypes.createPolicy`
  * CSP directives: `require-trusted-types-for`, `trusted-types`
* Look for any remaining DOM sinks (REACT-DOM-001).

Fix:

* Implement a small number of strictly constrained policies:

  * The HTML policy uses a sanitizer (DOMPurify or equivalent).
  * The script-URL policy uses strict allowlists.
* Run in report-only mode, fix violations, then enable enforce.

Notes:

* MDN describes Trusted Types as a way to ensure input transformation (typically sanitization) before passing data to injection sinks and highlights HTML sinks (`innerHTML`, `document.write`) and JS-URL sinks (`script.src`). ([MDN Web Docs][3])
* The W3C Trusted Types specification frames this as reducing DOM XSS risk by constraining sinks to typed values produced by vetted policies. ([W3C][15])

---

### REACT-CSP-001: Deploy and maintain CSP as defense-in-depth (especially when rendering untrusted content)

Severity: Medium-High

Required:

* SHOULD deploy CSP in production; MUST do so for applications that render untrusted content or integrate third-party scripts.
* SHOULD avoid `unsafe-inline` and `unsafe-eval` where possible.
* SHOULD use CSP nonces/hashes for inline scripts where required, and keep the policy realistic.
* SHOULD use CSP to require/encourage SRI where appropriate.

Insecure patterns:

* CSP completely absent on the application shell (the SPA's entry HTML).
* CSP relying broadly on `unsafe-inline`/`unsafe-eval` without justification.
* `script-src *` or overly broad sources.

Detection hints:

* Look for CSP configuration:

  * Server/CDN configuration, response headers for `index.html`, or framework configuration.
* If not visible in the repository, mark it as "verify at the edge".

Fix:

* Add CSP via HTTP response headers (preferred).
* Start with report-only to reduce breakage, then enable enforce.

Notes:

* OWASP describes CSP as "defense-in-depth" against XSS and notes that it can help enforce SRI even on static sites, but should not be the only defense. ([OWASP Cheat Sheet Series][2])

---

### REACT-SRI-001: Use Subresource Integrity (SRI) for third-party scripts and styles (or self-host)

Severity: Low

Required:

* MUST treat third-party JS as arbitrary code executing in your origin.
* When loading from a CDN or third party:

  * SHOULD use SRI (`integrity=...`) and `crossorigin` where applicable.
  * SHOULD pin to exact versions (avoid "latest" URLs).
  * SHOULD prefer self-hosting for critical code.

Insecure patterns:

* `<script src="https://cdn.example.com/lib/latest.js"></script>` without integrity.
* Tag managers that dynamically load arbitrary scripts without governance.

Detection hints:

* In `public/index.html`, templates, or SSR wrappers, look for:

  * `<script src=`, `<link rel="stylesheet" href=`
  * Tag-manager snippets (GTM, Segment, etc.)
* Identify scripts loaded dynamically in runtime JS.

Fix:

* Add SRI hashes for stable third-party assets, or self-host.
* Apply governance to tag managers (see REACT-3P-001).

Notes:

* MDN describes SRI as a security feature that lets browsers verify fetched resources (for example, from a CDN) have not been tampered with by checking a cryptographic hash. ([MDN Web Docs][7])
* The OWASP CSP guide notes that CSP can enforce SRI and is useful even on static sites. ([OWASP Cheat Sheet Series][2])

---

### REACT-3P-001: Third-party JavaScript and tag managers must be minimized and governed

Severity: High

Required:

* MUST minimize third-party scripts and treat each as a supply-chain risk.
* MUST know exactly which third-party JS executes in your origin and why.
* SHOULD implement governance:

  * Review and version-pinning (or in-house mirroring).
  * Limit data exposure (data-layer approach).
  * Use SRI and CSP; isolate untrusted UI in iframes when possible.

Insecure patterns:

* Unaudited analytics/ad scripts running with full access to DOM, cookies, storage, and user data.
* Tag managers modified by non-engineering roles without change control.

Detection hints:

* Look for common vendor snippets in HTML/JS:

  * GTM, Segment, Hotjar, FullStory, etc.
* Look for dynamic script insertion:

  * `document.createElement('script')`, `.src = ...`, `.appendChild(script)`

Fix:

* Reduce to only the necessary vendors.
* Where possible:

  * Self-host or mirror scripts.
  * Use SRI.
  * Limit data exposure via a controlled data layer.

Notes:

* OWASP notes that compromising a third-party JS server can inject malicious JS, and highlights the risks of arbitrary code execution and exposure of sensitive information to third parties. ([OWASP Cheat Sheet Series][5])

---

### REACT-AUTH-001: Token and session handling must be XSS-resistant (avoid sensitive Web Storage)

Severity: Medium

Required:

* SHOULD avoid storing session identifiers or long-lived tokens in `localStorage` (and Web Storage in general) because XSS can exfiltrate them.
* If tokens must exist on the client side:

  * SHOULD prefer in-memory storage with short lifetimes and refresh mechanisms.
  * MUST scope-limit and rotate tokens; avoid long-lived bearer tokens in persistent storage.
* SHOULD prefer HTTPOnly cookies for session tokens when possible (requires a CSRF strategy: see REACT-CSRF-001).

Insecure patterns:

* `localStorage.setItem('token', ...)` / `sessionStorage.setItem('token', ...)` for auth tokens.
* Storing refresh tokens in `localStorage`.
* Treating Web Storage data as trusted.

Detection hints:

* Grep for: `localStorage.`, `sessionStorage.`, `setItem(`, `getItem(`, `token`, `jwt`, `refresh`
* In auth code, look for "remember me" persisting tokens.

Fix:

* Switch to HTTPOnly cookies (server-side change) + CSRF protection, or short-lived in-memory tokens.
* Reduce token scope and lifetime.

Notes:

* The OWASP HTML5 guide recommends avoiding sensitive information and session identifiers in local storage and warns that a single XSS can steal all data from Web Storage. ([OWASP Cheat Sheet Series][4])
* The OAuth guidance for browser-based applications discusses how tokens stored in persistent browser storage such as localStorage may be accessible to malicious JS (for example, via XSS). ([IETF Datatracker][16])

---

### REACT-CSRF-001: Cookie-authenticated state-changing requests MUST be CSRF-protected

Severity: High

NOTE: if the application does not use cookie-based authentication (for example, it uses an Authentication header), CSRF is not a concern.

Required:

* If the application relies on cookies for authentication:

  * MUST protect state-changing requests (POST/PUT/PATCH/DELETE) from CSRF.
  * SHOULD include a CSRF-token mechanism (synchronizer token or double-submit cookie) or another robust pattern suited to the backend.
  * SHOULD use SameSite cookies as defense-in-depth, not as the sole defense.

Insecure patterns:

* `fetch('/api/transfer', { method: 'POST', credentials: 'include' })` without a CSRF token/header, relying solely on cookies.
* Using GET for state-changing operations.

Detection hints:

* Enumerate state-changing network calls and verify:

  * Whether `credentials: 'include'` or `withCredentials: true` is used.
  * Whether a CSRF header is included (for example, `X-CSRF-Token`).
* Look for "csrf" utilities; if none are present, treat with suspicion.

Fix:

* Add a CSRF-token flow:

  * Fetch a token from a safe endpoint and attach it to state-changing requests.
  * Verify it on the server.
* Keep SameSite cookies and Origin/Referer checks as defense-in-depth.

Notes:

* The OWASP CSRF guide explains SameSite behavior (Lax/Strict/None) as defense-in-depth and why Lax is often a usability/security balance, but it is not a complete replacement for CSRF protection. ([OWASP Cheat Sheet Series][6])

---

### REACT-AUTHZ-001: Do not rely on frontend-only authorization

Severity: High (only if used as the primary defense)

Required:

* MUST treat any frontend authorization checks as UX only.
* MUST enforce authorization on the server for any protected resource or action.

Insecure patterns:

* "Protected" actions hidden in the UI but called via APIs without server-side checks.
* Client-side checks such as `if (user.isAdmin) { showAdminPanel(); }` without server-side enforcement.

Detection hints:

* Look for UI gates around sensitive actions and verify that server endpoints enforce authorization.
* In a frontend-only audit, report this as "client-side checks are not security; verify the backend".

Fix:

* Add/confirm server-side authorization checks.
* Keep frontend gating as a usability convenience only.

Notes:

* This is a general property of web-application security; React itself cannot protect server resources.

---

### REACT-NET-001: Prevent data exfiltration and credential leakage through dynamic outbound requests

Severity: Medium-High

Required:

* MUST avoid authenticated requests to attacker-controlled origins.
* SHOULD avoid letting user input control the request destination (scheme/host/port).
* SHOULD centralize network clients (fetch/axios) with:

  * a fixed `baseURL` (or strict allowlist),
  * strict redirect handling,
  * explicit use of `credentials`.

Insecure patterns:

* `fetch(userProvidedUrl, { credentials: 'include' })`
* `axios.create({ baseURL: userProvidedBase })`
* "URL fetch/preview" client features that contact arbitrary domains with sensitive headers.

Detection hints:

* Look for `fetch(` / `axios(` where the first argument or `baseURL` is derived from:

  * query parameters, localStorage, API responses, postMessage
* Look for `credentials: 'include'`, `withCredentials: true`.

Fix:

* Implement destination allowlists; disallow cross-origin requests unless explicitly required.
* Strip credentials/Authorization headers for any destination not in the allowlist.

Notes:

* Even though browsers restrict some cross-origin behavior, leaking tokens/headers to untrusted endpoints is a frequent class of bug.

---

### REACT-REDIRECT-001: Prevent open redirects and untrusted navigation

Severity: Medium

Required:

* MUST validate redirect/navigation targets derived from untrusted input (`next`, `returnTo`, `redirect`).
* SHOULD allow only same-site relative paths or a strict allowlist of trusted origins for absolute URLs.

Insecure patterns:

* `window.location.href = new URLSearchParams(location.search).get('next')`
* `navigate(next)` where `next` comes from query parameters.

Detection hints:

* Look for: `next`, `returnTo`, `redirect`, `window.location`, `navigate(`
* Trace the origin of the redirect target.

Fix:

* Allow only relative paths (`/^\/[^\s]*$/`) or an origin allowlist.
* On invalid input, return to a safe default (for example, `/`).

Notes:

* Open redirects are commonly used in phishing and can undermine SSO/OAuth flows.

---

### REACT-SW-001: Service workers are highly privileged; HTTPS and safe caching/update rules are required

Severity: Medium

Required:

* MUST serve service workers over HTTPS (with the exception of `localhost` for dev) and deploy only in secure contexts.
* MUST avoid caching sensitive authenticated API responses unless explicitly designed and threat-modeled.
* SHOULD implement a safe update strategy (request reload, versioned caches, removal of old caches on activate).

Insecure patterns:

* Registering a service worker for an authenticated app and caching "everything indiscriminately".
* Long-lived caches containing PII or user-specific content shared between accounts.

Detection hints:

* Look for:

  * `navigator.serviceWorker.register`
  * `workbox`, `precacheAndRoute`, custom `fetch` handlers
* Inspect caching patterns (`caches.open`, `cache.put`, `respondWith`).

Fix:

* Restrict caching to static assets only (JS/CSS/images) unless an offline model is designed.
* Ensure cache keys are user-scoped if user-specific data is cached.
* Provide a clear update mechanism.

Notes:

* MDN notes that service workers require HTTPS for security reasons and act as a request/response proxy. ([MDN Web Docs][10])
* "Secure contexts" exist to prevent MITM attackers from accessing powerful APIs; service workers are an example of such a powerful capability. ([MDN Web Docs][18])

---

### REACT-HEADERS-001: Ensure important security headers are set for the React application shell (app or edge)

Severity: Medium

Required (typical SPA served from an origin):

* SHOULD set:

  * CSP (`Content-Security-Policy`)
  * `X-Content-Type-Options: nosniff`
  * Clickjacking protection (`frame-ancestors` in CSP and/or `X-Frame-Options`)
  * `Referrer-Policy`
  * `Permissions-Policy` as appropriate
* MUST ensure these are set somewhere (CDN/edge/server), even if not in the repository.

Insecure patterns:

* No security headers at all (neither in the application nor at the edge).
* Missing CSP for applications that render untrusted content or use third-party scripts.

Detection hints:

* Check server/CDN configuration in the repository (nginx, Cloudflare, Vercel config, etc.).
* If absent, mark as "verify at runtime/edge".

Fix:

* Set headers centrally at the edge.
* Keep CSP realistic and iterative (report-only -> enforce).

Notes:

* The MDN clickjacking guide discusses defenses including `X-Frame-Options` and CSP `frame-ancestors`. ([MDN Web Docs][8])
* The OWASP CSP guide explains response-header delivery and recommends headers as the preferred mechanism. ([OWASP Cheat Sheet Series][2])

---

### REACT-POSTMSG-001: `postMessage` MUST validate origin and treat the payload as untrusted data

Severity: Medium-High (depending on what messages can do)

Required:

* MUST specify an exact `targetOrigin` when sending messages (not `*`) unless there is a strong reason.
* MUST validate `event.origin` on receive and verify the message shape.
* MUST NOT execute message data as code or insert it into the DOM as HTML.

Insecure patterns:

* `window.postMessage(data, '*')` to unknown targets.
* On receive:

  * `window.addEventListener('message', (e) => { eval(e.data) })`
  * `element.innerHTML = e.data`

Detection hints:

* Look for: `postMessage(`, `addEventListener('message'`
* Verify the presence of origin checks and safe handling.

Fix:

* Add strict origin allowlists and schema validation (for example, zod).
* Treat the message payload strictly as data; render safely via React.

Notes:

* The OWASP HTML5 guide recommends specifying the expected origin for `postMessage`, validating the sender's origin, validating data, and avoiding eval/innerHTML with message content. ([OWASP Cheat Sheet Series][4])

---

### REACT-FILE-001: File uploads and previews must not introduce client-side active-content vulnerabilities

Severity: Medium (can be High if stored XSS becomes possible)

Required:

* MUST treat user-uploaded files and previews as potentially malicious.
* MUST NOT render uploaded HTML/SVG/other active content inline without sanitization and an explicit need.
* SHOULD validate file types on the client for UX, but MUST rely on server-side validation for security.

Insecure patterns:

* Rendering user-uploaded HTML as content.
* Inline rendering of untrusted SVG/HTML via `dangerouslySetInnerHTML` or `<iframe srcdoc=...>` without sanitization.

Detection hints:

* Look for upload components and preview logic:

  * `input type="file"`, `FileReader`, `URL.createObjectURL`, `<iframe>`, `<object>`, `<embed>`.
* Trace where uploaded content is later displayed.

Fix:

* Restrict accepted types, sanitize where required, and prefer download/attachment flows for risky types.
* Ensure the server enforces the actual policy (type checking, renaming, scanning, storage outside webroot).

Notes:

* The OWASP file-upload guide highlights extension allowlists, file-type validation, name generation, size limits, storage outside the webroot, and the need to consider "client-side active content (XSS, CSRF, etc.)" when files are publicly accessible. ([OWASP Cheat Sheet Series][19])

---

### REACT-SUPPLY-001: Dependency and supply-chain hygiene (frontend + build tooling)

Severity: Low

Required:

* MUST use a lockfile and ensure reproducible installs in CI.
* SHOULD audit dependencies regularly and respond promptly to advisories for:

  * React, react-dom, router libraries, build tooling (Vite/Webpack), sanitizers, auth libraries, etc.
* SHOULD reduce risk from install-time scripts and typo-squatting.

Audit focus:

* CI must use `npm ci` (or Yarn frozen lockfile / pnpm equivalent) to prevent drift.
* Use vulnerability scanning (`npm audit`, GitHub Dependabot/alerts, etc.).

Insecure patterns:

* No lockfile, or the lockfile is ignored in CI.
* `npm install` in CI, producing non-reproducible builds.
* Unpinned or unvetted high-risk dependencies; sudden major upgrades without review.
* Blindly running install scripts from third-party packages.

Detection hints:

* Verify a lockfile exists: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`.
* Inspect CI scripts: `npm install` vs. `npm ci`.
* Look for `postinstall` scripts and suspicious build steps.

Fix:

* Use a lockfile and enforce it in CI (for example, `npm ci`).
* Run audits regularly; pin/upgrade responsibly.
* Where possible, consider restricting install scripts.

Notes:

* npm documentation describes `npm audit` as submitting the project's dependency tree to the registry to obtain a report of known vulnerabilities and (optionally) apply fixes via `npm audit fix`, noting that some vulnerabilities require manual review. ([npm Docs][20])
* npm documentation describes `npm ci` as intended for automated/CI environments: it requires an existing lockfile and fails if `package.json` and the lockfile are out of sync. ([npm Docs][21])
* The OWASP NPM guide recommends enforcing a lockfile and explicitly cites `npm ci` / `yarn install --frozen-lockfile` for failing on mismatches, and highlights install-time-script risk and the `--ignore-scripts` option as ways to reduce attack surface. ([OWASP Cheat Sheet Series][22])

---

## 5) Practical Scanning Heuristics (how to "hunt")

When actively scanning, use these high-signal patterns:

* Raw HTML / XSS escape hatches:

  * `dangerouslySetInnerHTML`, `__html:`
  * Markdown HTML-passthrough flags: `rehype-raw`, `allowDangerousHtml`, `sanitize: false`
* DOM XSS sinks:

  * `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `DOMParser`, `createContextualFragment`
* Dangerous JS execution:

  * `eval(`, `new Function(`, `setTimeout("`, `setInterval("`
* Untrusted URL injection / navigation:

  * `href={` / `src={` with untrusted values
  * `window.location`, `location.href`, `window.open`, `navigate(`
  * Query parameters: `next`, `returnTo`, `redirect`
* Token/session risk:

  * `localStorage.setItem`, `sessionStorage.setItem`, `getItem(` with `token`, `jwt`, `refresh`
* Cookie/CSRF coupling:

  * `credentials: 'include'`, `withCredentials: true` on state-changing requests without CSRF headers
* Third-party scripts:

  * `<script src=...>` in `public/index.html`
  * Tag-manager snippets and dynamic script insertion
* Service workers:

  * `navigator.serviceWorker.register`, Workbox usage, custom `fetch` handlers
* postMessage:

  * `postMessage(` with `*`, missing `event.origin` checks
* Supply chain:

  * No lockfile, CI with `npm install`, no audit step, risky postinstall scripts

Always try to confirm:

* data origin (trusted/untrusted)
* sink type (React escape hatch vs. DOM sink vs. navigation vs. storage)
* presence of defenses (sanitization, allowlists, CSP/Trusted Types, CSRF tokens, headers, governance)

---

## 6) Sources (accessed 2026-01-26)

Primary React documentation:

* React 19 stable announcement -- `https://react.dev/blog/2024/12/05/react-19` ([React][23])
* React DOM documentation: warning about `dangerouslySetInnerHTML` -- `https://react.dev/reference/react-dom/components/common#dangerouslysetting-the-inner-html` ([React][12])
* React (legacy), JSX escaping statement -- `https://legacy.reactjs.org/docs/introducing-jsx.html` ([React][14])

OWASP Cheat Sheet Series:

* Cross Site Scripting Prevention (framework escape hatches; React `dangerouslySetInnerHTML`; URL-validation notes) -- `https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][9])
* Content Security Policy -- `https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][2])
* Cross-Site Request Forgery Prevention -- `https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][6])
* HTML5 Security (Web Storage, postMessage, tabnabbing, sandbox frames) -- `https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][4])
* Third Party JavaScript Management -- `https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][5])
* File Upload -- `https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][19])
* NPM Security best practices -- `https://cheatsheetseries.owasp.org/cheatsheets/NPM_Security_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][22])

Browser/platform references (MDN, W3C):

* Trusted Types API -- `https://developer.mozilla.org/en-US/docs/Web/API/Trusted_Types_API` ([MDN Web Docs][3])
* W3C Trusted Types specification -- `https://www.w3.org/TR/trusted-types/` ([W3C][15])
* Subresource Integrity -- `https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity` ([MDN Web Docs][7])
* Clickjacking defenses overview -- `https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/Clickjacking` ([MDN Web Docs][8])
* Using Service Workers (HTTPS requirement; proxy-like behavior) -- `https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers` ([MDN Web Docs][10])
* Secure contexts (powerful APIs limited to HTTPS) -- `https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts` ([MDN Web Docs][18])
* Link `rel` attribute values (noopener/noreferrer) -- `https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/rel` ([MDN Web Docs][17])

Build-tooling / env-exposure references:

* Create React App warning about env variables -- `https://create-react-app.dev/docs/adding-custom-environment-variables/` ([create-react-app.dev][1])
* Vite env-variable security notes -- `https://vite.dev/guide/env-and-mode` ([vitejs][11])

Auth-token storage guidance:

* OAuth 2.0 for browser-based apps (token-storage discussion) -- `https://datatracker.ietf.org/doc/html/draft-ietf-oauth-browser-based-apps` ([IETF Datatracker][16])

Dependency-tooling references:

* npm audit documentation -- `https://docs.npmjs.com/cli/v10/commands/npm-audit/` ([npm Docs][20])
* npm ci documentation -- `https://docs.npmjs.com/cli/v10/commands/npm-ci/` ([npm Docs][21])

Sanitizer reference:

* DOMPurify -- `https://github.com/cure53/DOMPurify` ([GitHub][13])

[1]: https://create-react-app.dev/docs/adding-custom-environment-variables/ "Adding Custom Environment Variables | Create React App"
[2]: https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html "Content Security Policy - OWASP Cheat Sheet Series"
[3]: https://developer.mozilla.org/en-US/docs/Web/API/Trusted_Types_API "Trusted Types API - Web APIs | MDN"
[4]: https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html "HTML5 Security - OWASP Cheat Sheet Series"
[5]: https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html "Third Party Javascript Management - OWASP Cheat Sheet Series"
[6]: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html "Cross-Site Request Forgery Prevention - OWASP Cheat Sheet Series"
[7]: https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Subresource_Integrity "Subresource Integrity - Security | MDN"
[8]: https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/Clickjacking "Clickjacking - Security | MDN"
[9]: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html "Cross Site Scripting Prevention - OWASP Cheat Sheet Series"
[10]: https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers "Using Service Workers - Web APIs | MDN"
[11]: https://vite.dev/guide/env-and-mode "Env Variables and Modes | Vite"
[12]: https://react.dev/reference/react-dom/components/common "Common components (e.g. <div>) - React"
[13]: https://github.com/cure53/DOMPurify "GitHub - cure53/DOMPurify: DOMPurify - a DOM-only, super-fast, uber-tolerant XSS sanitizer for HTML, MathML and SVG. DOMPurify works with a secure default, but offers a lot of configurability and hooks. Demo:"
[14]: https://legacy.reactjs.org/docs/introducing-jsx.html "Introducing JSX - React"
[15]: https://www.w3.org/TR/trusted-types/ "Trusted Types"
[16]: https://datatracker.ietf.org/doc/html/draft-ietf-oauth-browser-based-apps "
            
                draft-ietf-oauth-browser-based-apps-26
            
        "
[17]: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel "HTML attribute: rel - HTML | MDN"
[18]: https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts "Secure contexts - Security | MDN"
[19]: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html "File Upload - OWASP Cheat Sheet Series"
[20]: https://docs.npmjs.com/cli/v10/commands/npm-audit "npm-audit | npm Docs"
[21]: https://docs.npmjs.com/cli/v10/commands/npm-ci "npm-ci | npm Docs"
[22]: https://cheatsheetseries.owasp.org/cheatsheets/NPM_Security_Cheat_Sheet.html "NPM Security - OWASP Cheat Sheet Series"
[23]: https://react.dev/blog/2024/12/05/react-19 "React v19 - React"
