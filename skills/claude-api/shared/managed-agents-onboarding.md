# Managed Agents — Onboarding Flow

> **Invoked via `/claude-api managed-agents-onboard`?** You're in the right place. Walk through the interview below — don't summarize it back to the user, ask the questions.

Use this when the user wants to set up a Managed Agent from scratch. Three steps: **know-vs-explore branch → templated configuration → session setup**. Finish by emitting working code.

> Read `shared/managed-agents-core.md` alongside this — that file has the full per-setting details. This document is an interview script, not a reference.

---

Claude Managed Agents is a hosted agent: Anthropic runs the agent loop on its orchestration layer and provides a sandboxed per-session container where the agent's tools execute. You provide the agent configuration and the environment configuration; the harness — event stream, sandbox orchestration, prompt caching, context compression, and extended thinking — is handled for you.

**What you provide:**
- **Agent configuration** — tools, skills, model, system prompt. Reusable and versioned.
- **Environment configuration** — the sandbox in which your agent's tools run (networking, packages). Reusable across agents.

Each agent run is a **session**.

---

## 1. Know or Explore?

Ask the user:

> Do you already know what kind of agent you want to build, or would you like to explore common patterns first?

### Explore path — show patterns

Four options, the same runtime code path (`sessions.create()` → `sessions.events.send()` → stream). Only the trigger and sink differ.

| Pattern | Trigger | Example |
|---|---|---|
| Event-triggered | Webhook | GitHub PR push → CMA (GitHub tool) → Slack |
| Scheduled | Cron | Daily brief: browser + GitHub + Jira → CMA → Slack |
| Fire-and-forget PR | Human | Slack slash-command → CMA (GitHub tool) → PR passing CI |
| Research + dashboard | Human | Topic → CMA (web search + `frontend-design` skill) → HTML dashboard |

Ask which shape fits, then continue down the Know path using it as the reference.

### Know path — templated setup

Three rounds. Group the questions inside each round; do not ask them one by one.

**Round A — Tools.** Start here; it's the most concrete part. Three types; ask which the user needs (any combination):

| Type | What it is | How to drive it |
|---|---|---|
| **Prebuilt Claude Agent tools** (`agent_toolset_20260401`) | Ready-to-use: `bash`, `read`, `write`, `edit`, `glob`, `grep`, `web_fetch`, `web_search`. Enable all together or individually via `enabled: true/false`. | Recommend enabling the full toolset. List the 8 tools so the user knows what they get. Full details: `shared/managed-agents-tools.md` → Agent Toolset. |
| **MCP tools** | Third-party integrations (GitHub, Linear, Asana, etc.) via `mcp_toolset`. Credentials live in a vault, not inline. | Ask which services. For each, walk through the MCP server URL + vault credentials. Full details: `shared/managed-agents-tools.md` → MCP Servers + Vaults. |
| **Custom tools** | The user's application handles these tool calls — the agent emits `agent.custom_tool_use`, the application sends the result. | Ask for each tool: name, description, input schema. The application code that handles the event is *their* code, do not generate it. Full details: `shared/managed-agents-tools.md` → Custom Tools. |

**Round B — Skills, files, and repositories.** What the agent has at hand at start.

*Skills* — two types; both behave the same — Claude uses them automatically when appropriate. Maximum 64 per agent.
- [ ] **Pre-built Agent Skills**: `xlsx`, `docx`, `pptx`, `pdf`. Reference by name.
- [ ] **Custom Skills**: skills uploaded to the user's organization via the Skills API. Reference by `skill_id` + optional `version`. If the skill does not yet exist, walk the user through `POST /v1/skills` + `POST /v1/skills/{id}/versions` (beta header `skills-2025-10-02`). Full details: `shared/managed-agents-tools.md` → Skills + Skills API.

*GitHub repositories* — does the agent need any repositories on disk? For each:
- [ ] Repo URL (`https://github.com/org/repo`)
- [ ] `authorization_token` (PAT or repository-scoped GitHub App token)
- [ ] Optional `mount_path` (defaults to `/workspace/<repo-name>`) and `checkout` (branch or SHA)

Emit as `resources: [{type: "github_repository", url, authorization_token, ...}]`. Full details: `shared/managed-agents-environments.md` → GitHub Repositories.

> ‼️ **Creating a PR also requires the GitHub MCP server.** `github_repository` only provides filesystem access — to open PRs, additionally attach the GitHub MCP server in Round A and provide credentials via the vault. Workflow: edit files in the mounted repository → push the branch via `bash` → create the PR via the MCP `create_pull_request` tool.

*Files* — any local files to seed the session? For each:
- [ ] Upload via the Files API → save `file_id`
- [ ] Choose `mount_path` — absolute, e.g. `/workspace/data.csv` (parent directories are created automatically; files mount read-only)

Emit as `resources: [{type: "file", file_id, mount_path}]`. Maximum 999 file resources. The agent's working directory defaults to `/workspace`. Full details: `shared/managed-agents-environments.md` → Files API.

**Round C — Environment + identity:**
- [ ] Networking: unrestricted internet from the container, or restrict egress to specific hosts? (If restricted, MCP server domains must be in `allowed_hosts` or those tools will silently fail.)
- [ ] Name?
- [ ] Job (one or two sentences — becomes the system prompt)?
- [ ] Model? (defaults to `claude-opus-4-7`)

---

## 2. Session Setup

Per run. Points at the agent + environment, attaches credentials, starts.

**Vault credentials** (if the agent declared MCP servers):
- [ ] Existing vault, or create one? (`client.beta.vaults.create()` + `vaults.credentials.create()`)

Credentials are write-only, matched to MCP servers by URL, and refreshed automatically. See `shared/managed-agents-tools.md` → Vaults.

**Kickoff:**
- [ ] First message to the agent?

Session creation blocks until all resources are mounted. Open the event stream before sending the kickoff. The stream is SSE; stop on `session.status_terminated` or on `session.status_idle` with a terminal `stop_reason` — that is, anything except `requires_action`, which is emitted transiently while the session waits for a tool confirmation or a custom tool result (see `shared/managed-agents-client-patterns.md` Pattern 5). Usage arrives in `span.model_request_end`. Artifacts written by the agent land in `/mnt/session/outputs/` — download via `files.list({scope_id: session.id, betas: ["managed-agents-2026-04-01"]})`.

---

## 3. Emit Code

Go straight from the last interview answer to code — no preamble about setup-vs-runtime separation, no "critical thing to internalize…", no lecture about `agents.create()` being called once. The two-block structure below already shows that; don't comment on it. Generate **two clearly separated blocks** for each detected language (Python/TS/cURL — see SKILL.md → Language Detection):

**Block 1 — Setup (runs once, IDs are saved):**
1. `environments.create()` → save `env_id`
2. `agents.create()` with everything from §Round A–C → save `agent_id` and `agent_version`

Label: `# ONE-TIME SETUP — run once, save the IDs to config/.env`

**Block 2 — Runtime (runs each invocation):**
1. Load `env_id` + `agent_id` from config/env
2. `sessions.create(agent=AGENT_ID, environment_id=ENV_ID, resources=[...], vault_ids=[...])`
3. Open the stream, `events.send()` for the kickoff, loop until `session.status_terminated` or `session.status_idle && stop_reason.type !== 'requires_action'` (see `shared/managed-agents-client-patterns.md` Pattern 5 for the full gate — do not break on a bare `session.status_idle`)

> ⚠️ **Never emit `agents.create()` and `sessions.create()` together in one unguarded block.** That teaches the user to create a new agent on every run — anti-pattern #1. If they need one script, wrap the agent creation in `if not os.getenv("AGENT_ID"):`.

Take the exact syntax from `python/managed-agents/README.md`, `typescript/managed-agents/README.md`, or `curl/managed-agents.md`. Do not invent field names.
