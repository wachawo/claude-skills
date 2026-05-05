# Tool Use Concepts

This file covers the conceptual foundations of tool use in the Claude API. For language-specific code examples, see the `python/`, `typescript/`, or other language folders. For decision heuristics about which tools to provide, how to manage context in long-running agents, and caching strategy, see `agent-design.md`.

## User-Defined Tools

### Tool Definition Structure

> **Note:** When using the Tool Runner (beta), tool schemas are auto-generated from function signatures (Python), Zod schemas (TypeScript), annotated classes (Java), `jsonschema` struct tags (Go), or `BaseTool` subclasses (Ruby). The raw JSON schema format below is for the manual approach — including PHP `BetaRunnableTool`, which wraps a run closure around a hand-written schema — or for SDKs without tool-runner support.

Each tool needs a name, description, and a JSON Schema for its inputs:

```json
{
  "name": "get_weather",
  "description": "Get current weather for a location",
  "input_schema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "City and state, e.g., San Francisco, CA"
      },
      "unit": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "description": "Temperature unit"
      }
    },
    "required": ["location"]
  }
}
```

**Best practices for tool definitions:**

- Use clear, descriptive names (e.g., `get_weather`, `search_database`, `send_email`)
- Write detailed descriptions — Claude uses them to decide when to call a tool
- Include descriptions for each property
- Use `enum` for parameters with a fixed set of values
- Mark only truly required parameters in `required`; make the rest optional with default values

---

### Tool Choice Options

Control when Claude uses tools:

| Value                             | Behavior                                          |
| --------------------------------- | ------------------------------------------------- |
| `{"type": "auto"}`                | Claude decides whether to use tools (default)     |
| `{"type": "any"}`                 | Claude must use at least one tool                 |
| `{"type": "tool", "name": "..."}` | Claude must use the specified tool                |
| `{"type": "none"}`                | Claude cannot use tools                           |

Any `tool_choice` value can also include `"disable_parallel_tool_use": true` to force Claude to use at most one tool per response. By default Claude can request multiple tool calls in a single response.

---

### Tool Runner vs. Manual Loop

**Tool Runner (recommended):** the SDK tool runner automatically handles the agentic loop — calling the API, detecting tool-use requests, executing your tool functions, returning results to Claude, and repeating until Claude stops calling tools. Available in the Python, TypeScript, Java, Go, Ruby, and PHP SDKs (beta). The Python SDK also provides MCP conversion helpers (`anthropic.lib.tools.mcp`) for converting MCP tools, prompts, and resources for use with the tool runner — see `python/claude-api/tool-use.md` for details.

**Manual agentic loop:** use this when you need fine-grained control over the loop (e.g., custom logging, conditional tool execution, human-in-the-loop approval). Loop until `stop_reason == "end_turn"`, always append the full `response.content` to preserve tool_use blocks, and make sure each `tool_result` includes the matching `tool_use_id`.

**Stop reasons for server-side tools:** when using server-side tools (code execution, web search, etc.), the API runs a server-side sampling loop. If that loop reaches the default 10-iteration limit, the response will have `stop_reason: "pause_turn"`. To continue, send the user message and assistant response again and make another API request — the server resumes from where it stopped. Do NOT add an extra user message like "Continue." — the API recognizes the trailing `server_tool_use` block and knows to resume automatically.

```python
# Handle pause_turn in your agentic loop
if response.stop_reason == "pause_turn":
    messages = [
        {"role": "user", "content": user_query},
        {"role": "assistant", "content": response.content},
    ]
    # Make another API request — server resumes automatically
    response = client.messages.create(
        model="claude-opus-4-7", messages=messages, tools=tools
    )
```

Set a `max_continuations` limit (e.g., 5) to prevent infinite loops. Full guide: `https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons`

> **Safety:** the tool runner automatically executes your tool functions when Claude requests them. For tools with side effects (sending email, mutating databases, financial transactions), validate inputs inside your tool functions and consider requiring confirmation for destructive operations. Use the manual agentic loop when you need human-in-the-loop approval before each tool execution.

---

### Handling Tool Results

When Claude uses a tool, the response contains a `tool_use` block. You need to:

1. Execute the tool with the provided input
2. Send the result back in a `tool_result` message
3. Continue the conversation

**Error handling in tool results:** when a tool execution fails, set `"is_error": true` and provide an informative error message. Claude typically acknowledges the error and either tries a different approach or asks for clarification.

**Multiple tool calls:** Claude can request multiple tools in a single response. Process all of them before continuing — return all results in a single `user` message.

---

## Server-Side Tools: Code Execution

The code execution tool lets Claude run code in a secure sandboxed container. Unlike user-defined tools, server-side tools run on Anthropic's infrastructure — you don't execute anything client-side. Just include the tool definition and Claude does the rest.

### Key Facts

- Runs in an isolated container (1 CPU, 5 GiB RAM, 5 GiB disk)
- No internet access (fully sandboxed)
- Python 3.11 with preinstalled data-science libraries
- Containers persist for 30 days and can be reused across requests
- Free when used with the web search/web fetch tools; otherwise $0.05/hour after 1550 free hours/month per organization

### Tool Definition

The tool requires no schema — just declare it in the `tools` array:

```json
{
  "type": "code_execution_20260120",
  "name": "code_execution"
}
```

Claude automatically gains access to `bash_code_execution` (run shell commands) and `text_editor_code_execution` (create/view/edit files).

### Preinstalled Python Libraries

- **Data science**: pandas, numpy, scipy, scikit-learn, statsmodels
- **Visualization**: matplotlib, seaborn
- **File processing**: openpyxl, xlsxwriter, pillow, pypdf, pdfplumber, python-docx, python-pptx
- **Math**: sympy, mpmath
- **Utilities**: tqdm, python-dateutil, pytz, sqlite3

Additional packages can be installed at runtime via `pip install`.

### Supported File Types for Upload

| Type   | Extensions                         |
| ------ | ---------------------------------- |
| Data   | CSV, Excel (.xlsx/.xls), JSON, XML |
| Images | JPEG, PNG, GIF, WebP               |
| Text   | .txt, .md, .py, .js, etc.          |

### Container Reuse

Reuse containers across requests to preserve state (files, installed packages, variables). Extract the `container_id` from the first response and pass it on subsequent requests.

### Response Structure

The response contains alternating text and tool result blocks:

- `text` — Claude's explanation
- `server_tool_use` — what Claude is doing
- `bash_code_execution_tool_result` — code execution output (check `return_code` for success/failure)
- `text_editor_code_execution_tool_result` — file operation results

> **Safety:** always sanitize file names through `os.path.basename()` / `path.basename()` before writing uploaded files to disk to prevent path traversal attacks. Write files to a dedicated output directory.

---

## Server-Side Tools: Web Search and Web Fetch

Web search and web fetch let Claude search the web and retrieve page content. They run server-side — just include the tool definitions and Claude automatically handles queries, fetching, and result processing.

### Tool Definitions

```json
[
  { "type": "web_search_20260209", "name": "web_search" },
  { "type": "web_fetch_20260209", "name": "web_fetch" }
]
```

### Dynamic Filtering (Opus 4.7 / Opus 4.6 / Sonnet 4.6)

The `web_search_20260209` and `web_fetch_20260209` versions support **dynamic filtering** — Claude writes and runs code to filter search results before they hit the context window, improving accuracy and token efficiency. Dynamic filtering is built into these tool versions and activates automatically; you don't need to declare a separate `code_execution` tool or pass any beta header.

```json
{
  "tools": [
    { "type": "web_search_20260209", "name": "web_search" },
    { "type": "web_fetch_20260209", "name": "web_fetch" }
  ]
}
```

Without dynamic filtering, the previous `web_search_20250305` version is also available.

> **Note:** include a separate `code_execution` tool only when your application needs code execution for its own purposes (data analysis, file processing, visualization) independent of web search. Including it alongside the `_20260209` web tools creates a second execution environment that can confuse the model.

---

## Server-Side Tools: Programmatic Tool Calling

In standard tool use, each tool call is a round trip: Claude invokes, the result enters Claude's context, Claude reasons, then invokes the next tool. Chains of calls accumulate latency and tokens — and most of that intermediate data is never needed again.

Programmatic tool calling lets Claude compose those calls into a script. The script runs in a code-execution container; when it calls a tool, the container suspends, the call executes, and the result returns to the running code (not to Claude's context). The script handles it with normal control flow. Only the final output returns to Claude. Use this when you chain many tool calls or when intermediate results are large and must be filtered before reaching the context window.

For full documentation, use WebFetch:

- URL: `https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling`

---

## Server-Side Tools: Tool Search

The tool search tool lets Claude dynamically discover tools from large libraries without loading every definition into the context window. Use it when you have many tools but only a few are relevant for any given request. Discovered tool schemas are appended to the request rather than replacing it — this preserves the prompt cache (see `agent-design.md` §Caching for Agents).

For full documentation, use WebFetch:

- URL: `https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool`

---

## Skills

Skills package task-specific instructions that Claude loads only when relevant. Each skill is a folder containing a `SKILL.md` file. The skill's short description sits in context by default; Claude reads the full file when the current task requires it. Use skills to keep specialized instructions out of the base system prompt without losing discoverability.

For full documentation, use WebFetch:

- URL: `https://platform.claude.com/docs/en/agents-and-tools/skills`

---

## Tool Use Examples

You can provide example tool calls inside the tool definitions to demonstrate usage patterns and reduce parameter errors. This helps Claude understand how to format tool inputs correctly, especially for tools with complex schemas.

For full documentation, use WebFetch:

- URL: `https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use`

---

## Server-Side Tools: Computer Use

Computer use lets Claude interact with a desktop environment (screenshots, mouse, keyboard). It can be Anthropic-hosted (server-side, like code execution) or self-hosted (you provide the environment and execute the actions client-side).

For full documentation, use WebFetch:

- URL: `https://platform.claude.com/docs/en/agents-and-tools/computer-use/overview`

---

## Context Editing

Context editing clears stale tool results and thinking blocks from the transcript as a long-running agent accumulates turns. Unlike compaction (which summarizes), context editing removes — cleared content is dropped, not replaced. Use it when old tool outputs are no longer relevant and you want to keep the transcript compact without losing conversation structure. The thresholds for what to clear are configurable.

For full documentation, use WebFetch:

- URL: `https://platform.claude.com/docs/en/build-with-claude/context-editing`

---

## Client-Side Tools: Memory

The memory tool lets Claude store and retrieve information across conversations through a memory-file directory. Claude can create, read, update, and delete files that persist across sessions.

### Key Facts

- Client-side tool — you control storage through your implementation
- Supports commands: `view`, `create`, `str_replace`, `insert`, `delete`, `rename`
- Operates on files in the `/memories` directory
- The Python, TypeScript, and Java SDKs provide helper classes/functions for implementing the memory backend

> **Safety:** never store API keys, passwords, tokens, or other secrets in memory files. Be careful with personally identifiable information (PII) — verify data privacy regulations (GDPR, CCPA) before persisting user data. The reference implementations have no built-in access control; in multi-user systems, implement per-user memory directories and authentication in your tool handlers.

For full implementation examples, use WebFetch:

- Docs: `https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool.md`

---

## Structured Outputs

Structured outputs constrain Claude's responses to follow a specific JSON schema, guaranteeing valid, parsable output. This is not a separate tool — it extends the Messages API response format and/or tool parameter validation.

Two features are available:

- **JSON outputs** (`output_config.format`): control the format of Claude's response
- **Strict tool use** (`strict: true`): guarantees valid tool parameter schemas

**Supported models:** Claude Opus 4.7, Claude Sonnet 4.6, and Claude Haiku 4.5. Legacy models (Claude Opus 4.5, Claude Opus 4.1) also support structured outputs.

> **Recommended:** use `client.messages.parse()`, which automatically validates responses against your schema. When using `messages.create()` directly, use `output_config: {format: {...}}`. The convenience parameter `output_format` is also accepted by some SDK methods (e.g., `.parse()`), but `output_config.format` is the canonical API-level parameter.

### JSON Schema Limits

**Supported:**

- Basic types: object, array, string, integer, number, boolean, null
- `enum`, `const`, `anyOf`, `allOf`, `$ref`/`$def`
- String formats: `date-time`, `time`, `date`, `duration`, `email`, `hostname`, `uri`, `ipv4`, `ipv6`, `uuid`
- `additionalProperties: false` (required on every object)

**Not supported:**

- Recursive schemas
- Numeric constraints (`minimum`, `maximum`, `multipleOf`)
- String constraints (`minLength`, `maxLength`)
- Complex array constraints
- `additionalProperties` with a value other than `false`

The Python and TypeScript SDKs automatically handle unsupported constraints by stripping them from the schema sent to the API and validating them client-side.

### Important Notes

- **First-request latency:** new schemas carry a one-time compilation cost. Subsequent requests with the same schema use a 24-hour cache.
- **Refusals:** if Claude refuses for safety reasons (`stop_reason: "refusal"`), the output may not match your schema.
- **Token limits:** if `stop_reason: "max_tokens"`, the output may be incomplete. Increase `max_tokens`.
- **Incompatible with:** citations (returns a 400 error), message prefilling.
- **Works with:** Batches API, streaming, token counting, extended thinking.

---

## Tips for Effective Tool Use

1. **Provide detailed descriptions**: Claude relies heavily on descriptions to understand when and how to use tools
2. **Use specific tool names**: `get_current_weather` is better than `weather`
3. **Validate inputs**: always validate tool inputs before executing
4. **Handle errors gracefully**: return informative error messages so Claude can adapt
5. **Limit the number of tools**: too many tools can confuse the model — keep the set focused
6. **Test tool interactions**: verify that Claude uses tools correctly in a variety of scenarios

For detailed tool-use documentation, use WebFetch:

- URL: `https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview`
