# Managed Agents — Core Concepts

## Architecture

Managed Agents is built around four core concepts:

| Concept | Endpoint | What it is |
|---|---|---|
| **Agent** | `/v1/agents` | A persistent, versionable object that defines the agent's capabilities and persona: model, system prompt, tools, MCP servers, skills. **Must be created before starting a session.** See the Agents section below. |
| **Session** | `/v1/sessions` | A stateful interaction with the agent. References a pre-created agent by ID + environment + initial instructions. Produces an event stream. |
| **Environment** | `/v1/environments` | A template defining the configuration for provisioning containers. |
| **Container** | N/A | Isolated compute instance where the agent's **tools** execute (bash, file ops, code). The agent loop does not run here — it runs on Anthropic's orchestration layer and acts on the container through tool calls. |

```
                       ┌─────────────────────────────────────┐
                       │  Anthropic orchestration layer      │
Agent (config) ───────▶│  (agent loop: Claude + tool calls)  │
                       └──────────────┬──────────────────────┘
                                      │ tool calls
                                      ▼
Environment (template) ──▶ Container (tool execution workspace)
                                 │
                         Session ─┤
                                 ├── Resources (files, repos, memory stores — attached at startup)
                                 ├── Vault IDs (MCP credential references)
                                 └── Conversation (event stream in/out)
```

> **Agent creation is mandatory.** Sessions reference a pre-created agent by ID — `model`/`system`/`tools` live on the agent object, not on the session. Every flow starts with `POST /v1/agents`.

---

## Session Lifecycle

```
rescheduling → running ↔ idle → terminated
```

| Status         | Description                                                        |
| -------------- | ------------------------------------------------------------------ |
| `idle` | The agent has finished the current task and is awaiting input. It is either waiting for input to continue working via `user.message`, or blocked waiting for a `user.custom_tool_result` or `user.tool_confirmation`. The attached `stop_reason` carries additional information about why the agent stopped. |
| `running` | The session has started executing and the agent is actively working. |
| `rescheduling` | The session is (re)scheduled after a retryable error and is ready to be picked up by the orchestration system. |
| `terminated` | The session has ended and entered an irreversible, unusable state. |

- Events can be sent while the session is `running` or `idle`. Messages are queued and processed in order.
- The agent transitions `idle → running` when it receives a new event, then back to `idle` when finished.
- Errors surface as `session.error` events on the stream, not as a status value.

### Built-in Session Capabilities

- **Context compaction** — when you approach the max context, the API automatically compacts the session history so the interaction can continue
- **Prompt caching** — repeated tokens in history are cached, reducing processing time and cost
- **Extended thinking** — enabled by default, returned as `agent.thinking` events

### Session Operations

| Operation | Notes |
|---|---|
| List / fetch | Paginated list or a single resource by ID |
| Update | Only `title` is updatable |
| Archive | The session becomes **read-only**. Irreversible. |
| Delete | Permanently deletes the session, event history, container, and checkpoints. |

---

## Sessions

A session is a running instance of an agent inside an environment.

### The Session Object

Key fields returned by the API:

| Field           | Type     | Description                                         |
| --------------- | -------- | --------------------------------------------------- |
| `type` | string | Always `"session"` |
| `id` | string | Unique session ID |
| `title` | string | Human-readable title |
| `status` | string | `idle`, `running`, `rescheduling`, `terminated` |
| `created_at` | string | ISO 8601 timestamp |
| `updated_at` | string | ISO 8601 timestamp |
| `archived_at` | string | ISO 8601 timestamp (nullable) |
| `environment_id` | string | Environment ID |
| `agent` | object | Agent configuration |
| `resources` | array | Attached files, repos, and memory stores |
| `metadata` | object | User-supplied key-value pairs (max 8 keys) |
| `usage` | object | Token usage stats |

### Creating a Session

**A session is meaningless without an agent.** Sessions reference a pre-created agent by ID. Create the agent first via `agents.create()`, then reference it:

```ts
// 1. Create the agent (reusable, versioned)
const agent = await client.beta.agents.create(
  {
    name: "Coding Assistant",
    model: "claude-opus-4-7",
    system: "You are a helpful coding agent.",
    tools: [{ type: "agent_toolset_20260401"}],
  },
);

// 2. Start a session that references it
const session = await client.beta.sessions.create(
  {
    agent: agent.id,  // string shorthand → latest version. Or: { type: "agent", id: agent.id, version: agent.version }
    environment_id: environmentId,
    title: "Hello World Session",
  },
);
```

**Session creation parameters:**

| Field           | Type     | Required | Description                                    |
| --------------- | -------- | -------- | ---------------------------------------------- |
| `agent`         | string or object | **Yes** | String shorthand `"agent_abc123"` (latest version) or `{type: "agent", id, version}` |
| `environment_id`| string   | **Yes**  | Environment ID                                 |
| `title`         | string   | No       | Human-readable name (appears in logs/dashboards) |
| `resources`     | array    | No       | Files, GitHub repos, or memory stores attached to the container at startup. Memory stores attach only at session creation (cannot be added via `resources.add()`). |
| `vault_ids`     | array    | No       | Vault IDs (`vlt_*`) — MCP credentials with auto-refresh. See `shared/managed-agents-tools.md` → Vaults. |
| `metadata`      | object   | No       | User-supplied key-value pairs                   |

**Agent configuration fields** (passed to `agents.create()`, not `sessions.create()`):

| Field         | Type     | Required | Description                                    |
| ------------- | -------- | -------- | ---------------------------------------------- |
| `name`        | string   | **Yes**  | Human-readable name (1–256 characters)         |
| `model`       | string or object | **Yes** | Claude model ID (bare string or `{id, speed}` object). All Claude 4.5+ supported. |
| `system`      | string   | No       | System prompt — defines the agent's behavior (up to 100K characters) |
| `tools`       | array    | No       | Three types: (1) built-in Claude Agent tools (`agent_toolset_20260401`), (2) MCP tools (`mcp_toolset`), and (3) custom client-side tools. Maximum 128. |
| `mcp_servers` | array    | No       | MCP server connections — standardized third-party capabilities (e.g., GitHub, Asana). Maximum 20, unique names. See `shared/managed-agents-tools.md` → MCP Servers. |
| `skills`      | array    | No       | Customized "best-practices" context with progressive disclosure. Maximum 64. See `shared/managed-agents-tools.md` → Skills. |
| `description` | string   | No       | Agent description (up to 2048 characters)      |
| `metadata`    | object   | No       | Arbitrary key-value pairs (max 16, keys ≤64 chars, values ≤512 chars) |

---

## Agents

**Every Managed Agents flow starts here.** The agent object is a persistent, versionable configuration: you create it once and then reference it by ID every time you start a session. No agent, no session.

### The Agent Object

The API is **flat** — `model`, `system`, `tools`, etc. are top-level fields, not wrapped in an `agent: {}` sub-object.

| Field              | Type     | Required | Description                                        |
| ------------------ | -------- | -------- | -------------------------------------------------- |
| `name`             | string   | Yes      | Human-readable name                                |
| `model`            | string   | Yes      | Claude model ID                                    |
| `system`           | string   | No       | System prompt                                      |
| `tools`            | array    | No       | Agent toolset / MCP toolset / custom tools         |
| `mcp_servers`      | array    | No       | MCP server connections                             |
| `skills`           | array    | No       | Skill references (max 64)                          |
| `description`      | string   | No       | Agent description                                  |
| `metadata`         | object   | No       | Arbitrary key-value pairs                          |

### Lifecycle: Create Once, Run Many, Update In Place

The agent is a **persistent resource**, not a per-run parameter. The intended pattern:

```
┌─ setup (once) ─────────┐     ┌─ runtime (every invocation) ─┐
│ agents.create()        │     │ sessions.create(             │
│   → store agent_id     │ ──→ │   agent={type:..., id: ID}   │
│     in config/env/db   │     │ )                            │
└────────────────────────┘     └──────────────────────────────┘
```

**Anti-pattern:** calling `agents.create()` at the start of every script run. This accumulates orphan agent objects, pays creation latency on every run, and defeats the versioning model. If you see `agents.create()` inside a function called per-request or per-cron-tick — that's wrong; move it into one-time setup and store the ID.

### Versioning

Each `POST /v1/agents/{id}` (update) creates a new immutable version (numeric timestamp, e.g. `1772585501101368014`). The agent's history is append-only — you cannot edit a past version.

**Why version:**
- **Reproducibility** — pin a session to a known-good configuration: `{type: "agent", id, version: 3}`
- **Safe iteration** — update an agent without breaking sessions already running on an older version
- **Rollback** — if a new system prompt regresses, pin new sessions to the previous version while you debug

**`version` is optional.** Omit it (or use the string shorthand `agent="agent_abc123"`) to get the latest version at session-creation time. Pass it explicitly (`{type: "agent", id, version: N}`) to pin for reproducibility.

**Getting the version to pin.** `agents.create()` and `agents.update()` both return `version` in the response. Save it alongside `agent_id`. To fetch the current latest for an existing agent: `GET /v1/agents/{id}` → `.version`.

**When to update vs. create new.** Update (`POST /v1/agents/{id}`) when it's conceptually the same agent with adjusted behavior (better prompt, additional tool). Create a new agent when it's a different persona/purpose. Rule of thumb: if you would give it the same `name` — update.

### Agent Endpoints

| Operation        | Method   | Path                                  |
| ---------------- | -------- | ------------------------------------- |
| Create           | `POST`   | `/v1/agents`                          |
| List             | `GET`    | `/v1/agents`                          |
| Get              | `GET`    | `/v1/agents/{id}`                     |
| Update           | `POST`   | `/v1/agents/{id}`                     |
| Archive          | `POST`   | `/v1/agents/{id}/archive`             |

> ⚠️ **Archiving is permanent.** Archiving makes the agent read-only: existing sessions keep working, but **new sessions cannot reference it**, and there is no unarchive. Since the agent has no `delete`, this is the terminal lifecycle state. Never archive a production agent as routine cleanup — confirm with the user first.

### Using an Agent in a Session

Reference the agent by string ID (latest version) or by object with an explicit version:

```python
# String shorthand — uses the agent's latest version
session = client.beta.sessions.create(
    agent=agent.id,
    environment_id=environment_id,
)

# Or pin to a specific version (int)
session = client.beta.sessions.create(
    agent={"type": "agent", "id": agent.id, "version": agent.version},
    environment_id=environment_id,
)
```

