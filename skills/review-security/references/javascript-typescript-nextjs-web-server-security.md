# Next.js (TypeScript/JavaScript) Web Application Security Specification (Next.js 16.1.x, Node.js 20.9+)

This document is intended as a **security specification** that supports:

1. **Secure-by-default code generation** for new Next.js backend code (Route Handlers, API Routes, Server Actions, Proxy/Middleware).
2. **Security audit and vulnerability hunting** in existing Next.js repositories (both passive "spot issues while working" mode and active "scan the repo and report findings" mode).

The document is intentionally written as a set of **normative requirements** ("MUST/SHOULD/MAY") and **audit rules** (what insecure patterns look like, how to detect them, and how to fix or mitigate them).

Target scope: Next.js **16.1.x** (the latest line shown in the App Router documentation) ([Next.js][1]), running on Node.js **20.9+** (per Next.js system requirements). ([Next.js][2])

---

## 0) Safety, Boundaries, and Anti-Abuse Constraints (MANDATORY)

* MUST NOT request, output, log, or commit secrets (API keys, passwords, private keys, session cookies, OAuth tokens, `process.env` dumps, database URLs containing credentials).
* MUST NOT "fix" security by disabling protections (for example, disabling origin checks, weakening CORS to `*`, skipping authz checks, disabling cookie security flags, or disabling CSP because "it's hard").
* MUST provide **evidence-based findings** when auditing: cite file paths, code snippets, and configuration values that justify each claim.
* MUST be honest about uncertainty: if a defense may exist in the infrastructure (reverse proxy, CDN, WAF, platform headers), report it as "not visible in application code; verify at the runtime/config layer".
* MUST assume that all server code reachable from requests is reachable to attackers unless there is a clearly enforced authentication boundary (not just "the UI does not link to it").
* MUST treat TypeScript types as **non-security boundaries**: types do not validate runtime input; runtime checks are required. ([Next.js][3])

---

## 1) Modes of Operation

### 1.1 Generation Mode (default)

When asked to write new Next.js code or modify existing code:

* MUST honor every **MUST** requirement in this specification.
* SHOULD honor every **SHOULD** requirement unless the user explicitly directs otherwise.
* MUST prefer secure-by-default APIs and proven libraries over hand-rolled security code.
* MUST avoid introducing new risky "sinks" (dynamic code execution, unsafe redirects, serving user files as HTML, SSRF URL fetchers, building SQL strings, etc.).

### 1.2 Passive Review Mode (always on while editing)

When working anywhere in a Next.js repository (even if the user did not request a security scan):

* MUST "spot" violations of this specification in affected/adjacent code.
* SHOULD raise issues as they arise, with a brief explanation and a safe fix.

### 1.3 Active Audit Mode (explicit scan request)

When the user asks to "scan", "audit", or "hunt for vulns":

* MUST systematically search the codebase for violations of this specification.
* MUST output findings in a structured format (see §2.3).

Recommended audit order:

1. Deployment entry points and environment (Dockerfiles, `package.json` scripts, hosting configuration).
2. Next.js configuration (`next.config.*`), Proxy/Middleware, routing patterns.
3. Authentication, sessions, cookies.
4. CSRF defenses and state-changing endpoints (Server Actions, Route Handlers, API Routes).
5. XSS (React + CSP) and unsafe HTML rendering.
6. Data-leak hazards from cache (static rendering + caching + "use cache").
7. File handling (uploads/downloads) and path traversal.
8. Injection classes (SQL/ORM misuse, command execution, unsafe deserialization).
9. Outbound requests (SSRF).
10. Redirect handling (open redirects).
11. CORS and security headers.

---

## 2) Definitions and Review Guidance

### 2.1 Untrusted Input (treat as attacker-controlled until proven otherwise)

In Next.js backends, untrusted input includes:

App Router:

* Route Handler parameters and request data:

  * `context.params` (dynamic segments), search params (`request.url`, `new URL(request.url).searchParams`)
  * `request.headers`, `request.cookies`
  * `await request.json()`, `await request.formData()`, `await request.text()`
* Dynamic APIs used in Server Components/Server Functions:

  * `headers()` and `cookies()` values ([Next.js][4])

Pages Router:

* `req.query`, `req.cookies`, `req.body` in `pages/api/*` handlers ([Next.js][3])

Plus:

* Anything from external systems (webhooks, third-party APIs, message queues)
* Any stored user content (DB rows) that originally came from users

### 2.2 State-Changing Request

A request is state-changing if it can create/update/delete data, change auth/session state, cause side effects (purchase, sending email, dispatching a webhook), or initiate privileged actions.

Special note for Next.js:

* **Server Actions** are invoked via network requests and may mutate state; treat them as state-changing endpoints. ([Next.js][5])

### 2.3 Required Audit-Finding Format

For each issue found, output:

* Rule ID:
* Severity: Critical / High / Medium / Low
* Location: file path + function/route name + line(s)
* Evidence: exact code/config snippet
* Impact: what can go wrong, who can exploit it
* Fix: safe change (preferably a minimal diff)
* Mitigation: defense-in-depth if an immediate fix is difficult
* False positive notes: what to verify when uncertain

---

## 3) Secure Baseline: Minimum Production Configuration (MUST in production)

This is the minimum "production baseline" that prevents common Next.js backend misconfigurations.

### 3.1 Run Next.js in Production Mode (MUST)

* MUST run `next build` + `next start` (or the equivalent on a managed platform), not `next dev`. Dev mode has different error/reporting behavior and is not intended for production exposure. ([Next.js][6])
* MUST ensure that `NODE_ENV=production` is set in production (Next.js sets `NODE_ENV` by default depending on the command; verify the runtime environment). ([Next.js][7])

### 3.2 Place a Reverse Proxy / Edge Layer in Front of Self-Hosting (MUST for the public internet)

* When self-hosting, MUST place a reverse proxy (for example, nginx) or an equivalent edge layer in front of the Next.js server to handle malformed requests, slow attacks, payload size limits, rate limiting, and similar concerns. ([Next.js][8])

### 3.3 Baseline Header/Cookie Posture (SHOULD)

* SHOULD set baseline security headers globally (CSP, `X-Content-Type-Options`, clickjacking protection via CSP `frame-ancestors` and/or `X-Frame-Options`, etc.). Next.js provides guidance for implementing CSP via Proxy/headers. ([Next.js][7])
* MUST ensure auth/session cookies use safe attributes (`Secure`, `HttpOnly`, `SameSite`) as appropriate. ([Next.js][9])
IMPORTANT NOTE: only set `Secure` in production environments. When working in a local dev environment over HTTP, do not set the `Secure` property on cookies. Set this conditionally based on whether the application is running in production mode. Also include a property like `SESSION_COOKIE_SECURE` that can be used to disable `Secure` cookies when testing over HTTP.

### 3.4 Clear Separation Between Server-Only and Client Code (MUST)

* MUST prevent secrets and privileged logic from ending up in the client bundle.
* MUST treat `NEXT_PUBLIC_*` environment variables as public (visible in the browser and embedded at build time). ([Next.js][7])

---

## 4) Rules (generation + audit)

Each rule contains: required practice, insecure patterns, detection hints, and remediation guidance.

### NEXT-DEPLOY-001: Do not run `next dev` in production; ensure production-mode behavior

Severity: High (in production)

NOTE: If deployment is to a Next.js-specific hosting provider, this is not a concern.

Required:

* MUST NOT deploy `next dev` or any dev-server mode to production.
* MUST ensure that production builds and a production runtime are used for any public deployment. ([Next.js][6])

Insecure patterns:

* `next dev` in Docker `CMD`, Procfile, or platform start command.
* `NODE_ENV=development` in production environment configuration.
* Debug/dev-only endpoints or flags exposed publicly.

Detection hints:

* Look for `next dev` in `package.json` scripts and deployment manifests.
* Look for `NODE_ENV=development` or missing `NODE_ENV` in infrastructure.
* Inspect Kubernetes/PM2/systemd entry points for `next dev`.

Fix:

* Use `next build` during CI/build and `next start` at runtime (or platform-native build/run).
* Ensure the environment sets `NODE_ENV=production`.

Note:

* Dev mode is appropriate for local development. Flag it only when used as the production entry point.

---

### NEXT-SUPPLY-001: Stay on supported Next.js releases; apply patches for security advisories promptly

Severity: High (Critical for a known-vulnerable version)

Required:

* MUST run a supported Next.js version line and apply security updates promptly. Next.js documents an LTS/support policy. ([Next.js][10])
* MUST treat published advisories as urgent update signals (for example, upgrading to a patched release). ([GitHub][11])

Insecure patterns:

* Running an EOL major/minor Next.js version without backported security fixes.
* Ignoring advisories or pinning `next` to a vulnerable range.

Detection hints:

* Check `package.json` and lockfiles for the version of `next`.
* Compare against the Next.js support policy and advisories.

IMPORTANT: Any versions older than these minor versions are vulnerable to the "react2shell" vulnerability (https://nextjs.org/blog/CVE-2025-66478):
15.0.5
15.1.9
15.2.6
15.3.6
15.4.8
15.5.7
16.0.7

Fix:

* Update `next` to a supported and patched version.
* Add a dependency-update process and CI checks.


---

### NEXT-SECRETS-001: Secrets MUST NOT be committed or exposed to the browser

Severity: High (Critical when a secret is exposed to the client)

Required:

* MUST keep secrets in environment variables or a secret manager; MUST NOT commit `.env*` files.
* MUST treat `.env*` as sensitive; Next.js warns "you almost never want to commit these files". ([Next.js][7])
* MUST treat any `NEXT_PUBLIC_*` environment variable as public and visible in the browser (embedded into the client bundle at build time). ([Next.js][7])

Insecure patterns:

* `.env`, `.env.local`, `.env.production` committed to git.
* `NEXT_PUBLIC_API_KEY`, `NEXT_PUBLIC_SECRET`, `NEXT_PUBLIC_DATABASE_URL`, etc.
* Rendering `process.env` values into HTML or returning them from API routes.

Detection hints:

* Scan git history and repository files for `.env` content, `DB_PASS=`, `API_KEY=`, `SECRET=`.
* Grep for `NEXT_PUBLIC_` and review any names that look sensitive.
* Look for `process.env` usage in Client Components (`"use client"`) and shared modules.

Fix:

* Move secrets to server-only env variables (without the `NEXT_PUBLIC_` prefix).
* Ensure `.env*` is gitignored and that secrets are injected at deploy time.
* Rotate leaked keys.

---

### NEXT-SECRETS-002: Avoid server-only -> client bundling mistakes (the server/client boundary is a security boundary)

Severity: High

Required:

* MUST ensure that server-only modules (DB clients, secret-dependent code) are not imported into Client Components or other client-bundled code paths.
* SHOULD use server-only patterns/layers (for example, a dedicated DAL and server-only modules) and treat boundary violations as security bugs. Next.js explicitly discusses the "server-only" concept for sensitive modules. ([Next.js][6])

Insecure patterns:

* Importing DB clients, admin SDKs, or secret-reading modules into `"use client"` components.
* Common `lib/` modules imported by both server and client code that reference secrets.

Detection hints:

* Look for `"use client"` and inspect its imports for server-only dependencies.
* Look for DB-client packages (`pg`, `mysql2`, `mongoose`, `prisma`, admin SDKs) imported from `components/` or other client paths.
* Look for `process.env` access in UI components.

Fix:

* Refactor to `lib/server/*` and import only from server contexts (Route Handlers, Server Components, Server Actions).
* Add an explicit "server-only" guard pattern (and/or tests) to prevent accidental imports.

---

### NEXT-AUTH-001: Authentication/authorization MUST be enforced server-side for every protected action

Severity: High

Required:

* MUST enforce authn/authz in server code for:

  * Route Handlers (`app/**/route.ts`) ([Next.js][1])
  * API Routes (`pages/api/**`) ([Next.js][3])
  * Server Actions (`"use server"` functions called by clients) ([Next.js][6])
* MUST NOT rely on client-side checks (UI hiding, client-side route guards) as the sole defense.

Insecure patterns:

* Sensitive Route Handlers without a session check.
* Server Actions that mutate data but do not validate user identity/permissions.
* "Authorization" checks performed only in React components.

Detection hints:

* Enumerate all Route Handlers and API Routes; for each, determine whether auth is required.
* Grep for `"use server"` and review every exported action for auth checks.
* Look for admin actions triggered by query parameters / form submissions.

Fix:

* Centralize auth helpers and call them in every protected endpoint/action.
* Implement least-privilege authorization checks (role/resource ownership) for each action.

---

### NEXT-AUTH-002: Proxy/Middleware-based auth MUST NOT introduce route-coverage gaps

Severity: High

Required:

* When using **Proxy** or **Middleware** for authentication checks, MUST ensure they cover every route that needs protection.
* Next.js documentation notes that the Proxy can use `matcher`, and for auth it is recommended that the Proxy run on all routes. ([Next.js][12])
* MUST treat `matcher` mistakes as auth-bypass risk.

Insecure patterns:

* The Proxy/Middleware matches only "pages" but not `/api/*`, or matches only some route groups.
* "Denylist"-style matchers that miss alternative request forms (framework internals, RSC navigations, etc.).

Detection hints:

* Inspect `proxy.ts` / `middleware.ts` and its `matcher`.
* Compare matchers against the full set of routes (including `app/api/**` and `pages/api/**`).
* Verify that static assets and Next internals are excluded only intentionally and that sensitive routes are included.

Fix:

* Prefer allowlisting protected route prefixes, or run the Proxy globally and apply internal allow/deny logic.
* Add integration tests: request a protected route without auth and verify rejection.

Notes:

* The Proxy is typically used for "optimistic checks"; it is not by itself a complete authorization system. ([Next.js][12])

---

### NEXT-CSRF-001: Cookie-authenticated state-changing endpoints MUST be CSRF-protected

Severity: High

- IMPORTANT NOTE: If cookies are not used for auth (for example, auth via an Authentication header or another carrier token), CSRF is not a risk.

Required:

* MUST protect every state-changing endpoint that relies on cookies for auth (POST/PUT/PATCH/DELETE).
* For **Server Actions**, Next.js performs an Origin-vs-Host comparison to mitigate CSRF; do not disable or weaken this. ([Next.js][5])
* If Server Actions must be callable from additional trusted origins (for example, a trusted proxy domain), MUST use `allowedOrigins` with a strict allowlist. ([Next.js][5])
* For **Route Handlers** and **API Routes**, MUST implement CSRF protection explicitly (tokens and/or strict Origin/Referer + SameSite + custom headers). Route Handlers are an "escape hatch" and require application-level security decisions. ([Next.js][6])

Insecure patterns:

* POST endpoints (including Server Actions) that mutate state and accept cross-site requests without token/origin checks.
* `allowedOrigins: ['*']` (or wide wildcards) or "reflect Origin" logic.
* Using GET requests to change state.

Detection hints:

* Enumerate all state-changing endpoints and identify the auth mechanism.
* Look for `allowedOrigins` and confirm the list is small, specific, and justified. ([Next.js][5])
* In Route Handlers/API Routes: look for missing CSRF-token validation or missing Origin/Referer checks.

Fix:

* Implement a CSRF-token strategy for cookie-auth endpoints.
* Keep cookies `SameSite=Lax` or `Strict` when compatible; do not consider SameSite alone to be sufficient.
* Use strict Origin validation for JSON API endpoints, especially in the absence of CSRF tokens.

Notes:

* XSS can defeat CSRF protections; CSRF defenses are not a substitute for XSS prevention.

---

### NEXT-SESS-001: Session cookies MUST use safe attributes in production

Severity: Medium

Required (production, HTTPS):

* MUST set session/auth cookies with:

  * `Secure: true` (HTTPS only) IMPORTANT NOTE: only set `Secure` in production environments. When working in a local dev environment over HTTP, do not set the `Secure` property on cookies. Set this conditionally based on whether the application is running in production mode. Also include a property like `SESSION_COOKIE_SECURE` that can be used to disable `Secure` cookies when testing over HTTP.
  * `HttpOnly: true` (not readable by JS)
  * `SameSite: 'Lax'` (recommended) or `'Strict'` if compatible
* Use `SameSite: 'none'` only when you genuinely need cross-site cookies, and in that case MUST also set `Secure`. Cookie options are supported in the Next.js cookies API. ([Next.js][9])

Insecure patterns:

* `secure: false` in production.
* `httpOnly: false` for auth cookies.
* `sameSite: 'none'` without explicit need, especially on cookie-authenticated state-changing endpoints.

Detection hints:

* Look for cookie-setting locations (`cookies().set(...)`, `Set-Cookie` headers, the auth-library cookie configuration).
* Inspect cookie options used in Route Handlers and Server Actions. ([Next.js][9])

Fix:

* Set safe cookie attributes at the auth/session layer.
* Reduce cookie scope: avoid a broad `domain` unless cookies for all subdomains are explicitly required.

---

### NEXT-SESS-002: Sessions MUST be bounded and resistant to fixation/replay

Severity: Low

Required:

* SHOULD set bounded session lifetimes appropriate to the application.
* SHOULD rotate session identifiers on login and on privilege changes.
* MUST NOT store sensitive secrets directly in client-readable storage (including unencrypted cookies).

Insecure patterns:

* Long-lived admin sessions without rotation.
* "Remember me forever" for privileged roles without additional risk controls.
* Storing access tokens/refresh tokens in non-HttpOnly cookies or localStorage.

Detection hints:

* Inspect auth-library configuration for expiration and rotation.
* Look for `localStorage.setItem('token'...)` and use of non-HttpOnly cookies.

Fix:

* Use short lifetimes for privileged sessions; refresh with rotation.
* Store only opaque session IDs in cookies; keep sensitive material server-side.

---

### NEXT-INPUT-001: Runtime input validation is required (TypeScript is not validation)

Severity: High

Required:

* MUST validate and normalize all attacker-controlled input at runtime (schemas, type checks, bounds).
* Next.js API Routes explicitly note that `req.body` has type `any` and must be validated before use. ([Next.js][3])
* MUST validate Server Action arguments (treat them as hostile). ([Next.js][6])

Insecure patterns:

* Trusting the shape of `req.body` directly.
* Passing `params.id`/`searchParams` directly into DB queries or file paths.
* Parsing JSON and then assuming types without validation.

Detection hints:

* Identify endpoints that accept JSON/form input and verify schema validation is in place.
* Grep for `req.body.` and `await request.json()` usage in Route Handlers; verify validation exists.

Fix:

* Add schema validation (for example, zod/yup/valibot) and reject invalid input with 4xx.
* Validate IDs as strict types (UUID/int) and apply length/charset constraints.

---

### NEXT-HEADERS-001: Essential security headers MUST be set (in the application or at the edge)

Severity: Low

Required (typical web application):

* SHOULD set:

  * CSP (`Content-Security-Policy`) (see NEXT-CSP-001)
  * `X-Content-Type-Options: nosniff`
  * Clickjacking protection (`frame-ancestors` in CSP and/or `X-Frame-Options`)
  * `Referrer-Policy` and `Permissions-Policy` where appropriate
* MUST ensure cookies are set with safe attributes (see NEXT-SESS-001). ([Next.js][9])

Insecure patterns:

* No security headers anywhere (application or edge).
* Unintentionally allowing iframing.
* `Content-Type` sniffing possible due to missing `nosniff`.

Detection hints:

* Inspect `proxy.ts` / middleware for `response.headers.set(...)`. ([Next.js][7])
* If not visible in application code, mark it as "verify at edge/CDN".

Fix:

* Set headers centrally (Proxy/Middleware or another centralized mechanism).
* Ensure consistent headers across routes.

---

### NEXT-CSP-001: Use CSP to reduce XSS impact; prefer nonces for scripts

Severity: Medium

NOTE: The most important header to set is the CSP `script-src`. All other directives are less important and can usually be omitted in favor of development convenience.

Required:

* SHOULD deploy CSP, ideally with nonces for scripts.
* SHOULD follow the Next.js guidance for implementing CSP (including nonce generation and applying headers). ([Next.js][7])
* MUST avoid weakening CSP as a "fix" (for example, `script-src 'unsafe-inline'`) without an explicit risk acceptance.

Insecure patterns:

* CSP missing in applications that render user-generated HTML/markdown.
* CSP that broadly allows inline scripts or eval without strong justification.

Detection hints:

* Look for the setting of the `Content-Security-Policy` header and review its directives.
* Check `next/script` usage and whether a nonce is supplied when CSP requires one.

Fix:

* Implement CSP per the Next.js guide; use a nonce and apply it consistently.
* Reduce inline scripts; avoid `eval`.

Notes:

* CSP is defense-in-depth; it does not replace proper output encoding and sanitization.

---

### NEXT-XSS-001: Prevent reflected/stored XSS in React/Next rendering

Severity: High

Required:

* MUST rely on React's default escaping; MUST NOT inject untrusted HTML into the DOM without sanitization.
* MUST treat the following as high-risk sinks:

  * `dangerouslySetInnerHTML`
  * Rendering user-controlled strings into `<script>` tags or event-handler attributes
* MUST avoid serving uploaded HTML as active HTML (serve as an attachment, or sanitize/transform).

Insecure patterns:

* `<div dangerouslySetInnerHTML={{ __html: userContent }} />` without a sanitizer.
* Markdown renderers configured to allow raw HTML without a sanitizer.
* Returning user content with `Content-Type: text/html` from a Route Handler.

Detection hints:

* Look for `dangerouslySetInnerHTML`, `__html:`.
* Look for template-like string concatenation that builds HTML.
* Review any "render HTML" or "preview" features.

Fix:

* Sanitize untrusted HTML with a well-supported sanitizer; prefer strict allowlists.
* Prefer rendering user content as text rather than HTML.
* Add CSP to reduce impact.

---

### NEXT-ACTION-001: Server Actions MUST be treated as public endpoints

Severity: High (Critical for privileged actions)

Required:

* MUST apply the same controls as for Route Handlers:

  * authn/authz
  * input validation
  * CSRF/origin defenses
  * rate limiting for sensitive actions
* MUST NOT assume Server Actions are "unreachable" or "internal".
* MUST understand Server Action request defenses:

  * Next.js compares Origin to Host to mitigate CSRF; additional origins must be explicitly allowlisted via `allowedOrigins`. ([Next.js][5])

Insecure patterns:

* `"use server"` functions that update DB state without auth checks.
* Adding overly broad `allowedOrigins` "to make it work".

Detection hints:

* Grep for `"use server"` and inventory all exported actions.
* Identify any action performing privileged writes; verify it checks identity and permissions.

Fix:

* Wrap actions with an authz helper (fail closed).
* Keep `allowedOrigins` minimal and audited.

---

### NEXT-ACTION-002: Do not accidentally leak secrets through Server Action closure/binding patterns

Severity: Medium (High when important secrets are exposed)

Required:

* MUST treat closed-over Server Action values as sensitive and design intentionally.
* Next.js notes that closed-over values are encrypted/signed, but values passed via `.bind` are not encrypted; do not rely on `.bind` to protect secrets. ([Next.js][6])
* If a stable encryption key for Server Actions is used across deployments, MUST treat it as a secret and store it safely (do not commit/log). ([Next.js][6])

Insecure patterns:

* `myAction.bind(null, process.env.SECRET)` or binding sensitive tokens/IDs that should not be client-influenced.
* Logging action arguments that include secrets.

Detection hints:

* Look for `.bind(` on Server Action functions.
* Look for `process.env` usage near Server Actions.

Fix:

* Avoid binding secrets into actions; obtain secrets server-side inside the action.
* Keep action arguments minimal and validated.

---

### NEXT-CACHE-001: Prevent data leakage through static rendering and shared cache

Severity: High (Critical when cross-user data leakage is possible)

Required:

* MUST ensure that pages/endpoints returning user-specific or sensitive data are not statically generated or cached in a way that is shared across users.
* Route Handlers are not cached by default, but GET handlers can opt into caching/static behavior; do not do so for per-user data. ([Next.js][1])
* MUST treat `use cache` and similar caching mechanisms as potentially cross-user unless it has been explicitly proven that they are private; do not cache per-user DB results in shared caches. ([Next.js][1])
* SHOULD set explicit `Cache-Control: no-store` / `private` for sensitive responses (auth/session/user-data APIs).

Insecure patterns:

* `export const dynamic = 'force-static'` on a route returning user-specific data. ([Next.js][1])
* Use of `use cache` around a function querying user-specific data without a per-user cache key. ([Next.js][1])
* Returning auth/session responses from GET endpoints with caching enabled.

Detection hints:

* Look for `dynamic = 'force-static'`, `revalidate`, `use cache`, `cacheLife`, `unstable_cache`.
* Review all cacheable/static GET Route Handlers and verify they only return public data.
* Confirm that the use of `cookies()`/`headers()` (dynamic APIs) has not been accidentally removed in ways that make the route static. ([Next.js][1])

Fix:

* Mark sensitive routes as dynamic and set `Cache-Control: no-store`.
* Ensure cache keys include user identity if caching is genuinely required (and store in a user-private cache).

---

### NEXT-FILES-001: User uploads MUST be validated, stored safely, and served safely

Severity: Medium

Required:

* MUST enforce upload size limits at the edge and in application logic.
* MUST validate file type using an allowlist and content checks (not just the extension).
* MUST store uploads outside the `public/` directory (anything under `public/` is served as static content by default).
* MUST safely serve potentially active formats (`Content-Disposition: attachment`) unless explicitly intended.

Insecure patterns:

* Accepting arbitrary file types and serving them back inline.
* Using a user-supplied filename as the storage path.
* Writing uploads to `public/uploads/` and serving them directly.

Detection hints:

* Look for `formData()` / multipart parsing, `fs.writeFile` usage, storage SDKs.
* Look for any write path under `public/`.
* Look for "download" endpoints setting `Content-Type: text/html` or serving user files inline.

Fix:

* Use dedicated object storage (S3/GCS) or a safe server directory outside static roots.
* Generate random filenames server-side; store metadata separately.

---

### NEXT-PATH-001: Prevent path traversal and unsafe file access

Severity: High

Required:

* MUST NOT use user-controlled strings as filesystem paths.
* MUST validate and normalize identifiers; use allowlists and safe base directories.
* MUST avoid reading arbitrary files based on request parameters.

Insecure patterns:

* `fs.readFile(request.nextUrl.searchParams.get('path'))`
* `path.join(base, userPath)` without normalization + boundary checks

Detection hints:

* Look for `fs.` usage in Route Handlers/API Routes.
* Look for `path.join`/`path.resolve` fed by request parameters.

Fix:

* Use opaque IDs that map to server-stored paths.
* Enforce that resolved paths remain within the intended base directory.
* Sanitize and disallow `..` when building URLs.

---

### NEXT-SSRF-001: Outbound requests using user-influenced URLs MUST be constrained

Severity: Medium (High in internal networks)

NOTE: This mostly applies to applications deployed in a cloud/LAN configuration or that have other HTTP services on the same machine. Sometimes a feature unavoidably requires this functionality (webhooks).

Required:

* MUST treat any server `fetch()` to a user-supplied URL as high-risk.
* SHOULD allowlist destinations (hosts/domains) for URL-fetch features.
* SHOULD block:

  * localhost / private IP ranges / link-local
  * cloud metadata endpoints
* MUST restrict protocols to `http:` and `https:`.
* SHOULD set strict timeouts and limit redirects.

Insecure patterns:

* `await fetch(req.query.url)` or `await fetch((await request.json()).url)`
* "URL preview" endpoints that fetch arbitrary URLs.

Detection hints:

* Look for `fetch(` in server code and trace where the URL originates.
* Look for "webhook tester", "preview", "import from URL" features.

Fix:

* Parse URLs, enforce `http/https`, allowlist hostnames, re-resolve DNS/IP to block private ranges.
* Set timeouts (AbortSignal) and limit redirects.

---

### NEXT-REDIRECT-001: Prevent open redirects (including in auth flows)

Severity: Low

Required:

* MUST validate redirect targets derived from untrusted input (for example, `next`, `redirect`, `returnTo`).
* SHOULD prefer redirecting only to same-site relative paths.
* MUST validate any absolute URL against an allowlist.
* MUST ensure URLs use the `http` or `https:` scheme, disallowing the `javascript:` scheme.

Insecure patterns:

* `redirect(searchParams.get('next')!)`
* `NextResponse.redirect(new URL(req.nextUrl.searchParams.get('to')!, req.url))` without checks

Detection hints:

* Look for `redirect(` (server components/actions) and `NextResponse.redirect`.
* Look for `res.redirect(` in API Routes. ([Next.js][3])

Fix:

* Allow only relative paths (`/path`) and reject protocol-relative (`//evil.com`) or absolute URLs.
* On invalid input, fall back to a safe default (home/dashboard).

---

### NEXT-CORS-001: CORS must be explicit and least-privilege

Severity: Medium (High when misconfigured with credentials)

Required:

* If CORS is not needed, MUST keep it disabled.
* Next.js API Routes do not set CORS headers by default, meaning they are same-origin by default; enable CORS only when truly needed. ([Next.js][3])
* When CORS is enabled:

  * MUST allowlist trusted origins (do not reflect arbitrary Origin)
  * MUST be careful with credentialed requests (cookies); never combine wide origins with credentials.
  * SHOULD restrict methods and headers.

Insecure patterns:

* `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true`
* Reflecting `Origin` without validation.

Detection hints:

* Look for `Access-Control-Allow-Origin`, `cors`, or "CORS" middleware/wrappers.
* Inspect preflight `OPTIONS` handlers.

Fix:

* Implement a strict origin allowlist and minimal methods/headers.
* Ensure cookies are not exposed cross-origin unless necessary and reviewed.

---

### NEXT-WEBHOOK-001: Webhook endpoints MUST verify authenticity using the raw body

Severity: Medium

Required:

* MUST verify webhook signatures using the **raw request body** (not a re-serialized parsed object).
* Next.js notes that one use case for disabling body parsing is verifying the raw body of a webhook request. ([Next.js][3])

Insecure patterns:

* Verifying webhook signatures over `JSON.stringify(req.body)` (which can change formatting).
* Accepting webhooks without signature verification and without an allowlist.

Detection hints:

* Find webhook endpoints (`/api/webhook`, `/app/api/**/webhook`).
* Check whether they use raw-body verification.

Fix:

* Disable Next.js automatic body parsing only for these webhook routes, safely read the raw bytes, verify the signature, then parse.

---

### NEXT-INJECT-001: Prevent SQL injection (use parameterized queries / ORM)

Severity: High

Required:

* MUST use parameterized queries or an ORM that parameterizes under the hood.
* MUST NOT build SQL via string concatenation / template strings with untrusted input.

Insecure patterns:

* ``db.query(`SELECT * FROM users WHERE id = ${id}`)``
* `"WHERE name = '" + user + "'"`

Detection hints:

* Grep for `SELECT`, `INSERT`, `UPDATE`, `DELETE` strings.
* Trace untrusted input (`params`, `searchParams`, `req.query`, `req.body`, `request.json()`) into DB calls.

Fix:

* Use prepared statements / ORM query APIs.
* Validate and coerce types before querying.

---

### NEXT-INJECT-002: Prevent OS command injection and unsafe subprocess usage

Severity: Critical to High

Required:

* MUST avoid executing OS commands with attacker-controlled input.
* If a subprocess is necessary:

  * MUST pass args as an array (not as a single shell string)
  * MUST NOT use `shell: true` with attacker-influenced strings
  * SHOULD use strict allowlists for any variable components

Insecure patterns:

* `exec("convert " + filename)`
* `spawn("bash", ["-c", userInput])`
* `spawn(userInput, ["foo"])`

Detection hints:

* Look for `child_process`, `exec`, `spawn`, `shell: true`.

Fix:

* Use library APIs instead of shell commands.
* Hardcode commands and allowlist validated parameters (and use `--` to separate flags where supported).

---

### NEXT-INJECT-003: Avoid dynamic code execution and unsafe deserialization

Severity: High to Critical

Required:

* MUST NOT use `eval`, `new Function`, or `vm.runIn*` on untrusted strings.
* MUST treat deserialization of complex formats (YAML, XML, custom serialization) as risky; use safe parsers and strict schemas.

Insecure patterns:

* `eval(req.body.code)`
* Parsing YAML from user input with a non-safe schema.

Detection hints:

* Look for `eval(`, `new Function`, `vm.`, `require(` with non-literal arguments.
* Look for `js-yaml`, XML parsers, and custom serializer use on untrusted input.

Fix:

* Remove dynamic execution; use safe interpreters or strict parsers.
* Validate and constrain input.

---

### NEXT-LOG-001: Logging MUST NOT leak secrets or sensitive headers

Severity: Medium

Required:

* MUST NOT log:

  * `Authorization` headers
  * cookies / session tokens
  * request bodies that contain credentials
  * environment variables or configuration dumps
* SHOULD implement structured logging with redaction.

Insecure patterns:

* `console.log(req.headers)` in auth endpoints
* `console.log(process.env)` in server code

Detection hints:

* Look for `console.log(`, `logger.info(`, `debug(` in server routes/actions.
* Inspect logs of headers/cookies/bodies.

Fix:

* Redact sensitive fields; log only what is needed for debugging.
* Use safe error messages for clients; keep details server-side only.

---

### NEXT-ERROR-001: Error handling MUST avoid leaking implementation details in production

Severity: Low

Required:

* MUST NOT expose stack traces or internal error details to end users in production.
* Ensure production-mode behavior (Next.js production error handling differs from dev). ([Next.js][6])

Insecure patterns:

* Returning `err.stack` in JSON responses.
* Showing detailed exception data to unauthenticated users.

Detection hints:

* Look for `res.status(500).json(err)` or `return Response.json(err)`.
* Verify that error responses are sanitized.

Fix:

* Return generic error messages to clients; log details server-side with redaction.

---

### NEXT-PROXY-001: Proxy/Middleware must not introduce header smuggling or unsafe header forwarding

Severity: Medium

Required:

* MUST be careful when copying/forwarding request headers upstream:

  * Do not forward attacker-controlled `x-forwarded-*` headers unless you have a trusted proxy chain.
  * Do not forward `Authorization`/cookies to unrelated outbound services.
* Next.js Proxy patterns often mutate headers; ensure this does not introduce security problems.

Insecure patterns:

* Blindly cloning all request headers into an outbound `fetch()` call.
* Trusting `x-forwarded-host` or `host` to build sensitive absolute URLs without an allowlist.

Detection hints:

* Look for `headers()` and `request.headers` usage (especially for URL construction). ([Next.js][4])
* Inspect Proxy/Middleware for header rewrites.

Fix:

* Allowlist forwarded headers explicitly.
* Validate hostnames before using them to build callback URLs or redirects.

---

### NEXT-HOST-001: URL construction based on Host/Origin MUST be allowlisted

Severity: Medium

Required:

* MUST NOT generate security-sensitive absolute URLs (password-reset links, OAuth callback URLs, email-verification links) directly from unvalidated `Host` headers.
* For Server Actions, the Origin/Host comparison is part of CSRF mitigation; do not weaken it. ([Next.js][5])

Insecure patterns:

* `const base = "https://" + request.headers.get("host")`
* Using an unvalidated `x-forwarded-host` to generate an absolute URL.

Detection hints:

* Grep for `.get('host')`, `.get('x-forwarded-host')` and absolute URL construction.
* Review auth-related email-link generation code.

Fix:

* Use a configured, allowlisted canonical application origin (for example, `APP_ORIGIN=https://example.com`).
* Allowlist hostnames; fail closed.

---

### NEXT-DOS-001: Rate limiting and resource controls MUST exist for abuse-prone endpoints

Severity: Medium

Required:

* SHOULD implement rate limiting/throttling for:

  * login, password reset, signup
  * expensive Server Actions
  * webhook reception
* MUST implement request size limits (see NEXT-LIMITS-001).
* When self-hosting, MUST rely on a reverse proxy for additional defenses. ([Next.js][8])

Insecure patterns:

* No throttling on login/reset endpoints.
* Expensive actions invokable without auth or with unlimited frequency.

Detection hints:

* Identify auth endpoints and verify rate limiting is in place.
* Look for "send email", "charge", "generate report" flows.

Fix:

* Add edge rate limiting and app-level user/IP throttles.
* Add job queues for heavy work; return 202 where appropriate.

---

## 5) Practical Scanning Heuristics (how to "hunt")

When actively scanning, use these high-signal patterns:

* Production misconfig:

  * `next dev`, `NODE_ENV=development`, dev-only start commands ([Next.js][7])
* Secret leakage:

  * `.env` committed, `NEXT_PUBLIC_` on sensitive variables ([Next.js][7])
  * `process.env` used in `"use client"` modules
* Auth coverage:

  * `app/**/route.ts` or `pages/api/**` without auth checks ([Next.js][1])
  * `"use server"` actions performing DB writes without authz ([Next.js][6])
  * `proxy.ts` / `middleware.ts` matchers excluding sensitive routes ([Next.js][12])
* CSRF:

  * cookie-auth POST/PUT/PATCH/DELETE without token/origin checks
  * `serverActions.allowedOrigins` too broad ([Next.js][5])
* XSS:

  * `dangerouslySetInnerHTML`, raw markdown HTML rendering
  * missing CSP / overly permissive CSP ([Next.js][7])
* Caching/data leakage:

  * `dynamic = 'force-static'` on sensitive GET handlers ([Next.js][1])
  * `use cache`, `cacheLife`, `unstable_cache` around user-specific data ([Next.js][1])
* Files:

  * writing uploads under `public/`
  * `fs.readFile` / `path.join` with request input
* SSRF:

  * `fetch(userProvidedUrl)` from Route Handlers / Server Actions
* Redirect:

  * `redirect(searchParams.get('next'))`, `NextResponse.redirect(...)`, `res.redirect(req.query.next)` ([Next.js][3])
* CORS:

  * wildcard origins, origin reflection, credentials + wide origins ([Next.js][3])
* Limits:

  * API routes with `bodyParser: false` and no raw-body verification for webhooks ([Next.js][3])
  * `serverActions.bodySizeLimit` raised without justification ([Next.js][5])
* Dependency hygiene:

  * Old `next` versions conflicting with the support policy/advisories ([Next.js][10])

Always try to confirm:

* data origin (untrusted vs. trusted)
* sink type (HTML/DOM, SQL, subprocess, files, redirect, outbound HTTP)
* defensive controls present (schema validation, allowlists, middleware/proxy checks, authz helpers, edge defenses)

---

## 6) Sources (as of 2026-01-27)

Primary framework documentation (Next.js):

* Next.js Docs: Installation (system requirements / Node version) -- `https://nextjs.org/docs/app/getting-started/installation`
* Next.js Docs: Route Handlers -- `https://nextjs.org/docs/app/getting-started/route-handlers`
* Next.js Docs: API Routes (Pages Router) -- `https://nextjs.org/docs/pages/building-your-application/routing/api-routes`
* Next.js Docs: Environment Variables -- `https://nextjs.org/docs/pages/guides/environment-variables`
* Next.js Docs: Data Security -- `https://nextjs.org/docs/app/guides/data-security`
* Next.js Docs: Content Security Policy -- `https://nextjs.org/docs/app/guides/content-security-policy`
* Next.js Docs: Proxy -- `https://nextjs.org/docs/app/getting-started/proxy`
* Next.js Docs: `serverActions.allowedOrigins` and `serverActions.bodySizeLimit` -- `https://nextjs.org/docs/app/api-reference/config/next-config-js/serverActions`
* Next.js Docs: `cookies()` -- `https://nextjs.org/docs/app/api-reference/functions/cookies`
* Next.js Docs: `headers()` -- `https://nextjs.org/docs/app/api-reference/functions/headers`
* Next.js Docs: Self-hosting (reverse-proxy guidance) -- `https://nextjs.org/docs/pages/guides/self-hosting`
* Next.js Docs: Support policy (supported versions/LTS) -- `https://nextjs.org/docs/support-policy`

Next.js security guidance and advisories:

* Next.js Blog: How to think about security in Next.js -- `https://nextjs.org/blog/security-nextjs-server-components-actions`
* GitHub Security Advisory: Next.js DoS via Server Components / Server Actions (CVE-2026-23864) -- `https://github.com/advisories/GHSA-fq29-rrrv-cq2m`
* Next.js Blog: Security update (example security-advisory context) -- `https://nextjs.org/blog/security-update`

General web-security references (recommended baseline):

* OWASP Cheat Sheet Series (CSRF, Session Management, XSS Prevention, SSRF Prevention, File Upload, HTTP Headers) -- `https://cheatsheetseries.owasp.org/`

[1]: https://nextjs.org/docs/app/getting-started/route-handlers "Getting Started: Route Handlers | Next.js"
[2]: https://nextjs.org/docs/app/getting-started/deploying?utm_source=chatgpt.com "Getting Started: Deploying"
[3]: https://nextjs.org/docs/pages/building-your-application/routing/api-routes "Routing: API Routes | Next.js"
[4]: https://nextjs.org/docs/app/api-reference/functions/headers "Functions: headers | Next.js"
[5]: https://nextjs.org/docs/app/api-reference/config/next-config-js/serverActions "next.config.js: serverActions | Next.js"
[6]: https://nextjs.org/blog/security-nextjs-server-components-actions "How to Think About Security in Next.js | Next.js"
[7]: https://nextjs.org/docs/pages/guides/environment-variables "Guides: Environment Variables | Next.js"
[8]: https://nextjs.org/docs/pages/guides/self-hosting?utm_source=chatgpt.com "Guides: Self-Hosting"
[9]: https://nextjs.org/docs/app/api-reference/functions/cookies "Functions: cookies | Next.js"
[10]: https://nextjs.org/blog/next-16?utm_source=chatgpt.com "Next.js 16"
[11]: https://github.com/vercel/next.js/security/advisories/GHSA-9g9p-9gw9-jx7f?utm_source=chatgpt.com "Denial of Service in Image Optimizer - Advisory"
[12]: https://nextjs.org/docs/pages/guides/authentication "Guides: Authentication | Next.js"
