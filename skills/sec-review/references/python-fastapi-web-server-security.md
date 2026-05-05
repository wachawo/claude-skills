# FastAPI (Python) Web Application Security Specification (FastAPI 0.128.x, Python 3.x) ([PyPI][1])

This document is intended as a **security specification** that supports:

1. **Secure-by-default code generation** for new FastAPI code.
2. **Security review and vulnerability hunting** in existing FastAPI code (both passive "spot issues while working" mode and active "scan the repo and report findings" mode).

The document is intentionally written as a set of **normative requirements** ("MUST/SHOULD/MAY") together with **audit rules** (what bad patterns look like, how to detect them, and how to fix or mitigate them).

FastAPI is typically deployed with an ASGI server (for example, Uvicorn) and is built on top of Starlette + Pydantic, so this specification touches those layers where they affect security. ([PyPI][1])

---

## 0) Safety, Boundaries, and Anti-Abuse Constraints (MANDATORY)

* MUST NOT request, output, log, or commit secrets (API keys, passwords, private keys, session cookies, signing keys, DB connection strings with credentials).
* MUST NOT "fix" security by disabling protections (for example, weakening authentication, making CORS permissive, skipping signature verification, disabling validation, disabling TLS verification, adding `allow_origins=["*"]` together with credentials).
* MUST provide **evidence-based findings** when auditing: cite file paths, code snippets, and configuration values that justify the claim.
* MUST be honest about uncertainty: if a defense may exist in the infrastructure (reverse proxy, WAF, CDN, service mesh), report it as "not visible in application code; verify at runtime / in configuration".
* MUST treat browser mechanisms correctly:

  * CORS is **not** an authentication mechanism; it affects browsers only.
  * CSRF protection applies when the browser automatically attaches credentials (cookies); it is generally not relevant for purely header-based token APIs. ([OWASP Cheat Sheet Series][2])

---

## 1) Modes of Operation

### 1.1 Generation Mode (default)

When asked to write new FastAPI code or modify existing code:

* MUST honor every **MUST** requirement of this specification.
* SHOULD honor every **SHOULD** requirement unless the user explicitly states otherwise.
* MUST prefer secure-by-default APIs and proven libraries over hand-rolled security code.
* MUST avoid introducing new risky "sinks" (shell-command execution, unsafe deserialization, dynamic eval, untrusted template rendering, unsafe file serving, unsafe redirects, arbitrary outbound requests).

### 1.2 Passive Review Mode (always on while editing)

When working anywhere in a FastAPI repository (even if the user did not request a security scan):

* MUST "spot" violations of this specification in edited or adjacent code.
* SHOULD raise issues as they arise, with a brief explanation and a safe fix.

### 1.3 Active Audit Mode (explicit scan request)

When the user asks to "scan", "audit", or "hunt for vulnerabilities":

* MUST systematically search the codebase for violations of this specification.
* MUST output findings in a structured format (see §2.3).

Recommended audit order:

1. Application entry points / deploy scripts / Dockerfile / Procfile / Helm/terraform.
2. ASGI server configuration (Uvicorn/Gunicorn), proxy settings, debug/reload parameters.
3. FastAPI application configuration (docs exposure, middleware, trusted hosts, CORS).
4. Authentication/authorization design (dependencies, JWT/session handling, password storage).
5. Cookie/session usage + CSRF (when cookies are used).
6. Input validation and response shaping (Pydantic models, mass assignment, excessive data exposure).
7. Template rendering and XSS/SSTI (when serving HTML).
8. File handling (uploads + downloads), StaticFiles, Range support.
9. Injection classes (SQL, command execution, unsafe deserialization).
10. Outbound requests (SSRF), redirect handling, WebSockets security.

---

## 2) Definitions and Review Guidance

### 2.1 Untrusted Input (treat as attacker-controlled until proven otherwise)

Examples:

* Query parameters / path parameters
* JSON bodies (including nested fields)
* Headers (including `Host`, `Origin`, `X-Forwarded-*`)
* Cookies (including session cookies)
* File uploads (multipart parts)
* WebSocket messages, query parameters, and headers at the handshake stage ([Starlette][3])
* Any data from external systems (webhooks, third-party APIs, message queues)
* Any stored user content (DB rows) that originally came from users

### 2.2 State-Changing Request

A request is state-changing if it can create/update/delete data, change auth/session state, cause side effects (purchase, sending email, dispatching a webhook), or initiate privileged actions.

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

This is the minimum "production baseline" that prevents common FastAPI/ASGI misconfigurations.

Baseline goals:

* No debug tracebacks or auto-reload in production. ([PyPI][4])
* Run with production ASGI-server configuration (workers, timeouts, resource limits). ([PyPI][4])
* Host-header validation enabled (TrustedHostMiddleware or equivalent). ([PyPI][5])
* CORS disabled unless explicitly required; if enabled, configured strictly and with least privilege. ([OWASP Cheat Sheet Series][6])
* Authentication is consistently enforced via dependencies (no "oops, forgot auth on this route"). ([FastAPI][7])
* If cookies/sessions are used, cookie flags are safe and CSRF is addressed. ([OWASP Cheat Sheet Series][8])
* Request size and multipart limits are enforced at the edge and verified in the application as needed (to defend against memory/CPU DoS). ([advisories.gitlab.com][9])
* Dependencies are patched promptly, especially Starlette/python-multipart (historically affected by multiple DoS and path-traversal advisories). ([advisories.gitlab.com][10])

---

## 4) Rules (generation + audit)

Each rule contains: required practice, insecure patterns, detection hints, and remediation guidance.

### FASTAPI-DEPLOY-001: Do not use auto-reload / dev server modes in production

Severity: High (in production)

Required:

* MUST NOT run production with auto-reload/watch mode (for example, Uvicorn reload).
* MUST use a production process model (for example, multiple workers where appropriate) and stable server settings. ([PyPI][4])

Insecure patterns:

* `uvicorn ... --reload` (or equivalents with `reload=True`) in production entry points.
* Docker/Procfile/systemd commands launching `--reload` in production.

Detection hints:

* Look for `--reload`, `reload=True`, `watchfiles`, `fastapi dev`, "development"-style start scripts.
* Inspect Docker CMD/ENTRYPOINT, Procfile, systemd units, shell scripts.

Fix:

* Remove reload in production; run Uvicorn/Gunicorn with stable settings and explicit worker configuration. ([PyPI][4])

Note:

* Reload is appropriate for local development. Flag it only when it is explicitly used as a production entry point.

---

### FASTAPI-DEPLOY-002: Debug mode MUST be disabled in production

Severity: Critical

Required:

* MUST NOT enable debug tracebacks in production (FastAPI/Starlette debug mode can expose sensitive internal details and ease some exploit chains). ([PyPI][5])
* MUST treat any configuration that returns detailed stack traces to clients as sensitive.

Insecure patterns:

* `app = FastAPI(debug=True)` (or Starlette `debug=True`) or equivalent environment switches enabling debug in production. ([PyPI][5])
* Server/log configuration exposing stack traces to end users.

Detection hints:

* Look for `debug=True`, `DEBUG = True`, environment flags mapped to debug.
* Inspect exception middleware and error handlers.

Fix:

* Enable debug only in local development/tests.
* Return generic error messages to clients; log details internally.

---

### FASTAPI-OPENAPI-001: OpenAPI and interactive docs MUST be disabled or protected in production

Severity: Medium (can be High in sensitive/internal applications)

Required:

* SHOULD disable `/docs`, `/redoc`, and `/openapi.json` in production for public services unless there is an explicit business need.
* If enabled, MUST protect (for example, authentication, network allowlists, or internal routing).
* MUST NOT rely on "security through obscurity"; treat docs exposure as an information-disclosure amplifier.

Insecure patterns:

* Publicly accessible `/docs` and `/openapi.json` for internal/admin APIs.
* Docs enabled on the same hostname as production without access control.

Detection hints:

* Look for `FastAPI(docs_url=..., redoc_url=..., openapi_url=...)` or default values.
* Check routing and allowlists at the reverse proxy.

Fix:

* Disable docs endpoints in production (`docs_url=None`, `redoc_url=None`, `openapi_url=None`) or restrict access at the edge.

---

### FASTAPI-AUTH-001: Authentication MUST be explicit and consistently enforced via dependencies

Severity: High

Required:

* MUST implement authentication as a dependency (or a router-level dependency) so that protected endpoints cannot "forget" authentication.
* MUST default to deny for privileged routers/endpoints; explicitly mark genuinely public routes.
* SHOULD centralize authentication enforcement at router boundaries (for example, a protected `APIRouter` for authenticated endpoints). ([FastAPI][7])

Insecure patterns:

* Scattered ad-hoc authentication checks inside handlers (easy to miss).
* A mix of protected/unprotected endpoints without a clear policy.

Detection hints:

* Find routers and endpoints; verify that protected ones include `Depends(...)`/`Security(...)`.
* Look for `if user is None: raise ...` patterns inside handlers (instead of dependencies).

Fix:

* Move authentication into a dependency and consistently attach it to the router/endpoint via `Depends()`/`Security()`. ([FastAPI][7])

---

### FASTAPI-AUTH-002: Use standard authentication transports; avoid secrets in URLs

Severity: High

Required:

* SHOULD use the `Authorization: Bearer <token>` header for token-based authentication, not query parameters. ([FastAPI][11])
* MUST NOT place secrets (tokens, password-reset links with long-lived secrets, API keys) in the query string when avoidable.

Insecure patterns:

* `?token=...`, `?api_key=...`, `?auth=...` as the primary authentication.
* Long-lived access tokens embedded in URLs (leak via logs, referrers, caches).

Detection hints:

* Look for parameter names such as `token`, `api_key`, `key`, `secret`, `password`.
* Look for security schemes using query API keys without justification.

Fix:

* Move tokens to Authorization headers; rotate / shorten lifetimes; pass sensitive values in POST bodies.

---

### FASTAPI-AUTH-003: Password storage MUST use strong hashing; never store plaintext passwords

Severity: Critical

Required:

* MUST store passwords using a strong, slow password KDF (for example, Argon2id, bcrypt).
* MUST NOT store passwords in plaintext or use reversible encryption as the primary defense.
* SHOULD use vetted libraries for hashing and verification (do not roll your own).

Insecure patterns:

* Storing plaintext passwords in the DB.
* Using fast hashes (for example, SHA256) without a proper password KDF.
* Returning password hashes in API responses.

Detection hints:

* Look for persistent `password=` fields and use of `hashlib.md5/sha1/sha256` on passwords.
* Inspect response models for password/hash fields.

Fix:

* Switch to a full-fledged password-hashing library; add a hash-upgrade path on login.

---

### FASTAPI-AUTH-004: JWT validation MUST be strict; JWTs MUST NOT contain secrets

Severity: High

Required:

* MUST verify JWT signatures and enforce an algorithm allowlist.
* MUST validate standard claims relevant to the system (at minimum `exp`; usually also `iss`/`aud` for multi-service or multi-tenant systems).
* MUST treat JWT contents as readable by the client; do not place secrets in the JWT payload. ([FastAPI][12])

Insecure patterns:

* `jwt.decode(..., options={"verify_signature": False})` or equivalent.
* Accepting `alg=none` / algorithm confusion.
* Using the JWT payload to store sensitive secrets (API keys, passwords).

Detection hints:

* Look for `jwt.decode`, `python-jose`, `PyJWT`, `verify_signature`.
* Check for missing exp validation or excessively long lifetimes.

Fix:

* Apply strict validation (signature, allowed algorithms, exp, and any required issuer/audience constraints).
* Store only identifiers/claims that you are willing to expose to the client. ([FastAPI][12])

---

### FASTAPI-AUTHZ-001: Authorization MUST be enforced at the object and property level

Severity: High

Required:

* MUST perform object-level authorization when accessing a resource by an identifier the user controls (path/query/body IDs).
* MUST perform property-level authorization and response shaping to prevent "excessive data exposure" (for example, admin-only fields). ([OWASP Foundation][13])

Insecure patterns:

* `GET /users/{id}` returns the user record without verifying that the caller has access to that `id`.
* Response models include internal fields (roles, permissions, billing, password hashes).

Detection hints:

* Enumerate endpoints accepting IDs; trace whether an authorization check is performed.
* Compare response models for public vs. internal fields.

Fix:

* Add object-level checks (ownership, ACL, tenant boundaries).
* Use dedicated response models that include only allowed fields.

---

### FASTAPI-SESS-001: When using cookie sessions and TLS, cookie attributes MUST be safe in production

Severity: High (only when TLS is enabled)

Required (production, HTTPS):

* MUST mark session cookies as transmitted over HTTPS only (secure). IMPORTANT NOTE: only set `Secure` in production environments where TLS is configured. When working in a local dev environment over HTTP, do not set the `Secure` property on cookies. Set this conditionally based on whether the application is running in production mode. Also include a property such as `SESSION_COOKIE_SECURE` that can be used to disable `Secure` cookies when testing over HTTP.
* MUST set HttpOnly for session cookies (not accessible from JS).
* SHOULD use `SameSite=Lax` (or `Strict` if UX permits); if cross-site cookies are required, document the CSRF implications and add compensating controls. ([OWASP Cheat Sheet Series][8])
* When using Starlette's `SessionMiddleware`, MUST set `https_only=True` in production and choose an appropriate `same_site`. ([PyPI][5])

Insecure patterns:

* Session cookies without Secure/HttpOnly.
* `SameSite=None` cookies used for authenticated state-changing endpoints without CSRF protection.

Detection hints:

* Look for `SessionMiddleware(` and inspect parameters such as `https_only`, `same_site`.
* Look for `set_cookie(` usage and cookie flags.

Fix:

* Set safe cookie attributes; prefer short lifetimes for highly privileged sessions. ([OWASP Cheat Sheet Series][8])

---

### FASTAPI-SESS-002: Do not store sensitive secrets in signed session cookies

Severity: High

Required:

* MUST assume cookie-session data is readable by the client (signed != encrypted); do not store secrets/PII unless they are encrypted server-side.
* In cookies, store only opaque identifiers (for example, a session ID) or non-sensitive state; keep sensitive session state on the server. ([OWASP Cheat Sheet Series][8])

Insecure patterns:

* Storing access tokens, refresh tokens, or PII directly in the cookie-session payload.
* Treating "signed cookies" as a confidential storage mechanism.

Detection hints:

* Look for `request.session[...] =` or equivalent `session[...] =`; identify what is stored.
* Find use of `SessionMiddleware` or other cookie-session mechanisms.

Fix:

* Move sensitive values to server-side storage; keep cookies minimal.

---

### FASTAPI-CSRF-001: Cookie-authenticated state-changing requests MUST be CSRF-protected

Severity: High

Note: applies only when cookie-based authentication is used. If the application uses header- or token-based authentication (for example, an Authorization header), CSRF is not a concern.

Required:

* MUST protect all state-changing endpoints (POST/PUT/PATCH/DELETE) that rely on cookies for authentication.
* SHOULD use a vetted CSRF approach (synchronizer-token pattern or well-tested middleware), not a hand-rolled one. ([OWASP Cheat Sheet Series][2])
* MAY add defense-in-depth (Origin/Referer checks, SameSite cookies, Fetch Metadata), but tokens remain the primary defense for cookie-authenticated apps. ([OWASP Cheat Sheet Series][2])
* IMPORTANT NOTE: if cookies are not used for authentication (it is via the `Authorization` header), CSRF is generally not applicable. ([FastAPI][11])

Insecure patterns:

* Cookie-authenticated endpoints that change state without CSRF verification.
* Using GET for state-changing actions (amplifies CSRF risk).

Detection hints:

* Enumerate routes with non-GET methods; determine whether cookies are used for authentication.
* Look for CSRF-token generation/verification or relevant middleware.

Fix:

* Add CSRF tokens (and verify them) on state-changing actions when cookie-based auth is used. ([OWASP Cheat Sheet Series][2])

---

### FASTAPI-VALID-001: Request parsing and validation MUST be schema-based; prevent mass assignment

Severity: Medium (especially for APIs that write to a DB)

Required:

* SHOULD use Pydantic models for request bodies instead of accepting arbitrary `dict`/`Any`.
* SHOULD configure models to reject unexpected fields where appropriate (preventing "mass assignment"-class bugs).
* MUST validate and normalize identifiers (IDs, emails, URLs) before using them in access control or side effects. ([OWASP Cheat Sheet Series][14])

Insecure patterns:

* `payload = await request.json()` followed by `Model(**payload)` or direct DB writes from `payload` (without an allowlist).
* Models silently accepting unknown fields for write endpoints.

Detection hints:

* Look for `await request.json()`, `request.body()`, bodies typed as `dict`, bodies typed as `Any`.
* Look for endpoints performing `db.update(**payload)` or `Model(**payload)` with unfiltered input.

Fix:

* Use explicit Pydantic models with an allowlist of fields; reject extra fields for write endpoints. ([OWASP Cheat Sheet Series][14])

---

### FASTAPI-RESP-001: Prevent excessive data exposure via response models and explicit serialization

Severity: Medium

Required:

* MUST define response models that include only intended fields (especially for user objects, authentication objects, billing objects).
* SHOULD use separate models for "create input", "DB/internal", and "public output" to avoid leaking sensitive fields. ([FastAPI][15])

Insecure patterns:

* Returning ORM objects or dicts that include internal columns.
* Reusing the "DB model" as the response model (which includes `password_hash`, `is_admin`, etc.).

Detection hints:

* Look for endpoints where `return user` is used and `user` is an ORM instance.
* Check for missing `response_model` on endpoints returning sensitive resources.

Fix:

* Add explicit response models; create "public" schemas that exclude sensitive fields. ([FastAPI][15])

---

### FASTAPI-XSS-001: Prevent reflected/stored XSS in HTML responses and templates

Severity: High (when the service serves HTML)

Required:

* MUST use templating with autoescape enabled for HTML.
* MUST NOT mark untrusted content as safe (no "raw HTML" rendering of user data).
* SHOULD deploy CSP when serving HTML that includes user content. ([OWASP Cheat Sheet Series][16])

Insecure patterns:

* Rendering user content directly into HTML without escaping/sanitization.
* Disabling autoescape or using "raw HTML" without sanitization.

Detection hints:

* Look for template rendering and string concatenation that builds HTML.
* Inspect templates for "unsafe" filters/constructs and unescaped attributes.

Fix:

* Keep autoescape enabled; sanitize user HTML only when strictly necessary using a trusted sanitizer; add CSP. ([OWASP Cheat Sheet Series][16])

Note:

* If the application is a JSON-only API, XSS typically concerns the client/application, but error/docs pages may still serve HTML.

---

### FASTAPI-SSTI-001: Never render untrusted templates (Server-Side Template Injection)

Severity: Critical

Required:

* MUST NOT render templates that contain user-controlled template syntax.
* MUST treat "template-from-string" rendering as dangerous when influenced by untrusted input.
* If untrusted templates are absolutely required (a rare high-risk case):

  * MUST use a sandboxed templating approach and constrain capabilities.
  * MUST assume sandbox escapes are possible; add isolation and strict allowlists. ([OWASP Foundation][17])

Insecure patterns:

* Rendering templates loaded from user input or DB through a regular Jinja environment.
* Dynamically building templates from user strings.

Detection hints:

* Grep for Jinja `Environment.from_string`, `Template(...)`, and similar.
* Trace where the template string originates (request, DB, uploads, admin panels).

Fix:

* Replace with non-executing templating (simple string substitution).
* If genuinely required, use Jinja's sandbox environment plus strong isolation. ([jinja.palletsprojects.com][18])

---

### FASTAPI-HEADERS-001: Set important security headers (in the application or at the edge)

Severity: Medium

Required (typical API/web application):

* SHOULD set:

  * `X-Content-Type-Options: nosniff`
  * Clickjacking protection (`X-Frame-Options` and/or CSP `frame-ancestors`) when serving HTML
  * `Referrer-Policy` and `Permissions-Policy` as appropriate

NOTE:

* Headers may be set by a proxy/CDN. If they are not visible in application code, mark as "verify at edge". ([OWASP Cheat Sheet Series][6])

Insecure patterns:

* No security headers at all (neither in the application nor at the edge) for applications serving HTML or sensitive APIs.

Detection hints:

* Look for middleware that sets headers; inspect reverse-proxy configuration.

Fix:

* Set headers centrally (middleware) or via a reverse proxy/CDN.

---

### FASTAPI-CORS-001: CORS MUST be explicit and least-privilege

Severity: Medium (High when misconfigured with credentials)

Required:

* If CORS is not needed, MUST keep it disabled.
* If CORS is needed:

  * MUST allowlist trusted origins (do not reflect arbitrary origins).
  * MUST NOT combine credentialed requests with wildcard origins (insecure and typically rejected by spec-compliant middleware). ([OWASP Cheat Sheet Series][6])
  * SHOULD restrict allowed methods and headers.

Insecure patterns:

* `allow_origins=["*"]` together with `allow_credentials=True`.
* Reflecting `Origin` without validation.
* `allow_origin_regex=".*"` used broadly.

Detection hints:

* Look for `CORSMiddleware` configuration.
* Check for `allow_origins=["*"]`, `allow_credentials=True`, `allow_origin_regex`.

Fix:

* Use an explicit origin allowlist and minimal methods/headers; keep credentials off unless required. ([OWASP Cheat Sheet Series][6])

---

### FASTAPI-HOST-001: The Host header MUST be validated in production

Severity: Low

Required:

* SHOULD use `TrustedHostMiddleware` (or an equivalent at the edge) to constrain accepted Host values. ([PyPI][5])
* MUST NOT trust the `Host` header for security-sensitive decisions without validation.

Insecure patterns:

* Missing Host validation when generating external URLs (password-reset links, callback URLs) from the request host.
* Allowing arbitrary Host headers in applications behind permissive proxies.

Detection hints:

* Look for the use of `TrustedHostMiddleware`.
* Look for logic using `request.url`, `request.base_url`, or values derived from host to construct external URLs.

Fix:

* Configure a strict host allowlist in production; enforce at the edge as well where possible.

---

### FASTAPI-PROXY-001: Reverse-proxy trust MUST be configured correctly

Severity: High (when the application is behind a proxy)

Required:

* If the application is behind a reverse proxy, MUST correctly configure trust for forwarded headers.
* MUST NOT blindly trust `X-Forwarded-*` headers from the open internet.
* When using Uvicorn's proxy-header support, MUST restrict which IPs are allowed to send them. ([PyPI][4])

Insecure patterns:

* Enabling proxy headers broadly without restricting trusted proxy IPs.
* Using forwarded headers for "is this request secure", "is it internal", or "client IP" decisions without proper trust boundaries.

Detection hints:

* Look for `--proxy-headers`, `--forwarded-allow-ips`, or equivalent configuration.
* Look for security-sensitive use of `request.client.host`, `request.url.scheme`, `request.headers["x-forwarded-for"]`.

Fix:

* Configure Uvicorn with proxy headers only when the application is behind a known proxy, and restrict `forwarded_allow_ips` to that proxy. ([PyPI][4])
* Maintain a host allowlist behind the proxy as well.

---

### FASTAPI-LIMITS-001: Request and multipart limits MUST be enforced to prevent DoS

Severity: Low

Required:

* MUST enforce request size limits at the edge (reverse proxy/load balancer) and verify in the application as needed.
* MUST be especially careful with multipart/form-data handling; historically there have been advisories around unbounded buffering and DoS vectors. ([advisories.gitlab.com][9])
* SHOULD use rate limiting and/or per-IP/per-user throttling for expensive endpoints.

Insecure patterns:

* Accepting arbitrarily large JSON bodies or multipart forms.
* Parsing multipart forms without size/field-count controls.

Detection hints:

* Find file-upload endpoints and `multipart/form-data` usage.
* Look for missing limits at the proxy layer (nginx `client_max_body_size`, ALB limits, etc.) and missing application-level checks.

Fix:

* Enforce strict body limits and multipart constraints; keep Starlette and python-multipart on patched versions. ([advisories.gitlab.com][9])

---

### FASTAPI-FILES-001: Prevent path traversal and unsafe static-file exposure

Severity: High

Required:

* MUST NOT pass user-supplied file paths to `FileResponse`/file calls without strict validation and safe base directories.
* When using `StaticFiles`, MUST keep Starlette current and understand the security history (older versions had a path-traversal advisory). ([advisories.gitlab.com][10])
* MUST NOT serve user uploads as executable/active content (especially HTML/JS) from the static root without safe handling.

Insecure patterns:

* `FileResponse(request.query_params["path"])`
* Mounting `StaticFiles(directory="uploads")` where uploads include HTML/JS/SVG and are served inline.

Detection hints:

* Look for `FileResponse(`, `StaticFiles(`, `open(` in routes.
* Trace whether the path comes from untrusted input.

Fix:

* Use opaque IDs for files; map IDs to server-side paths.
* Serve untrusted content as attachment downloads where appropriate.

---

### FASTAPI-FILES-002: Mitigate Range-header DoS risk on file-serving endpoints

Severity: Low (when using vulnerable versions and file serving is enabled)

Required:

* MUST keep Starlette patched against known file-serving DoS issues if `FileResponse`/`StaticFiles` is used.
* MUST treat unusual Range-header handling and file serving as a DoS surface. ([advisories.gitlab.com][19])

Insecure patterns:

* Serving large files from vulnerable Starlette versions.
* No rate limiting / CDN shielding for file endpoints.

Detection hints:

* Determine the Starlette version; if in a vulnerable range, flag it.
* Find use of `FileResponse` and `StaticFiles`.

Fix:

* Update Starlette to the fixed version per the advisory. ([advisories.gitlab.com][19])
* Add edge caching / rate limiting for file endpoints where appropriate.

---

### FASTAPI-UPLOAD-001: File uploads MUST be validated, stored safely, and served safely

Severity: Medium

Required:

* MUST enforce upload size limits (application + edge).
* MUST validate file type using allowlists and content checks (not just extensions). ([OWASP Cheat Sheet Series][20])
* SHOULD generate filenames server-side (random IDs) and not trust original names.
* MUST safely serve potentially active formats (as a download attachment) unless explicitly intended otherwise.

Insecure patterns:

* Accepting arbitrary file types and serving them back inline.
* Using a user-supplied filename as the storage path.

Detection hints:

* Look for upload handlers and where/how files are written.
* Look for direct publication of upload directories.

Fix:

* Implement allowlist validation + safe storage + safe serving; add scanning/quarantine where applicable. ([OWASP Cheat Sheet Series][20])

---

### FASTAPI-INJECT-001: Prevent SQL injection (use parameterized queries / ORM)

Severity: High

Required:

* MUST use parameterized queries or an ORM that parameterizes under the hood.
* MUST NOT build SQL via string concatenation / f-strings with untrusted input. ([OWASP Cheat Sheet Series][21])

Insecure patterns:

* `f"SELECT ... WHERE id={user_id}"`
* `"... WHERE name = '%s'" % user_input`

Detection hints:

* Grep for SQL keywords in Python strings near `.execute(...)`.
* Trace untrusted data into DB calls.

Fix:

* Replace with parameterized queries / ORM APIs; validate types before querying. ([OWASP Cheat Sheet Series][21])

---

### FASTAPI-INJECT-002: Prevent OS command injection

Severity: Critical-High (depending on exposure)

Required:

* MUST avoid executing shell commands with untrusted input.
* If a subprocess is necessary:

  * MUST pass arguments as a list (not a string).
  * MUST NOT use `shell=True` with attacker-influenced strings.
  * SHOULD use strict allowlists for any variable component. ([OWASP Cheat Sheet Series][22])

Insecure patterns:

* `os.system(user_input)`
* `subprocess.run(f"cmd {user}", shell=True)`
* Passing user strings to `bash -c`, `sh -c`, PowerShell, etc.

Detection hints:

* Look for `os.system`, `subprocess`, `Popen`, `shell=True`.
* Trace request/DB data into these calls.

Fix:

* Use library APIs instead of shell commands.
* If unavoidable, hardcode the command and validate parameters via an allowlist; use the `--` separator where supported. ([OWASP Cheat Sheet Series][22])

---

### FASTAPI-SSRF-001: Prevent server-side request forgery (SSRF) in outbound HTTP

Severity: Medium (can be High in cloud/VPC environments)

- Note: For small standalone projects this is less important. It is most important when deployed in a LAN or alongside other services listening on the same server.

Required:

* MUST treat outbound requests to user-supplied URLs as high-risk.
* SHOULD validate and limit destinations (allowlist of hosts/domains) for any user-influenced URL fetch.
* SHOULD block access to localhost/private IP ranges/link-local and cloud metadata endpoints.
* MUST restrict protocols to http/https.
* SHOULD set timeouts and carefully control redirects. ([OWASP Cheat Sheet Series][23])

Insecure patterns:

* `httpx.get(request.query_params["url"])`
* "URL preview/import/webhook tester" features that accept arbitrary URLs.

Detection hints:

* Look for `requests`, `httpx`, `urllib`, `aiohttp` calls with URLs derived from requests/DB.
* Find endpoints named `fetch`, `preview`, `proxy`, `webhook`, `import`.

Fix:

* Implement strict URL parsing + allowlists; add outbound traffic controls; set short timeouts; disable redirects unless required. ([OWASP Cheat Sheet Series][23])

---

### FASTAPI-REDIRECT-001: Prevent open redirects

Severity: Low

Required:

* MUST validate redirect targets derived from untrusted input (`next`, `redirect`, `return_to`).
* SHOULD prefer redirects only to same-site relative paths or to an allowlist of domains. ([OWASP Cheat Sheet Series][24])

Insecure patterns:

* Returning `RedirectResponse(next)` where `next` is user-supplied without validation.

Detection hints:

* Look for `RedirectResponse(` or redirect logic and verify the source of the target.

Fix:

* Allow only relative paths or an allowlist of domains; on error, fall back to a safe default. ([OWASP Cheat Sheet Series][24])

---

### FASTAPI-WS-001: WebSocket endpoints MUST be authenticated and protected against cross-site abuse

Severity: Medium-High (depending on data/privileges)

Required:

* MUST authenticate WebSocket connections for any non-public channel (WebSockets do not provide authentication on their own). ([OWASP Cheat Sheet Series][25])
* SHOULD apply origin/CSRF-like protection appropriate for browser-based WebSocket clients (the typical control is Origin validation).
* SHOULD limit message and connection-attempt rates; close idle/abusive connections.

Insecure patterns:

* `@app.websocket(...)` accepts a connection and trusts it without an authentication check.
* Using query tokens for authentication without considering leakage/rotation.

Detection hints:

* Look for `@app.websocket` / `websocket_endpoint` and verify whether authentication is performed before accepting sensitive operations.
* Inspect origin checks, token parsing, and per-connection authorization.

Fix:

* Require authentication during the handshake (for example, a token or session) and apply authorization for actions/messages.
* Validate Origin for browser clients where appropriate; apply rate limits and timeouts. ([OWASP Cheat Sheet Series][25])

---

### FASTAPI-SUPPLY-001: Dependency and patch hygiene (focus on security-critical deps)

Severity: Low

Required:

* SHOULD pin and regularly update security-critical dependencies (FastAPI, Starlette, Uvicorn, Pydantic, python-multipart, auth/JWT libraries).
* MUST respond promptly to known security advisories.
* MUST treat file-serving and multipart-parsing dependencies as security-sensitive due to historical CVEs. ([advisories.gitlab.com][10])

Audit-focus examples (historical):

* Path traversal in Starlette StaticFiles (fixed in 0.27.0). ([advisories.gitlab.com][10])
* DoS in Starlette multipart/form-data (fixed in 0.40.0). ([advisories.gitlab.com][9])
* DoS via the Range header in Starlette FileResponse (fixed in 0.49.1). ([advisories.gitlab.com][19])

Detection hints:

* Inspect `requirements.txt`, lockfiles, container images, and runtime environments for the actual installed versions.
* Correlate upload/file-serving features with dependency versions.

Fix:

* Update to patched versions per the advisories; add regression tests around affected behavior.

---

## 5) Practical Scanning Heuristics (how to "hunt")

When actively scanning, use these high-signal patterns:

* Dev server / debug:

  * `--reload`, `reload=True`, `debug=True`, `FastAPI(debug=True)` ([PyPI][4])
* OpenAPI/docs exposure:

  * `/docs`, `/redoc`, `/openapi.json`, `docs_url=`, `openapi_url=`
* Authentication-enforcement gaps:

  * Endpoints without `Depends()`/`Security()` where they are expected; routers without a consistent dependency boundary ([FastAPI][7])
  * Tokens in query parameters (`token=`, `api_key=`, `key=`) ([FastAPI][11])
* Sessions/cookies + CSRF:

  * `SessionMiddleware(` and cookie flags (`https_only`, `same_site`) ([PyPI][5])
  * POST/PUT/PATCH/DELETE handlers with cookie auth and no CSRF checks ([OWASP Cheat Sheet Series][2])
* Input validation and mass assignment:

  * `await request.json()` and direct DB writes from a dict; models accepting extra fields ([OWASP Cheat Sheet Series][14])
* Excessive data exposure:

  * Returning ORM objects or dicts without `response_model`; responses with password/role/internal fields ([FastAPI][15])
* CORS:

  * `CORSMiddleware` with `allow_origins=["*"]`, `allow_origin_regex=".*"`, `allow_credentials=True` ([OWASP Cheat Sheet Series][6])
* Files:

  * `FileResponse(` with user-supplied paths; `StaticFiles(` exposing uploads ([advisories.gitlab.com][10])
* Uploads / multipart:

  * `multipart/form-data` endpoints without size/field constraints; outdated Starlette/python-multipart ([advisories.gitlab.com][9])
* Injection:

  * SQL strings with f-strings/concatenation in `.execute(...)` ([OWASP Cheat Sheet Series][21])
  * `subprocess.*`, `shell=True`, `os.system` ([OWASP Cheat Sheet Series][22])
* SSRF:

  * `httpx.get/post` or `requests.*` with URLs from request/DB, without allowlist/timeouts ([OWASP Cheat Sheet Series][23])
* Redirect:

  * `RedirectResponse(next)` without validation ([OWASP Cheat Sheet Series][24])
* WebSockets:

  * `@app.websocket` handlers without auth/origin checks; use of `ws://` in production configurations ([FastAPI][27])

Always try to confirm:

* data origin (trusted/untrusted)
* sink type (SQL/subprocess/files/template/http/redirect/ws)
* presence of defenses (validation, allowlists, middleware, edge controls)
* installed dependency versions vs. vulnerable ranges ([advisories.gitlab.com][10])

---

## 6) Sources (accessed 2026-01-27)

Primary framework documentation:

* FastAPI (PyPI metadata, versioning) -- `https://pypi.org/project/fastapi/` ([PyPI][1])
* FastAPI documentation: Security "First Steps" (Authorization Bearer header conventions) -- `https://fastapi.tiangolo.com/tutorial/security/first-steps/` ([FastAPI][11])
* FastAPI reference: Dependencies (`Depends`, `Security`) -- `https://fastapi.tiangolo.com/reference/dependencies/` ([FastAPI][7])
* FastAPI reference: APIRouter (router-level dependencies) -- `https://fastapi.tiangolo.com/reference/apirouter/` ([FastAPI][28])
* FastAPI documentation: WebSockets -- `https://fastapi.tiangolo.com/advanced/websockets/` ([FastAPI][27])

ASGI/server stack documentation:

* Starlette (PyPI, general capabilities) -- `https://pypi.org/project/starlette/` ([PyPI][5])
* Starlette documentation: WebSockets -- `https://starlette.dev/websockets/` ([Starlette][3])
* Uvicorn (PyPI metadata) -- `https://pypi.org/project/uvicorn/` ([PyPI][4])
* Pydantic documentation (v2.12.x) -- `https://docs.pydantic.dev/latest/` ([Pydantic][29])

Security standards and cheat sheets:

* OWASP Cheat Sheet Series: Session Management -- `https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][8])
* OWASP Cheat Sheet Series: CSRF Prevention -- `https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][2])
* OWASP Cheat Sheet Series: XSS Prevention -- `https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][16])
* OWASP Cheat Sheet Series: Mass Assignment -- `https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][14])
* OWASP API Security Top 10 (2023) -- `https://owasp.org/API-Security/editions/2023/en/0x11-t10/` ([OWASP Foundation][13])
* OWASP Cheat Sheet Series: SQL Injection Prevention -- `https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][21])
* OWASP Cheat Sheet Series: OS Command Injection Defense -- `https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][22])
* OWASP Cheat Sheet Series: SSRF Prevention -- `https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][23])
* OWASP Cheat Sheet Series: File Upload -- `https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][20])
* OWASP Cheat Sheet Series: Unvalidated Redirects and Forwards -- `https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][24])
* OWASP Cheat Sheet Series: HTTP Security Response Headers -- `https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][6])
* OWASP Cheat Sheet Series: WebSocket Security -- `https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html` ([OWASP Cheat Sheet Series][25])
* OWASP WSTG: Testing for Server-Side Template Injection -- `https://owasp.org/www-project-web-security-testing-guide/v41/4-Web_Application_Security_Testing/07-Input_Validation_Testing/18-Testing_for_Server_Side_Template_Injection` ([OWASP Foundation][17])
* OWASP WSTG: Testing WebSockets -- `https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/10-Testing_WebSockets` ([OWASP Foundation][26])

Template-security references:

* Jinja: Sandbox -- `https://jinja.palletsprojects.com/en/stable/sandbox/` ([jinja.palletsprojects.com][18])

Selected supply-chain / advisory references (Starlette examples):

* CVE-2023-29159 (path traversal in StaticFiles; fixed in 0.27.0) -- `https://advisories.gitlab.com/pkg/pypi/starlette/CVE-2023-29159/` ([advisories.gitlab.com][10])
* CVE-2024-47874 (multipart/form-data DoS; fixed in 0.40.0) -- `https://advisories.gitlab.com/pkg/pypi/starlette/CVE-2024-47874/` ([advisories.gitlab.com][9])
* CVE-2025-62727 (Range-header DoS in FileResponse; fixed in 0.49.1) -- `https://advisories.gitlab.com/pkg/pypi/starlette/CVE-2025-62727/` ([advisories.gitlab.com][19])

[1]: https://pypi.org/project/fastapi/ "https://pypi.org/project/fastapi/"
[2]: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html"
[3]: https://starlette.dev/websockets/?utm_source=chatgpt.com "Websockets"
[4]: https://pypi.org/project/uvicorn/ "https://pypi.org/project/uvicorn/"
[5]: https://pypi.org/project/starlette/ "https://pypi.org/project/starlette/"
[6]: https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html?utm_source=chatgpt.com "HTTP Security Response Headers Cheat Sheet"
[7]: https://fastapi.tiangolo.com/reference/dependencies/?utm_source=chatgpt.com "Dependencies - Depends() and Security() - FastAPI"
[8]: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html"
[9]: https://advisories.gitlab.com/pkg/pypi/starlette/CVE-2024-47874/ "Starlette Denial of service (DoS) via multipart/form-data | GitLab Advisory Database"
[10]: https://advisories.gitlab.com/pkg/pypi/starlette/CVE-2023-29159/ "Starlette has Path Traversal vulnerability in StaticFiles | GitLab Advisory Database"
[11]: https://fastapi.tiangolo.com/tutorial/security/first-steps/?utm_source=chatgpt.com "Security - First Steps - FastAPI"
[12]: https://fastapi.tiangolo.com/tutorial/response-model/ "https://fastapi.tiangolo.com/tutorial/response-model/"
[13]: https://owasp.org/API-Security/editions/2023/en/0x11-t10/ "https://owasp.org/API-Security/editions/2023/en/0x11-t10/"
[14]: https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html"
[15]: https://fastapi.tiangolo.com/tutorial/extra-models/ "https://fastapi.tiangolo.com/tutorial/extra-models/"
[16]: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html"
[17]: https://owasp.org/www-project-web-security-testing-guide/v41/4-Web_Application_Security_Testing/07-Input_Validation_Testing/18-Testing_for_Server_Side_Template_Injection?utm_source=chatgpt.com "Testing for Server Side Template Injection"
[18]: https://jinja.palletsprojects.com/en/stable/sandbox/?utm_source=chatgpt.com "Sandbox - Jinja Documentation (3.1.x)"
[19]: https://advisories.gitlab.com/pkg/pypi/starlette/CVE-2025-62727/ "Starlette vulnerable to O(n^2) DoS via Range header merging in ``starlette.responses.FileResponse`` | GitLab Advisory Database"
[20]: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html"
[21]: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
[22]: https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html"
[23]: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html "https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html"
[24]: https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html?utm_source=chatgpt.com "Unvalidated Redirects and Forwards Cheat Sheet"
[25]: https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html?utm_source=chatgpt.com "WebSocket Security - OWASP Cheat Sheet Series"
[26]: https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/10-Testing_WebSockets?utm_source=chatgpt.com "WSTG - Latest | OWASP Foundation"
[27]: https://fastapi.tiangolo.com/advanced/websockets/?utm_source=chatgpt.com "WebSockets - FastAPI"
[28]: https://fastapi.tiangolo.com/reference/apirouter/?utm_source=chatgpt.com "APIRouter class - FastAPI"
[29]: https://docs.pydantic.dev/latest/ "https://docs.pydantic.dev/latest/"
