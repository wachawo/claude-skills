# Go (Golang) Security Specification (Go 1.25.x, standard library, net/http)

This document is intended as a **security specification** that supports:
1) **Secure-by-default code generation** for new Go code.
2) **Security review / vulnerability hunting** in existing Go code (both passive "spot issues while working" mode and active "scan the repo and produce a report" mode).

The document is intentionally written as a set of **normative requirements** ("MUST/SHOULD/MAY") plus **audit rules** (what bad patterns look like, how to detect them, and how to fix or mitigate them).

--------------------------------------------------------------------

## 0) Safety, Boundaries, and Anti-Abuse Constraints (MUST FOLLOW)

- MUST NOT request, output, log, or commit secrets (API keys, passwords, private keys, session cookies, JWTs, DB connection strings with credentials, signing keys, client secrets).
- MUST NOT "fix" security by disabling protections (for example, `InsecureSkipVerify`, `GOSUMDB=off` for public modules, wildcard CORS + credentials, removing authentication checks, disabling CSRF defenses in cookie-authenticated apps).
- MUST provide **evidence-based findings** when auditing: cite file paths, code snippets, build/deploy configuration, and concrete values that justify the claim.
- MUST be honest about uncertainty: if a control may exist at the infrastructure layer (reverse proxy, WAF, service mesh, platform configuration), report it as "not visible in application code; verify at runtime/in configuration".
- MUST keep fixes minimal, correct, and production-safe; avoid introducing breaking changes without warning (especially around auth/session flows and proxies).

--------------------------------------------------------------------

## 1) Modes of Operation

### 1.1 Generation Mode (default)
When asked to write new Go code or modify existing code:
- MUST follow every **MUST** requirement in this specification.
- SHOULD follow every **SHOULD** requirement unless the user explicitly states otherwise.
- MUST prefer secure-by-default APIs and proven libraries over hand-rolled security code.
- MUST avoid introducing new risky "sinks" (shell execution, dynamic template execution, serving user files as HTML, unsafe redirects, weak crypto, unbounded parsing, etc.).

### 1.2 Passive Review Mode (always on while editing)
When working anywhere in a Go repository (even if the user did not request a security scan):
- MUST "spot" violations of this specification in edited or adjacent code.
- SHOULD raise issues as they arise, with a brief explanation and a safe fix.

### 1.3 Active Audit Mode (explicit scan request)
When the user asks to "scan", "audit", or "hunt for vulnerabilities":
- MUST systematically search the codebase for violations of this specification.
- MUST output findings in a structured format (see §2.3).

Recommended audit order:
1) Build/deploy entry points: `main.go`, `cmd/*`, Dockerfiles, Kubernetes manifests, systemd units, CI workflows.
2) Go toolchain and dependency policy: Go version, modules, `go.mod/go.sum`, proxy/sumdb settings, govulncheck usage.
3) Secret management and configuration loading (env, files, secret stores) + logging patterns.
4) HTTP server configuration (timeouts, body limits, proxy trust, security headers).
5) AuthN/AuthZ boundaries, session/cookie settings, token validation.
6) CSRF defenses for cookie-authenticated state-changing endpoints.
7) Template usage and output encoding (XSS), as well as any "render template from string" behavior (SSTI).
8) File handling (uploads/downloads/path traversal/temp files), static serving.
9) Injection sinks: SQL, OS command execution, SSRF/outbound fetch, open redirects.
10) Concurrency / resource exhaustion (unbounded goroutines/queues, missing timeouts/contexts).
11) Use of `unsafe` / `cgo` / `reflect` in security-sensitive code.
12) Access to debugging/diagnostic endpoints (pprof/expvar/metrics).
13) Cryptographic usage (randomness, password hashing).

--------------------------------------------------------------------

## 2) Definitions and Review Guidance

### 2.1 Untrusted Input (treated as attacker-controlled by default)
Examples:
- `*http.Request` fields: `r.URL.Path`, `r.URL.RawQuery`, `r.Form`, `r.PostForm`, headers, cookies, `r.Body`
- Path parameters from routers (including values extracted from URL paths)
- JSON/XML/YAML bodies, multipart form parts, uploaded files
- Any data from external systems (webhooks, third-party APIs, message queues)
- Any stored user content (DB rows) that originally came from users
- Configuration values that, in some deployments, may be attacker-influenced (headers set by upstream proxies, environment variables in multitenant systems)

### 2.2 State-Changing Request
A request is state-changing if it can create/update/delete data, change auth/session state, cause side effects (purchase, sending email, dispatching a webhook), or initiate privileged actions.

### 2.3 Required Audit-Finding Format
For each issue found, output:

- Rule ID:
- Severity: Critical / High / Medium / Low
- Location: file path + function/handler name + line(s)
- Evidence: exact code/config snippet
- Impact: what can go wrong, who can exploit it
- Fix: safe change (preferably a minimal diff)
- Mitigation: defense-in-depth if an immediate fix is difficult
- False positive notes: what to verify when uncertain (boundary configs, proxy behavior, authentication assumptions)

--------------------------------------------------------------------

## 3) Secure Baseline: Minimum Production Configuration (MUST in production)

This is the minimum "production baseline" that prevents common Go misconfigurations.

### 3.1 Toolchain, Patches, and Dependency Hygiene (MUST)
- MUST use a supported major Go version and keep it on the latest patch releases.
- MUST treat patch releases of the Go standard library as security-relevant (many security fixes ship in stdlib components such as `net/http`, `crypto/*`, parsing packages).
- MUST use Go modules with `go.mod` and `go.sum` committed.
- MUST NOT disable module-authentication mechanisms for public modules (checksum DB) unless you have a controlled and documented replacement.
- MUST run `govulncheck` (source scan and/or binary scan) in CI and remediate findings.

### 3.2 HTTP Server Baseline (MUST for network-facing services)
If the program serves HTTP (directly or via a framework built on `net/http`):
- MUST configure `http.Server` with explicit timeouts and header limits.
- MUST set request-body size limits (global and per-route as needed).
- MUST avoid publicly exposing diagnostic endpoints (pprof/expvar).
- SHOULD set a consistent set of security headers (or verify they are set at the edge).
- MUST set cookie security attributes for all issued cookies.
- SHOULD implement rate limiting and abuse controls for auth and heavy endpoints.

Illustrative baseline template (adapt to your project):
- Create a dedicated mux (avoid implicit globals unless deliberately managed).
- Wrap handlers in: panic-safe error handling, request ID, logging, authentication, and limits.

--------------------------------------------------------------------

## 4) Rules (generation + audit)

Each rule contains: required practice, insecure patterns, detection hints, and remediation.

### GO-DEPLOY-001: Keep Go toolchain and standard library up to date (security releases)
Severity: Medium

NOTE: Updating dependencies and the base Go version may unexpectedly break projects. Focus only on security-critical dependencies, and when you find them, inform the user rather than upgrading automatically.

Required:
- MUST use a supported major Go version and apply patch releases promptly.
- SHOULD treat patch releases as security-relevant even if your application code did not change.

Insecure patterns:
- Production builds pinned to old Go versions without a patching process.
- Docker images such as `golang:1.xx` or custom base images that are rarely updated.
- CI pipelines that intentionally suppress Go updates.

Detection hints:
- Check CI (`.github/workflows`, `gitlab-ci.yml`, etc.) for `go-version:` or toolchain configuration.
- Check Dockerfiles for `FROM golang:` tags.
- Check the `go` directive in `go.mod` and any toolchain pinning.

Fix:
- Upgrade to the latest patch of a supported Go version.
- Add an automated check (CI) that fails if Go is below an approved minimum.

Notes:
- Go regularly publishes minor releases that often include security fixes in stdlib packages.

---

### GO-SUPPLY-001: Go module authentication MUST NOT be disabled for public dependencies
Severity: High

Required:
- MUST keep module checksum verification enabled for public modules.
- SHOULD commit `go.sum` and treat its changes as security-sensitive.
- MUST NOT use insecure module-fetching settings for public modules.
- MAY configure private-module behavior via `GOPRIVATE`/`GONOSUMDB` for private repositories, but do so narrowly and deliberately.

Insecure patterns:
- `GOSUMDB=off` in CI or production-build environments for public modules.
- `GONOSUMDB=*` or excessively wide patterns that effectively disable verification.
- `GOINSECURE=*` or wide `GOINSECURE` patterns for public modules.
- `GOPROXY=direct` everywhere without a clear policy.

Detection hints:
- In build configs, look for `GOSUMDB`, `GONOSUMDB`, `GOINSECURE`, `GOPROXY`, `GOPRIVATE`.
- Look for documentation/scripts recommending disabling the checksum DB "to make builds work".

Fix:
- Restore default verification for public modules.
- For private modules:
  - Set `GOPRIVATE=your.private.domain/*`
  - Configure an internal proxy or direct fetch and limit `GONOSUMDB` to private patterns only.

Notes:
- Disabling checksum verification removes an important integrity layer against targeted attacks or upstream-distribution compromise.

---

### GO-CONFIG-001: Secrets must be externalized and never logged or committed
Severity: High (Critical if credentials are committed)

Required:
- MUST load secrets from environment variables, secret managers, or protected config files with restricted permissions.
- MUST NOT hardcode secrets in Go sources, test fixtures that may reach production, or build args.
- MUST NOT log secrets or full connection strings containing credentials.
- SHOULD fail closed in production if required secrets are missing.

Insecure patterns:
- String constants containing tokens/keys/passwords.
- `.env` files or config files with secrets committed to the repo.
- Logging `os.Environ()`, dumping full configurations, or printing DSNs.

Detection hints:
- Look for suspicious literals (`API_KEY`, `SECRET`, `PASSWORD`, `Authorization:`).
- Inspect configuration loaders and logging statements.
- Inspect CI logs or debug-output paths.

Fix:
- Move secrets to a secret store / environment variables.
- Redact sensitive fields in logs.
- Add secret scanning in CI and in pre-commit hooks.

---

### GO-HTTP-001: HTTP servers MUST set timeouts and MaxHeaderBytes
Severity: High (DoS risk)

Required:
- MUST set: `ReadHeaderTimeout`, and SHOULD set `ReadTimeout`, `WriteTimeout`, `IdleTimeout` depending on the service.
- MUST set `MaxHeaderBytes` with a value reasonable for the application.
- MUST NOT rely on default zero timeouts in production for internet-facing servers.

Insecure patterns:
- `http.ListenAndServe(":8080", handler)` with the default `http.Server` (no explicit timeouts).
- `&http.Server{}` with timeouts at zero.
- Missing `MaxHeaderBytes`.

Detection hints:
- Look for `http.ListenAndServe(`, `ListenAndServeTLS(`, `Server{` and verify configured fields.
- Verify the presence of a reverse proxy; even with a proxy, application-level timeouts still matter.

Fix:
- Use `http.Server{ReadHeaderTimeout: ..., ReadTimeout: ..., WriteTimeout: ..., IdleTimeout: ..., MaxHeaderBytes: ...}`.
- Tune timeouts to the endpoint type (streaming vs. JSON API).

Notes:
- net/http documents that these timeouts exist and that zero/negative values mean "no timeout"; production services should choose explicit values.

---

### GO-HTTP-002: Request body parsing and multipart MUST be size-limited
Severity: Medium (DoS risk; can be High for applications with active file uploads)

Required:
- MUST apply a global request-body size cap for endpoints that accept a body.
- MUST apply strict multipart-upload limits and avoid unbounded form parsing.
- SHOULD apply per-route limits when individual endpoints genuinely need larger bodies.
- SHOULD apply upstream limits (at the proxy) as defense-in-depth.

Insecure patterns:
- Reading `r.Body` via `io.ReadAll(r.Body)` without a size limit.
- Calling `r.ParseMultipartForm(...)` with limits that are too high (or with size control omitted).
- Accepting file uploads without limits on file size, number of parts, or total body size.

Detection hints:
- Look for `io.ReadAll(r.Body)`, `json.NewDecoder(r.Body)`, `ParseMultipartForm`, `FormFile`, `multipart`.
- Look for the absence of `http.MaxBytesReader` or an equivalent per-handler restriction.
- Look for "upload" endpoints and verify limits.

Fix:
- Wrap request bodies in `http.MaxBytesReader(w, r.Body, maxBytes)` before parsing.
- For multipart, set conservative limits and explicitly validate file sizes and the number of parts.
- Set proxy limits (for example, at ingress) in addition to application limits.

Notes:
- There are known classes of vulnerabilities and advisories related to excessive resource consumption when parsing multipart/form data; treat unbounded parsing as a security issue.

---

### GO-DEPLOY-002: Diagnostic endpoints (pprof/expvar/metrics) MUST NOT be publicly accessible
Severity: High

NOTE: This applies only to production configurations. These endpoints are often used for debugging or dev endpoints. When you find them, confirm that they are reachable from the actual production deployment.

Required:
- MUST NOT expose `net/http/pprof` handlers on a public internet listener without strong access control.
- SHOULD run diagnostics on a separate internal listener (loopback / VPC-only) and require authentication.
- MUST analyze what diagnostic endpoints reveal (stack traces, memory, command lines, environment, internal URLs).

Insecure patterns:
- The side-effect import `import _ "net/http/pprof"` in a server binary with a public mux.
- `/debug/pprof/*` accessible without authentication.
- `/debug/vars` (expvar) accessible without authentication.

Detection hints:
- Look for imports of `net/http/pprof` (including blank imports).
- Look for route prefixes `/debug/pprof`, `/debug/vars`.
- Check whether `http.DefaultServeMux` is used and whether debug handlers register globally.

Fix:
- Remove diagnostics from production builds or bind them to an internal listener.
- Add strong authentication/authorization (and ideally network restrictions).

Notes:
- pprof is typically imported for the side effect of registering HTTP handlers under `/debug/pprof/`.

---

### GO-HTTP-003: Reverse-proxy trust and forwarded headers MUST be explicit
Severity: High (correctness of auth, URL generation, logging/auditing)

Required:
- If the application is behind a reverse proxy, MUST determine which proxy is trusted and how client IP/scheme/host are derived.
- MUST NOT trust `X-Forwarded-For`, `X-Forwarded-Proto`, `Forwarded`, or similar headers from the open internet.
- MUST ensure that "secure cookie" logic, redirects, and absolute URL generation do not rely on spoofable headers.

Insecure patterns:
- Using `r.Header.Get("X-Forwarded-For")` as the client IP without verifying the proxy boundary.
- Inferring "is HTTPS" from `X-Forwarded-Proto` without confirming it came from a trusted proxy.
- Using a forwarded `Host` for password-reset links without an allowlist.

Detection hints:
- Look for `X-Forwarded-For`, `X-Forwarded-Proto`, `Forwarded`, `Real-IP`, and any custom "client IP" helpers.
- Inspect ingress/proxy configuration; if it is not visible, flag it as "verify at edge".

Fix:
- Enforce proxy trust both at the edge and in the application:
  - Accept forwarded headers only from known proxy IP ranges.
  - Prefer platform-provided mechanisms where available.
- When generating external links, use a configured canonical origin from an allowlist (rather than the request's Host header).

---

### GO-HTTP-004: Security headers SHOULD be set (in the application or at the edge)
Severity: Medium

Required (typical browser-facing web app):
- SHOULD set:
  - `Content-Security-Policy` (CSP) appropriate to the application. NOTE: The most important header to set is the CSP `script-src`. All other directives are less important and can usually be omitted in favor of development convenience.
  - `X-Content-Type-Options: nosniff`
  - Clickjacking protection (`X-Frame-Options` and/or CSP `frame-ancestors`)
  - `Referrer-Policy` and `Permissions-Policy` where appropriate
- MUST ensure cookies have security attributes (see GO-HTTP-005).

NOTE:
- These headers may be set via a reverse proxy/CDN; if they are not visible in application code, report it as "verify at edge".

Insecure patterns:
- A complete absence of security headers (in the application or at the edge) for a browser-targeted application.
- Missing CSP for applications that render untrusted content.

Detection hints:
- Look for header-setting middleware: `w.Header().Set("Content-Security-Policy", ...)`, etc.
- Look for reverse-proxy configuration that sets headers.

Fix:
- Add centralized header middleware in Go or configure at the edge.
- Keep CSP realistic; avoid `unsafe-inline` where possible.

---

### GO-HTTP-005: Cookies MUST use security attributes in production
Severity: Medium

Required (production, HTTPS):
- MUST set `Secure` for cookies that carry auth/session state. IMPORTANT NOTE: only set `Secure` in production environments where TLS is configured. When running in a local dev environment over HTTP, do not set the `Secure` property on cookies. Set this conditionally based on whether the application is running in production mode. It is also useful to add a property such as `SESSION_COOKIE_SECURE` that can be used to disable `Secure` cookies when testing over HTTP.
- MUST set `HttpOnly` for auth/session cookies.
- SHOULD set `SameSite=Lax` by default (or `Strict` if compatible), and use `None` only when necessary (and only with `Secure`).
- SHOULD set bounded lifetimes (`Max-Age`/`Expires`) appropriate to the application.

Insecure patterns:
- Setting auth/session cookies without `Secure` in HTTPS deployments.
- Cookies without `HttpOnly` for session identifiers.
- `SameSite=None` for cookie-authenticated apps without a strong CSRF strategy.

Detection hints:
- Look for `http.SetCookie`, `&http.Cookie{`, `Set-Cookie`.
- Inspect cookie flags in auth/session code.

Fix:
- Set the correct `http.Cookie` fields and centralize cookie creation.

Notes:
- SameSite is defense-in-depth and does not replace CSRF defenses for cookie-authenticated apps.

---

### GO-HTTP-006: Cookie-authenticated state-changing endpoints MUST be CSRF-protected
Severity: High

- IMPORTANT NOTE: If cookies are not used for authentication (for example, a pure bearer token in the Authorization header without accompanying cookies), CSRF is not a risk for those endpoints.

Required:
- MUST protect all state-changing endpoints (POST/PUT/PATCH/DELETE) that rely on cookies for authentication.
- SHOULD use a well-tested CSRF library/middleware rather than rolling your own.
- MAY use additional defenses (Origin/Referer checks, Fetch Metadata, SameSite cookies), but tokens remain the primary defense for cookie-authenticated apps.
If tokens are impractical or the application is small:
* MUST at minimum require setting a custom header and set the session cookie SESSION_COOKIE_SAMESITE=lax -- this is the strongest method other than form tokens and may be much easier to implement.


Insecure patterns:
- Cookie-authenticated JSON endpoints that change state without CSRF checks.
- Using GET for state-changing actions.

Detection hints:
- Enumerate all non-GET routes and identify their authentication mechanism.
- Look for the use of CSRF middleware; if none is present, treat this as suspicious for browser-targeted apps.

Fix:
- Add CSRF middleware and ensure it covers all state-changing routes.
- If the service is an API for non-browser clients, avoid cookie auth; use Authorization headers.

---

### GO-HTTP-007: CORS must be explicit and least-privilege
Severity: Medium (High when misconfigured with credentials)

Required:
- If CORS is not needed, MUST keep it disabled.
- If CORS is needed:
  - MUST allowlist trusted origins (do not reflect arbitrary origins)
  - MUST be careful with credentialed requests; do not combine wide origins with cookies
  - SHOULD restrict allowed methods/headers

Insecure patterns:
- `Access-Control-Allow-Origin: *` paired with cookies (`Access-Control-Allow-Credentials: true`).
- Reflecting `Origin` without validation.

Detection hints:
- Look for `Access-Control-Allow-` header settings.
- Look for CORS-middleware configuration.

Fix:
- Implement a strict origin allowlist and minimal methods/headers.
- Ensure cookie-authenticated endpoints are not exposed cross-origin without need.

---

### GO-XSS-001: Use html/template and do not bypass auto-escaping with untrusted data
Severity: High

Required:
- MUST use `html/template` for rendering HTML (not `text/template`).
- MUST NOT convert untrusted data into "trusted" template types (`template.HTML`, `template.JS`, `template.URL`, etc.).
- SHOULD keep templates static and developer-controlled; treat dynamic templates as high-risk.
- MUST NOT serve user-uploaded HTML/JS as active content unless this is the explicit intent and a safe sandbox is provided.

Insecure patterns:
- `text/template` used to generate HTML.
- Use of `template.HTML(userInput)` or similar typed wrappers.
- Direct writing of unescaped user content into HTML responses.

Detection hints:
- Look for `text/template`, `template.New(...).Parse(...)` and typed wrappers like `template.HTML(`.
- Inspect handlers that return HTML via string concatenation.

Fix:
- Use `html/template` and pass untrusted data as data, not as markup.
- If you must allow limited HTML, use a vetted HTML sanitizer and still be careful with attributes/URLs.

---

### GO-SSTI-001: Never parse/execute templates from untrusted input (SSTI)
Severity: Critical

Required:
- MUST NOT call `template.Parse` / `template.ParseFiles` / `template.New(...).Parse(...)` on template text influenced by untrusted input.
- MUST treat "user-defined templates" as a high-risk special design:
  - MUST use heavy sandboxing and strict allowlists
  - MUST isolate execution (process/container boundary) if it is genuinely required

Insecure patterns:
- `tmpl := template.Must(template.New("x").Parse(r.FormValue("tmpl")))`
- Reading templates from uploads / DB rows and executing them in the same trust domain as server code.

Detection hints:
- Look for `.Parse(` and trace the source of the template string.
- Look for "custom email templates", "user theme templates", etc.

Fix:
- Replace with safe substitution mechanisms (without code execution).
- If templates must be user-controlled, sandbox aggressively and isolate.

---

### GO-PATH-001: Prevent path traversal and unsafe file serving
Severity: High

Required:
- MUST NOT pass user-supplied paths to `os.Open`, `os.ReadFile`, `http.ServeFile`, or `http.FileServer` without strict validation and base-dir enforcement.
- MUST treat `..`, absolute paths, and OS-specific path tricks as hostile input.
- SHOULD store user uploads outside the static web root; serve them through controlled handlers.
- MUST avoid directory listings for sensitive file trees.

Insecure patterns:
- `http.ServeFile(w, r, r.URL.Query().Get("path"))`
- `os.Open(filepath.Join(baseDir, userPath))` without checking that the result remains inside `baseDir`
- `http.FileServer(http.Dir("."))` serving the project root or user-writable directories

Detection hints:
- Look for `ServeFile(`, `FileServer(`, `http.Dir(`, `os.Open(`, `ReadFile(`, `filepath.Join(`.
- Trace whether path components originate from a request or a DB.

Fix:
- Use an allowlist of file identifiers (for example, DB IDs) mapped to server-side paths.
- Enforce that the path remains inside the base directory after cleaning and joining.
- Serve active formats as downloads (`Content-Disposition: attachment`) unless inline serving is the explicit intent.

---

### GO-UPLOAD-001: File uploads must be validated, stored safely, and served safely
Severity: High

Required:
- MUST enforce upload size limits (application + edge).
- MUST validate file type via an allowlist and content checks (not just extensions).
- MUST store uploads outside executable/static roots when possible.
- SHOULD generate filenames server-side (random IDs) and not trust original names.
- MUST safely serve potentially active formats (download attachment) unless explicitly intended.

Insecure patterns:
- Accepting arbitrary file types and serving them back inline.
- Using a user-supplied filename as the storage path.
- Missing size/type validation.

Detection hints:
- Look for `multipart`, `FormFile`, `ParseMultipartForm`, `io.Copy` to disk.
- Verify where files are stored and how they are served.

Fix:
- Implement allowlist validation + safe storage + safe serving.
- Add scanning/quarantine processes where appropriate.

---

### GO-INJECT-001: Prevent SQL injection (parameterized queries / ORM)
Severity: High

Required:
- MUST use parameterized queries or an ORM that parameterizes under the hood.
- MUST NOT build SQL via string concatenation, `fmt.Sprintf`, or string interpolation with untrusted input.

Insecure patterns:
- `fmt.Sprintf("SELECT ... WHERE id=%s", r.URL.Query().Get("id"))`
- `query := "UPDATE users SET role='" + role + "' WHERE id=" + id`

Detection hints:
- Grep for `SELECT`, `INSERT`, `UPDATE`, `DELETE` and check how query strings are built.
- Trace untrusted data into `db.Query`, `db.Exec`, `QueryRow`, etc.

Fix:
- Replace with placeholders (`?`, `$1`, etc.) and pass parameters separately.
- Validate and check ID types before use.

---

### GO-INJECT-002: Prevent OS command injection; avoid the shell with untrusted input
Severity: Critical-High (depending on exposure)

Required:
- MUST avoid running external commands with attacker-controlled strings.
- If a subprocess is necessary:
  - MUST use `exec.CommandContext` with an argument list (not `sh -c`).
  - MUST NOT pass untrusted input to a shell (`bash -c`, `sh -c`, PowerShell).
  - SHOULD use strict allowlists for any variable component (subcommand, flags, filenames).
- MUST assume that CLI tools may interpret attacker-controlled arguments as flags or special values.

Insecure patterns:
- `exec.Command("sh", "-c", userString)`
- `exec.Command("bash", "-c", fmt.Sprintf("tool %s", user))`
- Invoking the shell purely for glob expansion of user-supplied globs.

Detection hints:
- Look for `os/exec`, `exec.Command(`, `CommandContext(`, `"sh"`, `"bash"`, `"-c"`.
- Trace untrusted input into the command name/arguments.

Fix:
- Use library APIs instead of subprocesses.
- Hardcode the command and validate/allowlist arguments.
- If the shell cannot be avoided, escape rigorously and treat it as high-risk (preferably avoid).

Notes:
- Go's `os/exec` package deliberately does not invoke a shell; introducing `sh -c` reintroduces shell-injection risk.

---

### GO-SSRF-001: Prevent SSRF in outbound HTTP requests
Severity: Medium (High in cloud/LAN environments)

- Note: For small isolated projects this is less important. It is especially important when deployed in a LAN or alongside other services on the same server.

Required:
- MUST treat outbound requests to user-supplied URLs as high-risk.
- SHOULD allowlist hosts/domains for any user-influenced URL fetch.
- SHOULD block access to localhost/private IP ranges/link-local and cloud metadata endpoints.
- MUST restrict schemes to `http`/`https` (no `file:`, `gopher:`, etc.).
- MUST set client timeouts and limit redirects.

Insecure patterns:
- `http.Get(r.URL.Query().Get("url"))`
- "URL preview" / "webhook test" endpoints that fetch arbitrary URLs.

Detection hints:
- Look for `http.Get`, `client.Do`, and URL values derived from requests/DB.
- Identify features that fetch remote resources.

Fix:
- Parse URLs strictly; enforce scheme and hostname allowlists.
- Resolve DNS and apply IP-range restrictions (mind DNS rebinding).
- Set timeouts, disable redirects when not needed, and limit response sizes.

---

### GO-HTTPCLIENT-001: Outbound HTTP clients MUST set timeouts and close response bodies
Severity: High (DoS and resource exhaustion)

Required:
- MUST set an overall timeout when using `http.Client` (or equivalent per-request deadlines via context + transport timeouts).
- MUST ensure `resp.Body.Close()` is called for all successful requests (typically `defer resp.Body.Close()` immediately after the error check).
- SHOULD limit response-body reads (do not `io.ReadAll` unbounded responses).
- SHOULD limit redirects for security-sensitive fetches (SSRF, auth flows).

Insecure patterns:
- Using `http.DefaultClient` / `http.Get` for user-influenced addresses without a timeout policy.
- Missing `defer resp.Body.Close()`, leading to resource leaks.
- `io.ReadAll(resp.Body)` without a limit.

Detection hints:
- Look for `http.Get(`, `http.Post(`, `client := &http.Client{}` without `Timeout`, `client.Do(` without close calls.
- Look for `io.ReadAll(resp.Body)`.

Fix:
- Use a configured client with timeouts.
- Always close response bodies.
- Use bounded readers (`io.LimitReader`) for large/untrusted responses.

Notes:
- The net/http package exports `DefaultClient` as a zero-valued `http.Client`, which easily produces "no timeout" behavior unless configured.

---

### GO-REDIRECT-001: Prevent open redirect
Severity: Medium (can be High in auth flows)

Required:
- MUST validate redirect targets derived from untrusted input (`next`, `redirect`, `return_to`).
- SHOULD prefer same-site relative paths only.
- SHOULD fall back to a safe default if validation fails.

Insecure patterns:
- `http.Redirect(w, r, r.URL.Query().Get("next"), http.StatusFound)` without validation.

Detection hints:
- Look for `http.Redirect(` and inspect the source of the location.

Fix:
- Allowlist internal paths or known domains.
- Reject absolute URLs unless explicitly required and on the allowlist.

---

### GO-CRYPTO-001: Cryptographic randomness MUST come from crypto/rand
Severity: High (Critical when used for auth/session tokens or keys)

Required:
- MUST use `crypto/rand` for:
  - session identifiers, password-reset tokens, API keys, CSRF tokens, nonces
  - encryption keys, signing keys, and salts where appropriate
- MUST NOT use `math/rand` for any security-sensitive value.
- SHOULD use built-in helpers that produce appropriately strong tokens when available.

Insecure patterns:
- `math/rand.Seed(time.Now().UnixNano())` followed by token generation for auth or sessions.
- Using UUIDv4-like constructions built on `math/rand`.

Detection hints:
- Look for `math/rand`, `rand.Seed`, `rand.Intn` in code that touches auth/session/token flows.
- Look for custom token generators.

Fix:
- Switch to `crypto/rand` (`rand.Reader`, `rand.Read`, or safe token helpers).
- Ensure sufficient entropy and use URL-safe encoding.

Notes:
- The crypto/rand package provides secure-randomness APIs and token-generation helpers.

---

### GO-AUTH-001: Password storage MUST use adaptive hashing (bcrypt/argon2id) and constant-time comparisons
Severity: High

Required:
- MUST hash passwords with an adaptive password-hashing function (bcrypt or argon2id).
- MUST NOT store passwords in cleartext or with reversible encryption.
- MUST compare secrets in constant time when appropriate (tokens, MACs, API keys) to reduce timing leaks.
- SHOULD ensure password policies do not exceed algorithm limits (for example, bcrypt has an input-length limit; handle long passphrases accordingly).

Insecure patterns:
- `sha256(password)` stored as a password hash.
- Storing passwords in cleartext.
- Comparing secrets via `==` in timing-sensitive contexts.

Detection hints:
- Look for `sha1`, `sha256`, `md5` applied to passwords.
- Look for use of `bcrypt`/`argon2`; if absent, treat with suspicion.
- Look for `==` comparisons of tokens/API keys.

Fix:
- Use `bcrypt.GenerateFromPassword` / `CompareHashAndPassword`, or argon2id with recommended parameters.
- Use constant-time comparison helpers when comparing MACs/tokens.

Notes:
- Go provides bcrypt in `golang.org/x/crypto/bcrypt`, and constant-time comparisons in `crypto/subtle`.

---

### GO-CONC-001: Data races and concurrency hazards MUST be treated as security-relevant
Severity: Medium-High (depending on what the races affect)

Required:
- MUST run tests with the race detector (`go test -race`) in CI for security-sensitive services.
- MUST fix detected races; do not suppress them without strong justification.
- SHOULD treat shared mutable state in handlers as high-risk; either synchronize or avoid shared mutability.

Insecure patterns:
- Global maps/slices mutated from multiple goroutines without a mutex.
- Caches or auth/session state in globals without concurrency protection.
- Racing access to authorization state (which can lead to bypasses or inconsistent checks).

Detection hints:
- Look for `var someMap = map[...]...` used in handlers.
- Look for the absence of `sync.Mutex`, `sync.Map`, channels, or other synchronization.
- Verify that CI uses `-race` and that it executes the relevant tests.

Fix:
- Add proper synchronization or redesign to avoid shared mutable state.
- Add race tests and run them continuously.

Notes:
- Go's race detector finds only the races that occur in executed code paths; improve test coverage and, when possible, run realistic workloads with `-race`.

---

### GO-UNSAFE-001: Use of unsafe/cgo MUST be minimized and audited as memory-unsafe code
Severity: High (Critical in high-risk code)

Required:
- SHOULD avoid importing `unsafe` in application code unless absolutely necessary.
- When `unsafe` is used, MUST treat it as "manual memory safety" requiring careful review and test coverage.
- When `cgo` is used, MUST treat the C/C++ boundary as memory-unsafe; apply secure coding practices on the C side and isolate where possible.

Insecure patterns:
- Wide use of `unsafe.Pointer` casts in parsing, serialization, auth, or networking code.
- `cgo` used for parsing or security boundaries without sandboxing.

Detection hints:
- Look for `import "unsafe"`, `unsafe.Pointer`, `// #cgo`, `import "C"`.
- Prioritize review where unsafe touches untrusted input.

Fix:
- Replace unsafe/cgo usage with safe stdlib alternatives where possible.
- Isolate unsafe code in small, well-tested modules with fuzz/race tests.

Notes:
- The unsafe package explicitly provides operations that bypass Go's type-safety guarantees.

--------------------------------------------------------------------

## 5) Practical Scanning Heuristics (how to "hunt")

When actively scanning, use these high-signal patterns:

Toolchain and dependencies:
- `FROM golang:` (Dockerfiles), `go-version:` (CI), `toolchain go` (go.mod), pinned old versions
- `GOSUMDB=off`, `GOINSECURE`, `GONOSUMDB`, `GOPROXY=direct`
- `replace` directives in `go.mod` pointing to forks/paths
- absence of `govulncheck` in CI

HTTP-server hardening:
- `http.ListenAndServe(`, `ListenAndServeTLS(`, `&http.Server{` without timeouts
- `ReadHeaderTimeout: 0`, `ReadTimeout: 0`, `WriteTimeout: 0`, `IdleTimeout: 0`, missing `MaxHeaderBytes`

Body parsing / DoS:
- `io.ReadAll(r.Body)`, `json.NewDecoder(r.Body)` without a size limit
- `ParseMultipartForm`, `FormFile`, `multipart.NewReader` without explicit limits
- Absence of `http.MaxBytesReader`

Debug exposure:
- `import _ "net/http/pprof"`
- `/debug/pprof`, `/debug/vars`

Templates / XSS / SSTI:
- `text/template` used for HTML output
- `template.HTML(`, `template.JS(`, `template.URL(` with user data
- `.Parse(` on user-supplied strings

Files:
- `http.ServeFile(` with a user-supplied path
- `http.FileServer(http.Dir(` pointing at the repo root or uploads
- `os.Open(filepath.Join(base, user))` without containment checks

Injection:
- SQL built via `fmt.Sprintf`, string concatenation near `db.Query/Exec`
- `exec.Command("sh","-c", ...)`, `exec.Command("bash","-c", ...)`

SSRF / outbound HTTP:
- `http.Get(userURL)`, `client.Do(req)` where the URL comes from a request/DB
- Missing client timeout, missing `resp.Body.Close()`, unbounded `io.ReadAll(resp.Body)`

Cryptography:
- `math/rand` in token/session generation
- `InsecureSkipVerify: true`
- Password hashing via `sha256`/`md5` instead of bcrypt/argon2

Concurrency:
- Shared maps/slices mutated from handlers without locks
- CI without `go test -race`

Always try to confirm:
- data origin (untrusted vs. trusted)
- sink type (template/SQL/subprocess/files/http)
- presence of defensive controls (limits, validation, allowlists, middleware, network controls)

--------------------------------------------------------------------

## 6) Sources (accessed 2026-01-28)

Primary Go documentation:
- Go Security Policy -- https://go.dev/doc/security/policy
- Go Release History (security fixes in patch releases) -- https://go.dev/doc/devel/release
- Go 1.25 Release Notes -- https://go.dev/doc/go1.25
- net/http (server timeouts, MaxHeaderBytes, DefaultClient) -- https://pkg.go.dev/net/http
- html/template (auto-escaping and trusted-template assumptions) -- https://pkg.go.dev/html/template
- crypto/tls (default MinVersion values, InsecureSkipVerify warnings) -- https://pkg.go.dev/crypto/tls
- crypto/rand (secure randomness, token helpers) -- https://pkg.go.dev/crypto/rand
- crypto/subtle (constant-time comparisons) -- https://pkg.go.dev/crypto/subtle
- os/exec (no-shell-by-default; command-execution guidance) -- https://pkg.go.dev/os/exec
- unsafe (type-safety bypass) -- https://go.dev/src/unsafe/unsafe.go
- net/http/pprof (debug endpoints) -- https://pkg.go.dev/net/http/pprof
- cmd/go (module authentication via go.sum/checksum DB; env vars such as GOINSECURE) -- https://pkg.go.dev/cmd/go
- Module Mirror and Checksum Database Launched (Go blog) -- https://go.dev/blog/module-mirror-launch
- govulncheck documentation -- https://pkg.go.dev/golang.org/x/vuln/cmd/govulncheck
- Go Race Detector documentation -- https://go.dev/doc/articles/race_detector
- bcrypt (password hashing) -- https://pkg.go.dev/golang.org/x/crypto/bcrypt
- Go vulnerability example (multipart resource consumption) -- https://pkg.go.dev/vuln/GO-2023-1569

OWASP Cheat Sheet Series (general web application security):
- Session Management -- https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- CSRF Prevention -- https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- SSRF Prevention -- https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- XSS Prevention -- https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- HTTP Security Response Headers -- https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html
