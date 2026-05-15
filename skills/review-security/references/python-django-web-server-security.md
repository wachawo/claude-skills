# Django (Python) Web Application Security Specification (Django 6.0.x, Python 3.x)

This document is intended as a **security specification** that supports:

1. **Secure-by-default code generation** for new Django code.
2. **Security review and vulnerability hunting** in existing Django code (both passive "spot issues while working" mode and active "scan the repo and report findings" mode).

The document is intentionally written as a set of **normative requirements** ("MUST/SHOULD/MAY") together with **audit rules** (what bad patterns look like, how to detect them, and how to fix or mitigate them).

---

## 0) Safety, Boundaries, and Anti-Abuse Constraints (MANDATORY)

* MUST NOT request, output, log, or commit secrets (API keys, passwords, private keys, session cookies, `SECRET_KEY`, `SECRET_KEY_FALLBACKS`, DB passwords).
* MUST NOT "fix" security by disabling protections (for example, removing `CsrfViewMiddleware`, sprinkling `@csrf_exempt`, weakening `ALLOWED_HOSTS` to `['*']`, disabling `SecurityMiddleware`, disabling template autoescape, or disabling permission checks).
* MUST provide **evidence-based findings** when auditing: cite file paths, code snippets, and concrete configuration values that justify the claim.
* MUST be honest about uncertainty: if a defense may exist in the infrastructure (reverse proxy, WAF, CDN, ingress controller), report it as "not visible in application code; verify at runtime / in edge configuration".
* MUST keep fixes consistent with Django's intended security model: prefer Django's built-in features (middleware, auth, forms, ORM) over hand-rolled security logic when possible. Django's deployment checklist and system checks are part of this intended model. ([Django Project][1])

---

## 1) Modes of Operation

### 1.1 Generation Mode (default)

When asked to write new Django code or modify existing code:

* MUST honor every **MUST** requirement of this specification.
* SHOULD honor every **SHOULD** requirement unless the user explicitly states otherwise.
* MUST prefer secure-by-default Django APIs and proven libraries over hand-rolled security code.
* MUST avoid introducing new risky "sinks" (dynamic template rendering from untrusted strings, unsafe redirects, unsafe file serving, shell execution, raw SQL formatting via strings, SSRF-capable fetch functions from untrusted input).

### 1.2 Passive Review Mode (always on while editing)

When working anywhere in a Django repository (even if the user did not request a security scan):

* MUST "spot" violations of this specification in edited or adjacent code.
* SHOULD raise issues as they arise, with a brief explanation and a safe fix.

### 1.3 Active Audit Mode (explicit scan request)

When the user asks to "scan", "audit", or "hunt for vulnerabilities":

* MUST systematically search the codebase for violations of this specification.
* MUST output findings in a structured format (see §2.3).

Recommended audit order:

1. Deployment entry points (ASGI/WSGI), Dockerfile, Procfile, systemd units, platform manifests.
2. `settings.py` and environment-specific settings modules.
3. Middleware order and enabled defenses.
4. Authentication/authorization (login, session management, permissions, admin).
5. CSRF protection and state-changing endpoints.
6. Templates and XSS.
7. File handling (uploads/downloads/static/media) and path traversal.
8. Injection classes (SQL, command execution, unsafe deserialization).
9. Outbound requests (SSRF).
10. Redirect handling (open redirects) + CORS + security headers (CSP, HSTS, etc.).
11. Dependencies/pinning and patch posture.

---

## 2) Definitions and Review Guidance

### 2.1 Untrusted Input (treat as attacker-controlled until proven otherwise)

Examples:

* `request.GET`, `request.POST`, `request.FILES`
* `request.body`, JSON bodies (for example, `json.loads(request.body)`), DRF `request.data`
* URL path parameters (for example, `<int:id>`, `<slug:...>`)
* `request.headers` / `request.META` (including `HTTP_HOST`, `HTTP_ORIGIN`, `HTTP_REFERER`, `HTTP_X_FORWARDED_*`)
* `request.COOKIES`
* Any data from external systems (webhooks, third-party APIs, message queues)
* Any stored content that originally came from users (DB rows, cached content, file uploads)

Django explicitly emphasizes "never trust user-controlled data" and recommends using forms/validation. ([Django Project][2])

### 2.2 State-Changing Request

A request is state-changing if it can create/update/delete data, change auth/session state, cause side effects (purchase, sending email, dispatching a webhook), or initiate privileged actions.

### 2.3 Required Audit-Finding Format

For each issue found, output:

* Rule ID:
* Severity: Critical / High / Medium / Low
* Location: file path + function/class/view name + line(s)
* Evidence: exact code/config snippet
* Impact: what can go wrong, who can exploit it
* Fix: safe change (preferably a minimal diff)
* Mitigation: defense-in-depth if an immediate fix is difficult
* False positive notes: what to verify when uncertain

---

## 3) Secure Baseline: Minimum Production Configuration (MUST in production)

This is the minimum "production baseline" that prevents common Django misconfigurations. Django provides a "Deployment checklist" and recommends running `manage.py check --deploy` against production settings. ([Django Project][1])

### 3.1 Settings Management Pattern (SHOULD)

* SHOULD use environment-based configuration (or a secret manager) so that production settings are not hardcoded.
* MUST treat sensitive settings as confidential (for example, `SECRET_KEY`, DB passwords) and keep them out of version control. The Django checklist explicitly recommends loading `SECRET_KEY` from env or a file, not hardcoding it. ([Django Project][1])
* SHOULD separate dev and prod settings modules, with secure defaults for production (fail-closed if a critical setting is missing). ([Django Project][1])

### 3.2 Minimum Baseline Goals (production)

* MUST NOT use `manage.py runserver` as a production entry point; use a production-ready WSGI or ASGI server. ([Django Project][1])
* MUST set `DEBUG = False` in production. ([Django Project][1])
* MUST set a strong, secret `SECRET_KEY` and keep it secret; MAY use `SECRET_KEY_FALLBACKS` for safe rotation. ([Django Project][1])
* MUST set `ALLOWED_HOSTS` to expected hosts (no wildcards unless you implement your own host validation). ([Django Project][1])
* MUST enforce HTTPS in authenticated areas (ideally site-wide for any application with login) and set `CSRF_COOKIE_SECURE=True` and `SESSION_COOKIE_SECURE=True` when HTTPS is in use. ([Django Project][1])
* SHOULD enable key `SecurityMiddleware` headers/settings: HSTS, Referrer-Policy, COOP, nosniff, SSL redirect (with proper proxy configuration). ([Django Project][3])
* MUST treat user uploads as untrusted; ensure the web server never interprets them as executable content; keep `MEDIA_ROOT` separate from `STATIC_ROOT`. ([Django Project][1])

---

## 4) Rules (generation + audit)

Each rule contains: required practice, insecure patterns, detection hints, and remediation guidance.

### DJANGO-DEPLOY-001: Do not use the Django dev server in production

Severity: High (in production)

Required:

* MUST NOT deploy `manage.py runserver` as a production server.
* MUST run behind a production-ready WSGI or ASGI server. ([Django Project][1])

Insecure patterns:

* Production documentation/scripts using `python manage.py runserver 0.0.0.0:8000`.
* Docker `CMD`/entrypoint uses `runserver`.
* Kubernetes/Procfile/systemd units invoking `runserver`.

Detection hints:

* Look for `manage.py runserver`, `runserver 0.0.0.0`, `--insecure`.
* Inspect Docker `CMD/ENTRYPOINT`, Procfile, systemd units, Helm charts.

Fix:

* Use a production server (WSGI/ASGI), as recommended by Django's deployment checklist. ([Django Project][1])

Note:

* `runserver` is appropriate for local development. Flag it only when used as a production entry point.

---

### DJANGO-DEPLOY-002: `DEBUG` MUST be disabled in production

Severity: High

Required:

* MUST set `DEBUG = False` in production.
* MUST treat any mechanism that exposes debug pages/tracebacks to untrusted users as a critical information disclosure. The Django checklist explicitly warns that `DEBUG=True` leaks source-code fragments, local variables, settings, and more. ([Django Project][1])

Insecure patterns:

* `DEBUG = True` in production settings.
* The default environment yields `DEBUG=True` unless explicitly overridden.

Detection hints:

* Look for `DEBUG = True`, `DEBUG=os.environ.get(..., True)`, `DJANGO_DEBUG`, `.env` files.
* Look for "production" settings modules importing dev defaults.

Fix:

* Set `DEBUG=False` in prod settings; use explicit configuration via the environment.
* Ensure error reporting flows through safe logging/monitoring rather than debug pages. ([Django Project][1])

---

### DJANGO-CONFIG-001: `SECRET_KEY` must be strong, secret, and rotated safely

Severity: High (Critical when missing in production with signing/sessions)

Required:

* MUST set a large random `SECRET_KEY` in production and keep it secret. ([Django Project][1])
* MUST NOT commit it to the repository or print/log it. ([Django Project][1])
* SHOULD load it from env or a file/secret store (not hardcode it). ([Django Project][1])
* MAY rotate keys via `SECRET_KEY_FALLBACKS` to avoid invalidating all signed data at once; MUST remove old keys from fallbacks promptly. ([Django Project][1])

Insecure patterns:

* Hardcoded `SECRET_KEY = "..."` in the repository for production.
* `SECRET_KEY` reused across environments.
* `SECRET_KEY_FALLBACKS` indefinitely retaining long-expired keys.

Detection hints:

* Look for `SECRET_KEY =`, `SECRET_KEY_FALLBACKS`, committed `.env` files, `print(settings.SECRET_KEY)`.

Fix:

* Load from a secret manager / environment variable.
* When rotating:

  * Set the new `SECRET_KEY`
  * Temporarily keep old key(s) in `SECRET_KEY_FALLBACKS`
  * Remove the old key(s) after the rotation window. ([Django Project][1])

---

### DJANGO-HOST-001: The Host header must be validated (`ALLOWED_HOSTS` strict)

Severity: Medium

Required:

* MUST set `ALLOWED_HOSTS` in production to the expected domains/hosts. ([Django Project][1])
* MUST NOT set `ALLOWED_HOSTS = ['*']` in production unless you implement your own robust `Host` validation (Django warns that wildcards require your own validation to avoid CSRF-class attacks). ([Django Project][1])
* SHOULD configure the front-end web server to reject unknown hosts early (defense-in-depth). ([Django Project][1])

Insecure patterns:

* `ALLOWED_HOSTS = ['*']` (or env that expands to `*`) in production.
* `ALLOWED_HOSTS = []` with `DEBUG=False` (the site does not start, or misconfigured deploys try to work around it).

Detection hints:

* Look for `ALLOWED_HOSTS`.
* Inspect platform environment settings overriding `ALLOWED_HOSTS`.

Fix:

* Set `ALLOWED_HOSTS = ['example.com', 'www.example.com', ...]` for prod.
* Keep dev hosts separate.

Notes:

* Django uses the Host header to build URLs; spoofed Host values can lead to CSRF, cache poisoning, and poisoned email links (Django's security documentation mentions this). ([Django Project][2])

---

### DJANGO-HTTPS-001: When using TLS, cookie transport must be secured

Severity: High (Critical for authenticated applications)

NOTE: only apply when TLS is enabled; otherwise non-TLS apps will break.

When TLS is in use:
* MUST set:

  * `CSRF_COOKIE_SECURE = True` ([Django Project][1])
  * `SESSION_COOKIE_SECURE = True` ([Django Project][1])
* SHOULD consider enabling:

  * `SECURE_SSL_REDIRECT = True` (with proper proxy configuration) ([Django Project][3])
  * HSTS via `SECURE_HSTS_SECONDS` (+ includeSubDomains/preload as appropriate). ([Django Project][3])

Insecure patterns:

* Login pages over HTTP, or mixed HTTP/HTTPS sharing the same session cookie.
* `CSRF_COOKIE_SECURE=False` or `SESSION_COOKIE_SECURE=False` in production HTTPS.
* HSTS enabled incorrectly (can break the site for an extended period).

Detection hints:

* Check `settings.py` for `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`.
* Check proxy/ingress configuration for HTTP-to-HTTPS redirect behavior.

Fix:

* Enable HTTPS redirect and secure cookies.
* Add HSTS carefully (start with a small value, verify, then increase). Django warns that misconfiguration can break the site for the duration of the HSTS validity. ([Django Project][3])

---

### DJANGO-PROXY-001: Reverse-proxy trust must be configured correctly (`SECURE_PROXY_SSL_HEADER`)

Severity: Medium (when behind a TLS-terminating proxy)

Required:

* If the application is behind a reverse proxy that terminates TLS, MUST configure Django so that `request.is_secure()` reflects the *external* scheme; otherwise CSRF and other logic may break. Django documents the use of `SECURE_PROXY_SSL_HEADER` for this. ([Django Project][3])
* MUST set `SECURE_PROXY_SSL_HEADER` only if you control the proxy (or have guarantees) and it strips spoofed inbound headers. Django explicitly warns that misconfiguration can compromise security and lists the required preconditions. ([Django Project][3])

Insecure patterns:

* `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` in an environment where the proxy does not strip user-supplied `X-Forwarded-Proto`.
* Infinite redirect loops after setting `SECURE_SSL_REDIRECT=True` (often a sign of incorrect HTTPS detection at the proxy). ([Django Project][3])

Detection hints:

* Look for `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`.
* Verify ingress/proxy behavior for clearing forwarded headers.

Fix:

* Set `SECURE_PROXY_SSL_HEADER` only if the proxy correctly clears and sets the header (per Django's documented preconditions). ([Django Project][3])

---

### DJANGO-SESS-001: Session cookies must use safe attributes in production

Severity: Medium (only when TLS is enabled)

Required (production, HTTPS):

* MUST set `SESSION_COOKIE_SECURE=True` (transmit over HTTPS only). ([Django Project][3])
* MUST keep `SESSION_COOKIE_HTTPONLY=True` (Django defaults to `True`). ([Django Project][3])
* SHOULD keep `SESSION_COOKIE_SAMESITE='Lax'` (Django default is `Lax`) unless a justified cross-site flow requires `None`. ([Django Project][3])
* SHOULD avoid setting `SESSION_COOKIE_DOMAIN` unless cross-subdomain cookies are genuinely required (whole-subdomain cookies expand the attack surface).

Insecure patterns:

* `SESSION_COOKIE_SECURE=False` in production HTTPS.

IMPORTANT NOTE: only set `Secure` in production environments where TLS is configured. When working in a local dev environment over HTTP, do not set the `Secure` property on cookies. Set this conditionally based on whether the application is running in production mode. Also include a property such as `SESSION_COOKIE_SECURE` that can be used to disable `Secure` cookies when testing over HTTP.

* `SESSION_COOKIE_HTTPONLY=False`.
* `SESSION_COOKIE_SAMESITE=None` combined with cookie-authenticated state-changing endpoints (heightened CSRF risk).

Detection hints:

* Look for `SESSION_COOKIE_` settings, `response.set_cookie(..., httponly=..., secure=..., samesite=...)`.

Fix:

* Set the listed values explicitly in production settings.
* Verify compatibility with authentication flows. ([Django Project][3])

---

### DJANGO-SESS-002: CSRF cookie settings must be intentional (HttpOnly has trade-offs)

Severity: Medium

Required:

* SHOULD set `CSRF_COOKIE_SECURE=True` when using HTTPS/TLS. ([Django Project][3])
* SHOULD keep `CSRF_COOKIE_SAMESITE='Lax'` unless a cross-site requirement applies. Django's default is `Lax`. ([Django Project][3])
* MAY set `CSRF_COOKIE_HTTPONLY=True` (default `False`) if the frontend does not need to read the CSRF cookie. If you enable this, your JS must read the CSRF token from the DOM (Django documents this). ([Django Project][3])

Insecure patterns:

* `CSRF_COOKIE_SECURE=False` in production HTTPS/TLS.
* Setting `CSRF_COOKIE_HTTPONLY=True` while keeping the "read csrftoken cookie from JS" pattern (which breaks CSRF for AJAX).
* `CSRF_COOKIE_SAMESITE=None` without a clear reason.

Detection hints:

* Look for `CSRF_COOKIE_` settings.
* Look for JS using `document.cookie` to obtain `csrftoken`.

Fix:

* Align cookie settings with the way the CSRF token is obtained (cookie or DOM), as Django describes. ([Django Project][4])

---

### DJANGO-CSRF-001: Cookie-authenticated state-changing requests MUST be CSRF-protected

Severity: High

Required:

* MUST keep `django.middleware.csrf.CsrfViewMiddleware` enabled (it is enabled by default). ([Django Project][4])
* MUST include `{% csrf_token %}` in internal POST forms; MUST NOT include it in forms that POST to external URLs (Django warns this leaks the token). ([Django Project][4])
* MUST protect all state-changing endpoints (POST/PUT/PATCH/DELETE) that rely on cookies for authentication.
* For AJAX/SPA calls, MUST send the CSRF token via the `X-CSRFToken` header (or the configured header name), as documented. ([Django Project][4])
* MUST be very careful with `@csrf_exempt` and use it only when strictly necessary; if used, MUST replace CSRF with a suitable alternative (for example, request signing for webhooks). Django explicitly warns about `csrf_exempt`. ([Django Project][2])

Insecure patterns:

* `CsrfViewMiddleware` missing from `MIDDLEWARE`.
* `@csrf_exempt` on general authenticated views.
* POST/PUT/PATCH/DELETE endpoints with session authentication and no CSRF tokens.
* Using GET for state-changing actions (amplifies CSRF risk).

Detection hints:

* Inspect `MIDDLEWARE` in `settings.py` for the presence of `CsrfViewMiddleware` and its order (Django notes it must come before any middleware that assumes CSRF has been processed). ([Django Project][4])
* Look for `csrf_exempt`, `csrf_protect`, `ensure_csrf_cookie`.
* Enumerate URL patterns for non-GET methods; confirm CSRF coverage.

Fix:

* Re-enable `CsrfViewMiddleware`, add CSRF tokens to forms, and handle the AJAX header.
* For caching decorators: if you cache a view that needs CSRF tokens, apply `@csrf_protect` as Django documents, so the response is not cached without the CSRF cookie/Vary headers. ([Django Project][4])

Notes:

* When deployed with HTTPS, Django's CSRF middleware also checks the Referer header for same-origin (Django's security docs mention this). ([Django Project][2])

---

### DJANGO-XSS-001: Prevent reflected/stored XSS in templates and HTML generation

Severity: High

Required:

* MUST rely on Django's template autoescape (safe-by-default) for HTML templates. Django's security docs emphasize that Django templates escape dangerous characters but have caveats. ([Django Project][2])
* MUST NOT broadly disable autoescape (`{% autoescape off %}`) unless the content is trusted or has been safely sanitized. ([Django Project][5])
* MUST NOT mark untrusted content as safe:

  * Avoid `mark_safe(...)` on user data.
  * Avoid `|safe` on user-controlled content.
* MUST be aware of HTML-context pitfalls (for example, unquoted attributes); Django explicitly shows an example where escaping does not protect in an unquoted attribute context. ([Django Project][2])
* SHOULD prefer safe-HTML-construction helpers (for example, `format_html`) over manual concatenation that risks missing escaping. ([Django Project][6])

Insecure patterns:

* `{% autoescape off %}{{ user_input }}{% endautoescape %}`
* `{{ user_input|safe }}`
* `mark_safe(request.GET["q"])`
* Injection into unquoted attributes: `<style class={{ var }}>...` (Django's own example). ([Django Project][2])

Detection hints:

* In templates, look for `|safe`, `autoescape off`, `safeseq`.
* In Python, look for `mark_safe`, `SafeString`, or direct concatenation of HTML with values from request/DB.
* Review any code that returns `HttpResponse(user_value)` where `user_value` contains HTML.

Fix:

* Remove unsafe markings; sanitize only when strictly necessary (with an allowlist HTML sanitizer).
* Quote attributes and do not place untrusted values in dangerous contexts.
* Add CSP as defense-in-depth (see DJANGO-CSP-001). ([Django Project][2])

---

### DJANGO-TEMPLATE-001: Never render untrusted template source strings

Severity: High-Critical (depending on context and surface area)

Required:

* MUST NOT render templates where the template source string is influenced by untrusted input (request, user content, DB rows editable by untrusted users).
* MUST treat "template-from-string" patterns as dangerous, even though Django templates are more constrained than some other engines: they can still leak data from the context, bypass escaping, and create XSS or content injection.

Insecure patterns:

* `Template(request.GET["tmpl"]).render(Context(...))`
* Storing user templates in the DB and rendering them with normal privileges/context.

Detection hints:

* Look for `django.template.Template(`, `Engine.from_string`, `.render(Context(` with non-constant strings.
* Trace where the template string comes from (admin panels, DB, uploads, requests).

Fix:

* Replace with non-executing formatting (for example, `string.Template`, explicit placeholders) or a strict allowlist rendering model.
* If user-defined templates *must* be supported, isolate strongly (separate service/tenant context, strict allowlists, and assume bypasses are possible).

---

### DJANGO-SQL-001: Prevent SQL injection (use the ORM or parameterized raw SQL)

Severity: High

Required:

* MUST use the Django ORM/querysets for normal DB access; Django notes that querysets are parameterized and protected against SQL injection in typical use. ([Django Project][2])
* MUST be very careful with raw SQL; when using `raw()`, `cursor.execute()`, `extra()`, or `RawSQL`, MUST pass parameters separately (for example, `params=`) and MUST NOT interpolate untrusted input into SQL via strings. Django's raw SQL documentation warns that user parameters must be escaped via `params`. ([Django Project][7])
* MUST NOT quote placeholders in SQL templates (Django's documentation explicitly warns that quoting `%s` makes the query unsafe). ([Django Project][8])
* SHOULD avoid `extra()` and `RawSQL` unless necessary; Django's security docs urge caution. ([Django Project][2])

Insecure patterns:

* `cursor.execute(f"SELECT ... WHERE id={request.GET['id']}")`
* `Model.objects.raw("... %s" % user_input)` (string formatting)
* `extra(where=[f"headline='{q}'"])`
* Quoted placeholders: `WHERE othercol = '%s'` (explicitly documented as unsafe). ([Django Project][8])

Detection hints:

* Grep for `.raw(`, `.extra(`, `RawSQL(`, `connection.cursor()`, `.execute(`.
* Grep for SQL keywords (`SELECT`, `UPDATE`, `DELETE`, `INSERT`) inside Python strings.
* Trace untrusted inputs into these call sites.

Fix:

* Prefer ORM queries.
* If raw SQL is unavoidable, use parameters (`params`, DB-API param binding) and do not quote placeholders. ([Django Project][7])

---

### DJANGO-CMD-001: Prevent OS command injection

Severity: Critical-High (depending on exposure)

Required:

* MUST avoid executing system commands with input that may be attacker-influenced.
* If a subprocess is necessary:

  * MUST pass arguments as a list (not a shell string).
  * MUST NOT use `shell=True` with content that may be attacker-influenced.
  * SHOULD use strict allowlists for variable components.
* SHOULD prefer pure Python libraries over invoking the shell.

Insecure patterns:

* `os.system(request.GET["cmd"])`
* `subprocess.run(f"convert {path}", shell=True)` where `path` is user-controlled.

Detection hints:

* Look for `os.system`, `subprocess`, `Popen`, `shell=True`.
* Trace request/DB inputs into these calls.

Fix:

* Replace with library APIs; if unavoidable, hardcode the executable and validate parameters via an allowlist.

---

### DJANGO-UPLOAD-001: File uploads must be validated, stored safely, and served safely

Severity: High

Required:

* MUST treat all user uploads as untrusted. Django explicitly warns: "Media files are uploaded by your users. They're untrusted!" ([Django Project][1])
* MUST ensure the web server never interprets user uploads as executable code (for example, do not allow uploaded `.php` or HTML to be executed/rendered inline as active content). ([Django Project][1])
* MUST enforce size limits (at minimum at the web server; Django's security docs recommend limiting upload sizes at the server to prevent DoS). ([Django Project][2])
* SHOULD validate file types via allowlists and content checks (not just extensions).
* SHOULD store uploads outside the application code directory and outside any static root.
* SHOULD consider serving uploads from a separate top/second-level domain to reduce same-origin impact; Django's security docs recommend a separate domain and note that a subdomain may be insufficient for some defenses. ([Django Project][2])
* MUST account for polyglot upload risks: Django documents the case where HTML can be uploaded "as an image" using a valid PNG header (and may be served as HTML depending on the web server). ([Django Project][2])

Insecure patterns:

* Serving uploads inline with `text/html` or without forced download for potentially active formats.
* Allowlisting uploads by extension only.
* Storing uploads inside the static root or code root.

Detection hints:

* Look for `request.FILES`, `FileField`, `ImageField`, upload forms/views.
* Inspect upload-serving paths and Nginx/Apache configuration (media handlers).
* Check `MEDIA_URL`, `MEDIA_ROOT`, and static configuration.

Fix:

* Configure the web server to serve uploads as inert bytes (no execution), and consider forcing `Content-Disposition: attachment` for risky types.
* Use a separate domain for user content where justified. ([Django Project][2])

---

### DJANGO-PATH-001: Prevent path traversal and unsafe file serving (static/media separation)

Severity: High

Required:

* MUST NOT treat user input as a filesystem path for reads/writes/serving.
* MUST keep `MEDIA_ROOT` and `STATIC_ROOT` distinct; Django's settings documentation explicitly warns that they must have different values to avoid security implications. ([Django Project][3])
* SHOULD prefer using Django's storage APIs by server-side identifier rather than accepting arbitrary relative paths from users.

Insecure patterns:

* `open(os.path.join(MEDIA_ROOT, request.GET["path"]))`
* Download endpoints that accept `?file=../../...`-style parameters.
* Misconfigured `MEDIA_ROOT == STATIC_ROOT`.

Detection hints:

* Grep for `open(`, `Path(`, `os.path.join(` used with values from the request.
* Inspect `MEDIA_ROOT`, `STATIC_ROOT` in settings. ([Django Project][3])

Fix:

* Use server-side IDs mapped to known files.
* Separate static and media and ensure the web server treats media as untrusted. ([Django Project][3])

---

### DJANGO-REDIRECT-001: Prevent open redirects (`next`, `return_to`, `redirect`)

Severity: Medium (High when combined with authentication flows)

Required:

* MUST validate redirect targets derived from untrusted input (for example, `next`, `return_to`).
* SHOULD restrict to same-site relative paths or an allowlist of hosts/schemes.
* SHOULD use Django's safe-URL helpers (for example, `django.utils.http.url_has_allowed_host_and_scheme`) instead of hand-rolled parsing.

Insecure patterns:

* `return redirect(request.GET.get("next"))` without validation.
* Redirect allowlists implemented via naive string checks.

Detection hints:

* Look for `redirect(` and trace the origin of the target.
* Look for parameters named `next`, `return_to`, `redirect`, `url`.

Fix:

* Validate via allowlists and fall back to a safe internal default on validation failure.
* Ensure host validation through `ALLOWED_HOSTS` remains strict (see DJANGO-HOST-001). ([Django Project][3])

---

### DJANGO-HEADERS-001: Enable important security headers (SecurityMiddleware + clickjacking protection)

Severity: Medium-High

Required:

* SHOULD use `django.middleware.security.SecurityMiddleware` and configure it appropriately (production) for:

  * `X-Content-Type-Options: nosniff` (Django setting `SECURE_CONTENT_TYPE_NOSNIFF`, default `True`). ([Django Project][3])
  * `Referrer-Policy` (Django setting `SECURE_REFERRER_POLICY`, default `'same-origin'`). ([Django Project][3])
  * COOP (Django setting `SECURE_CROSS_ORIGIN_OPENER_POLICY`, default `'same-origin'`). ([Django Project][3])
  * HTTPS redirects and HSTS as appropriate (see DJANGO-HTTPS-001). ([Django Project][3])
* SHOULD enable clickjacking protection via the X-Frame-Options middleware; Django's security docs strongly recommend this for sites that do not need third-party embedding. ([Django Project][2])

Insecure patterns:

* SecurityMiddleware missing.
* No clickjacking protection (or it is globally disabled) without an explicit embedding requirement.
* Overly broad framing permissions for sensitive endpoints.

Detection hints:

* Inspect `MIDDLEWARE` for SecurityMiddleware and XFrameOptionsMiddleware.
* Look for per-endpoint disabling of framing/CSRF defenses.

Fix:

* Add/enable middleware and configure parameters intentionally. ([Django Project][3])

NOTE:

* Some headers may be set at the edge (CDN/reverse proxy). If they are not visible in application code, mark as "verify at edge".

---

### DJANGO-CSP-001: Deploy a Content Security Policy (CSP) as defense-in-depth

Severity: Medium (High for applications rendering untrusted content)

NOTE: the most important CSP directive to set is `script-src`. Other directives are less important and can usually be omitted in favor of development convenience.

Required:

* SHOULD deploy CSP to mitigate XSS and content-injection classes; Django's security docs recommend CSP and note that this is a new feature in Django 6.0. ([Django Project][2])
* MUST understand CSP's limitations:

  * Avoid excluding routes from CSP coverage; Django warns that an unprotected page can undermine protected ones because of the same-origin policy. ([Django Project][2])
* MAY start with `SECURE_CSP_REPORT_ONLY` for safe iteration (Django provides report-only support). ([Django Project][3])

Insecure patterns:

* CSP missing in applications that render user-controlled content.
* CSP that excludes "just a few pages" (weakening overall protection), especially pages with any injection surface. ([Django Project][2])
* CSP using overly permissive directives (for example, ubiquitous `unsafe-inline`) without justification.

Detection hints:

* Look for `SECURE_CSP`, `SECURE_CSP_REPORT_ONLY`, and CSP-middleware configuration.
* Check reverse proxy/CDN configuration for CSP headers.

Fix:

* Roll out a realistic CSP, ideally report-only first, then enforce. ([Django Project][3])

---

### DJANGO-AUTH-001: Password storage must use Django's secure hashers; password policy must be configured

Severity: High

Required:

* MUST use Django's built-in password hashing (never store in plaintext or with reversible encryption).
* SHOULD prefer modern hashers and keep defaults up to date; Django documents `PASSWORD_HASHERS` and includes modern options (Argon2, bcrypt, scrypt, PBKDF2 variants). ([Django Project][3])
* SHOULD configure `AUTH_PASSWORD_VALIDATORS` (default empty) for production password policy. ([Django Project][3])

Insecure patterns:

* Hand-rolled password storage or hashing.
* Plaintext passwords in DB fields.
* No password validation in consumer applications.

Detection hints:

* Look for `.set_password(` usage versus manual hashing.
* Inspect settings for `PASSWORD_HASHERS` and `AUTH_PASSWORD_VALIDATORS`. ([Django Project][3])

Fix:

* Use Django's auth user model APIs.
* Enable password validators appropriate to the product's risk profile. ([Django Project][3])

---

### DJANGO-AUTHZ-001: Authorization must be explicit and consistent

Severity: High

Required:

* MUST enforce authorization checks for every privileged action (view, modify, admin-level operations).
* MUST NOT rely on UI-only restrictions (for example, hiding buttons) without server-side permission checks.
* SHOULD use Django's permission/group patterns and object-level authorization where applicable.

Insecure patterns:

* Views assuming "user is logged in" = "user can perform the action".
* Missing authorization checks on update/delete endpoints.

Detection hints:

* Enumerate state-changing views; verify they check ownership/permissions.
* Look for use of `is_authenticated` only or `is_staff` only without object-level access checks.

Fix:

* Add explicit permission checks and tests for unauthorized access.

---

### DJANGO-ADMIN-001: The Django admin must be treated as a high-value target

Severity: High

Required:

* MUST ensure the admin is protected by strong authentication and HTTPS-only transport (see DJANGO-HTTPS-001). ([Django Project][1])
* SHOULD restrict admin exposure (network allowlists, VPN, SSO, or additional authentication factors) when possible.
* SHOULD review installed admin extensions and third-party apps for XSS/CSRF risks.

Insecure patterns:

* Admin exposed to the internet with weak authentication.
* Admin served over HTTP.

Detection hints:

* Look for `admin.site.urls` in `urlpatterns`.
* Check deployment configuration for IP allowlists or auth gateways.

Fix:

* Add network controls and enforce HTTPS.

---

### DJANGO-LOG-001: Logging and error reporting must not leak secrets

Severity: Medium-High

Required:

* MUST NOT log secrets (including `SECRET_KEY`, session cookies, auth headers, password-reset tokens).
* MUST configure production logging deliberately; Django's deployment checklist explicitly requires reviewing logging before production. ([Django Project][1])
* MUST ensure `DEBUG=False` in production so that exceptions are not displayed with sensitive context. ([Django Project][1])

Insecure patterns:

* Logging full request headers or cookies in production.
* Printing settings dictionaries.
* Debug error pages.

Detection hints:

* Inspect `LOGGING` configuration; look for middleware logging request headers/cookies.
* Grep for `print(settings` / `logging.info(request.META)` patterns.

Fix:

* Redact sensitive values; log IDs rather than secrets.
* Use structured logging and a safe error-monitoring tool. ([Django Project][1])

---

### DJANGO-SUPPLY-001: Dependency and patch hygiene (Django + security-critical deps)

Severity: Medium (High for known-vulnerable versions)

Required:

* SHOULD pin and regularly update Django and security-critical dependencies.
* MUST respond promptly to Django security releases.

Detection hints:

* Inspect `requirements.txt`, lockfiles, build images.
* Identify the Django version; compare against the latest supported release (the Django downloads page lists the current stable and supported branches). ([Django Project][9])

Fix:

* Update to patched versions; add regression tests for previously vulnerable classes.

---

## 5) Practical Scanning Heuristics (how to "hunt")

When actively scanning, use these high-signal patterns:

* Deploy/dev server:

  * `manage.py runserver`, `runserver 0.0.0.0`, `--insecure` ([Django Project][1])
* Debug / settings:

  * `DEBUG = True` ([Django Project][1])
  * `SECRET_KEY =`, `SECRET_KEY_FALLBACKS` ([Django Project][1])
* Host validation:

  * `ALLOWED_HOSTS = ['*']` ([Django Project][3])
* HTTPS and proxy:

  * `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_PROXY_SSL_HEADER` ([Django Project][3])
* Cookies / sessions:

  * `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE` ([Django Project][3])
  * `CSRF_COOKIE_SECURE`, `CSRF_COOKIE_HTTPONLY`, `CSRF_COOKIE_SAMESITE` ([Django Project][3])
* CSRF bypass:

  * `csrf_exempt`, missing `CsrfViewMiddleware`, POST forms without `{% csrf_token %}` ([Django Project][4])
* XSS:

  * `|safe`, `autoescape off`, `mark_safe(`, HTML-string concatenation ([Django Project][5])
* SQL injection:

  * `.raw(`, `.extra(`, `RawSQL(`, `cursor.execute(` with formatted SQL strings ([Django Project][7])
* User uploads / media:

  * `request.FILES`, `MEDIA_ROOT`, `MEDIA_URL`, serving media inline; `MEDIA_ROOT == STATIC_ROOT` ([Django Project][1])
* Redirects:

  * `redirect(request.GET.get("next"))` patterns; missing allowlist validation
* Security headers and CSP:

  * Missing `SecurityMiddleware`, missing X-Frame-Options protection, missing `SECURE_CSP` adoption (where appropriate) ([Django Project][2])

Always try to confirm:

* data origin (trusted/untrusted)
* sink type (template/SQL/subprocess/files/redirect/http)
* presence of defenses (middleware, validation, allowlists, authorization checks)
* whether headers/security controls are set in the application or at the edge

---

## 6) Sources (accessed 2026-01-27)

Primary Django documentation:

```text
- Django Downloads (current stable & supported branches): https://www.djangoproject.com/download/
- Django 6.0 Release Notes: https://docs.djangoproject.com/en/6.0/releases/6.0/
- Django: Deployment checklist (incl. check --deploy, runserver warning, HTTPS/cookies guidance): https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/
- Django: Settings reference (SecurityMiddleware settings, cookies, SECRET_KEY_FALLBACKS, CSP settings): https://docs.djangoproject.com/en/6.0/ref/settings/
- Django: Security in Django (XSS/CSRF/SQLi/clickjacking/HTTPS/host header validation/uploads/CSP): https://docs.djangoproject.com/en/6.0/topics/security/
- Django: CSRF how-to (middleware, csrf_token usage, AJAX header patterns, csrf_exempt cautions): https://docs.djangoproject.com/en/6.0/howto/csrf/
- Django: Performing raw SQL queries (parameterization guidance): https://docs.djangoproject.com/en/6.0/topics/db/sql/
- Django: QuerySet API reference (extra() cautions; "do not quote placeholders" guidance): https://docs.djangoproject.com/en/6.0/ref/models/querysets/
- Django: Template built-ins (autoescape tag): https://docs.djangoproject.com/en/6.0/ref/templates/builtins/
- Django: Template language reference (turning off autoescape & risks): https://docs.djangoproject.com/en/6.0/ref/templates/language/
- Django: Utilities reference (e.g., format_html): https://docs.djangoproject.com/en/6.0/ref/utils/
```

OWASP:

```text
- OWASP Cheat Sheet Series: Django Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Django_Security_Cheat_Sheet.html
```

[1]: https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/ "https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/"
[2]: https://docs.djangoproject.com/en/6.0/topics/security/ "Security in Django | Django documentation | Django"
[3]: https://docs.djangoproject.com/en/6.0/ref/settings/ "Settings | Django documentation | Django"
[4]: https://docs.djangoproject.com/en/6.0/howto/csrf/ "How to use Django's CSRF protection | Django documentation | Django"
[5]: https://docs.djangoproject.com/en/6.0/ref/templates/builtins/ "https://docs.djangoproject.com/en/6.0/ref/templates/builtins/"
[6]: https://docs.djangoproject.com/en/6.0/ref/utils/ "https://docs.djangoproject.com/en/6.0/ref/utils/"
[7]: https://docs.djangoproject.com/en/6.0/topics/db/sql/ "https://docs.djangoproject.com/en/6.0/topics/db/sql/"
[8]: https://docs.djangoproject.com/en/6.0/ref/models/querysets/ "https://docs.djangoproject.com/en/6.0/ref/models/querysets/"
[9]: https://www.djangoproject.com/download/ "Download Django | Django"
