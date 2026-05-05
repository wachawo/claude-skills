# Managed Agents — Events and Steering

## Events

### Sending Events

Send events to the session via `POST /v1/sessions/{id}/events`.

| Event type                | When to send                                         |
| ------------------------- | --------------------------------------------------- |
| `user.message`            | Send a user message |
| `user.interrupt`          | Interrupt the agent's work mid-execution |
| `user.tool_confirmation`  | Confirm/deny a tool call (under the `always_ask` policy) |
| `user.custom_tool_result` | Provide a custom tool call's result |

### Receiving Events

Two ways:

1. **Streaming (SSE)**: `GET /v1/sessions/{id}/events/stream` — Server-Sent Events in real time. **Long-lived** — the server sends periodic heartbeats to keep the connection alive.
2. **Polling**: `GET /v1/sessions/{id}/events` — paginated list of events (query parameters: `limit` defaults to 1000, `page`). **Returns immediately** — this is a normal paginated GET, not long-poll.

Every received event has `id`, `type`, and `processed_at` (ISO 8601; `null` if not yet processed by the agent).

> ⚠️ **Reliable polling (raw HTTP).** If you bypass the SDK and write your own polling loop, do not rely on `requests` or `httpx` timeouts as total-time limits — these are **per-chunk** read timeouts that reset on each incoming byte. A slowly trickling response (heartbeats, a stalled chunked-encoding body, a misbehaving proxy) can block the call indefinitely even with `timeout=(5, 60)` or `httpx.Timeout(120)`. Neither library has a built-in "total wall-clock" timeout. For a hard deadline: track `time.monotonic()` at the loop level and abort/cancel if a single request exceeds your budget (e.g., via a watchdog thread or `asyncio.wait_for()` around async httpx). **Prefer the SDK** — `client.beta.sessions.events.stream()` and `client.beta.sessions.events.list()` handle timeout and retry correctly.
>
> If `GET /v1/sessions/{id}/events` (paginated) ever hangs after receiving headers, you likely accidentally hit `GET /v1/sessions/{id}/events` or there was a server-side failure — report it; don't treat it as a client configuration issue.

### Event Types (received)

Event types use dot notation, grouped by namespace:

| Event type | Description |
| --- | --- |
| `agent.message` | Agent text output |
| `agent.thinking` | Extended thinking blocks |
| `agent.tool_use` | The agent used a built-in tool (`agent_toolset_20260401`) |
| `agent.tool_result` | Result from a built-in tool |
| `agent.mcp_tool_use` | The agent used an MCP tool |
| `agent.mcp_tool_result` | Result from an MCP tool |
| `agent.custom_tool_use` | The agent invoked a custom tool — the session goes idle, you reply via `user.custom_tool_result` |
| `agent.thread_context_compacted` | The conversation context was compacted |
| `session.status_idle` | The agent finished the current task and awaits input. Either waiting for a `user.message` to continue or blocked waiting for a `user.custom_tool_result` or `user.tool_confirmation`. The attached `stop_reason` carries more information about why the agent stopped. |
| `session.status_running` | The session has started executing and the agent is actively working. |
| `session.status_rescheduled` | The session is (re)scheduled after a recoverable error and ready to be picked up by the orchestration system. |
| `session.status_terminated` | The session has ended and entered an irreversible, unusable state. |
| `session.error` | Error during processing |
| `span.model_request_start` | Start of model inference |
| `span.model_request_end` | End of model inference |

The stream also returns user-sent events (`user.message`, `user.interrupt`, `user.tool_confirmation`, `user.custom_tool_result`).

---

## Steering Patterns

Practical patterns for steering the session through the event interface.

### Stream-First Ordering

**Open the stream before sending events.** The stream delivers only events that occur *after* it is opened — it does not replay the current state or event history. If you send a message first and then open the stream, early events (including fast status transitions) arrive in a single buffered batch and you lose the ability to react in real time.

```ts
// ✅ Correct — stream and send concurrently
const [response] = await Promise.all([
  streamEvents(sessionId),   // opens SSE connection
  sendMessage(sessionId, text),
]);

// ❌ Wrong — events before stream opens arrive as a single buffered batch
await sendMessage(sessionId, text);
const response = await streamEvents(sessionId);
```

**For full history** use `GET /v1/sessions/{id}/events` (paginated list) — the stream only gives you live events from the moment of connection onward.

### Reconnecting After a Dropped Stream

**The SSE stream has no replay.** If your connection drops (httpx read timeout, network failure) and you reconnect, you only receive events emitted *after* the reconnect. Any events emitted during the gap are lost from the stream.

**Consolidation pattern:** on every (re)connect, combine the stream with a history fetch and dedupe by event ID:

```python
def connect_with_consolidation(client, session_id):
    # 1. Open the SSE stream first
    stream = client.beta.sessions.events.stream(session_id=session_id)

    # 2. Fetch history to cover any gap
    history = client.beta.sessions.events.list(
        session_id=session_id,
    )

    # 3. Yield history first, then stream — dedupe by event.id
    seen = set()
    for ev in history.data:
        seen.add(ev.id)
        yield ev
    for ev in stream:
        if ev.id not in seen:
            seen.add(ev.id)
            yield ev
```

### Message Queueing

**You don't need to wait for a response before sending the next message.** User events are queued server-side and processed in order. This is useful for chat bridges where a user fires off quick follow-ups:

```ts
// All three go into one session; agent processes them in order
await sendMessage(sessionId, "Summarize the README");
await sendMessage(sessionId, "Actually also check the CONTRIBUTING guide");
await sendMessage(sessionId, "And compare the two");
// Stream once — agent responds to all three as a coherent turn
```

Events can be sent to a session at any time. You don't need to wait for a particular session status to queue new events via `client.beta.sessions.events.send()`.

### Interrupting

The `interrupt` event **bypasses the queue** (ahead of any pending user messages) and transitions the session to `idle`. Use it for "stop" / "nevermind" / "cancel" commands:

```ts
await client.beta.sessions.events.send(sessionId, {
  events: [{ type: 'interrupt' }],
});
```

The agent stops mid-task. It does not see the interrupt as a message — it simply stops working. Send the next `user` event to explain what to do instead.

> **Note**: `interrupt` events may currently arrive with empty IDs. When troubleshooting, use the `processed_at` timestamp together with the surrounding events' IDs.

### Event Payloads

Some events carry useful metadata beyond the status change itself:

`session.status_idle` — contains a `stop_reason` field that clarifies why the session is stopped and what next user action is required.
```json
{
  "id": "sevt_456",
  "processed_at": "2026-04-07T04:27:43.197Z",
  "stop_reason": {
    "event_ids": [
      "sevt_123"
    ],
    "type": "requires_action"
  },
  "type": "status_idle"
}
```

`span.model_request_end` contains a `model_usage` field for cost tracking and efficiency analysis:

```json
{
  "type": "span.model_request_end",
  "id": "sevt_456",
  "is_error": false,
  "model_request_start_id": "sevt_123",
  "model_usage": {
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 6656,
    "input_tokens": 3571,
    "output_tokens": 727
  },
  "processed_at": "2026-04-07T04:11:32.189Z"
}
```

**`agent.thread_context_compacted`** — emitted when the conversation history has been summarized to fit context. Includes `pre_compaction_tokens` so you know how much was compacted:

```json
{
  "id": "sevt_abc123",
  "processed_at": "2026-03-24T14:05:15.787Z",
  "type": "agent.thread_context_compacted"
}
```

### Archiving

When the session is done, archive it to free resources:

```ts
await client.beta.sessions.archive(sessionId);
```

> Archiving a **session** is routine cleanup: sessions are single-run and disposable. **Do not generalize this to agents or environments**: those are persistent, reusable resources, and archiving them is irreversible (no unarchive; new sessions cannot reference them). See `shared/managed-agents-overview.md` → Common Pitfalls.

