# Managed Agents — Memory Stores

> **Public beta.** Memory stores ship under the beta header `managed-agents-2026-04-01`; the SDK sets it automatically on every `client.beta.memory_stores.*` call. If `client.beta.memory_stores` is missing, upgrade to the latest SDK version.

Sessions are ephemeral by default — when a session ends, everything the agent learned disappears. A **memory store** is a workspace-scoped collection of small text documents that persists across sessions. When attached to a session (via `resources[]`), it mounts into the container as a filesystem directory; the agent reads and writes through it with normal file tools, and a note in the system prompt tells the agent the mount exists.

Every change to memory creates an immutable **memory version** (`memver_...`), giving you an audit trail and surgical rollback/redact.

## Object Model

| Object | ID prefix | Scope | Notes |
| --- | --- | --- | --- |
| Memory store | `memstore_...` | Workspace | Attached to a session via `resources[]` |
| Memory | `mem_...` | Store | A single text file addressed by `path` (≤ 100KB each — prefer many small files) |
| Memory version | `memver_...` | Memory | Immutable snapshot per change; `operation` ∈ `created` / `modified` / `deleted` |

## Creating a Store

`description` is passed to the agent so it understands what the store contains — write it for the model, not for humans.

```python
store = client.beta.memory_stores.create(
    name="User Preferences",
    description="Per-user preferences and project context.",
)
print(store.id)  # memstore_01Hx...
```

Other SDKs: TypeScript `client.beta.memoryStores.create({...})`; Go `client.Beta.MemoryStores.New(ctx, ...)`. For the full per-language table, see `shared/managed-agents-api-reference.md` → SDK Method Reference.

Stores support `retrieve` / `update` / `list` (with filters `include_archived`, `created_at_{gte,lte}`) / `delete` / **`archive`**. Archive makes the store read-only — existing session attachments keep working, new sessions cannot reference it; there is no unarchive.

### Seeding Content (optional)

Pre-load reference material before any session starts. `memories.create` creates a memory at the given `path`; if a memory already exists there, the call returns `409` (`memory_path_conflict_error`, with `conflicting_memory_id`). The store ID is the first positional argument.

```python
client.beta.memory_stores.memories.create(
    store.id,
    path="/formatting_standards.md",
    content="All reports use GAAP formatting. Dates are ISO-8601...",
)
```

## Attaching to a Session

Memory stores go in the session's `resources[]` array alongside `file` and `github_repository` resources (see `shared/managed-agents-environments.md` → Resources). Memory stores attach **only at session creation** — `sessions.resources.add()` does not accept `memory_store`.

```python
session = client.beta.sessions.create(
    agent=agent.id,
    environment_id=environment.id,
    resources=[
        {
            "type": "memory_store",
            "memory_store_id": store.id,
            "access": "read_write",  # or "read_only"; default is "read_write"
            "instructions": "User preferences and project context. Check before starting any task.",
        }
    ],
)
```

| Field | Required | Notes |
| --- | --- | --- |
| `type` | ✅ | `"memory_store"` |
| `memory_store_id` | ✅ | `memstore_...` |
| `access` | — | `"read_write"` (default) or `"read_only"` — enforced at the filesystem level on mount |
| `instructions` | — | Session-specific instructions for this store, in addition to the store's `name`/`description`. ≤ 4096 characters. |

**Maximum 8 memory stores per session.** Attach multiple when different memory slices have different owners or lifecycles — for example, one read-only store with shared references plus one read-write store per user, or one store per end user/team/project sharing a common agent configuration.

### How the Agent Sees It (FUSE mount)

Each attached store mounts in the session container at `/mnt/memory/<store-name>/`. The agent interacts with it through standard file tools (`bash`, `read`, `write`, `edit`, `glob`, `grep`) — there are no special memory tools. `access: "read_only"` makes the mount read-only at the filesystem level; `"read_write"` lets the agent create, edit, and delete files under it. A short description of each mount (name, path, `instructions`, access) is automatically inserted into the system prompt, so the agent knows the store exists without you mentioning it.

Writes the agent makes under the mount are persisted back to the store and create memory versions the same way host-side `memories.update` calls do.

## Direct Memory Management (host-side)

Use this for review workflows, fixing bad memories, or seeding the store outside the main flow.

### List

Returns `Memory | MemoryPrefix` entries — `MemoryPrefix` (`type: "memory_prefix"`, only `path`) is a directory-like node in hierarchical listings. Use `path_prefix` to scope (with trailing slash: `"/notes/"` matches `/notes/a.md` but not `/notes_backup/old.md`) and `depth` to limit tree traversal. `order_by` / `order` sort the result. Pass `view="full"` to include `content` on each item; the default `"basic"` returns only metadata.

```python
for m in client.beta.memory_stores.memories.list(store.id, path_prefix="/"):
    if m.type == "memory":
        print(f"{m.path}  ({m.content_size_bytes} bytes, sha={m.content_sha256[:8]})")
    else:  # "memory_prefix"
        print(f"{m.path}/")
```

### Read

```python
mem = client.beta.memory_stores.memories.retrieve(memory_id, memory_store_id=store.id)
print(mem.content)
```

`retrieve` defaults to `view="full"` (content included); `view` matters mostly for list endpoints.

### Create vs. update

| Operation | Addressed by | Semantics |
| --- | --- | --- |
| `memories.create(store_id, path=..., content=...)` | **Path** | Creates at `path`. `409` (`memory_path_conflict_error`, includes `conflicting_memory_id`) if the path is already taken. |
| `memories.update(mem_id, memory_store_id=..., path=..., content=...)` | **`mem_...` ID** | Modifies an existing memory. Changes `content`, `path` (rename), or both. Renaming to a taken path returns the same `409 memory_path_conflict_error`. |

```python
mem = client.beta.memory_stores.memories.create(
    store.id,
    path="/preferences/formatting.md",
    content="Always use tabs, not spaces.",
)

client.beta.memory_stores.memories.update(
    mem.id,
    memory_store_id=store.id,
    path="/archive/2026_q1_formatting.md",  # rename
)
```

### Optimistic Concurrency (precondition on `update`)

`memories.update` accepts `precondition` so you can read → modify → write back without clobbering data with a concurrent writer. The only supported type is `content_sha256`. On a mismatch, the API returns `409` (`memory_precondition_failed_error`) — re-read and retry with the current state.

```python
client.beta.memory_stores.memories.update(
    mem.id,
    memory_store_id=store.id,
    content="CORRECTED: Always use 2-space indentation.",
    precondition={"type": "content_sha256", "content_sha256": mem.content_sha256},
)
```

### Delete

```python
client.beta.memory_stores.memories.delete(mem.id, memory_store_id=store.id)
```

Pass `expected_content_sha256` for conditional deletion.

## Audit and Rollback — Memory Versions

Every change creates an immutable `memver_...` snapshot. Versions accumulate over the parent memory's lifetime; `memories.retrieve` always returns the current head, the versions endpoints give you the history.

| Operation that triggers it | `operation` field on the version |
| --- | --- |
| `memories.create` at a new path | `"created"` |
| `memories.update` changing `content`, `path`, or both (or an agent-side write to the mount) | `"modified"` |
| `memories.delete` | `"deleted"` |

Each version also records `created_by` — an actor object with `type` ∈ `session_actor` / `api_actor` / `user_actor` — and, after redaction, `redacted_at` + `redacted_by`.

### List Versions

Newest first, paginated. Filter by `memory_id`, `operation`, `session_id`, `api_key_id`, or `created_at_gte` / `created_at_lte`. Pass `view="full"` to include `content`; default is metadata only.

```python
for v in client.beta.memory_stores.memory_versions.list(store.id, memory_id=mem.id):
    print(f"{v.id}: {v.operation}")
```

### Retrieve a Version

```python
version = client.beta.memory_stores.memory_versions.retrieve(
    version_id, memory_store_id=store.id
)
print(version.content)
```

### Redact a Version

Wipes content from a historical version while preserving the audit trail (actor + timestamps). Clears `content`, `content_sha256`, `content_size_bytes`, and `path`; everything else remains. Use this for leaked secrets, PII, or user data deletion requests.

```python
client.beta.memory_stores.memory_versions.redact(version_id, memory_store_id=store.id)
```

## Endpoint Reference

See `shared/managed-agents-api-reference.md` → Memory Stores / Memories / Memory Versions for the full HTTP method/path tables. The raw HTTP base path:

```
POST   /v1/memory_stores
POST   /v1/memory_stores/{memory_store_id}/archive
GET    /v1/memory_stores/{memory_store_id}/memories
PATCH  /v1/memory_stores/{memory_store_id}/memories/{memory_id}
GET    /v1/memory_stores/{memory_store_id}/memory_versions
POST   /v1/memory_stores/{memory_store_id}/memory_versions/{version_id}/redact
```

For cURL examples and the CLI (`ant beta:memory-stores ...`), WebFetch the Memory URL from `shared/live-sources.md` → Managed Agents.
