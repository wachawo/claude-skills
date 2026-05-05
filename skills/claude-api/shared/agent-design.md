# Agent Design Patterns

This file describes decision heuristics for building agents on the Claude API: which primitives to choose, how to design a tool set, and how to manage context and cost over long runs. The mechanics of specific tools and code examples live in `tool-use-concepts.md` and the language-specific folders.

---

## Model Parameters

| Parameter | When to use | What to expect |
| --- | --- | --- |
| **Adaptive thinking** (`thinking: {type: "adaptive"}`) | When you want Claude to manage when and how much to think on its own. | Claude determines thinking depth per request and automatically interleaves thinking between tool calls. No token budget to tune. |
| **Effort** (`output_config: {effort: ...}`) | When you need to tune the trade-off between thoroughness and token efficiency. | Lower effort → fewer and more consolidated tool calls, fewer preambles, more concise confirmations. `medium` often gives a good balance. Use `max` when correctness matters more than cost. |

See `SKILL.md` §Thinking & Effort for model-support details and parameters.

---

## Designing the Tool Set

### Bash vs. Specialized Tools

Claude does not know your application's safety boundaries, confirmation policies, or UX surface. Claude emits tool calls; your harness handles them. The shape of those tool calls determines what the harness can do with them.

**A bash tool** gives Claude broad programmatic capability — it can perform almost any action. But the harness only sees an opaque command string of identical shape for any action. Promoting an action to a **specialized tool** gives the harness a specific hook with typed arguments that it can intercept, restrict, render, or audit.

**When to promote an action to a specialized tool:**

- **Safety boundary.** Actions that need gating are natural candidates. A useful criterion is reversibility: hard-to-reverse actions (external API calls, sending messages, deleting data) can be gated behind a user confirmation. A `send_email` tool is easy to gate; `bash -c "curl -X POST ..."` is not.
- **Freshness checks.** A specialized `edit` tool can refuse a write if the file changed since Claude last read it. Bash cannot enforce that invariant.
- **Rendering.** Some actions benefit from custom UI. Claude Code promotes asking questions to a tool so it can render them as a modal, present options, and block the agent loop until an answer arrives.
- **Planning.** Read-only tools like `glob` and `grep` can be marked parallel-safe. When the same actions go through bash, the harness cannot tell a parallel-safe `grep` from a parallel-unsafe `git push`, so it must serialize.

**Rule of thumb.** Start with bash for breadth. Promote to specialized tools when you need to gate, render, audit, or parallelize an action.

---

## Tools Provided by Anthropic

| Tool | Side | When to use | What to expect |
| --- | --- | --- | --- |
| **Bash** | Client | Claude needs to run shell commands. | Claude emits commands; your harness executes them. A reference implementation is provided. |
| **Text editor** | Client | Claude needs to read or edit files. | Claude views, creates, and edits files through your implementation. A reference implementation is provided. |
| **Computer use** | Client or server | Claude needs to interact with GUIs, web apps, or visual interfaces. | Claude takes screenshots and emits mouse/keyboard commands. Can be self-hosted (you run the environment) or Anthropic-hosted. |
| **Code execution** | Server | Claude needs to run code in a sandbox you don't want to manage. | Anthropic-hosted container with built-in sub-tools for files and bash. No client-side execution. |
| **Web search / fetch** | Server | Claude needs information after the training cutoff (news, current events, recent docs) or the contents of a specific URL. | Claude emits a query or URL; Anthropic executes it and returns results with citations. |
| **Memory** | Client | Claude needs to persist context across sessions. | Claude reads/writes a `/memories` directory. You implement the storage backend. |

**Client-side** tools are defined by Anthropic (name, schema, the pattern Claude uses) but executed by your harness. Anthropic provides reference implementations. **Server-side** tools run entirely on Anthropic infrastructure — declare them in `tools` and Claude handles the rest.

---

## Composing Tool Calls: Programmatic Tool Calling

In standard tool use, each tool call is a round trip: Claude invokes a tool, the result enters Claude's context, Claude reasons over it, then invokes the next tool. Three sequential actions (read profile → find orders → check inventory) mean three round trips. Each adds latency and tokens, and most of the intermediate data is no longer needed.

**Programmatic tool calling (PTC)** lets Claude compose these calls into a script. The script runs in a code-execution container. When the script calls a tool, the container suspends, the call executes (client- or server-side), and the result returns to the running code — not to Claude's context. The script handles it with normal control flow (loops, filters, branches). Only the script's final output returns to Claude's context.

| When to use | What to expect |
| --- | --- |
| Many sequential tool calls or large intermediate results that need filtering before they hit the context window. | Claude writes code that calls tools as functions. Runs in a code-execution container. Token cost scales with the final output, not with intermediate results. |

---

## Scaling the Tool Set and Instructions

| Capability | When to use | What to expect |
| --- | --- | --- |
| **Tool search** | Many tools available, but only a few are relevant for any given request. You don't want to keep every schema in context up front. | Claude searches over the tool set and loads only relevant schemas. Tool definitions are added, not replaced — this preserves caching (see the caching section below). |
| **Skills** | Task-specific instructions Claude should load only when needed. | Each skill is a folder with a `SKILL.md`. The skill description is in context by default; Claude reads the full file when the task requires it. |

Both patterns keep fixed context small and pull in details on demand.

---

## Long-Running Agents: Context Management

| Pattern | When to use | What to expect |
| --- | --- | --- |
| **Context editing** | Context grows stale over many steps (old tool results, completed thinking). | Tool results and thinking blocks are cleared at configurable thresholds. The transcript stays compact without summarization. |
| **Compaction** | The conversation may approach or exceed the context window. | Earlier context is summarized into a compaction block server-side. See `SKILL.md` §Compaction for the critical handling of `response.content`. |
| **Memory** | State must persist across sessions (not just within one conversation). | Claude reads/writes files in a memory directory. Survives process restarts. |

**How to choose.** Context editing and compaction operate within a session — editing trims stale steps, compaction summarizes when you approach the limit. Memory is for cross-session persistence. Many long-running agents use all three.

---

## Caching for Agents

**Read `prompt-caching.md` first.** It covers the prefix-match invariant, breakpoint placement, silent-invalidator audits, and why changing tools or the model mid-session breaks the cache. This section only covers agent-specific workarounds for the corresponding limitations.

| Limitation (from `prompt-caching.md`) | Agent-specific workaround |
| --- | --- |
| Editing the system prompt mid-session invalidates the cache. | Append a `<system-reminder>` block to the `messages` array. The cached prefix stays untouched. Claude Code uses this for time updates and mode transitions. |
| Switching models mid-session invalidates the cache. | Spawn a **subagent** with a cheaper model for the subtask; keep the main loop on a single model. Claude Code's Explore subagents use Haiku this way. |
| Adding/removing tools mid-session invalidates the cache. | Use **tool search** for dynamic discovery — it adds tool schemas rather than replacing them, so the existing prefix is preserved. |

For breakpoint placement in multi-turn conversations, use top-level auto-caching — see `prompt-caching.md` §Placement patterns.

---

Live documentation for any of these capabilities is in `live-sources.md`.
