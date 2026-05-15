# Express (Node.js) Web Application Security Specification (Express 5.x / 4.19.2+, Node.js LTS)

This document is intended as a **security specification** that supports:

1. **Secure-by-default code generation** for new Express applications and routes.
2. **Security audit and vulnerability hunting** across existing Express code (both passive "spot issues while working" mode and active "scan the repo and report findings" mode).

The document is intentionally written as a set of **normative requirements** ("MUST/SHOULD/MAY") and **audit rules** (what insecure patterns look like, how to detect them, and how to fix or mitigate them).

---

## 0) Safety, Boundaries, and Anti-Abuse Constraints (MANDATORY)

* MUST NOT request, output, log, or commit secrets (API keys, passwords, private keys, session secrets, cookies, tokens).
* MUST NOT "fix" security by disabling protections (for example, weakening cookie flags, disabling CSRF protection in cookie-authenticated apps, enabling overly permissive CORS, trusting proxy headers from the open internet, enabling debug/stack traces in production, disabling TLS without replacement).
* MUST provide **evidence-based findings** when auditing: cite file paths, code fragments, middleware/config values, and runtime assumptions that justify the claim.
* MUST be honest about uncertainty: if a protection may exist in the infrastructure (reverse proxy, gateway, WAF, CDN), report it as "not visible in application code; verify at the runtime/config layer".
* MUST prefer proven libraries and platform features over hand-rolled crypto/auth/session/CSRF implementations. Express explicitly expects the application to validate/handle user input correctly itself; it does not do so automatically. ([Express][1])

---

## 1) Modes of Operation

### 1.1 Generation Mode (default)

When asked to write new Express code or modify existing code:

* MUST honor every **MUST** requirement of this specification.
* SHOULD honor every **SHOULD** requirement unless the user explicitly directs otherwise.
* MUST prefer secure-by-default APIs and proven libraries over hand-rolled security code.
* MUST avoid introducing new risky "sinks" (shell execution, dynamic code execution, unsafe redirects, serving user files as HTML, rendering templates from untrusted strings, unsafe filesystem paths, SSRF URL-fetch endpoints, etc.).

### 1.2 Passive Review Mode (always on while editing)

When working anywhere in an Express repository (even if the user did not request a security scan):

* MUST "spot" violations of this specification in affected/adjacent code.
* SHOULD mention issues as they arise with a brief explanation and a safe fix.

### 1.3 Active Audit Mode (explicit scan request)

When the user asks to "scan", "audit", or "hunt for vulns":

* MUST systematically search the codebase for violations of this specification.
* MUST output findings in a structured format (see §2.3).

Recommended audit order:

1. Entry points (server/app bootstrap), deployment manifests, Dockerfiles, process-manager config, CI/CD.
2. Express settings and middleware-stack ordering (helmet, parsers, auth, sessions, CSRF, CORS).
3. Proxy trust (`trust proxy`) and IP/protocol/host handling. ([Express][2])
4. Auth flows, sessions, cookies, password reset links, redirect handling. ([Express][1])
5. State-changing routes and CSRF defenses (cookie-authenticated apps). ([OWASP Cheat Sheet Series][3])
6. Template rendering and XSS defenses (HTML generation, CSP, `res.locals`). ([OWASP Cheat Sheet Series][4])
7. File handling (uploads + downloads + static files) and path traversal. ([Express][5])
8. Injection classes (SQL, NoSQL, command execution, unsafe deserialization). ([OWASP Cheat Sheet Series][6])
9. Outbound requests (SSRF) and webhook/callback delivery. ([OWASP Cheat Sheet Series][7])
10. Rate limiting / brute-force defenses / abuse controls. ([Express][1])
11. Dependency hygiene / lockfiles / npm audit / vulnerable Express versions. ([Express][1])

---

## 2) Definitions and Review Guidance

### 2.1 Untrusted Input (treat as attacker-controlled until proven otherwise)

In Express, typical untrusted input includes:

* `req.params` (route parameters)
* `req.query` (query-string parameters; may be strings/arrays/objects depending on parsing) ([OWASP Cheat Sheet Series][8])
* `req.body` from `express.json()`, `express.urlencoded()`, `express.text()`, `express.raw()` ([Express][5])
* `req.headers` / `req.get(...)`
* `req.cookies` / `req.signedCookies` (if cookie-parsing middleware is used)
* Upload metadata and filenames (for example, multer `file.originalname`, `file.mimetype`)
* Any data from external systems (webhooks, third-party APIs, message queues)
* Any stored user content (DB rows) that originally came from users

A note on proxies:

* If `trust proxy` is enabled, values such as `req.ip`, `req.hostname`, and `req.protocol` may be derived from `X-Forwarded-*` headers, which **may be attacker-controlled** if your proxy chain does not correctly rewrite/strip them. ([Express][2])

### 2.2 State-Changing Request

A request is state-changing if it can create/update/delete data, change auth/session state, cause side effects (purchase, sending email, dispatching a webhook), or initiate privileged actions.

### 2.3 Required Audit-Finding Format

For each issue found, output:

* Rule ID:
* Severity: Critical / High / Medium / Low
* Location: file path + function/route/middleware name + line(s)
* Evidence: exact code/config snippet
* Impact: what can go wrong, who can exploit it
* Fix: safe change (preferably a minimal diff)
* Mitigation: defense-in-depth if an immediate fix is difficult
* False positive notes: what to verify when uncertain

---

## 3) Secure Baseline: Minimum Production Configuration (MUST in production)

This is the minimum "production baseline" that prevents common Express misconfigurations.

Minimum baseline goals:

* `helmet()` is used and configured (especially CSP where applicable), and fingerprinting is reduced (disable `x-powered-by`). ([Express][1])
* Custom 404 and error handlers exist, and production does not leak internal stack traces. ([Express][1])
* Cookie/session usage is intentional:

  * The default session cookie name is not used
  * Cookies use safe attributes (`Secure`, `HttpOnly`, `SameSite`) as appropriate
  * Cookie sessions never store secrets (they are readable by the client)
  * Server-side sessions never use MemoryStore in production. ([Express][1])
* Request body parsing has explicit limits (`express.json({ limit })`, `express.urlencoded({ limit, parameterLimit, depth })`). ([Express][5])
* `trust proxy` is configured explicitly to match your proxy topology; not blindly `true`. ([Express][2])
* Login/auth endpoints have brute-force protection and rate limiting. ([Express][1])
* Dependencies are regularly checked/updated (`npm audit` + responding to advisories). ([Express][1])

---

## 4) Rules (generation + audit)

Each rule contains: required practice, insecure patterns, detection hints, and remediation guidance.

### EXPRESS-INPUT-001: Treat all input as untrusted and validate it

Severity: High

Required:

* MUST validate and normalize untrusted input before using it in security-sensitive logic or dangerous "sinks" (DB queries, redirects, filesystem, HTML output, shell commands). Ensure untrusted inputs are checked for type and structure before use or pass-through.
* SHOULD apply allowlists (known-safe values) instead of blocklists where possible.
* MUST reject or safely handle unexpected types/shapes in `req.query`, `req.params`, and `req.body`.

Insecure patterns:

* Passing `req.query`, `req.params`, `req.body` directly into DB/query builders, redirects, filesystem paths, or templates.
* Assuming `req.query.foo` is always a string (it can be an array/object depending on parsing). ([OWASP Cheat Sheet Series][8])

Detection hints:

* Identify "untrusted -> sink" flows: request -> sink (`res.redirect`, SQL execution, `sendFile`, `child_process`, template render, outbound fetch).
* Look for direct use of `req.query.*`, `req.body.*`, `req.params.*` in sensitive calls.

Fix:

* Add schema validation (for example, zod/joi/express-validator) at route boundaries.
* Normalize types (for example, coerce IDs to integers; reject arrays where a scalar is expected).

Notes:

* Express's production-security guide explicitly states that input validation/handling is the application's responsibility. ([Express][1])

---

### EXPRESS-REDIRECT-001: Prevent open redirect; validate redirect targets

Severity: Medium

Required:

* MUST validate redirect targets derived from untrusted input (`next`, `return_to`, `url`).
* SHOULD allowlist same-site relative paths only (preferred) or a strict allowlist of domains.
* MUST use a safe default if validation fails.

Insecure patterns:

* `res.redirect(req.query.next)` without validation.
* `res.redirect(req.body.url)` or `res.location(...)` with untrusted URLs.

Detection hints:

* Look for `res.redirect(` and `res.location(` and trace the source of the target.
* Look for query parameters named `next`, `redirect`, `return`, `url`.

Fix:

* Allow only relative paths (starting with `/`) and disallow `//`, backslashes, and encoded variants.
* If cross-domain redirects are required, allowlist exact hosts and enforce `https`.

Notes:

* Express documentation calls out open redirects as a dangerous user input and shows host validation before redirecting. ([Express][1])
* Keep Express up to date: Express had an open-redirect-related CVE affecting some versions, and updating is part of the mitigation posture. ([NVD][9])

---

### EXPRESS-HEADERS-001: Use Helmet (or equivalent) to set core security headers

Severity: Medium

Required:

* SHOULD use `helmet()` to set common security headers.
* SHOULD configure CSP realistically (avoiding `unsafe-inline` where possible) for pages that render user-influenced content.
* SHOULD set `X-Content-Type-Options: nosniff`, clickjacking protection (`X-Frame-Options` or CSP `frame-ancestors`), and an appropriate referrer policy.

NOTE: The most important header to set is the CSP `script-src`. All other directives are less important and can usually be omitted in favor of development convenience.

Insecure patterns:

* Application code does not set security headers and there is no indication they are set at the edge.
* CSP is missing in apps that render user content.
* Misconfigured framing headers that inadvertently allow clickjacking.

Detection hints:

* Look for `helmet(` usage; check whether CSP is configured or disabled.
* Look for `res.setHeader(` / `res.set(` setting security headers.
* If not visible in application code, check nginx/CDN configuration; otherwise flag as "verify at edge".

Fix:

* Add `helmet()` early in the middleware order and configure:

  * CSP (`contentSecurityPolicy`)
  * Framing protection (`frameguard` or CSP `frame-ancestors`)
  * `X-Content-Type-Options` (`noSniff`)

Notes:

* Express's production security best practices recommend Helmet and list the headers Helmet sets by default. ([Express][1])
* OWASP HTTP Headers is a useful reference when configuring policies. ([OWASP Cheat Sheet Series][10])

---

### EXPRESS-FINGERPRINT-001: Reduce fingerprinting by disabling `x-powered-by` and customizing error/404 responses

Severity: Low (defense-in-depth)

Required:

* SHOULD disable `X-Powered-By` via `app.disable('x-powered-by')`.
* SHOULD provide a custom 404 handler and a custom error handler to avoid identifiable default responses and to control information leakage.

Insecure patterns:

* The `X-Powered-By: Express` header is left enabled by default.
* Default Express 404/error responses in production with recognizable formatting and/or stack traces.

Detection hints:

* Look for `app.disable('x-powered-by')`.
* Check the tail of the middleware stack for a custom 404 (`app.use((req,res)=>...)`) and a custom error handler (`app.use((err,req,res,next)=>...)`).
* Check whether `NODE_ENV` is set correctly for production behavior (see EXPRESS-ERROR-001). ([Express][11])

Fix:

* Add:

  * `app.disable('x-powered-by')`
  * A custom 404 handler
  * A custom error handler that logs server-side and returns generic messages to clients

Notes:

* Express documentation explicitly recommends disabling `x-powered-by` and adding custom not-found and error handlers. ([Express][1])

---

### EXPRESS-COOKIE-001: Cookies must use safe attributes and minimal scope

Severity: Medium

Required:

* MUST set appropriate cookie flags for any auth/session cookie:

  * `Secure` over HTTPS (production) IMPORTANT NOTE: only set `Secure` in production environments where TLS is configured. When working in a local dev environment over HTTP, do not set the `Secure` property on cookies. Set this conditionally based on whether the application runs in production mode. Also include a property like `SESSION_COOKIE_SECURE` that can be used to disable `Secure` cookies when testing over HTTP.
  * `HttpOnly` for auth/session cookies
  * `SameSite` set deliberately (`Lax` is a common baseline; `Strict` if compatible; `None` only with `Secure` and a justified cross-site need)
* SHOULD avoid setting a broad `domain` (avoid "all subdomains" unless required).
* SHOULD set bounded lifetimes consistent with risk and UX.

Insecure patterns:

* Session/auth cookies without `HttpOnly`.
* Cookies without `Secure` over HTTPS production.
* `SameSite=None` + cookie-authenticated state-changing endpoints without CSRF protection.

Detection hints:

* Look for `res.cookie(`, `Set-Cookie`, `cookie: { ... }`, `express-session`, `cookie-session`.
* Check cookie flags in the session middleware configuration.

Fix:

* Set these attributes centrally in the session/cookie middleware configuration.

Notes:

* Express's production-security guide enumerates cookie security options (`secure`, `httpOnly`, etc.). ([Express][1])
* `res.cookie()` ultimately sets `Set-Cookie` with options; defaults follow RFC 6265 behavior when options are omitted. ([Express][5])
* OWASP's session-management guidance is relevant when choosing flags and lifetimes. ([OWASP Cheat Sheet Series][12])

---

### EXPRESS-SESS-001: Do not use the default session cookie name; avoid session fingerprinting

Severity: Low (defense-in-depth)

Required:

* SHOULD override the default session cookie name (for example, do not leave `connect.sid` when using `express-session`).
* SHOULD use a generic name (for example, `sessionId`) unless there is a compatibility reason.

Insecure patterns:

* `express-session` is used without a configured `name:` (default cookie name).
* Multiple apps on the same domain accidentally share a cookie name.

Detection hints:

* Look for `express-session` configuration blocks; check whether `name:` is present.

Fix:

* Set `name: 'sessionId'` (or similar) in `express-session` options.

Notes:

* Express documentation explicitly recommends not using the default session cookie name to reduce fingerprinting. ([Express][1])

---

### EXPRESS-SESS-002: Session storage and lifecycle must be production-safe

Severity: High

Required:

* MUST NOT use `MemoryStore` in production (it is not designed for production use).
* MUST keep session secrets out of version control and rotate them safely.
* SHOULD regenerate sessions on login / privilege changes to mitigate session fixation.
* MUST NOT store sensitive secrets in client-readable cookie sessions.

Insecure patterns:

* `app.use(session({ store: new MemoryStore(), ... }))` or a missing store (defaults to MemoryStore).
* Hardcoded values, for example: `secret: 'keyboard cat'` / `secret: 's3Cur3'` in the repository.
* Using `cookie-session` to store access tokens, refresh tokens, or PII.

Detection hints:

* Look for `express-session` and check for `MemoryStore` use or a missing `store`.
* Look for `secret:` in the session configuration and check whether it is hardcoded.
* Look for `req.session = ...` patterns and check whether sensitive data is stored.

Fix:

* Use a production session store (Redis, supported DB, etc.).
* Load secrets from the environment / a secret manager.
* On login: `req.session.regenerate(...)` or an equivalent flow with safe privilege re-binding.

Notes:

* `express-session` explicitly warns that `MemoryStore` is not designed for production. ([Express][1])
* `express-session` documents secret rotation and session regeneration to defend against fixation. ([Express][1])
* Express notes that cookie sessions serialize data in the cookie and that cookie data is visible to the client; keep it small and non-secret. ([Express][1])

---

### EXPRESS-CSRF-001: Cookie-authenticated state-changing requests MUST be CSRF-protected

Severity: High

- IMPORTANT NOTE: If cookies are not used for auth (for example, auth via an Authentication header or another carrier token), then there is no CSRF risk.

Required:

* MUST protect all state-changing endpoints (POST/PUT/PATCH/DELETE) that rely on cookies for authentication.
* SHOULD use a clear CSRF defense (token-based is the typical baseline).
* MAY add defense-in-depth: Origin/Referer validation, enforced Fetch Metadata, SameSite cookies, requiring custom headers for XHR/fetch -- **but do not treat them as a complete substitute** unless explicitly designed and justified.
* MUST at minimum require a custom HTTP header if form-based CSRF tokens are impractical, since this is the second-strongest method.

IMPORTANT NOTE:

* If authentication is performed via `Authorization: Bearer ...` headers (rather than cookies), classic browser CSRF is generally not applicable;

Insecure patterns:

* Cookie-authenticated state-changing endpoints without CSRF protection.
* Using GET for state-changing actions (amplifies CSRF risk).
* "CSRF protection" that only checks a user-controlled field.

Detection hints:

* Enumerate routes with non-GET/HEAD methods and determine whether auth is verified via cookies.
* Look for the presence/absence of CSRF middleware and token checks.
* Inspect JSON APIs as well, not just HTML forms.

Fix:

* Implement CSRF tokens for cookie-authenticated flows.
* Add Origin/Referer checks where possible and ensure SameSite is set appropriately.

Notes:

* OWASP's CSRF guide and OWASP's Node.js guide recommend anti-CSRF tokens as the standard control for web applications. ([OWASP Cheat Sheet Series][3])

---

### EXPRESS-CORS-001: CORS must be explicit and least-privilege

Severity: Medium (High when misconfigured with credentials)

Required:

* If CORS is not needed, MUST keep it disabled.
* If CORS is needed:

  * MUST allowlist trusted origins (do not reflect arbitrary `Origin` without validation).
  * MUST NOT combine wide origins with credentialed cookies (`Access-Control-Allow-Credentials: true`).
  * SHOULD restrict methods, headers, and exposed headers to what is necessary.

Insecure patterns:

* `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true`.
* Reflecting `Origin` for all requests without an allowlist.
* Applying permissive CORS middleware globally when only a subset of routes requires cross-origin access.

Detection hints:

* Look for `cors(`, `Access-Control-Allow-Origin`, `Access-Control-Allow-Credentials`.
* Check whether cookies are used for auth on endpoints exposed cross-origin.

Fix:

* Implement a strict origin allowlist and ensure credentialed requests are only for intended origins.
* Consider per-route-group CORS configuration instead of global.

Notes:

* OWASP's HTTP Headers guide covers the security implications of response headers, including those that affect browser behavior; use it as a reference when reviewing header posture. ([OWASP Cheat Sheet Series][10])

---

### EXPRESS-PROXY-001: Reverse-proxy trust (`trust proxy`) must be configured correctly

Severity: Medium (High when IP-based authentication is used)

Required:

* If behind a reverse proxy/LB, MUST configure `app.set('trust proxy', ...)` to match the actual proxy chain.
* MUST NOT blindly set `trust proxy = true` unless you fully control proxy behavior and header rewriting.
* MUST ensure that the last trusted proxy rewrites/strips `X-Forwarded-For`, `X-Forwarded-Host`, and `X-Forwarded-Proto` so that clients cannot spoof them.

Insecure patterns:

* `app.set('trust proxy', true)` in an app exposed directly to the internet or behind unknown proxies.
* Using `req.ip`, `req.protocol`, `req.hostname` for security decisions without correct trust-proxy configuration.
* Rate limiting keyed on `req.ip` with spoofable forwarded headers.

Detection hints:

* Look for `app.set('trust proxy'`.
* Check infrastructure documentation (nginx/LB) for header-rewriting behavior.
* Identify any security logic that uses `req.ip`, `req.ips`, `req.protocol`, `req.hostname`.

Fix:

* Set `trust proxy` to a hop count, an explicit list of IPs/subnets, or a custom function matching your network.
* Ensure proxies rewrite forwarded headers.

Notes:

* Express explicitly warns that when `trust proxy` is `true`, the client IP is derived from `X-Forwarded-For`, and if proxies do not rewrite forwarded headers the client can supply any value. It also describes that enabling trust proxy affects `req.hostname` and `req.protocol`, derived from forwarded headers. ([Express][2])

---

### EXPRESS-BODY-001: Request body size and parsing limits MUST be set appropriately

Severity: Low

Required:

* SHOULD set explicit body size limits for:

  * `express.json({ limit })`
  * `express.urlencoded({ limit, parameterLimit, depth })`
* SHOULD enable only the parsers you need; do not parse large bodies by default for all routes.
* SHOULD apply additional limits at the reverse proxy / gateway layer.

Insecure patterns:

* No explicit body limits (accepting arbitrarily large JSON/urlencoded).
* Global parsers applied to all routes when only some need bodies.
* Very high `parameterLimit` without justification (DoS potential).

Detection hints:

* Look for `express.json(` and verify that `limit` is set (or deliberately accepted).
* Look for `express.urlencoded(` and check `limit`, `parameterLimit`, and `depth`.
* Review upload/webhook endpoints for parsing-specific needs.

Fix:

* Configure parsers with conservative defaults and override per route group when necessary.

Notes:

* Express documents `express.json` options (including `limit`, defaulting to 100kb) and explicitly notes that `req.body` is untrusted and must be validated. ([Express][5])
* Express documents `express.urlencoded` options including `limit`, `parameterLimit`, and `depth`. ([Express][5])
* OWASP's Node.js guide also recommends setting request size limits. ([OWASP Cheat Sheet Series][8])

---

### EXPRESS-INPUT-002: Prevent HTTP Parameter Pollution and type confusion in `req.query`

Severity: Medium

Required:

* MUST treat `req.query` values as potentially multi-valued (array/object), depending on query parsing.
* SHOULD reject ambiguous multi-valued parameters for sensitive fields (for example, `role`, `isAdmin`, `redirect`, `amount`, `userId`).
* SHOULD consider explicit parsing or specialized middleware if parameter pollution is a concern.

Insecure patterns:

* `if (req.query.admin) { ... }` without type checks (arrays/objects can coerce truthy).
* Passing `req.query` directly into ORM/NoSQL query objects.

Detection hints:

* Look for security-sensitive comparisons against `req.query.*` without type coercion.
* Look for code that assumes query parameters are strings.

Fix:

* Validate shape: enforce strings only for specific parameters and reject arrays/objects.
* Normalize query-parsing settings (simple vs. extended) where applicable and documented.

Notes:

* The OWASP Node.js cheat sheet explicitly highlights that Express's query parsing may produce strings, arrays, or objects, and recommends preventing HTTP Parameter Pollution. ([OWASP Cheat Sheet Series][8])

---

### EXPRESS-XSS-001: Prevent reflected/stored XSS in HTML responses and templates

Severity: High

Required:

* MUST escape untrusted content in HTML output (templates should auto-escape by default; do not bypass this).
* MUST NOT inject untrusted strings into HTML without escaping/sanitization.
* SHOULD set CSP (via Helmet) for applications that render user-controlled content.
* SHOULD keep `res.locals` free of user-controlled input intended for templates unless validated/escaped.

Insecure patterns:

* `res.send("<div>" + req.query.q + "</div>")`
* Passing untrusted HTML through "safe" template flags/filters.
* Writing untrusted strings to `res.locals` and later rendering them without escaping.

Detection hints:

* Look for `res.send(` with strings that contain user input.
* Look for "safe"-flag template constructs (engine-specific) and trace data origin.
* Look for assignments to `res.locals` and check whether they may contain untrusted data.

Fix:

* Use a templating engine with auto-escaping; pass only validated data.
* For rich text that must contain HTML, use a trusted sanitizer with an allowlist policy.
* Add CSP with realistic directives.

Notes:

* Express's API documentation explicitly warns that `res.locals` "should not contain user-controlled input" and is often used to expose values such as CSRF tokens to templates. ([Express][5])
* OWASP's XSS prevention guide gives the standard recommendations on output encoding and policies. ([OWASP Cheat Sheet Series][4])
* Helmet can mitigate some classes of XSS via headers such as CSP. ([Express][1])

---

### EXPRESS-TEMPLATE-001: Never render untrusted templates or template paths (SSTI / LFI risk)

Severity: Critical (if template strings/paths can be shown to be user/attacker-controlled)

Required:

* MUST NOT render templates whose contents or template path/name depend on untrusted input.
* MUST NOT load templates from user-controlled filesystem locations.
* SHOULD treat "email-template editors", "theme engines", and "CMS-like template storage" as high-risk designs requiring sandboxing and isolation.

Insecure patterns:

* `res.render(req.query.view, data)` where `view` is not allowlisted.
* Rendering a template from a string that includes user input (engine-specific).
* Loading templates from upload directories.

Detection hints:

* Look for `res.render(` where the first argument is derived from request/DB without an allowlist.
* Look for template-compilation APIs (engine-specific) being fed user content.

Fix:

* Use allowlisted template names and a fixed templates directory.
* If user-defined templates are required, implement strict sandboxing and isolate execution.

Notes:

* Express's templating system depends on the chosen engine; treat it as unsafe whenever user input influences template selection or its source.

---

### EXPRESS-FILES-001: Prevent path traversal and unsafe file serving (sendFile/download)

Severity: High

Required:

* MUST NOT pass user-controlled filesystem paths directly to `res.sendFile()` / `res.download()` / filesystem APIs.
* SHOULD use `res.sendFile` with a fixed `root` and strict options (for example, deny dotfiles) when serving user-selected files from a directory.
* MUST enforce authorization before serving user-owned files.

Insecure patterns:

* `res.sendFile(req.query.path)` or `res.download(req.params.file)` without root constraints.
* File-serving routes that accept `..` segments, encoded traversal, or absolute paths.

Detection hints:

* Look for `res.sendFile(` and trace the origin of the `path` argument.
* Look for `res.download(` and trace the origin of the `path` argument.
* Look for `fs.readFile`/`createReadStream` over paths derived from requests.

Fix:

* Use an identifier-to-path mapping stored server-side (DB) rather than raw paths from clients.
* Use `root: <trusted_base_dir>` and `dotfiles: 'deny'` where appropriate; strictly validate the filename component.

Notes:

* Express's `res.sendFile` documentation shows the use of `root` and `dotfiles: 'deny'` as part of a safe serving configuration. ([Express][5])
* `res.download` transfers the file as an attachment, but you still need to control/validate the underlying `path`. ([Express][5])

---

### EXPRESS-STATIC-001: Harden `express.static` / serve-static and never serve untrusted uploads as active content

Severity: Medium (if untrusted user files are served and there are no robust file-extension limits)

Required:

* MUST NOT serve user uploads from a public static directory as active content (especially HTML/JS/SVG) unless explicitly intended and sandboxed. If you are confident the content is inactive (png, jpg, other images, etc.), this can be safe. It may be useful to validate that image-file extensions are allowlisted before serving.
* SHOULD configure static serving to:

  * deny/ignore dotfiles
  * avoid unintended directory indexes unless required
  * apply appropriate cache controls for immutable assets

Insecure patterns:

* `app.use(express.static('uploads'))` where users can upload arbitrary files.
* Serving uploaded HTML or SVG inline from the same origin as the application.

Detection hints:

* Look for `express.static(` and identify the directories being served.
* Compare served directories against upload storage locations.
* Check `dotfiles` and `index` options on static middleware.

Fix:

* Store uploads outside any static web root and serve them through controlled routes that set a safe `Content-Type` and `Content-Disposition: attachment` where appropriate.
* Configure `express.static(root, { dotfiles: 'deny'|'ignore', index: false (if required) })`.

Notes:

* Express documents `express.static` options including `dotfiles` and `index` behavior. ([Express][5])

---

### EXPRESS-UPLOAD-001: File uploads must be validated, stored safely, and served safely

Severity: Low - Medium

Required:

* SHOULD enforce upload size limits (application + edge).
* MUST validate file type using an allowlist and content checks (not just the extension on the filename).
* MUST store uploads outside executable/static roots when possible.
* SHOULD generate filenames server-side (random IDs); do not trust original names.
* MUST safely serve potentially active formats (download attachment) unless explicitly intended.

Insecure patterns:

* Accepting arbitrary file types and serving them back inline.
* Using `file.originalname` as the storage path.
* Missing size/type validation.

Detection hints:

* Look for use of multer/busboy/formidable and verify `limits`.
* Check where uploaded files are written and how they are served.
* Check whether uploads end up under `public/` or any `express.static` root.

Fix:

* Implement allowlist validation + safe storage + safe serving as per the OWASP file-upload guide.

Notes:

* The OWASP File Upload guide covers allowlists, content validation, storage, and safe-serving patterns. ([OWASP Cheat Sheet Series][13])

---

### EXPRESS-INJECT-001: Prevent SQL injection (use parameterized queries / ORM)

Severity: High

Required:

* MUST use parameterized queries or an ORM/query builder that parameterizes under the hood.
* MUST NOT build SQL via string concatenation/template literals with untrusted input.

Insecure patterns:

* ``db.query(`SELECT * FROM users WHERE id = ${req.query.id}`)``
* `"SELECT ... WHERE name = '" + req.body.name + "'"`

Detection hints:

* Grep for `SELECT`, `INSERT`, `UPDATE`, `DELETE` strings in JS/TS.
* Trace untrusted input into `.query(...)`, `.execute(...)`, or raw SQL APIs.

Fix:

* Replace with parameterized queries (placeholders) or ORM query APIs.
* Validate types (for example, integer IDs) before querying.

Notes:

* OWASP's SQL injection prevention guide strongly recommends parameterized queries. ([OWASP Cheat Sheet Series][6])

---

### EXPRESS-INJECT-002: Prevent NoSQL injection / operator injection (Mongo-style)

Severity: High (application-dependent)

Required:

* MUST validate types and schemas for any query object built from untrusted input.
* MUST prevent operator injection (for example, `$ne`, `$gt`, `$where`) when user input is merged into query objects.
* SHOULD consider defensive libraries/middleware as appropriate.

Insecure patterns:

* `collection.find(req.body)` where the body is attacker-controlled.
* Merging `req.query`/`req.body` into Mongo queries without schema validation.

Detection hints:

* Look for `find(`, `findOne(`, `aggregate(` calls where the argument is derived from a request.
* Check patterns such as `{ ...req.query }` or `Object.assign(query, req.body)`.

Fix:

* Use schema validation at the boundary; explicitly construct query objects only from validated fields.

Notes:

* The OWASP Node.js cheat sheet discusses input validation and references Node ecosystem modules commonly used for sanitization in NoSQL contexts. ([OWASP Cheat Sheet Series][8])

---

### EXPRESS-CMD-001: Prevent OS command injection (child_process)

Severity: Critical to High (depending on exposure); please prove the input is user/attacker-controlled

Required:

* MUST avoid executing shell commands with untrusted input.
* If a subprocess is necessary:

  * MUST avoid `exec()` / `execSync()` with attacker-influenced strings
  * MUST NOT use `shell: true` with attacker-influenced data
  * SHOULD use `spawn()` with an argument array and strict allowlists. Ensure the executable is hardcoded or allowlisted; do not use a command name supplied by the user.
  * SHOULD place user-controlled values after `--` when the subcommand supports it, to avoid flag injection

Insecure patterns:

* `exec(req.query.cmd)`
* `exec(`convert ${userPath} ...`)`
* `spawn('sh', ['-c', userString])`
* `spawn(userString, ['foo'])`

Detection hints:

* Look for `child_process`, `exec(`, `execSync(`, `spawn(`, `fork(`.
* Trace request/DB data into command construction.

Fix:

* Where possible, implement the functionality in JavaScript or use a library instead of a subprocess.
* If unavoidable, hardcode the command and strictly allowlist parameters.

Notes:

* OWASP's OS Command Injection Defense guide covers avoid-shell and allowlist patterns. ([OWASP Cheat Sheet Series][14])

---

### EXPRESS-SSRF-001: Prevent SSRF in outbound HTTP requests

Severity: Medium (High in cloud/LAN deployments)

NOTE: This mostly applies to applications deployed in a cloud/LAN configuration or that have other HTTP services on the same machine. Sometimes a feature unavoidably requires this functionality (webhooks).

Required:

* MUST treat outbound requests to user-supplied URLs as high-risk if other reachable private HTTP endpoints exist.
* SHOULD validate and limit destinations (allowlist of hosts/domains) for any user-influenced URL fetch.
* SHOULD block access to:

  * localhost / private IP ranges / link-local
  * cloud metadata endpoints
* MUST permit only `http`/`https` for URL-fetch features (to avoid schemes such as `file:`, `javascript:`)
* SHOULD set timeouts and limit redirects.

Insecure patterns:

* `fetch(req.query.url)`
* "URL preview" / "import from URL" endpoints accepting arbitrary URLs.

Detection hints:

* Look for use of `fetch(`, `axios(`, `got(`, `request(`, `node-fetch` where the URL originates from users/DB.
* Review webhook testers, previewers, image fetchers.

Fix:

* Enforce a scheme allowlist, host allowlist, DNS/IP resolution checks, timeouts, and a redirect policy.
* Consider egress network controls at the infrastructure layer.

Notes:

* OWASP's SSRF prevention guide provides standard controls and common pitfalls. ([OWASP Cheat Sheet Series][7])

---

### EXPRESS-ERROR-001: Error handling MUST NOT leak sensitive details in production

Severity: Low

Required:

* SHOULD define a centralized error handler (`app.use((err, req, res, next) => ...)`) at the end of the middleware chain.
* MUST avoid returning stack traces, internal error messages, or secrets to clients in production.
* SHOULD log errors server-side with appropriate redaction.
* SHOULD ensure the application runs with production settings so that default behavior does not leak details.
* MUST avoid logging or returning sensitive information such as secrets, env vars, sessions, or cookies in error messages in production.

Insecure patterns:

* Returning `err.stack` to clients.
* Using dev-only error middleware in production.
* `NODE_ENV` left as development, causing verbose error responses.

Detection hints:

* Verify that there is a final error-handling middleware.
* Look for `res.status(500).send(err)` or similar.
* Check production environment variables and startup scripts.

Fix:

* Add a production-safe error handler that returns generic messages and logs details internally.
* Ensure the environment is configured for production behavior.

Notes:

* Express's production-security guide recommends custom error handling. ([Express][1])
* Express's error-handling documentation describes the default error handler's behavior and how production mode affects what is emitted. ([Express][11])

---

### EXPRESS-AUTH-001: Prevent brute-force attacks against authentication endpoints

Severity: Medium

NOTE: This is highly application-dependent, and although it is useful to draw the user's attention to it, it is hard to fix without additional involved configuration. Prefer informing the user; if they ask for help implementing a solution, walk them through possible options.

Required:

* SHOULD protect login/auth endpoints against brute-force.
* SHOULD rate-limit on:

  1. consecutive failed attempts by username+IP
  2. failed attempts by IP within a time window

Insecure patterns:

* Unbounded login attempts.

Detection hints:

* Identify all auth endpoints and check whether rate limiting/throttling is applied.
* Look for `rate-limiter-flexible`, `express-rate-limit`, or gateway policies.

Fix:

* Implement rate limiting/throttling (application or edge). Express documentation points to `rate-limiter-flexible` as a tool for this approach. ([Express][1])

Notes:

* The OWASP Node.js cheat sheet also recommends precautions against brute-force. ([OWASP Cheat Sheet Series][8])

---

### EXPRESS-DEPS-001: Dependency and patch hygiene (Express + Node + critical middleware)

Severity: Medium / Low

NOTE: `npm audit` often returns a large number of trivial "vulnerabilities" that do not actually matter. Focus only on Express or other extremely critical packages, ignoring those listed in dev tooling, bundlers, etc.

Do not upgrade packages without the user's consent. This may unexpectedly break existing code. Instead, inform the user about outdated packages.

Required:

* MUST keep Express on a supported version line (avoid EOL major versions).
* MAY use `npm audit` in CI and during maintenance work.
* SHOULD pin dependencies via lockfiles and carefully review major upgrades.

Insecure patterns:

* Running EOL Express versions (for example, very old major lines).
* Ignoring `npm audit` findings without triage.
* Unpinned dependency ranges that auto-update into unsafe versions.

Detection hints:

* Check `package.json` and lockfiles for the version of `express` and other critical middleware.
* Check CI pipelines for `npm audit`/SCA steps.

Fix:

* Update to the latest stable Express and apply patches.
* Add automated dependency scanning and an upgrade process.

Notes:

* Express's production-security guide emphasizes that vulnerabilities in dependencies can compromise the application and recommends `npm audit`. ([Express][1])
* Track security issues affecting Express versions (including known CVEs related to open redirect). ([NVD][9])

---

### EXPRESS-DOS-001: Configure DoS defenses (timeouts, limits, reverse proxy)

Severity: Low

NOTE: It can be difficult to determine from the provided application context whether the app runs behind a reverse proxy. You can inform the user or recommend it, but do not attempt to configure the proxy without their initiative. This is highly deployment-dependent.

Required:

* SHOULD use a reverse proxy to provide caching, load balancing, and filtering when possible.
* MAY configure server/proxy timeouts and connection limits to reduce exposure to Slowloris and similar DoS patterns.
* MUST ensure that server/socket errors are handled so that malformed connections do not crash the process. (Express should handle exceptions, but there are edge cases.)

Insecure patterns:

* No reverse proxy in front of the public Node server, defaults everywhere.
* Missing error handlers on server/socket objects.
* Extremely permissive timeouts and unbounded body sizes.

Detection hints:

* Review server creation (`http.createServer`, `https.createServer`) and whether timeouts are set.
* Check proxy/gateway configuration for timeouts and max body size.

Fix:

* Explain how to configure a reverse proxy and timeouts; set request size limits.
* Add robust error-handling middleware.

Notes:

* The Node security guide for HTTP DoS discusses use of reverse proxies and proper server-timeout configuration. ([Node.js][15])

---

### EXPRESS-NODE-INSPECT-001: Do not expose the Node inspector in production

Severity: Critical

NOTE: Verify that this finding is actually in a production path and is not just used for local debugging.

Required:

* MUST NOT run Node with `--inspect` (especially bound to a non-loopback address) in production.
* MUST ensure `NODE_OPTIONS` or startup scripts do not enable the inspector in prod.
* SHOULD firewall / debug only locally.

Insecure patterns:

* `node --inspect=0.0.0.0:9229 app.js` in production.
* Container/PM2/systemd configurations that enable the inspector.

Detection hints:

* Look for `--inspect` in Dockerfiles, Procfiles, systemd units, PM2 configs, npm scripts.
* Check `NODE_OPTIONS`.

Fix:

* Remove inspector flags from production startup commands; restrict to local development.

Notes:

* The Node security guide discusses inspector-exposure risks (for example, DNS rebinding) and recommends not running the inspector in production. ([Node.js][15])

---

### EXPRESS-NODE-HTTP-001: Do not enable insecure HTTP parsing in production

Severity: High

NOTE: Verify that this finding is actually in a production path and is not just used for local development.

Required:

* MUST NOT use Node's `insecureHTTPParser` in production.
* MAY suggest configuring a front-end proxy to normalize ambiguous requests to reduce request-smuggling risk.

Insecure patterns:

* Creating an HTTP server with `{ insecureHTTPParser: true }`.

Detection hints:

* Look for `insecureHTTPParser` in server-creation code.

Fix:

* Remove insecure parsing; rely on spec-compliant parsing and normalize at the edge.

Notes:

* The Node security guide explicitly recommends not using `insecureHTTPParser`. ([Node.js][15])

---

## 5) Practical Scanning Heuristics (how to "hunt")

When actively scanning an Express repository, these patterns have a high signal:

* TLS / transport:

  * `app.listen(80` with no mention of a reverse proxy; missing `helmet`; cookies without `secure` ([Express][1]) (NOTE: this applies only to web-facing applications; internal applications likely do not have TLS)
* Proxy trust:

  * `app.set('trust proxy', true)`; logic that uses `req.ip`/`req.protocol`/`req.hostname` ([Express][2])
* Security headers / fingerprinting:

  * missing `helmet(`; missing `app.disable('x-powered-by')` ([Express][1])
* Cookies / sessions:

  * `express-session` with a missing `store` (MemoryStore risk), hardcoded `secret:`, missing `cookie: { secure/httpOnly/sameSite }` ([Express][1])
  * `cookie-session` storing large objects or secrets ([Express][1])
* Body parsing limits:

  * `express.json()` or `express.urlencoded()` without `limit`/`parameterLimit`/`depth` ([Express][5])
* CSRF:

  * POST/PUT/PATCH/DELETE routes with cookie authentication and no CSRF tokens / origin checks ([OWASP Cheat Sheet Series][3])
* Open redirects:

  * `res.redirect(req.query.next)` or similar ([Express][1])
* XSS / HTML output:

  * `res.send(` building HTML with user input; "safe" template flags; untrusted values in `res.locals` ([Express][5])
* File handling:

  * `res.sendFile(` / `res.download(` where the path comes from a request; `express.static('uploads')` ([Express][5])
* Injection:

  * SQL strings + template literals in DB calls ([OWASP Cheat Sheet Series][6])
  * `child_process.exec` / `execSync` / `shell: true` ([OWASP Cheat Sheet Series][14])
* SSRF:

  * Outbound `fetch/axios/got` to user-provided URLs ([OWASP Cheat Sheet Series][7])
* Brute force / abuse:

  * Auth endpoints without throttling; no rate-limiting middleware ([Express][1])
* Supply chain:

  * Outdated Express versions; no lockfiles; no `npm audit` workflow ([Express][1])
* Node runtime hazards:

  * `--inspect` in production scripts; use of `insecureHTTPParser` ([Node.js][15])

Always try to confirm:

* data origin (untrusted vs. trusted)
* sink type (HTML/template, SQL/NoSQL, subprocess, filesystem, redirect, outbound HTTP)
* defensive controls present (validation, allowlists, middleware, proxy configuration, header policies)
* whether defenses are at the edge or in application code

---

## 6) Sources (as of 2026-01-27)

Primary Express documentation:

* Express: Production Best Practices -- Security: `https://expressjs.com/en/advanced/best-practice-security.html` ([Express][1])
* Express: Behind Proxies (`trust proxy`): `https://expressjs.com/en/guide/behind-proxies.html` ([Express][2])
* Express 5.x API Reference (parsers, static, sendFile, redirect, cookies): `https://expressjs.com/en/5x/api.html` ([Express][5])
* Express: Error Handling: `https://expressjs.com/en/guide/error-handling.html` ([Express][11])

Session middleware documentation:

* express-session docs (cookie flags, secret rotation, fixation mitigation, MemoryStore warning): `https://expressjs.com/en/resources/middleware/session.html` ([Express][1])

Official Node.js and npm references:

* Node.js -- Security Best Practices (DoS, proxy guidance, inspector risks, request-smuggling notes): `https://nodejs.org/en/learn/getting-started/security-best-practices` ([Node.js][15])
* npm Docs -- `npm audit`: `https://docs.npmjs.com/cli/v9/commands/npm-audit/` ([npm Docs][16])

OWASP Cheat Sheet Series:

* Session Management: `https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][12])
* CSRF Prevention: `https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][3])
* XSS Prevention: `https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][4])
* Input Validation: `https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][17])
* SQL Injection Prevention: `https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][6])
* OS Command Injection Defense: `https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][14])
* SSRF Prevention: `https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][7])
* File Upload: `https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][13])
* Unvalidated Redirects: `https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][18])
* HTTP Headers: `https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][10])

Versioning / advisories:

* Express package version (npm): `https://www.npmjs.com/package/express`
* Express open-redirect advisory (CVE): `https://nvd.nist.gov/vuln/detail/CVE-2024-29041` ([NVD][9])

[1]: https://expressjs.com/en/advanced/best-practice-security.html "Security Best Practices for Express in Production"
[2]: https://expressjs.com/en/guide/behind-proxies.html "Express behind proxies"
[3]: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html "Cross-Site Request Forgery Prevention - OWASP Cheat Sheet Series"
[4]: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html "Cross Site Scripting Prevention - OWASP Cheat Sheet Series"
[5]: https://expressjs.com/en/5x/api.html "Express 5.x - API Reference"
[6]: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html "SQL Injection Prevention - OWASP Cheat Sheet Series"
[7]: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html "Server Side Request Forgery Prevention - OWASP Cheat Sheet Series"
[8]: https://cheatsheetseries.owasp.org/cheatsheets/Nodejs_Security_Cheat_Sheet.html "Nodejs Security - OWASP Cheat Sheet Series"
[9]: https://nvd.nist.gov/vuln/detail/cve-2024-29041?utm_source=chatgpt.com "CVE-2024-29041 Detail - NVD"
[10]: https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html "HTTP Headers - OWASP Cheat Sheet Series"
[11]: https://expressjs.com/en/guide/error-handling.html "Express error handling"
[12]: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html "Session Management - OWASP Cheat Sheet Series"
[13]: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html "File Upload - OWASP Cheat Sheet Series"
[14]: https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html "OS Command Injection Defense - OWASP Cheat Sheet Series"
[15]: https://nodejs.org/en/learn/getting-started/security-best-practices "Node.js -- Security Best Practices"
[16]: https://docs.npmjs.com/cli/v9/commands/npm-audit/ "npm-audit | npm Docs"
[17]: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html "Input Validation - OWASP Cheat Sheet Series"
[18]: https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html "Unvalidated Redirects and Forwards - OWASP Cheat Sheet Series"
