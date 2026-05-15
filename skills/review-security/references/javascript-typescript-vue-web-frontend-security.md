# Vue.js Security Specification (Vue 3.x, TypeScript/JavaScript, typical tooling: Vite)

This document is intended as a **security specification** that supports:

1. **Secure-by-default code generation** for new Vue code.
2. **Security review / vulnerability hunting** in existing Vue code (both passive "spot issues while working" mode and active "scan the repo and produce a report" mode).

The document is intentionally written as a set of **normative requirements** ("MUST/SHOULD/MAY") plus **audit rules** (what bad patterns look like, how to detect them, and how to fix or mitigate them).

---

## 0) Safety, Boundaries, and Anti-Abuse Constraints (MUST FOLLOW)

* MUST NOT request, output, log, or commit secrets (API keys, passwords, private keys, session cookies, auth tokens).
* MUST NOT "fix" security by disabling protections (for example, weakening CSP, enabling unsafe template compilation, using `v-html` as a "quick way", bypassing backend authentication, or "just storing the token in localStorage").
* MUST provide **evidence-based findings** when auditing: cite file paths, code snippets, and configuration values that justify the claim.
* MUST be honest about uncertainty: if a defense may exist at the edge (CDN, reverse proxy, WAF, server headers), report it as "not visible in the repo; verify the runtime/infrastructure configuration".
* MUST keep the frontend trust model in mind: **any code shipped to the browser is readable and modifiable by an attacker**. Secrets and "security enforcement" cannot rely on frontend logic alone.

---

## 1) Modes of Operation

### 1.1 Generation Mode (default)

When asked to write new Vue code or modify existing code:

* MUST follow every **MUST** requirement in this specification.
* SHOULD follow every **SHOULD** requirement unless the user explicitly states otherwise.
* MUST prefer secure-by-default framework features and proven libraries over hand-rolled security code.
* MUST avoid introducing new risky sinks (runtime template compilation, `v-html` / `innerHTML`, unsafe URL navigation, dynamic script injection, etc.). ([Vue.js][1])

### 1.2 Passive Review Mode (always on while editing)

When working anywhere in a Vue repository (even if the user did not request a security scan):

* MUST "spot" violations of this specification in edited or adjacent code.
* SHOULD raise issues as they arise, with a brief explanation and a safe fix.

### 1.3 Active Audit Mode (explicit scan request)

When the user asks to "scan", "audit", or "hunt for vulnerabilities":

* MUST systematically search the codebase for violations of this specification.
* MUST output findings in a structured format (see §2.3).

Recommended audit order:

1. Build/deploy entry points and hosting configuration (Docker, CI, static hosting, SSR server).
2. Secret leakage (env usage, `.env*`, hardcoded keys). ([vitejs][2])
3. XSS surface area: templates, `v-html` / `innerHTML`, URL/style injection, DOM APIs. ([Vue.js][1])
4. Auth/session handling in the browser (token storage, credentialed requests, CSRF integration). ([Vue.js][1])
5. Routing/navigation (open redirect, "return_to/next", unsafe external navigation). ([Vue.js][1])
6. Third-party scripts and content (CDN assets, analytics, widgets, iframes). ([Vue.js][1])
7. Security headers and browser-hardening expectations (CSP, clickjacking). ([Vue.js][1])
8. SSR-specific concerns (state serialization, template boundaries) when applicable. ([Vue.js][1])

---

## 2) Definitions and Review Guidance

### 2.1 Untrusted Input (treated as attacker-controlled by default)

In a Vue application, untrusted input includes (non-exhaustive list):

* Anything from APIs: `fetch`, `axios`, GraphQL responses, webhooks, third-party SDKs.
* Router-controlled data: `route.params`, `route.query`, `route.hash`, and anything derived from `window.location`.
* Stored user content: DB content displayed in the UI (comments, profiles, CMS content).
* Browser-controlled storage: `localStorage`, `sessionStorage`, `IndexedDB`.
* Cross-window messaging: `postMessage` input.
* Anything an attacker may influence via DOM clobbering or HTML injection (especially when Vue is mounted on a "non-sterile" DOM). ([Vue.js][1])

### 2.2 State-Changing Action (frontend perspective)

An action is state-changing if it can:

* Create/update/delete data via API calls.
* Change auth/session state (login, logout, token refresh).
* Trigger privileged operations (payments, admin actions).
* Cause side effects (sending email, dispatching webhooks, modifying account settings).

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

This is the minimum "production baseline" that prevents common Vue/frontend misconfigurations.

* MUST ship a **production build** (not a dev build or dev server). ([Vue.js][3])
* MUST NOT include secrets in frontend bundles; treat all client env variables as public. ([vitejs][2])
* MUST NOT render untrusted templates and MUST NOT allow users to provide Vue templates (this is equivalent to arbitrary JS execution). ([Vue.js][1])
* SHOULD avoid raw HTML injection (`v-html`, `innerHTML`) unless the content is trusted or sandboxed reliably. ([Vue.js][1])
* SHOULD deploy baseline security headers (especially CSP and clickjacking protection) at the server/CDN level. ([OWASP Cheat Sheet Series][4])
* SHOULD use safe authentication patterns (prefer HttpOnly cookies for session tokens; coordinate CSRF with the backend). ([Vue.js][1])

---

## 4) Rules (generation + audit)

Each rule contains: required practice, insecure patterns, detection hints, and remediation.

### VUE-DEPLOY-001: Do not run a dev/preview server in production

Severity: High

Required:

* MUST NOT deploy the Vite/Vue dev server (`vite`, `npm run dev`, HMR) as a production server.
* MUST NOT use `vite preview` as a production server. ([vitejs][5])
* MUST build (`vite build`) and serve the built assets via a production-grade static server/CDN, or via a production SSR server when SSR is used. ([vitejs][6])

Insecure patterns:

* Docker/Procfile/systemd that runs `vite`, `npm run dev`, or `vite preview` as the production entry point.
* Publicly exposed HMR endpoints.

Detection hints:

* Look for: `vite`, `npm run dev`, `pnpm dev`, `yarn dev`, `vite preview`, `vue-cli-service serve`.
* Inspect Docker `CMD`, `ENTRYPOINT`, CI deploy scripts, platform configurations.

Fix:

* Build artifacts via `vite build`.
* Serve `dist/` from hardened hosting (CDN/static server) or integrate it into your backend server as static assets.

Notes:

* Using a dev/preview server locally is fine; flag this only if it is the production entry point.

---

### VUE-DEPLOY-002: Use Vue production builds and keep devtools off in production

Severity: Medium (High when production devtools/debug hooks are enabled)

Required:

* When loading Vue from a CDN/self-host without a bundler, MUST use the `.prod.js` builds in production. ([Vue.js][3])
* SHOULD ensure that production bundles do not enable Vue devtools and do not deliberately set production-devtools flags. ([Vue.js][7])

Insecure patterns:

* Dev-build artifacts present in production.
* Explicit enabling of production devtools/diagnostic hooks.

Detection hints:

* In HTML, look for `vue.global.js` or non-`.prod.js` variants when using a CDN.
* In build configuration, look for Vue feature flags such as `__VUE_PROD_DEVTOOLS__`. ([Vue.js][7])

Fix:

* Switch to production build artifacts and ensure compile-time flags are configured for production.

---

### VUE-SECRETS-001: Never ship secrets in frontend code or env variables

Severity: High (Critical when actual credentials are exposed)

Required:

* MUST treat frontend code and configuration as public.
* MUST NOT embed secrets in:

  * source code
  * `.env` files committed to the repo
  * `import.meta.env.*` variables that end up in the bundle
* MUST assume that any env variable that ends up in the client bundle is readable by an attacker. ([vitejs][2])

Insecure patterns:

* `VITE_API_KEY=...` containing an actual secret (rather than a public identifier).
* Hardcoded API keys, private tokens, service credentials, or signing keys in JS/TS.

Detection hints:

* Look for: `VITE_`, `import.meta.env`, `.env`, `.env.production`, `.env.*.local`.
* Grep for `API_KEY`, `SECRET`, `TOKEN`, `PRIVATE_KEY`, `BEGIN`, `sk-`, `AKIA`, etc.

Fix:

* Move secrets to backend/edge functions.
* Where necessary, use short-lived tokens issued by the backend for the browser.

Notes:

* Vite specifically warns that `.env.*.local` should be in gitignore and that `VITE_*` variables end up in the client bundle and must not contain sensitive information. ([vitejs][2])

---

### VUE-SECRETS-002: Do not broaden Vite's env-variable exposure

Severity: High

Required:

* MUST NOT configure Vite to expose all environment variables to the client.
* SHOULD keep `envPrefix` strict and explicit.

Insecure patterns:

* Setting `envPrefix` to overly broad values (or `''`) "to make env variables work".
* Custom scripts that inject server-side secrets into global variables in HTML at build time.

Detection hints:

* Inspect `vite.config.*` for `envPrefix`.
* Look for `define: { 'process.env': ... }` or manual injection into `window.__CONFIG__`.

Fix:

* Keep secrets server-side.
* Expose only non-sensitive values that were originally intended for public use.

Notes:

* Vite documentation explains that only prefixed variables are exposed and that these variables end up in the client bundle. ([vitejs][2])

---

### VUE-XSS-001: Prefer Vue's default escaping; avoid raw HTML injection

Severity: High

Required:

* MUST rely on Vue's automatic escaping for text interpolation and attribute binding where possible. ([Vue.js][1])
* MUST NOT render user HTML via:

  * `v-html`
  * `innerHTML` in render functions / JSX
  * direct DOM APIs (`element.innerHTML`, `insertAdjacentHTML`)
    unless the HTML is trusted or robustly sanitized and the risk is explicitly accepted. ([Vue.js][1])

Insecure patterns:

* `<div v-html="userProvidedHtml"></div>`
* `h('div', { innerHTML: userProvidedHtml })`
* `<div innerHTML={userProvidedHtml}></div>`
* `el.innerHTML = untrusted`

Detection hints:

* Look for: `v-html`, `innerHTML`, `insertAdjacentHTML`, `DOMParser`, `document.write`.

Fix:

* Render untrusted content as text (via interpolation).
* If HTML rendering is required (for example, Markdown), sanitize via a well-supported HTML sanitizer and apply defense-in-depth (CSP, Trusted Types). ([Vue.js][1])

Notes:

* Vue documentation explicitly warns that user-provided HTML is never "100% safe" unless sandboxed or visible only to the user themselves. ([Vue.js][1])

---

### VUE-XSS-002: Never use untrusted templates (client-side template/code injection)

Severity: Critical

Required:

* MUST NOT use untrusted content as a Vue component template.
* MUST treat "the user can write a Vue template" as "the user can execute arbitrary JavaScript in your application", and in an SSR context potentially on the server. ([Vue.js][1])
* SHOULD prefer a runtime-only build (templates compiled at build time) and not ship the runtime compiler without a verified need.

Insecure patterns:

* `createApp({ template: '<div>' + userProvidedString + '</div>' }).mount(...)`
* Storing templates in a DB and compiling/rendering them in the browser.
* Admin/CMS features that allow inputting Vue template syntax.

Detection hints:

* Look for: `template:` where the value is not a static string.
* Look for: `@vue/compiler-dom`, `compile(`, build configurations selecting the runtime compiler, dynamic SFC compilation.
* Look for "template editor", "custom template", "theme HTML" features.

Fix:

* Treat templates as code: keep them under developer control.
* If end-user customization is required, use a safe format (a restricted Markdown subset) rendered through a sanitizer, or isolate it in a sandboxed iframe.

---

### VUE-XSS-003: Do not mount Vue on a DOM that may contain user-provided server-rendered HTML

Severity: Medium

Required:

* MUST NOT mount Vue on nodes that may contain server-rendered user content (because attacker-controlled HTML that is "safe as HTML" can become unsafe as a Vue template). ([Vue.js][1])
* SHOULD mount Vue into a "sterile" root element and render the application's DOM from Vue-controlled templates/components.

Insecure patterns:

* The server renders user content into `#app`, then Vue mounts on `#app` and interprets that DOM as a template.
* "Sprinkle Vue" added to large server-rendered pages with user content.

Detection hints:

* Inspect server templates (for example, Rails/Django/Express) for user HTML being inserted inside the Vue root element.
* Look for `mount('#app')` where `#app` contains server-rendered UGC.

Fix:

* Move user HTML outside the Vue mount root, or render it safely (as text/sanitized HTML) from Vue components.

---

### VUE-XSS-004: Prevent URL injection in bindings and navigations

Severity: High

Required:

* MUST validate/sanitize any user-influenced URL before binding to navigation sinks (`href`, `src`, `action`, `window.location`, `window.open`, router navigation to an external URL).
* MUST in particular prevent execution of `javascript:` URLs in bindings such as `<a :href="userProvidedUrl">`. ([Vue.js][1])
* SHOULD validate the protocol and destination (allowlist `https:` and expected hosts; `mailto:`/`tel:` only when intended).

Insecure patterns:

* `<iframe :src="userProvidedUrl">`
* `window.location = route.query.next`
* `window.open(userProvidedUrl)`

Detection hints:

* Look for: `:href=`, `:src=`, `window.location`, `location.href`, `window.open`, `router.push(` with untrusted input.
* Look for query parameters `next`, `return_to`, `redirect`.

Fix:

* Prefer internal navigation via route names/paths that you control.
* For external URLs: parse via `new URL(...)`, allowlist protocol/host, reject `javascript:` and other dangerous schemes.
* Sanitize and validate on the backend before storing user URLs (Vue documentation explicitly recommends sanitization on the backend). ([Vue.js][1])

---

### VUE-XSS-005: Prevent style/CSS injection and UI redressing

Severity: Low

Required:

* MUST NOT bind broad attacker-controlled CSS strings (for example, `:style="userProvidedStyles"`).
* SHOULD use Vue's object style syntax and allow only specific safe properties when customization is required. ([Vue.js][1])
* SHOULD isolate "user controls layout/CSS" features in a sandboxed iframe.

Insecure patterns:

* `:style="userProvidedStyles"` where styles are attacker-controlled.
* Rendering user `<style>` content (even though Vue blocks some patterns, do not try to work around this).

Detection hints:

* Look for: `:style="` bound to non-constant variables coming from APIs/user content.
* Look for "custom CSS", "theme editor", "profile CSS".

Fix:

* Allowlist properties and values; avoid raw style strings.
* Use a sandboxed iframe for rich user customization.

---

### VUE-XSS-006: Never bind user-supplied JavaScript to event-handler attributes

Severity: Critical

Required:

* MUST NOT bind attacker-supplied strings to event-handler attributes (for example, `onclick`, `onfocus`, etc.).
* MUST treat "user JS" as unsafe unless run in a sandbox guaranteed to be visible only to the user themselves. ([Vue.js][1])

Insecure patterns:

* `<div :onclick="userProvidedString">`
* `<a :onmouseenter="userProvidedString">`

Detection hints:

* Look for: `:on` followed by event-attribute names (`:onclick`, `:onload`, etc.).
* Look for `setAttribute('on` patterns.

Fix:

* Use real event listeners with developer-controlled handlers.
* If user-defined scripting is genuinely required, isolate it (sandboxed iframe + strict boundaries).

---

### VUE-ROUTER-001: Do not treat client-side route guards as authorization

Severity: High

Required:

* MUST NOT rely on Vue Router guards, UI hiding, or client-side checks for authorization.
* MUST enforce authorization on the backend for every privileged action and every response containing sensitive data. ([OWASP Cheat Sheet Series][8])

Insecure patterns:

* "The admin route is protected because `beforeEach` checks `user.isAdmin`."
* Sensitive API endpoints assuming "the frontend will not call this if it is not allowed".

Detection hints:

* Look for `router.beforeEach` role-based protection and verify whether the backend does the same.
* Look for "security by route meta" patterns (`meta.requiresAdmin`) without server-side enforcement.

Fix:

* Keep route guards as UX only (reducing accidental access), but perform the actual check on the server.

---

### VUE-ROUTER-002: Prevent open redirects and unsafe "return_to/next" handling

Severity: Low

Required:

* MUST validate redirect targets from untrusted input (`next`, `return_to`, `redirect`).
* SHOULD allow only same-site relative paths or an explicit allowlist of destinations.
* MUST NOT allow non-`http`/`https` protocols (for example, `javascript:`).

Insecure patterns:

* `router.push(route.query.next as string)`
* `window.location.href = route.query.redirect`

Detection hints:

* Look for `route.query.next`, `route.query.redirect`, `return_to`, `continue`, `callback`.
* Trace the value into router/window navigation sinks.

Fix:

* Allow only relative paths starting with `/` (and reject `//host`, `javascript:`, etc.).
* Prefer redirecting to named routes that you control.

Notes:

* Even Vue documentation notes that sanitized URLs may still not guarantee a safe destination. ([Vue.js][1])

---

### VUE-AUTH-001: Token storage must assume that XSS is possible

Severity: Low

Required:

* MUST assume that any token accessible to JavaScript can be stolen via XSS.
* SHOULD prefer HttpOnly cookies (set by the backend) for session tokens, combined with CSRF defenses where appropriate. ([Vue.js][1])
* SHOULD avoid storing long-lived tokens (especially refresh tokens) in `localStorage`/`sessionStorage`.

Insecure patterns:

* `localStorage.setItem('token', ...)` for long-lived bearer tokens.
* Storing refresh tokens in JS-accessible storage.

Detection hints:

* Look for: `localStorage`, `sessionStorage`, `indexedDB`, `persist`, `pinia-plugin-persistedstate`.
* Determine whether the stored values are auth/session material.

Fix:

* Prefer server-managed sessions via HttpOnly cookies.
* If bearer tokens are unavoidable, keep them short-lived, in memory, and rotated frequently; combine with strong XSS defenses (CSP, Trusted Types, strict sanitization). ([OWASP Cheat Sheet Series][4])

---

### VUE-CSRF-001: Coordinate CSRF with the backend when using cookies

Severity: High (for cookie-authenticated state-changing requests)

NOTE: If the application does not use cookie-based authentication (for example, it sends an Authorization header), CSRF is not a concern.

Required:

* If API requests include cookies (`credentials: 'include'` / `withCredentials: true`) and cookies authenticate the user, MUST include CSRF defenses coordinated with the backend (token/header patterns, Origin checks, SameSite cookies as defense-in-depth). ([Vue.js][1])
* MUST NOT "fix CORS/CSRF errors" by disabling backend defenses or using `mode: 'no-cors'` on the frontend.

Insecure patterns:

* `fetch(url, { credentials: 'include', method: 'POST', body: ... })` without any use of a CSRF token/header.
* Enabling cross-origin credentialed requests without a strict origin allowlist (on the backend).

Detection hints:

* Look for: `credentials: 'include'`, `withCredentials`, `xsrf`, `csrf`, `X-CSRF-Token`, `X-XSRF-TOKEN`.
* Inspect API wrapper modules for headers and cookie settings.

Fix:

* Implement backend issuance of CSRF tokens and require them on state-changing requests.
* Keep cookies `SameSite=Lax/Strict` where compatible, and verify Origin/Referer where appropriate (on the backend). ([OWASP Cheat Sheet Series][9])

Notes:

* Vue documentation explicitly states that CSRF is mostly addressed on the backend, but recommends coordinating CSRF-token transmission. ([Vue.js][1])

---

### VUE-HTTP-001: Do not put secrets in URLs; avoid leakage of sensitive data through navigation/logs

Severity: Medium

Required:

* MUST NOT put tokens/secrets in query strings or fragments (they leak via logs, the referrer, and browser history).
* SHOULD avoid logging sensitive values to the console in production.

Insecure patterns:

* `/?token=...`, `/#access_token=...` used beyond a short-lived OAuth handoff.
* `console.log(userSession)` including tokens/PII.

Detection hints:

* Look for `token=` in router parsing, auth-callback handlers, analytics logs.
* Look for `console.log(` near auth code.

Fix:

* Use Authorization headers or HttpOnly cookies.
* Clean up logs; gate debug logs behind dev-only checks.

---

### VUE-HEADERS-001: Require security headers at the deployment layer

Severity: Medium

Required:

* SHOULD deploy a CSP (`Content-Security-Policy`) appropriate to your Vue application.
* SHOULD deploy clickjacking protection (CSP `frame-ancestors` and/or `X-Frame-Options`) unless intentional embedding is required.
* SHOULD deploy `X-Content-Type-Options: nosniff` plus other headers as required (Referrer-Policy, Permissions-Policy). ([OWASP Cheat Sheet Series][4])

Insecure patterns:

* No evidence of headers in server/CDN configuration for an application with UGC or rich HTML rendering.
* CSP includes `unsafe-inline`/`unsafe-eval` without strong justification.

Detection hints:

* Look for hosting configuration: nginx, Netlify/Vercel header configs, CloudFront/Cloudflare rules.
* If absent from the repo, mark as "verify at edge".

Fix:

* Configure headers at the edge or on the server. Start with a conservative CSP and tighten over time.

---

### VUE-CSP-001: When possible, use Trusted Types and DOM XSS hardening

Severity: Low

Required:

* For applications with significant DOM-injection surface area (rich text, plugins, `v-html`), SHOULD consider enabling Trusted Types to reduce DOM XSS risk. ([web.dev][10])
* SHOULD treat Trusted Types as defense-in-depth, not a replacement for sanitization.

Insecure patterns:

* Frequent use of `innerHTML`/`v-html` without sanitization or CSP hardening.

Detection hints:

* Look for: `v-html`, `innerHTML`, `insertAdjacentHTML`.
* Check the CSP for `require-trusted-types-for 'script'` (if headers are in the repo).

Fix:

* Reduce/centralize HTML injection, sanitize input, and add Trusted Types policies where appropriate.

---

### VUE-THIRDPARTY-001: Avoid dynamic third-party script injection; prefer static, vetted loading

Severity: Low

Required:

* MUST NOT inject `<script src="...">` where the URL is user-controlled.
* SHOULD treat third-party widgets/analytics as supply-chain risk; load only from vetted, pinned sources.

Insecure patterns:

* `const s=document.createElement('script'); s.src = userProvidedUrl; ...`
* "Plugin marketplace" features that load arbitrary remote scripts.

Detection hints:

* Look for: `createElement('script')`, `.src =`, `appendChild(script)`.
* Look for "loadExternalScript", "injectScript", "cdnUrl".

Fix:

* Bundle dependencies, or allowlist strict origins and apply integrity (see the SRI rule).
* Consider sandboxed iframes for untrusted third-party UI.

---

### VUE-SRI-001: Use Subresource Integrity for CDN-served scripts/styles

Severity: Low

Required:

* When loading scripts/styles from a CDN, SHOULD use Subresource Integrity (the `integrity` attribute) with the appropriate `crossorigin` configuration. ([MDN Web Docs][11])
* SHOULD prefer self-hosting or bundling over runtime CDN dependencies for security-critical code.

Insecure patterns:

* `<script src="https://cdn.example/...">` without `integrity`.
* Remote-script URLs that may change content without version pinning.

Detection hints:

* In `index.html` and server templates, look for `https://` script/style tags.
* Verify that `integrity=` is present.

Fix:

* Add SRI hashes (and pin versions) or bundle the assets into your build.

---

### VUE-SUPPLY-001: Dependency and patch hygiene is required

Severity: Low

Required:

* SHOULD keep Vue and official companion libraries up to date; Vue explicitly recommends using the latest versions for maximum security. ([Vue.js][1])
* MUST respond promptly to security advisories.
* SHOULD pin dependencies and keep a lockfile in the repo (to reduce drift in production artifacts).

Insecure patterns:

* Outdated major versions with known CVEs.
* No lockfile in the repo; broad semver ranges for critical dependencies.
* Ignored advisories for template/rendering/compiler packages.

Detection hints:

* Inspect `package.json`, lockfiles, and install commands in CI.
* Look for disabled `npm audit` or "ignore vulnerabilities" scripts.

Fix:

* Update dependencies and add regression tests around affected behavior.
* Add dependency scanning to CI.

---

### VUE-SSR-001: SSR adds extra trust boundaries; treat state injection as XSS-sensitive

Severity: Medium

Required:

* When using SSR, MUST treat anything injected into the HTML document (initial state, serialized data, inline scripts) as XSS-sensitive.
* MUST follow the "trusted templates only" rule even more strictly because unsafe templates can lead to server-side execution during rendering. ([Vue.js][1])
* SHOULD follow Vue SSR documentation and SSR security best practices. ([Vue.js][1])

Insecure patterns:

* Concatenating untrusted strings into SSR templates.
* JSON injection into `<script>` blocks without robust escaping/serialization control.

Detection hints:

* In server-side code, look for `__INITIAL_STATE__`, `window.__*STATE__`, template concatenation, and SSR pipelines.
* Trace untrusted data into these sinks.

Fix:

* Use safe serialization patterns recommended by your SSR stack.
* Avoid rendering untrusted HTML; sanitize or isolate it.

---

## 5) Practical Scanning Heuristics (how to "hunt")

When actively scanning, use these high-signal patterns:

* Dev/preview servers in production:

  * `npm run dev`, `vite`, `vite preview`, `vue-cli-service serve` ([vitejs][5])
* Secret leakage:

  * `.env`, `.env.production`, `.env.*.local`, `VITE_`, `import.meta.env`, hardcoded `API_KEY` / `SECRET` ([vitejs][2])
* XSS sinks:

  * `v-html`, `innerHTML`, `insertAdjacentHTML`, `DOMParser`, `document.write` ([Vue.js][1])
* Client-side template injection:

  * `template:` concatenation, `compile(`, runtime-compiler usage, mounting on a non-sterile DOM ([Vue.js][1])
* URL injection / open redirect:

  * `:href="..."` / `:src="..."` from user data
  * `javascript:` occurrences
  * `route.query.next` / `redirect` / `return_to` flowing into `router.push` or `window.location` ([Vue.js][1])
* Style injection:

  * `:style="userProvidedStyles"` or user-controlled CSS themes ([Vue.js][1])
* Token storage:

  * `localStorage.setItem('token'...)`, persisted auth stores, refresh tokens in JS-accessible storage
* CSRF integration red flags:

  * `credentials: 'include'` / `withCredentials: true` with no CSRF header/token handling ([Vue.js][1])
* Third-party scripts:

  * dynamic script injection (`createElement('script')`), CDN scripts without SRI ([MDN Web Docs][11])
* External-link safety:

  * `target="_blank"` without `rel="noopener"`/`noreferrer` (still recommended for compatibility and explicitness) ([MDN Web Docs][12])

Always try to confirm:

* data origin (untrusted vs. trusted)
* sink type (HTML/DOM insertion, template compilation, URL navigation, style injection, script injection)
* presence of defensive controls (sanitization, allowlists, CSP/Trusted Types, backend validation)

---

## 6) Sources (accessed 2026-01-27)

Primary Vue documentation:

* Vue Docs: Security -- `https://vuejs.org/guide/best-practices/security` ([Vue.js][1])
* Vue Docs: Template Syntax (in-DOM template security warning) -- `https://vuejs.org/guide/essentials/template-syntax` ([Vue.js][13])
* Vue Docs: Production Deployment -- `https://vuejs.org/guide/best-practices/production-deployment` ([Vue.js][3])
* Vue Docs: Feature Flags -- `https://link.vuejs.org/feature-flags` ([Vue.js][7])

Vite documentation (typical Vue tooling):

* Vite Docs: Env Variables and Modes (VITE_* exposure + security notes) -- `https://vite.dev/guide/env-and-mode` ([vitejs][2])
* Vite Docs: CLI (`vite preview` is not intended for production) -- `https://vite.dev/guide/cli` ([vitejs][5])
* Vite Docs: Server Options (`server.host` may listen on public addresses) -- `https://vite.dev/config/server-options` ([vitejs][14])

OWASP and web-platform hardening references:

* OWASP Cheat Sheet Series: XSS Prevention -- `https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html` ([Vue.js][1])
* OWASP Cheat Sheet Series: CSRF Prevention -- `https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][9])
* OWASP Cheat Sheet Series: Authorization -- `https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][8])
* OWASP Cheat Sheet Series: HTTP Headers -- `https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][4])
* HTML5 Security Cheat Sheet (referenced by Vue) -- `https://html5sec.org/` ([Vue.js][1])

Browser/platform references:

* MDN: `rel="noopener"` -- `https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel/noopener` ([MDN Web Docs][12])
* MDN: Subresource Integrity -- `https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity` ([MDN Web Docs][11])
* web.dev: Trusted Types -- `https://web.dev/trusted-types/` ([web.dev][10])

[1]: https://vuejs.org/guide/best-practices/security "https://vuejs.org/guide/best-practices/security"
[2]: https://vite.dev/guide/env-and-mode "https://vite.dev/guide/env-and-mode"
[3]: https://vuejs.org/guide/best-practices/production-deployment "https://vuejs.org/guide/best-practices/production-deployment"
[4]: https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html"
[5]: https://vite.dev/guide/cli "https://vite.dev/guide/cli"
[6]: https://vite.dev/guide/build "https://vite.dev/guide/build"
[7]: https://vuejs.org/guide/best-practices/production-deployment?utm_source=chatgpt.com "Production Deployment"
[8]: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html"
[9]: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html"
[10]: https://web.dev/articles/trusted-types "https://web.dev/articles/trusted-types"
[11]: https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Subresource_Integrity?utm_source=chatgpt.com "Subresource Integrity - Security - MDN Web Docs"
[12]: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel/noopener "https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel/noopener"
[13]: https://vuejs.org/guide/essentials/template-syntax "Template Syntax | Vue.js"
[14]: https://vite.dev/config/server-options "https://vite.dev/config/server-options"
