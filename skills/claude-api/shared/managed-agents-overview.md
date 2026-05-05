# Managed Agents — Overview

Managed Agents provides a per-session container as the agent's workspace. The agent loop runs on Anthropic's orchestration layer; the container is where the agent's *tools* execute — bash commands, file operations, code. You create a stored **Agent** configuration (model, system prompt, tools, MCP servers, skills), then start **Sessions** that reference it. The session streams events back to you; you send user messages and tool results in.

## ⚠️ MANDATORY FLOW: Agent (once) → Session (each run)

**Why agents are separate objects: versioning.** An agent is a stored, versioned configuration; each update creates a new immutable version, and sessions pin to a version at creation. This lets you iterate the agent (tweak the prompt, add a tool) without breaking already-running sessions, roll back if a change regresses, and A/B test versions side-by-side. None of that works if you call `agents.create()` afresh on every run.

Each session references a pre-created `/v1/agents` object. Create the agent once, save the ID, and reuse across runs.

| Step | Call | Frequency |
|---|---|---|
| 1 | `POST /v1/agents` — `model`, `system`, `tools`, `mcp_servers`, `skills` live here | **ONCE.** Save `agent.id` **and** `agent.version`. |
| 2 | `POST /v1/sessions` — `agent: "agent_abc123"` or `{type: "agent", id, version}` | **Each run.** The string shorthand uses the latest version. |

If you are about to write `sessions.create()` with `model`, `system`, or `tools` in the session body — **stop**. Those fields live on `agents.create()`. The session accepts only a *pointer*.

**When generating code, separate setup and runtime.** `agents.create()` belongs to a setup script (or a guarded `if agent_id is None:` block), not to the top of the hot path. If user code calls `agents.create()` on every invocation, it accumulates orphaned agents and pays creation latency for nothing. The correct shape: create once → save the ID (config file, env var, secrets manager) → each run loads the ID and calls `sessions.create()`.

**To change agent behavior, use `POST /v1/agents/{id}` — don't create a new one.** Each update bumps the version; running sessions keep their pinned version, new sessions get the latest (or pin explicitly via `{type: "agent", id, version}`). See `shared/managed-agents-core.md` → Agents → Versioning.

## Beta Headers

Managed Agents is in beta. The SDK sets the required beta headers automatically:

| Beta Header                    | What it enables                                       |
| ------------------------------ | ----------------------------------------------------- |
| `managed-agents-2026-04-01`    | Agents, Environments, Sessions, Events, Session Resources, Vaults, Credentials, Memory Stores |
| `skills-2025-10-02`            | Skills API (for managing custom skill definitions)    |
| `files-api-2025-04-14`         | Files API for uploading files                         |

**Which beta header goes where:** the SDK sets `managed-agents-2026-04-01` automatically on `client.beta.{agents,environments,sessions,vaults,memory_stores}.*` calls, and `files-api-2025-04-14` / `skills-2025-10-02` automatically on `client.beta.files.*` / `client.beta.skills.*` calls. You do NOT need to add the Skills or Files beta header when calling Managed Agents endpoints. **Exception — session-scoped file listing:** `client.beta.files.list({scope_id: session.id})` is a Files endpoint that accepts a Managed Agents parameter, so it needs **both** headers. Pass `betas: ["managed-agents-2026-04-01"]` explicitly on that call (the SDK adds the Files header; you add the Managed Agents header). See `shared/managed-agents-environments.md` → Session outputs.


## Reading Guide

| User wants to...                                       | Read these files                                        |
| ------------------------------------------------------ | ------------------------------------------------------- |
| **Start from scratch / "help me set up an agent"**     | `shared/managed-agents-onboarding.md` — guided interview (WHERE→WHO→WHAT→WATCH), then emit code |
| Understand how the API works                           | `shared/managed-agents-core.md`                         |
| See the full endpoint reference                        | `shared/managed-agents-api-reference.md`                |
| **Create an agent** (mandatory first step)             | `shared/managed-agents-core.md` (Agents section) + the language file |
| Update/version an agent                                | `shared/managed-agents-core.md` (Agents → Versioning) — update, don't recreate |
| Create a session                                       | `shared/managed-agents-core.md` + `{lang}/managed-agents/README.md` |
| Configure tools and permissions                        | `shared/managed-agents-tools.md`                        |
| Configure MCP servers                                  | `shared/managed-agents-tools.md` (MCP Servers section)  |
| Stream events / handle tool_use                        | `shared/managed-agents-events.md` + the language file   |
| Configure an environment                               | `shared/managed-agents-environments.md` + the language file |
| Upload files / mount repositories                      | `shared/managed-agents-environments.md` (Resources)     |
| Give an agent persistent memory across sessions        | `shared/managed-agents-memory.md` — memory stores, the session `memory_store` resource, preconditions, versions/redact |
| Store MCP credentials                                  | `shared/managed-agents-tools.md` (Vaults section)       |
| Call a non-MCP API / CLI that needs a secret           | `shared/managed-agents-client-patterns.md` Pattern 9 — no container env vars; vaults are MCP-only; keep the secret host-side via a custom tool |

## Common Pitfalls

- **Agent first, then session — NO EXCEPTIONS** — the session's `agent` field accepts **only** a string ID or `{type: "agent", id, version}`. `model`, `system`, `tools`, `mcp_servers`, `skills` are **top-level fields on `POST /v1/agents`**, never on `sessions.create()`. If the user has not created an agent, that's the zeroth step of every example.
- **Agent ONCE, not per run** — `agents.create()` is a setup step. Save the returned `agent_id` and reuse it; do not call `agents.create()` at the start of your hot path. If the agent configuration must change, `POST /v1/agents/{id}` — each update creates a new version, and sessions can pin to a specific version for reproducibility.
- **MCP auth flows through vaults** — the agent's `mcp_servers` array declares only `{type, name, url}` (no auth). Credentials live in vaults (`client.beta.vaults.credentials.create`) and attach to sessions via `vault_ids`. Anthropic automatically refreshes OAuth tokens using the stored refresh token.
- **Stream to receive events** — `GET /v1/sessions/{id}/events/stream` is the primary way to receive agent output in real time.
- **The SSE stream has no replay — reconnect with consolidation** — if the stream drops while an `agent.tool_use`, `agent.mcp_tool_use`, or `agent.custom_tool_use` is awaiting resolution (`user.tool_confirmation` for the first two, `user.custom_tool_result` for the last), the session deadlocks (client disconnects → session goes idle → reconnect happens → client doesn't resolve). On every (re)connect: open the stream via `GET /v1/sessions/{id}/events/stream`, fetch `GET /v1/sessions/{id}/events`, dedupe by event ID, then continue. See `shared/managed-agents-events.md` → Reconnecting after a dropped stream.
- **Don't trust HTTP library timeouts as total-time limits** — `requests` `timeout=(c, r)` and `httpx.Timeout(n)` are *per-chunk* read timeouts; they reset on every byte, so a slow connection can block indefinitely. For a hard deadline on raw-HTTP polling, track `time.monotonic()` at the loop level and exit explicitly. Prefer the SDK `sessions.events.stream()` / `session.events.list()` over manual HTTP. See `shared/managed-agents-events.md` → Receiving Events.
- **Messages are queued** — you can send events while the session is `running` or `idle`; they are processed in order. You don't need to wait for a response before sending the next message.
- **Cloud environments only** — `config.type: "cloud"` is the only supported environment type.
- **Archive is irreversible per resource** — archiving an agent, environment, session, vault, credential, or memory store makes it read-only with no unarchive. For agents, environments, and memory stores specifically, archived resources can no longer be used by new sessions (existing sessions continue). Do not call `.archive()` on a production agent, environment, or memory store as a cleanup — **always confirm with the user before archiving**.
