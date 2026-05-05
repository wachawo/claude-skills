# Model Migration Guide

How to port existing code to newer Claude models. Covers breaking changes, deprecated parameters, and drop-in replacements for retired models.

For the latest authoritative version (with code examples in every supported language), WebFetch the **Migration Guide** URL from `shared/live-sources.md`. Use this file as a consolidated, skill-resident reference; consult the live documentation whenever a model launch or breaking change might have shifted the picture.

**This file is large.** Use the section names below to jump (or `Grep` the heading text). Read Step 0 and Step 1 first — they apply to any migration. Then read only the per-target section for the model you are migrating to.

| Section | When needed |
|---|---|
| Step 0: Confirm the migration scope | Always — before any edits |
| Step 1: Classify each file | Always — determines whether to swap, add-alongside, or skip |
| Per-SDK Syntax Reference | Translate the Python examples from this guide into TypeScript / Go / Ruby / Java / C# / PHP |
| Destination Models / Retired Model Replacements | Choosing the target model |
| Breaking Changes by Source Model | Migrating to Opus 4.6 / Sonnet 4.6 |
| Migrating to Opus 4.7 | Migrating to Opus 4.7 (breaking changes, silent defaults, behavioral shifts) |
| Opus 4.7 Migration Checklist | Mandatory vs. optional items for 4.7, `[BLOCKS]` / `[TUNE]` tags |
| Verify the Migration | After edits — runtime spot-check |

**TL;DR.** Change the model ID string. If you used `budget_tokens`, switch to `thinking: {type: "adaptive"}`. If you used assistant prefills, those return 400 on Opus 4.6 and Sonnet 4.6 — switch to one of the prefill replacements (most often `output_config.format`; see the table in Breaking Changes by Source Model). When moving from Sonnet 4.5 to Sonnet 4.6, set `effort` explicitly — 4.6 defaults to `high`. Remove the beta headers `effort-2025-11-24` and `fine-grained-tool-streaming-2025-05-14` (GA on 4.6); remove `interleaved-thinking-2025-05-14` once you've switched to adaptive thinking (keep it only if you're using the transitional escape hatch with `budget_tokens`). Then move back from `client.beta.messages.create` to `client.messages.create`. Soften any aggressive "CRITICAL: YOU MUST" instructions for tools; 4.6 follows the system prompt much more closely.

---

## Step 0: Confirm the migration scope

**Before any Write, Edit, or MultiEdit call, confirm the scope.** If the user's request does not explicitly name a single file, a specific directory, or an explicit list of files, **ask first — do not start editing**. This is non-negotiable: even imperative-sounding requests like "migrate my codebase", "move my project to X", "upgrade to Sonnet 4.6", or a bare "migrate to Opus 4.7" leave the scope ambiguous and require a clarifying question. Phrases like "my project", "my code", "my codebase", "the whole thing", "everywhere", or "across the repo" are **ambiguous, not directive**: they say *what* to do but not *where*. Ask before acting.

Explicitly offer typical scopes and wait for an answer before touching any file:

1. The entire working directory
2. A specific subdirectory (e.g., `src/`, `app/`, `services/billing/`)
3. A specific file or list of files

Present this as a single clarifying question so the user can answer in one step. **Act without asking only when the scope is already unambiguous** — the user named an exact file ("migrate `extract.py` to Sonnet 4.6"), specified a specific directory ("migrate everything under `services/billing/` to Opus 4.6"), listed specific files ("update `a.py` and `b.py`"), or already answered a scope question in a previous step. If you can precisely answer "which files will this change touch?" with a list from the prompt alone, act. Otherwise, ask.

**Worked example.** If the user says *"Move my project to Opus 4.6. I want adaptive thinking everywhere it makes sense."*, you don't know whether "my project" means the entire working directory, only `src/`, only production code, or something else — `everywhere` makes the intent clear (update every call site *within the scope*), but the scope itself is still undefined. Do not start editing. Reply:

> Before I start editing, can you confirm the scope? I can migrate:
> 1. Every `.py` file in the working directory
> 2. Only files under `src/` (production code)
> 3. A specific subdirectory or list of files that you name
>
> Which one?

Then wait for the answer. The same applies to *"Migrate to Opus 4.7"* and a bare *"Help me upgrade to Sonnet 4.6"* — ask before editing.

**How to ask the scope question well on large repositories.** Before the question, get a count of references per directory so the user can choose specifically:

```sh
rg -l "<old-model-id>" --type-not md | cut -d/ -f1 | sort | uniq -c | sort -rn
```

Present the breakdown in the scope question (e.g., *"Found 217 references across 3 directories: api/ (130), api-go/ (62), routing/ (25). Which to migrate?"*). Also make sure `git status` is clean before review — unexpected modifications mean a parallel process; stop and investigate before continuing.

---

## Step 1: Classify each file

Not every file containing an old model ID is a **caller** of the API. Before editing, classify each file into one of these buckets — the right action differs:

| # | Bucket | What it looks like | Action |
|---|---|---|---|
| 1 | **Calls the API/SDK** | `client.messages.create(model=…)`, `anthropic.Anthropic()`, request payloads | Change the model ID **and** apply the breaking-changes checklist for the target version (below). |
| 2 | **Defines or serves the model** | Model registries, OpenAPI spec, routing/queue configs, model-policy enums, generated catalogs | The old entry **stays** (the model is still served). Clarify whether to (a) add the new model alongside, (b) leave as is, or (c) retire the old one — never blindly replace. **If you can't ask, default to (a): add the new model alongside and flag it** — replacing would deregister a model that's still in production. |
| 3 | **References the ID as an opaque string** | UI fallback constants, capability-gate substring checks, generic test fixtures, label parsers, env defaults | Usually change the string and verify any parser/regex/substring match handles the new ID — but check the subcases below first. |
| 4 | **Suffix variant ID** | `claude-<model>-<suffix>` like `-fast`, `-1024k`, `-200k`, `[1m]`, date snapshots | These are deployment/routing identifiers, not the public model ID. **Don't assume an equivalent exists for the new model.** Check the registry first; if missing, leave the string and flag it. |

**Bucket 3 subcases — check before replacing a string occurrence.**

- **Capability gate** (e.g., `if 'opus-4-6' in model_id:` enables a feature) → **add the new ID alongside**, don't replace. The old model is still served and still has the capability, so replacing would silently disable the feature for any old-model traffic still flowing through this gate. If you know old-model traffic won't reach this point (single-caller codebase migrating fully), replacement is acceptable; if uncertain, add alongside.
- **Registry assert test** (e.g., `assert "claude-X" in supported_models`, `test_X_has_N_clusters`) → **add an assertion for the new model alongside; keep the old one.** The old model is still served, so its assertion remains valid — but the new model should also be in the registry, so check it too. Heuristic: if a test references multiple model versions in a list, it's a registry test; if a single model is compared inside a struct only against itself, it's a generic fixture.
- **Frozen / generated snapshot** → **regenerate**, don't hand-edit.
- **Linked to a definer** (e.g., an integration test that threads model authorization through a shared conftest seed list, or asserts against a billing-tier / rate-limit-group enum or a generated SKU/pricing catalog) → **first make sure the definer has an entry for the new model.** If not, add a seed entry (reusing the nearest existing tier as a placeholder); if you can't confidently do that, ask the user how to populate the definer. **Don't skip the test.** Replacing without populating the definer will cause a runtime test failure.

When migrating tests specifically: breaking parameters (`temperature`, `top_p`, `budget_tokens`) are usually absent — test fixtures rarely set sampling parameters on placeholder models. Scanning for breaking changes is still required, but expect mostly clean results.

**Find intentionally marked sync points first.** Many codebases mark places that must change with every model launch using markers like `MODEL LAUNCH`, `KEEP IN SYNC`, `@model-update`, and similar. Grep for the convention used in this repo *before* a broad grep on the model ID — these markers point to load-bearing changes.

---

## Per-SDK Syntax Reference

The code examples in this guide are in Python. **The same fields exist in every official Anthropic SDK** — Stainless generates all 7 from a single OpenAPI spec, so JSON field names map 1:1, with only case conventions differing. Use the strings below to translate the Python examples into the SDK you're migrating to.

> **Verify type and method names against the SDK source before writing them into customer code.** WebFetch the corresponding repository from the SDK sources table in `shared/live-sources.md` (one row per SDK) and confirm the exact symbol — especially for typed SDKs (Go, Java, C#), where union/builder names may differ from the JSON form. Don't guess type names that aren't in the table below or in `<lang>/claude-api/README.md`.


### `thinking` — `budget_tokens` → adaptive

| SDK | Before | After |

|---|---|---|
| Python | `thinking={"type": "enabled", "budget_tokens": N}` | `thinking={"type": "adaptive"}` |
| TypeScript | `thinking: { type: 'enabled', budget_tokens: N }` | `thinking: { type: 'adaptive' }` |
| Go | `Thinking: anthropic.ThinkingConfigParamOfEnabled(N)` | `Thinking: anthropic.ThinkingConfigParamUnion{OfAdaptive: &anthropic.ThinkingConfigAdaptiveParam{}}` |
| Ruby | `thinking: { type: "enabled", budget_tokens: N }` | `thinking: { type: "adaptive" }` |
| Java | `.thinking(ThinkingConfigEnabled.builder().budgetTokens(N).build())` | `.thinking(ThinkingConfigAdaptive.builder().build())` |
| C# | `Thinking = new ThinkingConfigEnabled { BudgetTokens = N }` | `Thinking = new ThinkingConfigAdaptive()` |
| PHP | `thinking: ['type' => 'enabled', 'budget_tokens' => N]` | `thinking: ['type' => 'adaptive']` |

### Sampling parameters — `temperature` / `top_p` / `top_k`

(Remove the field entirely on Opus 4.7; on Claude 4.x keep at most one of `temperature` or `top_p`.)

| SDK | Field(s) to remove |
|---|---|
| Python | `temperature=…`, `top_p=…`, `top_k=…` |
| TypeScript | `temperature: …`, `top_p: …`, `top_k: …` |
| Go | `Temperature: anthropic.Float(…)`, `TopP: anthropic.Float(…)`, `TopK: anthropic.Int(…)` |
| Ruby | `temperature: …`, `top_p: …`, `top_k: …` |
| Java | `.temperature(…)`, `.topP(…)`, `.topK(…)` |
| C# | `Temperature = …`, `TopP = …`, `TopK = …` |
| PHP | `temperature: …`, `topP: …`, `topK: …` |

### Prefill replacement — structured outputs via `output_config.format`

| SDK | Remove (last assistant turn) | Add |
|---|---|---|
| Python | `{"role": "assistant", "content": "…"}` | `output_config={"format": {"type": "json_schema", "schema": SCHEMA}}` |
| TypeScript | `{ role: 'assistant', content: '…' }` | `output_config: { format: { type: 'json_schema', schema: SCHEMA } }` |
| Go | trailing `anthropic.MessageParam{Role: "assistant", …}` | `OutputConfig: anthropic.OutputConfigParam{Format: anthropic.JSONOutputFormatParam{…}}` |
| Ruby | `{ role: "assistant", content: "…" }` | `output_config: { format: { type: "json_schema", schema: SCHEMA } }` |
| Java | trailing `Message.builder().role(ASSISTANT)…` | `.outputConfig(OutputConfig.builder().format(JsonOutputFormat.builder()…build()).build())` |
| C# | trailing `new Message { Role = "assistant", … }` | `OutputConfig = new OutputConfig { Format = new JsonOutputFormat { … } }` |
| PHP | trailing `['role' => 'assistant', 'content' => '…']` | `outputConfig: ['format' => ['type' => 'json_schema', 'schema' => $SCHEMA]]` |

### `thinking.display` — opt back into summarized reasoning (Opus 4.7)

| SDK | Add |
|---|---|
| Python | `thinking={"type": "adaptive", "display": "summarized"}` |
| TypeScript | `thinking: { type: 'adaptive', display: 'summarized' }` |
| Go | `Thinking: anthropic.ThinkingConfigParamUnion{OfAdaptive: &anthropic.ThinkingConfigAdaptiveParam{Display: anthropic.ThinkingConfigAdaptiveDisplaySummarized}}` |
| Ruby | `thinking: { type: "adaptive", display: "summarized" }` (or `display_:` when constructing the model class directly) |
| Java | `.thinking(ThinkingConfigAdaptive.builder().display(ThinkingConfigAdaptive.Display.SUMMARIZED).build())` |
| C# | `Thinking = new ThinkingConfigAdaptive { Display = Display.Summarized }` |
| PHP | `thinking: ['type' => 'adaptive', 'display' => 'summarized']` |

For any field not in these tables, the JSON key from the Python example translates directly: `snake_case` for Python/TypeScript/Ruby, `camelCase` arguments for PHP, `PascalCase` struct fields for Go/C#, `camelCase` builder methods for Java.

---

## Explain Every Change You Make

Migration edits often look arbitrary to a user who hasn't read the release notes — a removed `temperature`, a removed prefill, a rewritten phrase in the system prompt. **For each edit, tell the user what you changed and why**, tying it to the specific API or behavioral change that motivated it. Do this in a running summary, not only at the end.

Be especially explicit about **system prompt edits**. Users rightly protect their prompts, and prompt tuning is a judgment call (not a hard API requirement). For any prompt edit:

- Quote the before and after text.
- State the behavioral shift that motivated it (e.g., *"Opus 4.7 calibrates response length to task complexity, so I added an explicit length instruction"* or *"4.6 follows instructions more literally, so 'CRITICAL: YOU MUST use the search tool' will now overtrigger — softened to 'Use the search tool when…'"*).
- Clearly label which prompt edits are **optional tuning** (tone, length, subagent instructions) and which code edits are **mandatory to avoid 400** (sampling parameters, `budget_tokens`, prefills). Never present an optional prompt change as mandatory.

If you apply several prompt edits at once, offer them as a short list the user can accept or reject item by item, rather than silently rewriting the system prompt.

---

## Before Migrating

1. **Confirm the target model ID.** Use only exact strings from `shared/models.md` — don't add date suffixes to aliases (`claude-opus-4-6`, not `claude-opus-4-6-20251101`). A guessed ID returns 404.
2. **Check which features your code uses** against this checklist:
   - `thinking: {type: "enabled", budget_tokens: N}` → migrate to adaptive thinking on Opus 4.6 / Sonnet 4.6 (still functional but deprecated)
   - Assistant-turn prefills (`messages` ending with `role: "assistant"`) → must change on Opus 4.6 / Sonnet 4.6 (return 400)
   - `output_format` parameter on `messages.create()` → must change on all models (deprecated API-wide)
   - `max_tokens > ~16000` → must use streaming on any model (above ~16K risks SDK HTTP timeout). When streaming, Sonnet 4.6 / Haiku 4.5 are capped at 64K, and Opus 4.6 at 128K
   - Beta headers `effort-2025-11-24`, `fine-grained-tool-streaming-2025-05-14`, `interleaved-thinking-2025-05-14` → GA on 4.6, remove them and switch from `client.beta.messages.create` to `client.messages.create`
   - Moving Sonnet 4.5 → Sonnet 4.6 without setting `effort` → 4.6 defaults to `high`, which can change your latency/cost profile
   - System prompts with `CRITICAL`, `MUST`, `If in doubt, use X` → likely overtriggering on 4.6 (see Prompt-Behavior Changes)
   - Coming from 3.x / 4.0 / 4.1: also check sampling parameters (`temperature` + `top_p`), tool versions (`text_editor_20250728`), `refusal` + `model_context_window_exceeded` stop reasons, trailing-newline handling in tool parameters
3. **Test on a single request first.** Make one call against the new model, inspect the response, then roll out further.

---

## Destination Models (recommended)

| If you're on…                         | Migrate to         | Why                                               |
| ------------------------------------- | ------------------ | ------------------------------------------------- |
| Opus 4.6                              | `claude-opus-4-7`  | Most capable model; adaptive thinking only; high-res vision; see Migrating to Opus 4.7 |
| Opus 4.0 / 4.1 / 4.5 / Opus 3         | `claude-opus-4-6`  | The smartest 4.x before 4.7; adaptive thinking; 128K output |
| Sonnet 4.0 / 4.5 / 3.7 / 3.5          | `claude-sonnet-4-6`| Best balance of speed / intelligence; adaptive thinking; 64K output |
| Haiku 3 / 3.5                         | `claude-haiku-4-5` | Fastest and most cost-effective                   |

By default, pick the latest Opus for the customer's tier unless they explicitly chose otherwise. If moving from Opus 4.5 or earlier directly to Opus 4.7, apply the 4.6 migration first, then layer the Opus 4.7 changes on top (see Migrating to Opus 4.7 below).

---

## Retired Model Replacements

These models return 404 — upgrade immediately:

| Retired model                 | Retired       | Drop-in replacement  |
| ----------------------------- | ------------- | -------------------- |
| `claude-3-7-sonnet-20250219`  | Feb 19, 2026  | `claude-sonnet-4-6`  |
| `claude-3-5-haiku-20241022`   | Feb 19, 2026  | `claude-haiku-4-5`   |
| `claude-3-opus-20240229`      | Jan 5, 2026   | `claude-opus-4-7`    |
| `claude-3-5-sonnet-20241022`  | Oct 28, 2025  | `claude-sonnet-4-6`  |
| `claude-3-5-sonnet-20240620`  | Oct 28, 2025  | `claude-sonnet-4-6`  |
| `claude-3-sonnet-20240229`    | Jul 21, 2025  | `claude-sonnet-4-6`  |
| `claude-2.1`, `claude-2.0`    | Jul 21, 2025  | `claude-sonnet-4-6`  |

## Deprecated Models (retiring soon)

| Model                         | Retires       | Replacement          |
| ----------------------------- | ------------- | -------------------- |
| `claude-3-haiku-20240307`     | Apr 19, 2026  | `claude-haiku-4-5`   |
| `claude-opus-4-20250514`      | June 15, 2026 | `claude-opus-4-7`    |
| `claude-sonnet-4-20250514`    | June 15, 2026 | `claude-sonnet-4-6`  |

---

## Breaking Changes by Source Model

### Sonnet 4.5 → Sonnet 4.6 Migration (effort default change)

Sonnet 4.5 had no `effort` parameter; Sonnet 4.6 defaults to `high`. If you only change the model string and nothing else, you may see noticeably higher latency and token usage. Set `effort` explicitly.

**Recommended starting points:**

| Workload                                          | Start at       | Notes                                                                                                    |
| ------------------------------------------------- | -------------- | -------------------------------------------------------------------------------------------------------- |
| Chat, classification, content generation          | `low`          | With `thinking: {"type": "disabled"}` you'll see similar or better perf vs. Sonnet 4.5 without thinking |
| Most applications (balanced)                      | `medium`       | The default sweet spot for quality vs. cost                                                              |
| Agentic coding, tool-heavy workflows              | `medium`       | Combine with adaptive thinking and a generous `max_tokens` (up to 64K with streaming — Sonnet 4.6's cap) |
| Autonomous multi-step agents, long-horizon loops  | `high`         | Drop to `medium` if latency/tokens become a problem                                                      |
| Computer-use agents                               | `high` + adaptive | Sonnet 4.6's best computer-use accuracy is on adaptive + high                                         |

For non-thinking chat workloads specifically:

```python
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8192,
    thinking={"type": "disabled"},
    output_config={"effort": "low"},
    messages=[{"role": "user", "content": "..."}],
)
```

**When to use Opus 4.6 instead of Sonnet 4.6.** The hardest, longest tasks — large code migrations, deep research, sustained autonomous work. Sonnet 4.6 wins on quick turnaround and cost efficiency.

### Migrating to Opus 4.6 / Sonnet 4.6 (from any older model)

**1. Manual extended thinking deprecated — use adaptive thinking.**

`thinking: {type: "enabled", budget_tokens: N}` (manual extended thinking with a fixed token budget) is deprecated on Opus 4.6 and Sonnet 4.6. Replace with `thinking: {type: "adaptive"}` — Claude decides when and how much to think. Adaptive thinking also automatically enables interleaved thinking (no beta header required).

```python
# Old (still works on older models, deprecated on 4.6)
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 8000},
    messages=[...]
)

# New (Opus 4.6 / Sonnet 4.6)
response = client.messages.create(
    model="claude-opus-4-6",  # or "claude-sonnet-4-6"
    max_tokens=16000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},  # optional: low | medium | high | max
    messages=[...]
)
```

Adaptive thinking is the long-term goal, and on internal evals it outperforms manual extended thinking. Switch when you can.

**Transitional escape hatch.** Manual extended thinking is still *functional* on Opus 4.6 and Sonnet 4.6 (deprecated, will be removed in a future release). If you need a hard ceiling during migration — for example, to cap token spend on a runaway workload before you tune `effort` — you can keep `budget_tokens` alongside an explicit `effort` value, then remove it in a follow-up. `budget_tokens` must be strictly less than `max_tokens`:

```python
# Transitional only — deprecated, plan to remove
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=16384,
    thinking={"type": "enabled", "budget_tokens": 8192},  # must be < max_tokens
    output_config={"effort": "medium"},
    messages=[...],
)
```

If the user asks for "thinking budget" on 4.6, the preferred answer is `effort`: use `low`, `medium`, `high`, or `max` (Opus-tier only — not Sonnet, not Haiku) instead of a token count.

**2. Effort parameter (Opus 4.5, Opus 4.6, Sonnet 4.6 only).**

Controls thinking depth and overall token spend. Sits inside `output_config`, not at the top level. Defaults to `high`. `max` is Opus-tier only (Opus 4.6 and later — not Sonnet, not Haiku). On Sonnet 4.5 and Haiku 4.5 it errors.

```python
output_config={"effort": "medium"}  # often the best cost / quality balance
```

### Migrating to the 4.6 Family (Opus 4.6 and Sonnet 4.6)

**3. Assistant-turn prefills return 400 (Opus 4.6 and Sonnet 4.6).**

Prefill responses on the final assistant turn are no longer supported on either Opus 4.6 or Sonnet 4.6 — both return 400. Adding assistant messages *elsewhere* in the conversation (e.g., for few-shot examples) still works. Pick a replacement that matches what the prefill was used for:

| Prefill was used for                                | Replacement                                                                                                                              |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Forcing JSON / YAML / schema output                 | `output_config.format` with `json_schema` — see the example below                                                                         |
| Forcing a classification label                      | A tool with an enum field of valid labels, or structured outputs                                                                          |
| Skipping preambles (`Here is the summary:\n`)       | A system prompt instruction: *"Respond directly without preamble. Do not start with phrases like 'Here is...' or 'Based on...'."*         |
| Steering around bad refusals                        | Usually no longer needed — 4.6 refuses much more appropriately. A normal user-turn prompt is enough.                                      |
| Continuing an interrupted response                  | Move the continuation into a user turn: *"Your previous response was interrupted and ended with `[last text]`. Continue from there."*     |
| Injecting reminders / context hydration             | Inject in a user turn. For complex agent harnesses, expose context through a tool call or during compaction.                              |

```python
# Old (fails on Opus 4.6 / Sonnet 4.6) — prefill forcing JSON shape
messages=[
    {"role": "user", "content": "Extract the name."},
    {"role": "assistant", "content": "{\"name\": \""},
]

# New — structured outputs replace the prefill
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    output_config={"format": {"type": "json_schema", "schema": {...}}},
    messages=[{"role": "user", "content": "Extract the name."}],
)
```

**4. Streaming for `max_tokens > ~16K` (all models); only Opus 4.6 goes up to 128K.**

Non-streaming requests hit the SDK HTTP timeout on large `max_tokens`, regardless of model — stream anything above ~16K output. The streamable cap varies: Sonnet 4.6 and Haiku 4.5 are limited to 64K, and only Opus 4.6 goes up to 128K.

```python
with client.messages.stream(model="claude-opus-4-6", max_tokens=64000, ...) as stream:
    message = stream.get_final_message()
```

**5. JSON escaping in tool calls may differ (Opus 4.6 and Sonnet 4.6).**

Both 4.6 models can produce tool call `input` with Unicode or forward-slash escaping. Always parse via `json.loads()` / `JSON.parse()`; never compare a raw serialized-input string.

### All Models

**6. `output_format` → `output_config.format` (API-wide).**

The old top-level `output_format` parameter on `messages.create()` is deprecated. Use `output_config.format`. This is not 4.6-specific — it applies to all models.

---

## Beta Headers to Remove on 4.6

Several beta headers that were required on 4.5 are now GA on 4.6 and should be removed. Leaving them is harmless but misleading; removing them also lets you switch back from `client.beta.messages.create(...)` to `client.messages.create(...)`.

| Header                                    | Status on 4.6                                              | Action                                                  |
| ----------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------- |
| `effort-2025-11-24`                       | Effort parameter GA                                        | Remove                                                  |
| `fine-grained-tool-streaming-2025-05-14`  | GA                                                         | Remove                                                  |
| `interleaved-thinking-2025-05-14`         | Adaptive thinking automatically enables interleaved thinking | Remove when using adaptive thinking; still works on Sonnet 4.6 *with* manual extended thinking, but that path is deprecated |
| `token-efficient-tools-2025-02-19`        | Built into all Claude 4+ models                             | Remove (no effect)                                      |
| `output-128k-2025-02-19`                  | Built into Claude 4+ models                                 | Remove (no effect)                                      |

Once you've removed all of these and completed the switch to adaptive thinking, you can move the SDK call site back from the beta namespace to the regular one:

```python
# Before
response = client.beta.messages.create(
    model="claude-opus-4-5",
    betas=["interleaved-thinking-2025-05-14", "effort-2025-11-24"],
    ...
)

# After
response = client.messages.create(
    model="claude-opus-4-6",
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},
    ...
)
```

---

## Additional Changes When Coming from 3.x / 4.0 / 4.1 → 4.6

If you're jumping from Opus 4.1, Sonnet 4, Sonnet 3.7, or older Claude 3.x straight to 4.6, apply everything above *plus* the items in this section. Those already on Opus 4.5 / Sonnet 4.5 can skip.

**1. Sampling parameters: `temperature` OR `top_p`, not both.**

Passing both errors on any Claude 4+ model:

```python
# Old (3.x only — errors on 4+)
client.messages.create(temperature=0.7, top_p=0.9, ...)

# New
client.messages.create(temperature=0.7, ...)  # or top_p, not both
```

**2. Update tool versions.**

Legacy tool versions aren't supported on 4+. **Both the `type` field and the `name` field change** — `text_editor_20250728` and `str_replace_based_edit_tool` go together; updating one without the other returns 400. Also remove the `undo_edit` command from your text-editor integration:

| Old                                               | New                                                     |
| ------------------------------------------------- | ------------------------------------------------------- |
| `text_editor_20250124` + `str_replace_editor`     | `text_editor_20250728` + `str_replace_based_edit_tool`  |
| `code_execution_*` (earlier versions)             | `code_execution_20250825`                               |
| `undo_edit` command                               | *(no longer supported — remove call sites)*             |

```python
# Before
tools = [{"type": "text_editor_20250124", "name": "str_replace_editor"}]

# After — BOTH fields change
tools = [{"type": "text_editor_20250728", "name": "str_replace_based_edit_tool"}]
```

**3. Handling the `refusal` stop reason.**

Claude 4+ may return `stop_reason: "refusal"` in the response. If your code only handles `end_turn` / `tool_use` / `max_tokens`, add a branch:

```python
if response.stop_reason == "refusal":
    # Surface the refusal to the user; do not retry with the same prompt
    ...
```

**4. Handling the `model_context_window_exceeded` stop reason (4.5+).**

Different from `max_tokens`: it means the model hit the *context window* limit, not the requested output cap. Handle both:

```python
if response.stop_reason == "model_context_window_exceeded":
    # Context window exhausted — compact or split the conversation
    ...
elif response.stop_reason == "max_tokens":
    # Requested output cap hit — retry with higher max_tokens or stream
    ...
```

**5. Trailing newlines are preserved in tool call string parameters (4.5+).**

4.5 and 4.6 preserve trailing newlines that older models trimmed. If your tool implementations do exact string-match on tool call `input` values (e.g., `if name == "foo"`), make sure they still match when the model sends `"foo\n"`. Normalizing via `.rstrip()` on the receiving side is usually the simplest fix.

**6. Haiku: rate limits reset between generations.**

Haiku 4.5 has its own rate-limit pool, separate from Haiku 3 / 3.5. If you're ramping traffic during migration, check the Haiku 4.5 limits for your tier on [API rate limits](https://platform.claude.com/docs/en/api/rate-limits): a quota that comfortably covered Haiku 3.5 may need a tier bump for the same volume on 4.5.

---

## Prompt Behavior Changes (Opus 4.5 / 4.6, Sonnet 4.6)

These don't break your code, but prompts that worked on 4.5-and-earlier may over- or under-trigger on 4.6. Tune as needed.

**1. Aggressive instructions cause overtriggering.** Opus 4.5 and 4.6 follow the system prompt much more closely than earlier models. Prompts written to *overcome* old reluctance are now too aggressive:

| Before (worked on 4.0 / 4.5)                | After (use on 4.6)                        |
| ------------------------------------------- | ----------------------------------------- |
| `CRITICAL: You MUST use this tool when...`  | `Use this tool when...`                   |
| `Default to using [tool]`                   | `Use [tool] when it would improve X`      |
| `If in doubt, use [tool]`                   | *(remove — no longer needed)*             |

If the model now overtriggers a tool or skill, the fix is almost always to soften the language, not add more guardrails.

**2. Overthinking and excessive exploration (Opus 4.6).** At higher `effort` settings, Opus 4.6 explores more before answering. If that burns too many thinking tokens, lower `effort` first (`medium` is often the sweet spot), and only then add prose instructions limiting reasoning.

**3. Spawning subagents too often (Opus 4.6).** Opus 4.6 strongly prefers delegating to subagents. If you see it spawning a subagent for something a direct `grep` or `read` would solve, add: *"Use subagents only for parallel or independent workstreams. For single-file reads or sequential operations, work directly."*

**4. Overengineering (Opus 4.5 / 4.6).** Both models can add unnecessary files, abstractions, or defensive error handling beyond what was requested. If you want minimal changes, ask explicitly: *"Only make changes directly requested. Don't add helpers, abstractions, or error handling for scenarios that can't happen."*

**5. LaTeX math output (Opus 4.6).** Opus 4.6 defaults to LaTeX (`\frac{}{}`, `$...$`) for math and technical content. If you need plain text, instruct explicitly: *"Format all math as plain text — no LaTeX, no `$`, no `\frac{}{}`. Use `/` for division and `^` for exponents."*

**6. Skipping verbal summaries (4.6 family).** The 4.6 models are more concise and may skip a summary paragraph after a tool call, jumping straight to the next action. If you rely on those summaries for visibility, add: *"After completing a task that involves tool use, provide a brief summary of what you did."*

**7. "Think" as a trigger word (Opus 4.5 with thinking off).** When `thinking` is off, Opus 4.5 is especially sensitive to the word *think* and may reason more than needed. Use `consider`, `evaluate`, or `reason through`.

---

## Quick Model-ID Renaming Table

| Old string (migration source)    | New string         |
| -------------------------------- | ------------------ |
| `claude-opus-4-6`                 | `claude-opus-4-7`  |
| `claude-opus-4-5`                 | `claude-opus-4-7`  |
| `claude-opus-4-1`                 | `claude-opus-4-7`  |
| `claude-opus-4-0`                 | `claude-opus-4-7`  |
| `claude-sonnet-4-5`               | `claude-sonnet-4-6`|
| `claude-sonnet-4-0`               | `claude-sonnet-4-6`|

Older aliases (`claude-opus-4-5`, `claude-sonnet-4-5`, `claude-opus-4-1`, etc.) are still active and can be pinned if you need time before upgrading — see `shared/models.md` for the full legacy list.

---

## Migration Checklist

Each item is tagged: **`[BLOCKS]`** — items that will return 400, infinite loop, silent timeout, or wrong tool selection if skipped — apply as code edits, not as recommendations. **`[TUNE]`** — quality/cost settings.

For each file that calls `messages.create()` / equivalent SDK method:

- [ ] **[BLOCKS]** Update the `model=` string to the new alias
- [ ] **[BLOCKS]** Replace `budget_tokens` with `thinking={"type": "adaptive"}` (deprecated on Opus 4.6 / Sonnet 4.6)
- [ ] **[BLOCKS]** Move `format` from top-level `output_format` to `output_config.format`
- [ ] **[BLOCKS]** Remove any assistant-turn prefills if targeting Opus 4.6 or Sonnet 4.6 (see prefill replacement table)
- [ ] **[BLOCKS]** Move to streaming if `max_tokens > ~16000` (otherwise SDK HTTP timeout)
- [ ] **[TUNE]** Set `output_config={"effort": "..."}` explicitly — especially when moving Sonnet 4.5 → Sonnet 4.6 (4.6 defaults to `high`)
- [ ] **[TUNE]** Remove GA beta headers: `effort-2025-11-24`, `fine-grained-tool-streaming-2025-05-14`, `token-efficient-tools-2025-02-19`, `output-128k-2025-02-19`; remove `interleaved-thinking-2025-05-14` once you've moved to adaptive thinking
- [ ] **[TUNE]** Switch `client.beta.messages.create(...)` → `client.messages.create(...)` once all betas are removed
- [ ] **[TUNE]** Review the system prompt for aggressive tool language (`CRITICAL:`, `MUST`, `If in doubt`) and soften it

**Additional items when coming from 3.x / 4.0 / 4.1:**
- [ ] **[BLOCKS]** Remove either `temperature` or `top_p` (passing both returns 400 on Claude 4+)
- [ ] **[BLOCKS]** Update text-editor tool `type` to `text_editor_20250728`
- [ ] **[BLOCKS]** Update text-editor tool `name` to `str_replace_based_edit_tool` — **changing only `type` while keeping `name: "str_replace_editor"` returns 400**
- [ ] **[BLOCKS]** Update the code-execution tool to `code_execution_20250825`
- [ ] **[BLOCKS]** Remove any `undo_edit` command call sites
- [ ] **[TUNE]** Add handling for `stop_reason == "refusal"`
- [ ] **[TUNE]** Add handling for `stop_reason == "model_context_window_exceeded"` (4.5+)
- [ ] **[TUNE]** Verify that string matching on tool parameters tolerates trailing newlines (preserved on 4.5+)
- [ ] **[TUNE]** When moving to Haiku 4.5: review the rate-limit tier (separate pool from Haiku 3.x)

**Verification:**
- [ ] Make one test request and check `response.stop_reason`, `response.usage`, and whether tool-use / thinking behavior matches expectations

For cached prompts: render order and hash inputs haven't changed, so existing `cache_control` breakpoints continue to work. However, **changing the model string invalidates the existing cache** — the first request on the new model writes the cache from scratch.

---

## Migrating to Opus 4.7

> **Model ID `claude-opus-4-7` is authoritative as written here.** When the user asks to migrate to Opus 4.7, write `model="claude-opus-4-7"` exactly. **Don't** WebFetch to verify — this guide is the source of truth for migration target model IDs. A matching entry exists in `shared/models.md`.

Claude Opus 4.7 is our most capable generally available model to date. It is highly autonomous and exceptionally good at long-horizon agentic tasks, knowledge work, vision tasks, and memory tasks. This section summarizes everything new at launch. It layers on top of the 4.6 migration above — if the caller is jumping from Opus 4.5 or earlier, apply the 4.6 changes first, then layer this section on top.

**TL;DR for those already on Opus 4.6.** Update the model ID to `claude-opus-4-7`, remove any remaining `budget_tokens` and sampling parameters (both return 400 on Opus 4.7), give `max_tokens` headroom and re-baseline via `count_tokens()` against the new model, opt back into `thinking.display: "summarized"` if reasoning is shown to users, and re-tune `effort` — it matters more on 4.7 than on any prior Opus.

### Breaking Changes (will return 400 on Opus 4.7)

**Extended thinking removed.**

`thinking: {type: "enabled", budget_tokens: N}` is no longer supported on Claude Opus 4.7 or newer models and returns 400. Switch to adaptive thinking (`thinking: {type: "adaptive"}`) and use the effort parameter to control thinking depth. Adaptive thinking is **off by default** on Claude Opus 4.7: requests without a `thinking` field go without thinking, as on Opus 4.6. Set `thinking: {type: "adaptive"}` explicitly to turn it on.

```python
# Before (Opus 4.6)
client.messages.create(
    model="claude-opus-4-6",
    max_tokens=64000,
    thinking={"type": "enabled", "budget_tokens": 32000},
    messages=[{"role": "user", "content": "..."}],
)

# After (Opus 4.7)
client.messages.create(
    model="claude-opus-4-7",
    max_tokens=64000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},  # or "max", "xhigh", "medium", "low"
    messages=[{"role": "user", "content": "..."}],
)
```

If the caller did not use extended thinking, no change is required — thinking is off by default or can be set explicitly via `thinking={"type": "disabled"}`.

Remove the `budget_tokens` plumbing entirely. For the replacement `effort` value, see **Choosing an effort level on Opus 4.7** below — there is no exact 1:1 mapping from `budget_tokens`.

**Sampling parameters removed.**

The `temperature`, `top_p`, and `top_k` parameters are no longer accepted on Claude Opus 4.7. Requests that include them return 400. Remove these fields from the request payload. Prompting is the recommended way to steer model behavior on Claude Opus 4.7. If you used `temperature = 0` for determinism, it never guaranteed identical outputs on prior models either.

```python
# Before — errors on Opus 4.7
client.messages.create(temperature=0.7, top_p=0.9, ...)

# After
client.messages.create(...)  # no sampling params
```

- **If the intent was determinism**, use `effort: "low"` with a tighter prompt.
- **If the intent was creative variance**, the replacement in the prompt depends on the use case; **ask the user** how they want to introduce variance. If you can't ask, add a use-case-appropriate instruction like *"choose something off-distribution and interesting"* — for example, for text generation, *"Vary your phrasing and structure across responses"*; for frontend/design use the 4-direction approach in **Design and frontend coding** below.

### Choosing an Effort Level on Opus 4.7

`budget_tokens` controlled how much to *think*; `effort` controls how much to think *and* act, so there is no exact 1:1 mapping. **Use `xhigh` for the best results on coding and agentic use cases, and at least `high` for most intelligence-sensitive use cases.** Experiment with other levels to further tune token usage and intelligence:

| Level | Use when | Notes |
| --- | --- | --- |
| `max` | Intelligence-demanding tasks where it's worth testing the ceiling | May yield gains in some use cases, but can show diminishing returns from increased token usage; prone to overthinking |
| `xhigh` | **Most coding and agentic use cases** | The best setting for these; used as the default in Claude Code |
| `high` | Intelligence-sensitive use cases in general | Balances token usage and intelligence; the recommended minimum for most intelligence-sensitive work |
| `medium` | Cost-sensitive use cases that need to reduce token usage with an intelligence trade-off | |
| `low` | Short, narrow tasks and latency-sensitive workloads that aren't intelligence-sensitive | |

### Silent Default Changes (no error, but behavior differs)

**Thinking content is omitted by default.**

Thinking blocks still appear in the response stream on Claude Opus 4.7, but their `thinking` field is empty unless you explicitly opt in. This is a silent change from Claude Opus 4.6, where the default was to return summarized thinking text. To restore summarized thinking content on Claude Opus 4.7, set `thinking.display` to `"summarized"`. **The block field name does not change** — it's still `block.thinking` on a `thinking`-type block; don't rename it.

**How to detect.** Any code that reads `block.thinking` (or equivalent) from a `thinking`-type block and renders it in a UI, log, or trace. **The fix is a request parameter, not response handling** — add `display: "summarized"` to the `thinking` parameter:

```python
thinking={"type": "adaptive", "display": "summarized"}  # "display" is new on Opus 4.7; values: "omitted" (default) | "summarized"
```

The default is `"omitted"` on Claude Opus 4.7. If thinking content was not shown anywhere, no change is needed. If your product streams reasoning to users, the new default looks like a long pause before output begins; set `display: "summarized"` to restore visible progress during thinking.

**Updated token counting.**

Claude Opus 4.7 and Claude Opus 4.6 count tokens differently. The same input text yields a higher token count on Claude Opus 4.7 than on Claude Opus 4.6, and `/v1/messages/count_tokens` will return a different token count for Claude Opus 4.7 than for Claude Opus 4.6. Claude Opus 4.7's token efficiency may vary by workload shape. Prompting interventions, `task_budget`, and `effort` can help control cost and ensure appropriate token usage. Note that these controls may trade off model intelligence. **Update your `max_tokens` parameters to give extra headroom, including compaction triggers.** Claude Opus 4.7 provides a 1M context window at standard API pricing without a long-context premium.

What else to check:

- Client-side token estimators (tiktoken-style approximations) calibrated to 4.6
- Cost calculators multiplying tokens by a fixed per-token price
- Rate-limit retry thresholds tied to measured token counts

Re-baseline by re-running `client.messages.count_tokens()` against `claude-opus-4-7` on a representative sample of the caller's prompts. Don't apply a flat multiplier. For cost-sensitive workloads, consider lowering `effort` by one level (e.g., `high` → `medium`). For agentic loops, consider adopting Task Budgets (below).

### New Feature: Task Budgets (beta)

Opus 4.7 introduces **task budgets** — tell Claude how many tokens it has for the full agentic loop (thinking + tool calls + final output). The model sees a running countdown and uses it to prioritize work and gracefully wrap up as the budget runs out.

This is a **hint that the model is aware of**, not a hard cap. It differs from `max_tokens`, which remains a forcing per-response limit *not* exposed to the model. Use `task_budget` when you want the model to pace itself; use `max_tokens` as a hard ceiling to cap usage.

Requires the beta header `task-budgets-2026-03-13`:

```python
client.beta.messages.create(
    betas=["task-budgets-2026-03-13"],
    model="claude-opus-4-7",
    max_tokens=64000,
    thinking={"type": "adaptive"},
    output_config={
        "effort": "high",
        "task_budget": {"type": "tokens", "total": 128000},
    },
    messages=[...],
)
```

Set a generous budget for open-ended agentic tasks and tighten it for latency-sensitive ones. **The minimum `task_budget.total` is 20,000 tokens.** If the budget is too constrained for the task, the model may complete it less thoroughly, referencing the budget as a limitation. **Don't add `task_budget` during migration unless you're confident the budget value is right** — if you can run the workload and measure, do that; otherwise ask the user rather than guess. It's the main lever for offsetting the token-count shift on agentic workloads.

### Capability Improvements

**High-resolution vision.** Opus 4.7 is the first Claude model to support high-resolution images. The maximum resolution is **2576 pixels on the long side** (up from 1568px on Opus 4.6 and earlier). This unlocks gains on vision-heavy workloads, especially computer use and understanding screenshots/artifacts/documents. Coordinates returned by the model now map 1:1 to actual pixels, so no scaling math is needed.

High-res support is **automatic on Opus 4.7** — no beta header, no client-side opt-in. The model accepts larger inputs and returns pixel-accurate coordinates out of the box.

**Token cost.** Full-resolution images on Opus 4.7 may use up to ~3× more image tokens than on prior models (up to ~4784 tokens per image, vs. the previous cap of ~1,600 tokens). If the extra precision isn't needed, downsample client-side before sending to control cost — but **don't add downsampling by default during migration**. If you're unsure whether the pipeline needs the precision, ask the user rather than guess. Use `count_tokens()` on representative images on Opus 4.7 to re-baseline before reacting to any measured cost shift.

Beyond resolution, Opus 4.7 also improves low-level perception (pointing, measuring, counting) and natural-image bounding-box localization and detection.

**Knowledge work.** Significant gains on tasks where the model visually verifies its own output — `.docx` redlining, `.pptx` editing, programmatic chart/figure analysis (e.g., pixel-level data transcription via image-processing libraries). If your prompts contain scaffolding like *"double-check the slide layout before returning"*, try removing it and re-baselining.

**Memory.** Opus 4.7 is better at writing and using filesystem-based memory. If your agent keeps a scratchpad, a notes file, or a structured memory store across steps, that agent should be better at taking notes and using them on future tasks.

**User-facing progress updates.** Opus 4.7 provides more regular, higher-quality intermediate updates during long agentic traces. If the system prompt has scaffolding like *"After every 3 tool calls, summarize progress"*, try removing it to avoid excessive user-facing text. If the length or content of Opus 4.7's updates is poorly calibrated for your use case, explicitly describe how these updates should look in the prompt and provide examples.

### Real-time Cybersecurity Safeguards

Requests touching prohibited or high-risk topics may result in refusals.

### Fast Mode: not available on Opus 4.7

Opus 4.7 has no Fast Mode variant. **Opus 4.6 Fast is still supported.** Bring this up only if the caller's code actually uses a Fast Mode string (e.g., `claude-opus-4-6-fast`); if the word "fast" doesn't appear in the code, say nothing about Fast Mode.

When you see `model="claude-opus-4-6-fast"` (or similar), **the migration edit is this:**

```python
# Opus 4.7 has no Fast Mode — keeping on 4.6 Fast (caller's choice to switch to standard Opus 4.7).
model="claude-opus-4-6-fast",
```

In other words: leave the model string **unchanged**, add a comment above it, and tell the user two options — (a) stay on Opus 4.6 Fast, which is still supported, or (b) move latency-tolerant traffic to standard Opus 4.7 for the intelligence gain. **Don't** rewrite the model string to `claude-opus-4-7` yourself — that silently trades latency for intelligence, which is the caller's decision.

### Behavioral Shifts (tunable via prompt)

These don't break anything, but prompts tuned for Opus 4.6 may land differently. Opus 4.7 is more steerable than 4.6, so small prompt nudges usually close the gap.

**More literal instruction-following.** Claude Opus 4.7 interprets prompts more literally and explicitly than Claude Opus 4.6, especially at low effort levels. It won't silently generalize an instruction from one item to another and won't surface things you didn't ask for. The upside of this literalness is precision and less thrash. Overall it performs better on API use cases with carefully tuned prompts, structured extraction, and pipelines where you want predictable behavior. A prompt-and-harness review can be especially useful when migrating to Claude Opus 4.7.

**Verbosity calibrates to task complexity.** Opus 4.7 scales response length to how complex it thinks the task is, rather than defaulting to a fixed verbosity — shorter on simple lookups, considerably longer on open-ended analysis. If the product depends on a specific length or style, tune the prompt explicitly. To reduce verbosity:

> *"Provide concise, focused responses. Skip non-essential context, and keep examples minimal."*

If you see specific kinds of over-verbosity (e.g., over-explaining), add instructions targeting that. Positive examples showing the desired level of concision usually work better than negative examples or "don't do this" instructions. **Don't** assume existing "be concise" instructions should be removed — test first.

**Tone and writing style.** Opus 4.7 is more direct and opinionated, with less validation-forward phrasing and fewer emoji than Opus 4.6's warm style. As with any new model, the prose style of long-form writing may shift. If the product relies on a specific voice, re-evaluate style prompts against the new baseline. If you want a warmer or more conversational voice, specify:

> *"Use a warm, collaborative tone. Acknowledge the user's framing before answering."*

**`effort` matters more than on any prior Opus.** Opus 4.7 respects `effort` levels more strictly, especially at the low end. At `low` and `medium`, it scopes work to what was asked rather than going above and beyond — good for latency and cost, but on moderate tasks at `low` there's some risk of under-thinking.

- If shallow reasoning appears on complex tasks, raise `effort` to `high` or `xhigh` rather than prompt around it.
- If `effort` must stay at `low` for latency, add a targeted instruction: *"This task involves multi-step reasoning. Think carefully through the problem before responding."*
- **At `xhigh` or `max`, set a large `max_tokens`** so the model has room to think and act through tool calls and subagents. Start at 64K and tune from there. (`xhigh` is a new effort level on Opus 4.7, between `high` and `max`.)

Adaptive-thinking triggering is also steerable. If the model thinks more often than you'd like — which can happen with large or complex system prompts — add: *"Thinking adds latency and should only be used when it will meaningfully improve answer quality — typically for problems that require multi-step reasoning. When in doubt, respond directly."*

**Uses tools less often by default.** Opus 4.7 tends to use tools less than 4.6 and lean more on reasoning. This gives better results in most cases, but for products that rely on tools (search/retrieval, function-calling, computer-use steps), it can reduce the tool-use rate. Two levers:

- **Raise `effort`** — `high` or `xhigh` show substantially more tool use in agentic search and coding, and are especially useful for knowledge work.
- **Prompt for it** — be explicit in tool descriptions or in the system prompt about when and how to use a tool, and encourage the model to err on the side of using it more often:

> *"When the answer depends on information not present in the conversation, you MUST call the `search` tool before answering — do not answer from prior knowledge."*

**Fewer subagents by default.** Opus 4.7 tends to spawn fewer subagents than 4.6. This is steerable — give explicit guidance for when delegation is desired. For example, for a coding agent:

> *"Do NOT spawn a subagent for work you can complete directly in a single response (e.g. refactoring a function you can already see). Spawn multiple subagents in the same turn when fanning out across items or reading multiple files."*

**Design and frontend coding.** Opus 4.7 has stronger design instincts than 4.6, with a stable default house style: warm cream/off-white backgrounds (around `#F4F1EA`), serif display fonts (Georgia, Fraunces, Playfair), italic word accents, and terracotta/amber accent colors. This reads well for editorial, hospitality, and portfolio briefs, but will feel inappropriate for dashboards, dev tools, fintech, healthcare, or enterprise apps — and it shows up in slide decks as well as web UI.

The default is sticky. Generic instructions ("don't use cream", "make it clean and minimal") usually push the model to another fixed palette rather than producing variety. Two approaches work reliably:

1. **Specify a concrete alternative.** The model follows explicit specs precisely — give exact hex values, fonts, and layout constraints.
2. **Have the model propose options before building.** This breaks the default and gives the user control:

   > *"Before building, propose 4 distinct visual directions tailored to this brief (each as: bg hex / accent hex / typeface — one-line rationale). Ask the user to pick one, then implement only that direction."*

If the caller previously relied on `temperature` for design variety, use approach (2): it produces meaningfully different directions across runs.

Opus 4.7 also needs less frontend-design prompting than prior models to avoid generic "AI slop" aesthetics. Where earlier models needed a long anti-slop snippet, Opus 4.7 generates distinctive, creative frontends with a much shorter nudge. This snippet works well alongside the variety approaches above:

> *"NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white or dark backgrounds), predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character. Use unique fonts, cohesive colors and themes, and animations for effects and micro-interactions."*

**Interactive coding products.** Opus 4.7's token usage and behavior can differ between autonomous, asynchronous coding agents with a single user turn and interactive, synchronous coding agents with multiple user turns. Specifically, it tends to use more tokens in interactive settings, mostly because it reasons more after a user turn. This can improve long-horizon coherence, instruction following, and coding capabilities in long interactive coding sessions, but also comes with higher token usage. To maximize both performance and token efficiency in coding products, use `effort: "xhigh"` or `"high"`, add autonomous features (like auto mode), and reduce the number of human interactions required from users.

When limiting required user interactions, specify the task, intent, and relevant constraints upfront in the first human turn. Well-specified, clear, and precise task descriptions upfront help maximize autonomy and intelligence while minimizing extra token usage after the user turn — since Opus 4.7 is more autonomous than prior models, this usage pattern helps maximize performance. In contrast, ambiguous or underspecified prompts delivered progressively across multiple user turns usually reduce token efficiency and sometimes performance.

**Code review.** Opus 4.7 is significantly better at finding bugs than prior models, with higher recall and precision. However, if a code-review harness was tuned for an earlier model, it may initially show *lower* recall — this is likely a harness effect, not a capability regression. When a review prompt says "only report high-severity issues", "be conservative", or "don't nitpick", Opus 4.7 follows the instruction more faithfully than prior models: it investigates just as thoroughly, identifies bugs, then refuses to report findings it considers below the stated bar. Precision goes up, but measured recall can drop even though underlying bug-finding improved.

Recommended prompt language:

> *"Report every issue you find, including ones you are uncertain about or consider low-severity. Do not filter for importance or confidence at this stage — a separate verification step will do that. Your goal here is coverage: it is better to surface a finding that later gets filtered out than to silently drop a bug. For each finding, include your confidence level and an estimated severity so a downstream filter can rank them."*

This can be used without an actual second step, but moving confidence filtering out of the finding step often helps. If the harness has a separate verification/dedup/ranking stage, tell the model explicitly that its job in the finding stage is coverage, not filtering. If you want single-pass self-filtering, be specific about the bar rather than using qualitative terms like "important" — for example, *"report any bugs that could cause incorrect behavior, a test failure, or a misleading result; only omit nits like pure style or naming preferences."* Iterate on prompts against a subset of evals to validate the recall or F1 gain.

**Computer use.** Computer use works at resolutions up to the new maximum of 2576px / 3.75MP. Sending images at **1080p** gives a good balance of performance and cost. For especially cost-sensitive workloads, **720p** or **1366×768** are cheaper options with strong performance. Test to find ideal settings for your use case; experimenting with `effort` can also help tune behavior.

---

## Opus 4.7 Migration Checklist

Each item is tagged: **`[BLOCKS]`** — items that produce 400, an infinite loop, silent truncation, or empty output if skipped — apply as code edits, not as recommendations. **`[TUNE]`** — quality/cost settings — present them to the user as recommendations.

`[BLOCKS]` items prefixed with **"If…"** or **"At…"** are conditional. Before walking the list, **scan the file** for the conditions: does it display thinking text in a UI/log? Does it set `output_config.effort` to `"x-high"` or `"max"`? Is this a security workload? Is this a multi-turn agentic loop? Apply only the items whose condition matches.

- [ ] **[BLOCKS]** Replace `thinking: {type: "enabled", budget_tokens: N}` with `thinking: {type: "adaptive"}` + `output_config.effort`; remove `budget_tokens` plumbing entirely
- [ ] **[BLOCKS]** Remove `temperature`, `top_p`, `top_k` from request construction
- [ ] **[BLOCKS]** If thinking content is shown to users or stored in logs: add `thinking.display: "summarized"` (otherwise the rendered text is empty)
- [ ] **[BLOCKS]** When `output_config.effort` is `xhigh` or `max`: set `max_tokens` ≥ 64000 (otherwise output is truncated mid-thought)
- [ ] **[TUNE]** Give `max_tokens` and compaction triggers extra headroom; re-run `count_tokens()` against `claude-opus-4-7` on representative prompts to re-baseline (no flat multiplier)
- [ ] **[TUNE]** Re-baseline cost and rate-limit dashboards *before* reacting to measured shifts
- [ ] **[TUNE]** Re-evaluate `effort` per route — use `xhigh` for coding/agentic and at least `high` for most intelligence-sensitive work; on 4.7 it matters more than on any prior Opus
- [ ] **[TUNE]** Multi-turn agentic loops: adopt API-native Task Budgets (`output_config.task_budget`, beta `task-budgets-2026-03-13`, minimum 20k tokens) — these cap *cumulative* spend across the loop; per-turn depth is `effort`
- [ ] **[TUNE]** Review ambiguous or underspecified instructions that relied on 4.6 to generalize intent, and update them to be clearer or more precise — 4.7 follows them literally
- [ ] **[TUNE]** Tool-use workloads: add explicit when/how-to-use guidance to tool descriptions (4.7 reaches for tools less often)
- [ ] **[TUNE]** Verbosity: test existing length instructions before changing them — 4.7 calibrates length to task complexity, so tune to the desired output rather than assuming direction
- [ ] **[TUNE]** Remove progress-update forcing scaffolding (*"after every N tool calls…"*)
- [ ] **[TUNE]** Remove knowledge-work verification scaffolding (*"double-check the slide layout…"*) and re-baseline
- [ ] **[TUNE]** Add a tone instruction if you want a warmer / more conversational voice; re-evaluate style prompts on writing-heavy routes
- [ ] **[TUNE]** Subagent tool present: add explicit spawn / don't-spawn guidance
- [ ] **[TUNE]** Frontend/design output: specify a concrete palette/font, or have the model propose 4 visual directions before building (the default cream/serif house style is sticky)
- [ ] **[TUNE]** Interactive coding products: use `effort: "xhigh"` or `"high"`, add autonomous features (e.g., auto mode) to reduce human interactions, and specify task/intent/constraints upfront in the first turn
- [ ] **[TUNE]** Code-review harness: remove or weaken "only report high-severity" / "be conservative" filters and make the model report every finding with confidence + severity; move filtering into a downstream step (4.7 follows severity filters more literally, which can depress measured recall)
- [ ] **[TUNE]** Vision-heavy pipelines (screenshots, charts, document understanding): keep images at native resolution up to 2576px on the long side for the accuracy gain; remove scale-factor math from coordinate handling (coords are now 1:1 with pixels). No beta header / opt-in needed — high-res is automatic on Opus 4.7.
- [ ] **[TUNE]** Computer-use pipelines: send screenshots at 1080p for a good performance/cost balance (720p or 1366×768 for cost-sensitive workloads); experiment with `effort` to tune behavior
- [ ] **[TUNE]** Cost-sensitive image pipelines: full-res images on 4.7 use up to ~4784 tokens vs. ~1,600 on prior models (~3×). Client-side downsampling before upload avoids the increase, but **don't downsample by default** — if you're unsure whether the precision is needed, ask the user. Re-baseline via `count_tokens()` on representative images before reacting to cost shifts.

---

## Verify the Migration

After updating, verify that the new model is actually being used. Replace `YOUR_TARGET_MODEL` with the model string you migrated to (e.g., `claude-opus-4-7`, `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5`) and keep the assertion prefix in sync:

```python
YOUR_TARGET_MODEL = "claude-opus-4-7"  # or "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"
response = client.messages.create(model=YOUR_TARGET_MODEL, max_tokens=64, messages=[...])
assert response.model.startswith(YOUR_TARGET_MODEL), response.model
```

For changes in rate-limit headroom, pricing, or capability deltas (vision, structured outputs, effort support), query the Models API:

```python
m = client.models.retrieve(YOUR_TARGET_MODEL)
m.max_input_tokens, m.max_tokens
m.capabilities["effort"]["max"]["supported"]
```

See `shared/models.md` for the full capability-lookup pattern.
