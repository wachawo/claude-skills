---
name: claude-api
description: "Build, debug, and optimize Claude API / Anthropic SDK applications. Applications built with this skill should include prompt caching. Also handles migrating existing Claude API code between Claude model versions (4.5 → 4.6, 4.6 → 4.7, retired-model replacements). TRIGGERS when: code imports `anthropic`/`@anthropic-ai/sdk`; user asks about the Claude API, Anthropic SDK, or Managed Agents; user adds/modifies/tunes a Claude feature (caching, thinking, compaction, tool use, batch, files, citations, memory) or model (Opus/Sonnet/Haiku) in a file; questions about prompt caching / cache hit rate in an Anthropic SDK project. SKIP: file imports `openai`/another provider's SDK, filename like `*-openai.py`/`*-generic.py`, provider-neutral code, general programming/ML."
---

# Building LLM Applications on Claude

This skill helps you build LLM applications on Claude. Pick the appropriate surface based on your needs, identify the project language, then read the corresponding language-specific documentation.

## Before You Start

Scan the target file (or, if there is no target file, the prompt and project) for markers of non-Anthropic providers — `import openai`, `from openai`, `langchain_openai`, `OpenAI(`, `gpt-4`, `gpt-5`, filenames like `agent-openai.py` or `*-generic.py`, or any explicit instruction to keep the code provider-neutral. If anything is found, stop and tell the user that this skill produces Claude/Anthropic SDK code; ask whether they want to switch the file to Claude or want a non-Claude implementation. Do not edit a non-Anthropic file with Anthropic SDK calls.

## Output Requirement

When the user asks you to add, change, or implement a Claude feature, your code must call Claude through one of:

1. **The official Anthropic SDK** for the project's language (`anthropic`, `@anthropic-ai/sdk`, `com.anthropic.*`, etc.). This is the default whenever a supported SDK exists for the project.
2. **Raw HTTP** (`curl`, `requests`, `fetch`, `httpx`, etc.) — only when the user explicitly asks for cURL/REST/raw HTTP, the project is a shell/cURL project, or the language has no official SDK.

Never mix the two — do not reach for `requests`/`fetch` in a Python or TypeScript project just because it seems easier. Never fall back to OpenAI-compatible shims.

**Never guess SDK usage.** Function names, class names, namespaces, method signatures, and import paths must come from explicit documentation — either from the `{lang}/` files in this skill, the official SDK repositories, or the documentation links listed in `shared/live-sources.md`. If a needed binding is not explicitly documented in the skill files, WebFetch the corresponding SDK repository from `shared/live-sources.md` before writing code. Do not infer Ruby/Java/Go/PHP/C# APIs from cURL forms or another language's SDK.

## Defaults

Unless the user requests otherwise:

For the Claude model version, use Claude Opus 4.7, accessible via the exact model string `claude-opus-4-7`. By default, use adaptive thinking (`thinking: {type: "adaptive"}`) for anything even remotely complex. Finally, by default use streaming for any request that may involve long input, long output, or large `max_tokens` — this prevents request timeouts. Use the SDK's `.get_final_message()` / `.finalMessage()` helper to get the full response if you don't need to handle individual stream events.

---

## Subcommands

If the User Request at the bottom of this prompt is a bare subcommand string (no prose), inspect every **Subcommands** table in this document — including any in sections appended below — and follow the action from the Action column directly. This lets users invoke specific flows via `/claude-api <subcommand>`. If no table in the document matches, handle the request as ordinary prose.


---

## Language Detection

Before reading code examples, determine which language the user is working in:

1. **Look at project files** to infer the language:

   - `*.py`, `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` → **Python** — read from `python/`
   - `*.ts`, `*.tsx`, `package.json`, `tsconfig.json` → **TypeScript** — read from `typescript/`
   - `*.js`, `*.jsx` (no `.ts` files) → **TypeScript** — JS uses the same SDK, read from `typescript/`
   - `*.java`, `pom.xml`, `build.gradle` → **Java** — read from `java/`
   - `*.kt`, `*.kts`, `build.gradle.kts` → **Java** — Kotlin uses the Java SDK, read from `java/`
   - `*.scala`, `build.sbt` → **Java** — Scala uses the Java SDK, read from `java/`
   - `*.go`, `go.mod` → **Go** — read from `go/`
   - `*.rb`, `Gemfile` → **Ruby** — read from `ruby/`
   - `*.cs`, `*.csproj` → **C#** — read from `csharp/`
   - `*.php`, `composer.json` → **PHP** — read from `php/`

2. **If multiple languages are detected** (e.g., both Python and TypeScript files):

   - Check which language the current file or the user's question relates to
   - If still ambiguous, ask: "I detected both Python and TypeScript files. Which language are you using for the Claude API integration?"

3. **If the language cannot be inferred** (empty project, no source files, or unsupported language):

   - Use AskUserQuestion with options: Python, TypeScript, Java, Go, Ruby, cURL/raw HTTP, C#, PHP
   - If AskUserQuestion is unavailable, default to Python examples and note: "Showing Python examples. Let me know if you need a different language."

4. **If an unsupported language is detected** (Rust, Swift, C++, Elixir, etc.):

   - Offer cURL/raw HTTP examples from `curl/` and note that community SDKs may exist
   - Offer to show Python or TypeScript examples as reference implementations

5. **If the user wants cURL/raw HTTP examples**, read from `curl/`.

### Feature Support by Language

| Language   | Tool Runner | Managed Agents | Notes                                  |
| ---------- | ----------- | -------------- | -------------------------------------- |
| Python     | Yes (beta)  | Yes (beta)     | Full support — `@beta_tool` decorator  |
| TypeScript | Yes (beta)  | Yes (beta)     | Full support — `betaZodTool` + Zod     |
| Java       | Yes (beta)  | Yes (beta)     | Beta tool use with annotated classes   |
| Go         | Yes (beta)  | Yes (beta)     | `BetaToolRunner` in `toolrunner` package |
| Ruby       | Yes (beta)  | Yes (beta)     | `BaseTool` + `tool_runner` in beta     |
| C#         | No          | No             | Official SDK                           |
| PHP        | Yes (beta)  | Yes (beta)     | `BetaRunnableTool` + `toolRunner()`    |
| cURL       | N/A         | Yes (beta)     | Raw HTTP, no SDK features              |

> **Managed Agents code examples**: separate language-specific READMEs are provided for Python, TypeScript, Go, Ruby, PHP, Java, and cURL (`{lang}/managed-agents/README.md`, `curl/managed-agents.md`). Read your language's README plus the language-agnostic conceptual files `shared/managed-agents-*.md`. **Agents are persistent — create once, reference by ID.** Save the agent ID returned by `agents.create` and pass it to every subsequent `sessions.create`; do not call `agents.create` in the request path. The Anthropic CLI is one convenient way to create agents and environments from version-controlled YAML — its URL is in `shared/live-sources.md`. If a needed binding is not shown in the README, WebFetch the corresponding entry from `shared/live-sources.md` rather than guessing. C# does not currently support Managed Agents; use raw cURL-style HTTP requests to the API.

---

## Which Surface to Use?

> **Start simple.** Default to the simplest level that meets your needs. Single API calls and workflows cover most cases — move to agents only when the task truly requires open-ended, model-driven exploration.

| Use Case                                                | Level           | Recommended surface       | Why                                                          |
| ------------------------------------------------------- | --------------- | ------------------------- | ------------------------------------------------------------ |
| Classification, summarization, extraction, Q&A          | Single LLM call | **Claude API**            | One request, one response                                    |
| Batch processing or embeddings                          | Single LLM call | **Claude API**            | Specialized endpoints                                        |
| Multi-step pipelines with code-controlled logic         | Workflow        | **Claude API + tool use** | You orchestrate the loop                                     |
| Custom agent with your own tools                        | Agent           | **Claude API + tool use** | Maximum flexibility                                          |
| Server-managed stateful agent with workspace            | Agent           | **Managed Agents**        | Anthropic runs the loop and hosts a sandbox for tool execution |
| Persistent, versionable agent configs                   | Agent           | **Managed Agents**        | Agents are stored objects; sessions are pinned to a version  |
| Long-running multi-step agent with file mounts          | Agent           | **Managed Agents**        | Per-session containers, SSE event stream, Skills + MCP       |

> **Note:** Managed Agents is the right choice when you want Anthropic to run the agent loop *and* host the container in which tools execute — file ops, bash, code execution all run in a per-session workspace. If you want to host the compute yourself or run your own custom tool runtime, the right choice is Claude API + tool use — use the tool runner for automatic loop handling or a manual loop for fine-grained control (approval gates, custom logging, conditional execution).

> **Third-party providers (Amazon Bedrock, Google Vertex AI, Microsoft Foundry):** Managed Agents are **not available** on Bedrock, Vertex, or Foundry. If you deploy through any third-party provider, use **Claude API + tool use** for all use cases — including those for which Managed Agents would otherwise be the recommended surface.

### Decision Tree

```
What does your application need?

0. Are you deploying through Amazon Bedrock, Google Vertex AI, or Microsoft Foundry?
   └── Yes → Claude API (+ tool use for agents) — Managed Agents is 1P only.
   No → continue.

1. Single LLM call (classification, summarization, extraction, Q&A)
   └── Claude API — one request, one response

2. Want Anthropic to run the agent loop and host a per-session container
   where Claude executes tools (bash, file ops, code)?
   └── Yes → Managed Agents — server-managed sessions, persistent agent configs,
       SSE event stream, Skills + MCP, file mounts.
       Examples: "stateful coding agent with per-task workspace",
                 "long-running research agent streaming events to a UI",
                 "agent with persistent, versionable config used across many sessions"

3. Workflow (multi-step, orchestrated by code, with your own tools)
   └── Claude API with tool use — you control the loop

4. Open-ended agent (model decides its own trajectory, your tools, you host the compute)
   └── Claude API agentic loop (maximum flexibility)
```

### Should You Build an Agent?

Before choosing the agent level, check all four criteria:

- **Complexity** — Is the task multi-step and difficult to fully specify upfront? (e.g., "turn this design doc into a PR" vs. "extract the title from this PDF")
- **Value** — Does the result justify higher cost and latency?
- **Feasibility** — Is Claude capable of handling this type of task?
- **Cost of error** — Can errors be detected and recovered from? (tests, review, rollback)

If the answer is "no" for any of them, stay at a simpler level (single call or workflow).

---

## Architecture

Everything goes through `POST /v1/messages`. Tools and output constraints are features of this single endpoint, not separate APIs.

**User-defined tools** — You define tools (via decorators, Zod schemas, or raw JSON), and the SDK tool runner handles the API call, executing your functions, and looping until Claude is done. For full control you can write the loop manually.

**Server-side tools** — Anthropic-hosted tools that run on Anthropic infrastructure. Code execution is fully server-side (declare it in `tools` and Claude automatically runs the code). Computer use can be server-hosted or self-hosted.

**Structured outputs** — Constrain the Messages API response format (`output_config.format`) and/or validate tool parameters (`strict: true`). The recommended approach is `client.messages.parse()`, which automatically validates responses against your schema. Note: the older `output_format` parameter is deprecated; use `output_config: {format: {...}}` on `messages.create()`.

**Supporting endpoints** — Batches (`POST /v1/messages/batches`), Files (`POST /v1/files`), Token Counting, and Models (`GET /v1/models`, `GET /v1/models/{id}` — live capability/context-window discovery) supplement or support Messages API requests.

---

## Current Models (cached: 2026-04-15)

| Model             | Model ID            | Context        | Input $/1M | Output $/1M |
| ----------------- | ------------------- | -------------- | ---------- | ----------- |
| Claude Opus 4.7   | `claude-opus-4-7`   | 1M             | $5.00      | $25.00      |
| Claude Opus 4.6   | `claude-opus-4-6`   | 1M             | $5.00      | $25.00      |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 1M             | $3.00      | $15.00      |
| Claude Haiku 4.5  | `claude-haiku-4-5`  | 200K           | $1.00      | $5.00       |

**ALWAYS use `claude-opus-4-7` unless the user explicitly names another model.** This is non-negotiable. Do not use `claude-sonnet-4-6`, `claude-sonnet-4-5`, or any other model unless the user literally said "use sonnet" or "use haiku". Never downgrade to save cost — that is the user's decision, not yours.

**CRITICAL: Use only the exact model ID strings from the table above — they are complete as is. Do not append date suffixes.** For example, use `claude-sonnet-4-5`, never `claude-sonnet-4-5-20250514` or any other dated-suffix variant you may recall from training data. If the user requests an older model not in the table (e.g., "opus 4.5", "sonnet 3.7"), read `shared/models.md` for the exact ID — do not construct it yourself.

Note: if any of the model strings above look unfamiliar to you, that's expected — it just means they were released after your training-data cutoff. Rest assured these are real models; we wouldn't joke with you about that.

**Live capability lookup:** The table above is cached. When the user asks "what's the context window for X", "does X support vision/thinking/effort", or "which models support Y", query the Models API (`client.models.retrieve(id)` / `client.models.list()`) — see `shared/models.md` for a field reference and capability-filter examples.

---

## Thinking & Effort (quick reference)

**Opus 4.7 — adaptive thinking only:** Use `thinking: {type: "adaptive"}`. `thinking: {type: "enabled", budget_tokens: N}` returns 400 on Opus 4.7 — adaptive is the only enabling mode. `{type: "disabled"}` and omitting `thinking` both work. Sampling parameters (`temperature`, `top_p`, `top_k`) are also removed and will return 400. See `shared/model-migration.md` → Migrating to Opus 4.7 for the full breaking-change list.
**Opus 4.6 — adaptive thinking (recommended):** Use `thinking: {type: "adaptive"}`. Claude dynamically decides when and how much to think. `budget_tokens` is not needed — `budget_tokens` is deprecated on Opus 4.6 and Sonnet 4.6 and should not be used in new code. Adaptive thinking also automatically enables interleaved thinking (no beta header required). **When the user asks for "extended thinking", "thinking budget", or `budget_tokens`: always use Opus 4.7 or 4.6 with `thinking: {type: "adaptive"}`. The fixed-token-budget concept for thinking is deprecated — adaptive thinking replaces it. DO NOT use `budget_tokens` for new 4.6/4.7 code, and DO NOT switch to an older model.** *Gradual-migration concession:* `budget_tokens` still works on Opus 4.6 and Sonnet 4.6 as a transitional escape hatch — if you are migrating existing code and need a hard token cap before you tune `effort`, see `shared/model-migration.md` → Transitional escape hatch. Note: this concession does **not** extend to Opus 4.7 — `budget_tokens` is removed entirely there.
**Effort parameter (GA, no beta header):** Controls thinking depth and overall token spend via `output_config: {effort: "low"|"medium"|"high"|"max"}` (inside `output_config`, not at the top level). Defaults to `high` (equivalent to omitting it). `max` is Opus-tier only (Opus 4.6 and later — not Sonnet, not Haiku). Opus 4.7 adds `"xhigh"` (between `high` and `max`) — the best setting for most coding and agentic use cases on 4.7, and the default in Claude Code; use at least `high` for most intelligence-sensitive work. Works on Opus 4.5, Opus 4.6, Opus 4.7, and Sonnet 4.6. Returns an error on Sonnet 4.5 / Haiku 4.5. On Opus 4.7, effort matters more than on any prior Opus — re-tune it when migrating. Combine with adaptive thinking for the best cost-quality balance. Lower effort means fewer and more consolidated tool calls, fewer preambles, and more concise confirmations — `high` is often optimal between quality and token efficiency; use `max` when correctness matters more than cost; use `low` for subagents or simple tasks.

**Opus 4.7 — thinking content omitted by default:** `thinking` blocks still stream, but their text is empty unless you explicitly enable it via `thinking: {type: "adaptive", display: "summarized"}` (default is `"omitted"`). Silent change — no error. If you stream reasoning to users, this looks like a long pause before output by default; set `"summarized"` to restore visible progress.

**Task Budgets (beta, Opus 4.7):** `output_config: {task_budget: {type: "tokens", total: N}}` tells the model how many tokens it has for the full agentic loop — it sees a countdown and self-limits (minimum 20,000; beta header `task-budgets-2026-03-13`). Different from `max_tokens`, which is a hard ceiling on the response that the model is unaware of. See `shared/model-migration.md` → Task Budgets.

**Sonnet 4.6:** Supports adaptive thinking (`thinking: {type: "adaptive"}`). `budget_tokens` is deprecated on Sonnet 4.6 — use adaptive thinking instead.

**Older models (only if explicitly requested):** If the user specifically asks for Sonnet 4.5 or another older model, use `thinking: {type: "enabled", budget_tokens: N}`. `budget_tokens` must be less than `max_tokens` (minimum 1024). Never select an older model just because the user mentions `budget_tokens` — use Opus 4.7 with adaptive thinking instead.

---

## Compaction (quick reference)

**Beta, Opus 4.7, Opus 4.6, and Sonnet 4.6.** For long-running conversations that may exceed the 1M context window, enable server-side compaction. The API automatically summarizes the earlier portion of context when it approaches the trigger threshold (default: 150K tokens). Requires the beta header `compact-2026-01-12`.

**Critical:** Append `response.content` (not just text) back to your messages on every turn. Compaction blocks in the response must be preserved — the API uses them to replace the compacted history on the next request. Extracting only the text string and appending that silently loses compaction state.

See `{lang}/claude-api/README.md` (Compaction section) for code examples. Full documentation via WebFetch in `shared/live-sources.md`.

---

## Prompt Caching (quick reference)

**Prefix match.** Any byte change anywhere in the prefix invalidates everything after it. Render order: `tools` → `system` → `messages`. Keep stable content first (frozen system prompt, deterministic tool list), put volatile content (timestamps, per-request identifiers, varying questions) after the last `cache_control` breakpoint.

**Top-level auto-caching** (`cache_control: {type: "ephemeral"}` on `messages.create()`) is the simplest option when you don't need fine-grained placement. Maximum 4 breakpoints per request. Minimum cacheable prefix is ~1024 tokens; shorter prefixes are silently not cached.

**Verify via `usage.cache_read_input_tokens`** — if it is zero on repeated requests, a silent invalidator is at work (`datetime.now()` in the system prompt, unsorted JSON, varying tool set).

For placement patterns, architectural guidance, and a silent-invalidator audit checklist: read `shared/prompt-caching.md`. Language-specific syntax: `{lang}/claude-api/README.md` (Prompt Caching section).

---

## Managed Agents (Beta)

**Managed Agents** is the third surface: server-managed stateful agents with Anthropic-hosted tool execution. You create a persistent, versionable Agent config (`POST /v1/agents`), then start Sessions that reference it. Each session allocates a container as the agent's workspace — bash, file ops, and code execution run there; the agent loop itself runs on Anthropic's orchestration layer and acts on the container through tools. The session streams events; you send messages and tool results back.

**Managed Agents is first-party only.** Not available on Amazon Bedrock, Google Vertex AI, or Microsoft Foundry. For agents on third-party providers, use Claude API + tool use.

**Mandatory flow:** Agent (once) → Session (each run). `model`/`system`/`tools` live on the agent, never on the session. See `shared/managed-agents-overview.md` for the full reading guide, beta headers, and pitfalls.

**Beta headers:** `managed-agents-2026-04-01` — the SDK sets it automatically for all `client.beta.{agents,environments,sessions,vaults,memory_stores}.*` calls. The Skills API uses `skills-2025-10-02`, and the Files API uses `files-api-2025-04-14`, but you don't need to pass them explicitly for endpoints other than `/v1/skills` and `/v1/files`.

**Subcommands** — invoke directly via `/claude-api <subcommand>`:

| Subcommand | Action |
|---|---|
| `managed-agents-onboard` | Walk the user through setting up a Managed Agent from scratch. **Read `shared/managed-agents-onboarding.md` immediately** and follow its interview script: mental model → know-or-explore branch → templated config → session setup → emit code. Do not summarize — conduct the interview. |

**Reading guide:** Start with `shared/managed-agents-overview.md`, then the topical files `shared/managed-agents-*.md` (core, environments, tools, events, memory, client-patterns, onboarding, api-reference). For Python, TypeScript, Go, Ruby, PHP, and Java, read `{lang}/managed-agents/README.md` for code examples. For cURL, read `curl/managed-agents.md`. **Agents are persistent — create once, reference by ID.** Save the agent ID returned by `agents.create` and pass it to every subsequent `sessions.create`; do not call `agents.create` in the request path. The Anthropic CLI is one convenient way to create agents and environments from version-controlled YAML (URL in `shared/live-sources.md`). If a needed binding is not shown in the language README, WebFetch the corresponding entry from `shared/live-sources.md` rather than guessing. C# does not currently support Managed Agents; use the raw HTTP from `curl/managed-agents.md` as a reference.

**When the user wants to set up a Managed Agent from scratch** (e.g., "how do I get started", "walk me through creating one", "set up a new agent"): read `shared/managed-agents-onboarding.md` and run its interview — same flow as the `managed-agents-onboard` subcommand.

**When the user asks "how do I write client code for X":** consult `shared/managed-agents-client-patterns.md` — covers lossless stream reconnect, queued/processed `processed_at` gate, interrupt, `tool_confirmation` round-trip, correct idle/terminated break gate, post-idle status race, stream-first ordering, file-mount pitfalls, holding credentials on the host side via custom tools, etc.

---

## Reading Guide

After identifying the language, read the corresponding files based on what the user needs:

### Quick task reference

**One-shot text classification/summarization/extraction/Q&A:**
→ Read only `{lang}/claude-api/README.md`

**Chat UI or real-time response display:**
→ Read `{lang}/claude-api/README.md` + `{lang}/claude-api/streaming.md`

**Long-running conversations (may exceed the context window):**
→ Read `{lang}/claude-api/README.md` — see the Compaction section
**Migrating to a new model (Opus 4.7 / Opus 4.6 / Sonnet 4.6) or replacing a retired model:**
→ Read `shared/model-migration.md`
**Prompt caching / cache optimization / "why is my cache hit rate low":**
→ Read `shared/prompt-caching.md` + `{lang}/claude-api/README.md` (Prompt Caching section)

**Function calling / tool use / agents:**
→ Read `{lang}/claude-api/README.md` + `shared/tool-use-concepts.md` + `{lang}/claude-api/tool-use.md`

**Agent design (tool surface, context management, caching strategy):**
→ Read `shared/agent-design.md`

**Batch processing (latency-insensitive):**
→ Read `{lang}/claude-api/README.md` + `{lang}/claude-api/batches.md`

**Uploading files across multiple requests:**
→ Read `{lang}/claude-api/README.md` + `{lang}/claude-api/files-api.md`

**Managed Agents (server-managed stateful agents with workspace):**
→ Read `shared/managed-agents-overview.md` + the rest of the `shared/managed-agents-*.md` files. For Python, TypeScript, Go, Ruby, PHP, and Java, read `{lang}/managed-agents/README.md` for code examples. For cURL, read `curl/managed-agents.md`. **Agents are persistent — create once, reference by ID.** Save the agent ID returned by `agents.create` and pass it to every subsequent `sessions.create`; do not call `agents.create` in the request path. The Anthropic CLI is one convenient way to create agents and environments from version-controlled YAML (URL in `shared/live-sources.md`). If a needed binding is not shown in the language README, WebFetch the corresponding entry from `shared/live-sources.md` rather than guessing. C# does not currently support Managed Agents — use the raw HTTP from `curl/managed-agents.md` as a reference.

### Claude API (full file reference)

Read the **language-specific Claude API folder** (`{language}/claude-api/`):

1. **`{language}/claude-api/README.md`** — **Read this first.** Setup, quick start, common patterns, error handling.
2. **`shared/tool-use-concepts.md`** — Read when the user needs function calling, code execution, memory, or structured outputs. Covers conceptual foundations.
3. **`shared/agent-design.md`** — Read when designing an agent: bash vs. dedicated tools, programmatic tool calling, tool search/skills, context editing vs. compaction vs. memory, caching principles.
4. **`{language}/claude-api/tool-use.md`** — Read for language-specific tool use code examples (tool runner, manual loop, code execution, memory, structured outputs).
5. **`{language}/claude-api/streaming.md`** — Read when building chat UIs or interfaces that display responses incrementally.
6. **`{language}/claude-api/batches.md`** — Read when processing many requests offline (latency-insensitive). Runs asynchronously at 50% cost.
7. **`{language}/claude-api/files-api.md`** — Read when sending one file across multiple requests without re-uploading.
8. **`shared/prompt-caching.md`** — Read when adding or optimizing prompt caching. Covers prefix-stability design, breakpoint placement, and anti-patterns that silently invalidate the cache.
9. **`shared/error-codes.md`** — Read when debugging HTTP errors or implementing error handling.
10. **`shared/model-migration.md`** — Read when upgrading to newer models, replacing retired models, or porting `budget_tokens` / prefill patterns to the current API.
11. **`shared/live-sources.md`** — WebFetch URLs for retrieving the latest official documentation.

> **Note:** For Java, Go, Ruby, C#, PHP, and cURL — each has a single file covering all the basics. Read that file plus `shared/tool-use-concepts.md` and `shared/error-codes.md` as needed.

> **Note:** For the Managed Agents file reference, see the `## Managed Agents (Beta)` section above — it lists every `shared/managed-agents-*.md` file and the language-specific READMEs.

---

## When to Use WebFetch

Use WebFetch to retrieve the latest documentation when:

- The user asks for "latest" or "current" information
- The cached data appears to be incorrect
- The user asks about features not covered here

Live documentation URLs are listed in `shared/live-sources.md`.

## Common Pitfalls

- Do not truncate inputs when passing files or content to the API. If the content is too long to fit the context window, notify the user and discuss options (chunking, summarization, etc.) rather than silently truncating.
- **Opus 4.7 thinking:** Adaptive only. `thinking: {type: "enabled", budget_tokens: N}` returns 400 on Opus 4.7 — `budget_tokens` is removed entirely there (along with `temperature`, `top_p`, `top_k`). Use `thinking: {type: "adaptive"}`.
- **Opus 4.6 / Sonnet 4.6 thinking:** Use `thinking: {type: "adaptive"}` — DO NOT use `budget_tokens` for new 4.6 code (deprecated on both Opus 4.6 and Sonnet 4.6; for gradual migration of existing code, see the transitional escape hatch in `shared/model-migration.md` — note: this concession does not extend to Opus 4.7). For older models, `budget_tokens` must be less than `max_tokens` (minimum 1024). Mixing them up will error.
- **4.6/4.7 family — prefill removed:** Last-assistant-turn prefills return a 400 error on Opus 4.6, Opus 4.7, and Sonnet 4.6. Use structured outputs (`output_config.format`) or system-prompt instructions to control response format.
- **Confirm migration scope before editing:** When the user asks to migrate code to a new Claude model without naming a specific file, directory, or list of files, **first ask which scope to apply** — the entire working directory, a specific subdirectory, or a specific set of files. Do not start editing until the user confirms. Imperative phrasings like "migrate my codebase", "move my project to X", "upgrade to Sonnet 4.6", or a bare "migrate to Opus 4.7" are **still ambiguous** — they say what to do but not where, so ask. Act without asking only when the prompt names an exact file, a specific directory, or an explicit list of files ("migrate `app.py`", "migrate everything under `services/`", "update `a.py` and `b.py`"). See `shared/model-migration.md` Step 0.
- **`max_tokens` defaults:** Don't set `max_tokens` too low — hitting the cap truncates output mid-thought and requires a retry. For non-streaming requests, default to `~16000` (keeps responses under SDK HTTP timeouts). For streaming requests, default to `~64000` (timeouts aren't an issue, so give the model headroom). Go lower only with a strong reason: classification (`~256`), cost ceilings, or deliberately short outputs.
- **128K output tokens:** Opus 4.6 and Opus 4.7 support up to 128K `max_tokens`, but SDKs require streaming for such large values to avoid HTTP timeouts. Use `.stream()` with `.get_final_message()` / `.finalMessage()`.
- **Tool call JSON parsing (4.6/4.7 family):** Opus 4.6, Opus 4.7, and Sonnet 4.6 may produce different JSON string escaping in tool call `input` fields (e.g., Unicode or forward-slash escaping). Always parse tool inputs through `json.loads()` / `JSON.parse()` — never do raw string comparison on the serialized input.
- **Structured outputs (all models):** Use `output_config: {format: {...}}` instead of the deprecated `output_format` parameter on `messages.create()`. This is a general API change, not specific to 4.6.
- **Don't reimplement SDK functionality:** The SDK provides high-level helpers — use them instead of building from scratch. Specifically: use `stream.finalMessage()` instead of wrapping `.on()` events in `new Promise()`; use typed exception classes (`Anthropic.RateLimitError`, etc.) instead of string-matching error messages; use SDK types (`Anthropic.MessageParam`, `Anthropic.Tool`, `Anthropic.Message`, etc.) instead of redefining equivalent interfaces.
- **Don't define custom types for SDK data structures:** The SDK exports types for all API objects. Use `Anthropic.MessageParam` for messages, `Anthropic.Tool` for tool definitions, `Anthropic.ToolUseBlock` / `Anthropic.ToolResultBlockParam` for tool results, `Anthropic.Message` for responses. Defining your own `interface ChatMessage { role: string; content: unknown }` duplicates what the SDK already provides and loses type safety.
- **Reports and document outputs:** For tasks that produce reports, documents, or visualizations, the sandbox code execution comes with `python-docx`, `python-pptx`, `matplotlib`, `pillow`, and `pypdf` preinstalled. Claude can generate formatted files (DOCX, PDF, charts) and return them via the Files API — consider this for "report" or "document" requests instead of plain stdout text.
