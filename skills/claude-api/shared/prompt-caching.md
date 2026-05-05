# Prompt Caching — Design and Optimization

This file describes how to design prompt-construction code for effective caching. For language-specific syntax, see the `## Prompt Caching` section in each language's README or single-document file.

## One Invariant That Drives Everything Else

**Prompt caching is a prefix match. Any change anywhere in the prefix invalidates everything after it.**

The cache key is derived from the exact bytes of the rendered prompt up to each `cache_control` breakpoint. A one-byte difference at position N — a timestamp, a reordered JSON key, a different tool in the list — invalidates the cache for every breakpoint at positions ≥ N.

Render order: `tools` → `system` → `messages`. A breakpoint on the last system block caches tools and system together.

Design your prompt-construction path around this constraint. Get the order right and most caching works for free. Get it wrong and no amount of `cache_control` markers will help.

---

## Workflow for Optimizing Existing Code

When asked to add or optimize caching:

1. **Trace the prompt-construction path.** Find where `system`, `tools`, and `messages` are constructed. Identify every input that flows into them.
2. **Classify each input by stability:**
   - Never changes → belongs at the start of the prompt, before any breakpoint
   - Changes per session → belongs after the global prefix, cached per session
   - Changes per turn → belongs at the end, after the last breakpoint
   - Changes per request (timestamps, UUIDs, random IDs) → **eliminate or move to the very end**
3. **Verify the rendered order matches the stability order.** Stable content must physically precede unstable content. If a timestamp is interpolated into the system prompt header, everything after it is uncacheable regardless of markers.
4. **Place breakpoints at stability boundaries.** See placement patterns below.
5. **Audit for silent invalidators.** See the anti-pattern table.

---

## Placement Patterns

### Large System Prompt Shared Across Many Requests

Put a breakpoint on the last system text block. If tools are present, they render before system — a marker on the last system block caches tools + system together.

```json
"system": [
  {"type": "text", "text": "<large shared prompt>", "cache_control": {"type": "ephemeral"}}
]
```

### Multi-Turn Conversations

Put a breakpoint on the last content block of the most recently appended turn. Each subsequent request reuses the entire prior conversation prefix. Earlier breakpoints remain valid read points, so hits accumulate incrementally as the conversation grows.

```json
// Last content block of the last user turn
messages[-1].content[-1].cache_control = {"type": "ephemeral"}
```

### Shared Prefix, Varying Suffix

Many requests share a large fixed preamble (few-shot examples, retrieved docs, instructions) but differ in the final question. Put the breakpoint at the end of the **shared** part, not at the end of the entire prompt — otherwise each request writes a separate cache entry and nothing is ever read.

```json
"messages": [{"role": "user", "content": [
  {"type": "text", "text": "<shared context>", "cache_control": {"type": "ephemeral"}},
  {"type": "text", "text": "<varying question>"}  // no marker — differs every time
]}]
```

### Prompts That Change from the Start Every Time

Don't cache. If the first 1K tokens differ on every request, there's no reusable prefix. Adding `cache_control` only pays the cache-write premium with zero reads. Leave it unmarked.

---

## Architectural Guidance

These decisions matter more than marker placement. Fix them first.

**Keep the system prompt frozen.** Don't interpolate "current date: X", "mode: Y", "user name: Z" into the system prompt — that sits at the start of the prefix and invalidates everything downstream. Inject dynamic context as a user or assistant message later in `messages`. A message at turn 5 doesn't invalidate anything before turn 5.

**Don't change tools or model mid-conversation.** Tools render at position 0; adding, removing, or reordering a tool invalidates the entire cache. Same for switching models (caches are model-bound). If you need "modes," don't swap the tool set — give Claude a tool that records a mode transition, or pass the mode as message content. Serialize tools deterministically (sort by name).

**Fork operations must reuse the parent's exact prefix.** Side computations (summarization, compaction, sub-agents) often launch a separate API call. If the fork rebuilds `system` / `tools` / `model` with any difference, it misses the parent's cache entirely. Copy the parent's `system`, `tools`, and `model` verbatim, then append fork-specific content at the end.

---

## Silent Invalidators

When reviewing code, look for these patterns inside anything that feeds the prompt prefix:

| Pattern | Why it breaks caching |
|---|---|
| `datetime.now()` / `Date.now()` / `time.time()` in the system prompt | The prefix changes on every request |
| `uuid4()` / `crypto.randomUUID()` / request IDs early in content | Same — every request is unique |
| `json.dumps(d)` without `sort_keys=True` / iterating a `set` | Non-deterministic serialization → prefix bytes differ |
| f-string interpolating session/user ID into the system prompt | Per-user prefix; no cross-user sharing |
| Conditional system sections (`if flag: system += ...`) | Each flag combination is a separate prefix |
| `tools=build_tools(user)` where the set differs per user | Tools render at position 0; nothing caches across users |

Fix by moving the dynamic part after the last breakpoint, making it deterministic, or removing it if it carries no load.

---

## API Reference

```json
"cache_control": {"type": "ephemeral"}              // 5-minute TTL (default)
"cache_control": {"type": "ephemeral", "ttl": "1h"} // 1-hour TTL
```

- Maximum **4** `cache_control` breakpoints per request.
- Goes on any content block: system text blocks, tool definitions, message content blocks (`text`, `image`, `tool_use`, `tool_result`, `document`).
- Top-level `cache_control` on `messages.create()` is automatically placed on the last cacheable block — the simplest option when fine-grained placement isn't needed.
- The minimum cacheable prefix depends on the model. Shorter prefixes are silently not cached even with a marker — no error, just `cache_creation_input_tokens: 0`:

| Model | Minimum |
|---|---:|
| Opus 4.7, Opus 4.6, Opus 4.5, Haiku 4.5 | 4096 tokens |
| Sonnet 4.6, Haiku 3.5, Haiku 3 | 2048 tokens |
| Sonnet 4.5, Sonnet 4.1, Sonnet 4, Sonnet 3.7 | 1024 tokens |

A 3K-token prompt caches on Sonnet 4.5 but is silently not cached on Opus 4.7.

**Economics:** cache reads cost ~0.1× the base input price. Cache writes cost **1.25× for 5-minute TTL, 2× for 1-hour TTL**. The break-even point depends on TTL: with the 5-minute TTL, two requests break even (1.25× + 0.1× = 1.35× vs. 2× without cache); with the 1-hour TTL, you need at least three requests (2× + 0.2× = 2.2× vs. 3× without cache). The 1-hour TTL keeps entries alive between gaps in irregular traffic, but the doubled write cost means you need more reads to pay for it.

---

## Verifying Cache Hits

The response's `usage` object reports cache activity:

| Field | Meaning |
|---|---|
| `cache_creation_input_tokens` | Tokens written to cache in this request (you paid the ~1.25× write premium) |
| `cache_read_input_tokens` | Tokens served from cache in this request (you paid ~0.1×) |
| `input_tokens` | Tokens processed at full price (not from cache) |

If `cache_read_input_tokens` is zero on repeated requests with identical prefixes, a silent invalidator is at work; compare the rendered prompt bytes between two requests to find it.

**`input_tokens` is only the uncached remainder.** Total prompt size = `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. If your agent has been running for hours but `input_tokens` shows 4K, the rest was served from cache — check the sum, not a single field.

Per-language access: `response.usage.cache_read_input_tokens` (Python/TS/Ruby), `$message->usage->cacheReadInputTokens` (PHP), `resp.Usage.CacheReadInputTokens` (Go/C#), `.usage().cacheReadInputTokens()` (Java).

---

## Invalidation Hierarchy

Not every parameter change invalidates everything. The API has three cache levels, and changes invalidate only their level and below:

| Change | Tools cache | System cache | Messages cache |
|---|:---:|:---:|:---:|
| Tool definitions (add/remove/reorder) | ❌ | ❌ | ❌ |
| Model switch | ❌ | ❌ | ❌ |
| `speed`, web-search, citations toggle | ✅ | ❌ | ❌ |
| System prompt content | ✅ | ❌ | ❌ |
| `tool_choice`, images, `thinking` enable/disable | ✅ | ✅ | ❌ |
| Message content | ✅ | ✅ | ❌ |

Implication: you can change `tool_choice` per request or toggle `thinking` without losing the tools+system cache. Don't worry about it — only tool-definition and model changes force a full rebuild.

---

## 20-Block Lookback Window

Each breakpoint looks back **at most 20 content blocks** for a previous cache entry. If a single turn appends more than 20 blocks (common in agentic loops with many tool_use/tool_result pairs), the next request's breakpoint won't find the previous cache and will silently miss.

Solution: place an intermediate breakpoint roughly every 15 blocks in long turns, or place the marker on a block that sits within 20 of the last cached block of the prior turn.

---

## Parallel-Request Timing

A cache write becomes readable only after the first response **begins streaming**. N parallel requests with identical prefixes all pay full price — none can read what the others are still writing.

For fan-out patterns: send 1 request, wait for the first streamed token (not the full response), then launch the remaining N−1. They will read the cache that the first one just wrote.
