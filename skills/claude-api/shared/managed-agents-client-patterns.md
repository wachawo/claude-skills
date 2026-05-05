# Managed Agents — Common Client Patterns

Patterns you'll write on the client side when steering a Managed Agent session, based on working SDK examples.

Code examples are in TypeScript; Python and cURL have the same shape — see `python/managed-agents/README.md` and `curl/managed-agents.md` for equivalents.

---

## 1. Lossless Stream Reconnect

**Problem.** SSE has no replay. If the connection drops mid-session, a naive reconnect opens the stream "from now" — and you silently miss every event emitted in the gap.

**Solution.** On reconnect, first fetch the full event history via `events.list()` *before* starting to read the live stream, and dedupe by event ID as the live stream catches up.

```ts
const seenEventIds = new Set<string>()
const stream = await client.beta.sessions.events.stream(session.id)

// Stream is now open and buffering server-side. Read history first.
for await (const event of client.beta.sessions.events.list(session.id)) {
  seenEventIds.add(event.id)
  handle(event)
}

// Tail the live stream. Dedupe only gates handle() — terminal checks must run
// even for already-seen events, or a terminal event that was in the history
// response gets skipped by `continue` and the loop never exits.
for await (const event of stream) {
  if (!seenEventIds.has(event.id)) {
    seenEventIds.add(event.id)
    handle(event)
  }
  if (event.type === 'session.status_terminated') break
  if (event.type === 'session.status_idle' && event.stop_reason.type !== 'requires_action') break
}
```

---

## 2. `processed_at` — Queued vs. Processed

Every event on the stream carries `processed_at` (ISO 8601). For client-sent events (`user.message`, `user.interrupt`, `user.tool_confirmation`, `user.custom_tool_result`), it is `null` while the event is queued but not yet picked up by the agent, and is filled in once the agent processes it. The same event appears on the stream twice — once with `processed_at: null`, once with a timestamp.

```ts
for await (const event of stream) {
  if (event.type === 'user.message') {
    if (event.processed_at == null) onQueued(event.id)
    else onProcessed(event.id, event.processed_at)
  }
}
```

Use this to drive a pending → acknowledged UI state for everything you send. How you correlate a locally-rendered optimistic message with a server `event.id` depends on your application (typically via the return value of `events.send()` or FIFO order).

---

## 3. Interrupt a Running Session

Send `user.interrupt` as a regular event. The session continues until a safe boundary, then transitions to idle.

```ts
await client.beta.sessions.events.send(session.id, {
  events: [{ type: 'user.interrupt' }],
})

// Drain until the session is truly done — see Pattern 5 for the full gate.
for await (const event of stream) {
  if (event.type === 'session.status_terminated') break
  if (
    event.type === 'session.status_idle' &&
    event.stop_reason.type !== 'requires_action'
  ) break
}
```

Reference: `interrupt.ts` — sends an interrupt the moment it sees `span.model_request_start`, drains the stream to idle, then verifies via `sessions.retrieve()`.

---

## 4. `tool_confirmation` Round-Trip

When the agent has `permission_policy: { type: 'always_ask' }`, every call to that tool emits an `agent.tool_use` event with `evaluated_permission === 'ask'`, and the session goes idle awaiting a decision. Reply with `user.tool_confirmation`.

```ts
for await (const event of stream) {
  if (event.type === 'agent.tool_use' && event.evaluated_permission === 'ask') {
    await client.beta.sessions.events.send(session.id, {
      events: [{
        type: 'user.tool_confirmation',
        tool_use_id: event.id,         // not a toolu_ id — use event.id
        result: 'allow',               // or 'deny'
        // deny_message: '...',        // optional, only with result: 'deny'
      }],
    })
  }
}
```

Key points.
- `tool_use_id` is `event.id` (typically `sevt_...`), **not** a `toolu_...` ID.
- `result` is `'allow' | 'deny'`. Use `deny_message` to tell the model *why* you denied — it gets passed to the agent.
- Multiple tools waiting: respond once per `agent.tool_use` event with `evaluated_permission === 'ask'`.

Reference: `tool-permissions.ts`.

---

## 5. Correct idle-Exit Gate

Don't break on `session.status_idle` alone. The session goes idle transiently — for example, between parallel tool executions, while waiting for `user.tool_confirmation` or `user.custom_tool_result`. Break on idle with a terminal `stop_reason` or on `session.status_terminated`.

```ts
for await (const event of stream) {
  handle(event)
  if (event.type === 'session.status_terminated') break
  if (event.type === 'session.status_idle') {
    if (event.stop_reason.type === 'requires_action') continue // waiting on you — handle it
    break // end_turn or retries_exhausted — both terminal
  }
}
```

`stop_reason.type` values for `session.status_idle`:
- `requires_action` — the agent is waiting for a client event (tool confirmation, custom tool result). Handle it; do not break.
- `retries_exhausted` — terminal failure. Break, then check `sessions.retrieve()` for the error state.
- `end_turn` — normal completion.

---

## 6. Post-Idle Status-Write Race

The SSE stream emits `session.status_idle` slightly before the queryable session status reflects it. Clients that exit on idle and immediately call `sessions.delete()` or `sessions.archive()` periodically get a 400 with "cannot delete/archive while running."

Poll before cleanup:

```ts
let s
for (let i = 0; i < 10; i++) {
  s = await client.beta.sessions.retrieve(session.id)
  if (s.status !== 'running') break
  await new Promise(r => setTimeout(r, 200))
}
if (s?.status !== 'running') {
  await client.beta.sessions.archive(session.id)
} // else: still running after 2s — don't archive, let it settle or escalate
```

---

## 7. Stream First, Then Send

Always open the stream **before** sending the kickoff event. Otherwise the agent may process the event and emit the first events before your consumer connects — and you'll miss them.

```ts
const stream = await client.beta.sessions.events.stream(session.id)
await client.beta.sessions.events.send(session.id, {
  events: [{ type: 'user.message', content: [{ type: 'text', text: 'Hello' }] }],
})
for await (const event of stream) { /* ... */ }
```

The `Promise.all([stream, send])` form also works, but stream-first is simpler and has the same effect — the stream starts buffering the moment it opens.

---

## 8. File-Mount Pitfalls

**A mounted resource has a different `file_id` than the file you uploaded.** Session creation creates a session-scoped copy.

```ts
const uploaded = await client.beta.files.upload({ file })
// uploaded.id         → the original file
const session = await client.beta.sessions.create({
  /* ... */
  resources: [{ type: 'file', file_id: uploaded.id, mount_path: '/workspace/data.csv' }],
})
// session.resources[0].file_id !== uploaded.id  ← different IDs
```

Delete the original via `files.delete(uploaded.id)`; the session-scoped copy is garbage-collected with the session. `mount_path` must be absolute — see `shared/managed-agents-environments.md`.

---

## 9. Secrets for non-MCP APIs and CLIs — Keep Them Host-Side via Custom Tools

**Problem.** You want the agent to call a third-party API or run a CLI that needs a secret (API key, token, service-account credential), but there is currently no way to set environment variables inside the session container, and vaults today only hold MCP credentials — they are not exposed in the container's shell. So `curl`, installed CLIs, or SDK clients running through the `bash` tool have no first-class place to read the secret from.

**Solution.** Move the authenticated call to your side. Declare a custom tool on the agent; when the agent emits `agent.custom_tool_use`, your orchestrator (the process reading the SSE stream) executes the call with its own credentials and replies via `user.custom_tool_result`. The container never sees the key.

```ts
// Agent template: declare the tool, no credentials
tools: [{ type: 'custom', name: 'linear_graphql', input_schema: { /* query, vars */ } }]

// Orchestrator: handle the call with host-side creds
for await (const event of stream) {
  if (event.type === 'agent.custom_tool_use' && event.name === 'linear_graphql') {
    const result = await linear.request(event.input.query, event.input.vars) // host's key
    await client.beta.sessions.events.send(session.id, {
      events: [{ type: 'user.custom_tool_result', tool_use_id: event.id, result }],
    })
  }
}
```

The same shape works for the `gh` CLI, local eval scripts, or anything else that requires host-side auth or binaries.

**Security note.** This does not expose a public endpoint. `agent.custom_tool_use` arrives on the SSE stream, which your orchestrator already keeps open under your Anthropic API key, and `user.custom_tool_result` goes back via `events.send()` under the same key. Your orchestrator is a client, not a server; nothing unauthenticated is listening.

**Don't embed API keys in the system prompt or user messages as a workaround.** Prompts and messages are persisted in the session's event history, returned by `events.list()`, and end up in compaction summaries — a secret left there is durably stored and readable via the API for the lifetime of the session.
