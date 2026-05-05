# Streaming — TypeScript

## Quick Start

```typescript
const stream = client.messages.stream({
  model: "claude-opus-4-7",
  max_tokens: 64000,
  messages: [{ role: "user", content: "Write a story" }],
});

for await (const event of stream) {
  if (
    event.type === "content_block_delta" &&
    event.delta.type === "text_delta"
  ) {
    process.stdout.write(event.delta.text);
  }
}
```

---

## Handling Different Content Types

> **Opus 4.7 / Opus 4.6:** use `thinking: {type: "adaptive"}`. On older models, use `thinking: {type: "enabled", budget_tokens: N}`.

```typescript
const stream = client.messages.stream({
  model: "claude-opus-4-7",
  max_tokens: 64000,
  thinking: { type: "adaptive" },
  messages: [{ role: "user", content: "Analyze this problem" }],
});

for await (const event of stream) {
  switch (event.type) {
    case "content_block_start":
      switch (event.content_block.type) {
        case "thinking":
          console.log("\n[Thinking...]");
          break;
        case "text":
          console.log("\n[Response:]");
          break;
      }
      break;
    case "content_block_delta":
      switch (event.delta.type) {
        case "thinking_delta":
          process.stdout.write(event.delta.thinking);
          break;
        case "text_delta":
          process.stdout.write(event.delta.text);
          break;
      }
      break;
  }
}
```

---

## Streaming with Tool Use (Tool Runner)

Use the tool runner with `stream: true`. The outer loop iterates over tool runner iterations (messages); the inner loop handles stream events:

```typescript
import Anthropic from "@anthropic-ai/sdk";
import { betaZodTool } from "@anthropic-ai/sdk/helpers/beta/zod";
import { z } from "zod";

const client = new Anthropic();

const getWeather = betaZodTool({
  name: "get_weather",
  description: "Get current weather for a location",
  inputSchema: z.object({
    location: z.string().describe("City and state, e.g., San Francisco, CA"),
  }),
  run: async ({ location }) => `72°F and sunny in ${location}`,
});

const runner = client.beta.messages.toolRunner({
  model: "claude-opus-4-7",
  max_tokens: 64000,
  tools: [getWeather],
  messages: [
    { role: "user", content: "What's the weather in Paris and London?" },
  ],
  stream: true,
});

// Outer loop: each tool runner iteration
for await (const messageStream of runner) {
  // Inner loop: stream events for this iteration
  for await (const event of messageStream) {
    switch (event.type) {
      case "content_block_delta":
        switch (event.delta.type) {
          case "text_delta":
            process.stdout.write(event.delta.text);
            break;
          case "input_json_delta":
            // Tool input being streamed
            break;
        }
        break;
    }
  }
}
```

---

## Getting the Final Message

```typescript
const stream = client.messages.stream({
  model: "claude-opus-4-7",
  max_tokens: 64000,
  messages: [{ role: "user", content: "Hello" }],
});

for await (const event of stream) {
  // Process events...
}

const finalMessage = await stream.finalMessage();
console.log(`Tokens used: ${finalMessage.usage.output_tokens}`);
```

---

## Stream Event Types

| Event type            | Description                              | When it fires                     |
| --------------------- | ---------------------------------------- | --------------------------------- |
| `message_start`       | Contains message metadata                | Once at the start                 |
| `content_block_start` | Start of a new content block             | When a text/tool_use block starts |
| `content_block_delta` | Incremental content update               | On each token/chunk               |
| `content_block_stop`  | Content block complete                   | When a block ends                 |
| `message_delta`       | Message-level updates                    | Contains `stop_reason`, usage     |
| `message_stop`        | Message complete                         | Once at the end                   |

## Best Practices

1. **Always flush the output buffer** — use `process.stdout.write()` for immediate display
2. **Handle partial responses** — if the stream breaks, content may be incomplete
3. **Track token usage** — the `message_delta` event contains usage information
4. **Use `finalMessage()`** — get the full `Anthropic.Message` object even when streaming. Do not wrap `.on()` events in `new Promise()` — `finalMessage()` handles all completion/error/abort states itself
5. **Buffer for web UIs** — consider buffering multiple tokens before rendering to avoid excessive DOM updates
6. **Use `stream.on("text", ...)` for deltas** — the `text` event yields only the delta string, which is simpler than manually filtering `content_block_delta` events
7. **For agentic loops with streaming**, see the [Streaming Manual Loop](./tool-use.md#streaming-manual-loop) section in tool-use.md, where `stream()` + `finalMessage()` are combined with the tool-use loop

## Raw SSE Format

When using raw HTTP (no SDK), the stream returns Server-Sent Events:

```
event: message_start
data: {"type":"message_start","message":{"id":"msg_...","type":"message",...}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":12}}

event: message_stop
data: {"type":"message_stop"}
```
