# HTTP Error Code Reference

This file describes the HTTP error codes returned by the Claude API, their typical causes, and how to handle them. For language-specific error-handling examples, see the `python/` or `typescript/` folders.

## Error Code Summary

| Code | Error type              | Retry | Typical cause                            |
| ---- | ----------------------- | ----- | ---------------------------------------- |
| 400  | `invalid_request_error` | No    | Invalid request format or parameters     |
| 401  | `authentication_error`  | No    | Invalid or missing API key               |
| 403  | `permission_error`      | No    | API key lacks required permissions       |
| 404  | `not_found_error`       | No    | Invalid endpoint or model ID             |
| 413  | `request_too_large`     | No    | Request exceeds size limits              |
| 429  | `rate_limit_error`      | Yes   | Too many requests                        |
| 500  | `api_error`             | Yes   | Anthropic-side issue                     |
| 529  | `overloaded_error`      | Yes   | API temporarily overloaded               |

## Detailed Error Information

### 400 Bad Request

**Causes.**

- Malformed JSON in the request body
- Missing required parameters (`model`, `max_tokens`, `messages`)
- Wrong parameter types (e.g., a string where an integer is expected)
- Empty messages array
- Messages don't alternate user/assistant

**Example error:**

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "messages: roles must alternate between \"user\" and \"assistant\""
  },
  "request_id": "req_011CSHoEeqs5C35K2UUqR7Fy"
}
```

**What to do.** Validate the request structure before sending. Check that:

- `model` is a valid model ID
- `max_tokens` is a positive integer
- The `messages` array is non-empty and roles alternate correctly

---

### 401 Unauthorized

**Causes.**

- Missing `x-api-key` or `Authorization` header
- Invalid API key format
- Revoked or deleted API key

**What to do.** Make sure the `ANTHROPIC_API_KEY` environment variable is set correctly.

---

### 403 Forbidden

**Causes.**

- The API key doesn't have access to the requested model
- Organization-level restrictions
- Calling beta features without beta access

**What to do.** Check API key permissions in the Console. You may need a different API key or to request access to specific features.

---

### 404 Not Found

**Causes.**

- Typo in the model ID (e.g., `claude-sonnet-4.6` instead of `claude-sonnet-4-6`)
- Using a deprecated model ID
- Wrong API endpoint

**What to do.** Use exact model IDs from the model documentation. Aliases are supported (e.g., `claude-opus-4-7`).

---

### 413 Request Too Large

**Causes.**

- Request body exceeds the maximum size
- Too many input tokens
- Image data too large

**What to do.** Reduce the size of the input — trim conversation history, compress/resize images, or split large documents into chunks.

---

### 400 Validation Errors

Some 400 errors are specifically parameter-validation errors:

- `max_tokens` exceeds the model's limit
- Invalid `temperature` (must be 0.0–1.0)
- `budget_tokens` >= `max_tokens` in extended thinking
- Invalid tool definition schema

**Opus 4.7-specific 400s:**

- `temperature`, `top_p`, `top_k` are removed — sending any of them returns 400. Drop the parameter; see `shared/model-migration.md` → Per-SDK Syntax Reference.
- `thinking: {type: "enabled", budget_tokens: N}` is removed — sending it returns 400. Use `thinking: {type: "adaptive"}`.

**Common error with extended thinking on older models (Opus 4.6 and earlier):**

```
# Wrong: budget_tokens must be < max_tokens
thinking: budget_tokens=10000, max_tokens=1000  → Error!

# Correct
thinking: budget_tokens=10000, max_tokens=16000
```

---

### 429 Rate Limited

**Causes.**

- Requests per minute (RPM) exceeded
- Tokens per minute (TPM) exceeded
- Tokens per day (TPD) exceeded

**Headers worth checking:**

- `retry-after`: how many seconds to wait before retrying
- `x-ratelimit-limit-*`: your limits
- `x-ratelimit-remaining-*`: remaining quota

**What to do.** The Anthropic SDKs automatically retry on 429 and 5xx errors with exponential backoff (default `max_retries=2`). For custom retry behavior, see the language-specific error-handling examples.

---

### 500 Internal Server Error

**Causes.**

- Temporary Anthropic service issue
- Bug in API processing

**What to do.** Retry with exponential backoff. If the error is persistent, check [status.anthropic.com](https://status.anthropic.com).

---

### 529 Overloaded

**Causes.**

- High API demand
- Service capacity reached

**What to do.** Retry with exponential backoff. Consider falling back to a different model (Haiku is typically less loaded), spreading requests over time, or queueing requests.

---

## Common Errors and Fixes

| Error                                           | Code             | What to do                                              |
| ----------------------------------------------- | ---------------- | ------------------------------------------------------- |
| `temperature`/`top_p`/`top_k` on Opus 4.7       | 400              | Remove the parameter (see `shared/model-migration.md`)  |
| `budget_tokens` on Opus 4.7                     | 400              | Use `thinking: {type: "adaptive"}`                      |
| `budget_tokens` >= `max_tokens` (older models)  | 400              | Make sure `budget_tokens` < `max_tokens`                |
| Typo in model ID                                | 404              | Use a valid ID, e.g. `claude-opus-4-7`                  |
| First message is `assistant`                    | 400              | The first message must be `user`                        |
| Consecutive messages with the same role         | 400              | Alternate `user` and `assistant`                        |
| API key in code                                 | 401 (leaked key) | Use an environment variable                             |
| Need custom retry logic                         | 429/5xx          | The SDK retries automatically; configure `max_retries`  |

## Typed SDK Exceptions

**Always use the typed exception classes from the SDK** instead of checking message text. Each HTTP error code maps to a class:

| HTTP Code | TypeScript Class                  | Python Class                      |
| --------- | --------------------------------- | --------------------------------- |
| 400       | `Anthropic.BadRequestError`       | `anthropic.BadRequestError`       |
| 401       | `Anthropic.AuthenticationError`   | `anthropic.AuthenticationError`   |
| 403       | `Anthropic.PermissionDeniedError` | `anthropic.PermissionDeniedError` |
| 404       | `Anthropic.NotFoundError`         | `anthropic.NotFoundError`         |
| 429       | `Anthropic.RateLimitError`        | `anthropic.RateLimitError`        |
| 500+      | `Anthropic.InternalServerError`   | `anthropic.InternalServerError`   |
| Any       | `Anthropic.APIError`              | `anthropic.APIError`              |

```typescript
// ✅ Correct: use typed exceptions
try {
  const response = await client.messages.create({...});
} catch (error) {
  if (error instanceof Anthropic.RateLimitError) {
    // Handle rate limiting
  } else if (error instanceof Anthropic.APIError) {
    console.error(`API error ${error.status}:`, error.message);
  }
}

// ❌ Wrong: don't check error messages with string matching
try {
  const response = await client.messages.create({...});
} catch (error) {
  const msg = error instanceof Error ? error.message : String(error);
  if (msg.includes("429") || msg.includes("rate_limit")) { ... }
}
```

All exception classes inherit from `Anthropic.APIError`, which has a `status` property. Use `instanceof` checks from most specific to least specific (e.g., check `RateLimitError` before `APIError`).
