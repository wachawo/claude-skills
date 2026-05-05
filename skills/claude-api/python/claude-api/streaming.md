# Streaming — Python

## Quick Start

```python
with client.messages.stream(
    model="claude-opus-4-7",
    max_tokens=64000,
    messages=[{"role": "user", "content": "Write a story"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### Async

```python
async with async_client.messages.stream(
    model="claude-opus-4-7",
    max_tokens=64000,
    messages=[{"role": "user", "content": "Write a story"}]
) as stream:
    async for text in stream.text_stream:
        print(text, end="", flush=True)
```

---

## Handling Different Content Types

Claude can return text, thinking blocks, or tool use. Handle each appropriately:

> **Opus 4.7 / Opus 4.6:** use `thinking: {type: "adaptive"}`. On older models, use `thinking: {type: "enabled", budget_tokens: N}`.

```python
with client.messages.stream(
    model="claude-opus-4-7",
    max_tokens=64000,
    thinking={"type": "adaptive"},
    messages=[{"role": "user", "content": "Analyze this problem"}]
) as stream:
    for event in stream:
        if event.type == "content_block_start":
            if event.content_block.type == "thinking":
                print("\n[Thinking...]")
            elif event.content_block.type == "text":
                print("\n[Response:]")

        elif event.type == "content_block_delta":
            if event.delta.type == "thinking_delta":
                print(event.delta.thinking, end="", flush=True)
            elif event.delta.type == "text_delta":
                print(event.delta.text, end="", flush=True)
```

---

## Streaming with Tool Use

The Python tool runner currently returns completed messages. Use streaming for individual API calls inside a manual loop if you need token-by-token streaming together with tools:

```python
with client.messages.stream(
    model="claude-opus-4-7",
    max_tokens=64000,
    tools=tools,
    messages=messages
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

    response = stream.get_final_message()
    # Continue with tool execution if response.stop_reason == "tool_use"
```

---

## Getting the Final Message

```python
with client.messages.stream(
    model="claude-opus-4-7",
    max_tokens=64000,
    messages=[{"role": "user", "content": "Hello"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

    # Get full message after streaming
    final_message = stream.get_final_message()
    print(f"\n\nTokens used: {final_message.usage.output_tokens}")
```

---

## Streaming with Progress Updates

```python
def stream_with_progress(client, **kwargs):
    """Stream a response with progress updates."""
    total_tokens = 0
    content_parts = []

    with client.messages.stream(**kwargs) as stream:
        for event in stream:
            if event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    text = event.delta.text
                    content_parts.append(text)
                    print(text, end="", flush=True)

            elif event.type == "message_delta":
                if event.usage and event.usage.output_tokens is not None:
                    total_tokens = event.usage.output_tokens

        final_message = stream.get_final_message()

    print(f"\n\n[Tokens used: {total_tokens}]")
    return "".join(content_parts)
```

---

## Error Handling in Streams

```python
try:
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=64000,
        messages=[{"role": "user", "content": "Write a story"}]
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
except anthropic.APIConnectionError:
    print("\nConnection lost. Please retry.")
except anthropic.RateLimitError:
    print("\nRate limited. Please wait and retry.")
except anthropic.APIStatusError as e:
    print(f"\nAPI error: {e.status_code}")
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

1. **Always flush the output buffer** — use `flush=True` so tokens appear immediately
2. **Handle partial responses** — if the stream breaks, content may be incomplete
3. **Track token usage** — the `message_delta` event contains usage information
4. **Use timeouts** — set timeouts appropriate for your application
5. **Default to streaming** — `.get_final_message()` returns the full response even when streaming, giving you timeout protection without needing to handle events manually
