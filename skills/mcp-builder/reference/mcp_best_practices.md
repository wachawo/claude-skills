# MCP Server Best Practices

## Quick reference

### Server naming
- **Python**: `{service}_mcp` (e.g. `slack_mcp`)
- **Node/TypeScript**: `{service}-mcp-server` (e.g. `slack-mcp-server`)

### Tool naming
- Use snake_case with a service prefix
- Format: `{service}_{action}_{resource}`
- Examples: `slack_send_message`, `github_create_issue`

### Response formats
- Support both formats: JSON and Markdown
- JSON for programmatic processing
- Markdown for human readability

### Pagination
- Always honor the `limit` parameter
- Return `has_more`, `next_offset`, `total_count`
- Default to 20-50 items

### Transport
- **Streamable HTTP**: for remote servers, multi-client scenarios
- **stdio**: for local integrations, command-line tools
- Avoid SSE (deprecated in favor of streamable HTTP)

---

## Server naming conventions

Follow these standardized naming patterns:

**Python**: format `{service}_mcp` (lowercase with underscores)
- Examples: `slack_mcp`, `github_mcp`, `jira_mcp`

**Node/TypeScript**: format `{service}-mcp-server` (lowercase with dashes)
- Examples: `slack-mcp-server`, `github-mcp-server`, `jira-mcp-server`

The name should be general, describe the integrated service, be easy to derive from the task description, and contain no version numbers.

---

## Tool naming and design

### Tool naming

1. **Use snake_case**: `search_users`, `create_project`, `get_channel_info`
2. **Include a service prefix**: assume your MCP server may be used alongside other MCP servers
   - Use `slack_send_message` rather than just `send_message`
   - Use `github_create_issue` rather than just `create_issue`
3. **Be action-oriented**: start with verbs (get, list, search, create, etc.)
4. **Be specific**: avoid generic names that may collide with other servers

### Tool design

- Tool descriptions should describe functionality narrowly and unambiguously
- Descriptions must accurately match the actual functionality
- Provide tool annotations (readOnlyHint, destructiveHint, idempotentHint, openWorldHint)
- Keep tool operations focused and atomic

---

## Response formats

All tools that return data should support multiple formats:

### JSON format (`response_format="json"`)
- Machine-readable structured data
- Include all available fields and metadata
- Consistent field names and types
- Used for programmatic processing

### Markdown format (`response_format="markdown"`, usually the default)
- Human-readable formatted text
- Use headings, lists, and formatting for clarity
- Convert timestamps to a human-readable format
- Show display names with IDs in parentheses
- Omit verbose metadata

---

## Pagination

For tools that list resources:

- **Always honor the `limit` parameter**
- **Implement pagination**: use `offset` or cursor-based pagination
- **Return pagination metadata**: include `has_more`, `next_offset`/`next_cursor`, `total_count`
- **Never load all results into memory**: especially important for large datasets
- **Default to reasonable limits**: 20-50 items is the typical range

Example paginated response:
```json
{
  "total": 150,
  "count": 20,
  "offset": 0,
  "items": [...],
  "has_more": true,
  "next_offset": 20
}
```

---

## Transport options

### Streamable HTTP

**Best for**: remote servers, web services, multi-client scenarios

**Characteristics**:
- Bidirectional communication over HTTP
- Supports multiple concurrent clients
- Can be deployed as a web service
- Allows server-to-client notifications

**Use when**:
- Serving multiple clients simultaneously
- Deploying as a cloud service
- Integrating with web applications

### stdio

**Best for**: local integrations, command-line tools

**Characteristics**:
- Communication via standard input/output streams
- Simple setup, no network configuration required
- Runs as a subprocess of the client

**Use when**:
- Building tools for a local development environment
- Integrating with desktop applications
- Single-user, single-session scenarios

**Note**: stdio servers MUST NOT log to stdout (use stderr for logging)

### Transport selection

| Criterion | stdio | Streamable HTTP |
|-----------|-------|-----------------|
| **Deployment** | Local | Remote |
| **Clients** | Single | Multiple |
| **Complexity** | Low | Medium |
| **Real-time** | No | Yes |

---

## Security best practices

### Authentication and authorization

**OAuth 2.1**:
- Use secure OAuth 2.1 with certificates from recognized authorities
- Validate access tokens before processing requests
- Accept only tokens specifically intended for your server

**API keys**:
- Store API keys in environment variables, never in code
- Validate keys at server startup
- Provide clear error messages when authentication fails

### Input validation

- Sanitize file paths to prevent directory traversal
- Validate URLs and external identifiers
- Check parameter sizes and ranges
- Prevent command injection in system calls
- Use schema-based validation (Pydantic/Zod) for all input data

### Error handling

- Don't expose internal errors to clients
- Log security-relevant errors on the server side
- Provide useful, non-leaking error messages
- Release resources after errors

### DNS rebinding protection

For streamable HTTP servers running locally:
- Enable DNS rebinding protection
- Validate the `Origin` header on all incoming connections
- Listen on `127.0.0.1` rather than `0.0.0.0`

---

## Tool annotations

Provide annotations to help clients understand tool behavior:

| Annotation | Type | Default | Description |
|-----------|------|---------|-------------|
| `readOnlyHint` | boolean | false | Tool does not modify the environment |
| `destructiveHint` | boolean | true | Tool may perform destructive updates |
| `idempotentHint` | boolean | false | Repeated calls with the same arguments have no additional effect |
| `openWorldHint` | boolean | true | Tool interacts with external entities |

**Important**: annotations are hints, not security guarantees. Clients must not make safety-critical decisions based on annotations alone.

---

## Error handling

- Use standard JSON-RPC error codes
- Report tool errors inside result objects (not as protocol-level errors)
- Provide useful, concrete error messages with suggested next steps
- Don't expose internal implementation details
- Release resources cleanly on errors

Error-handling example:
```typescript
try {
  const result = performOperation();
  return { content: [{ type: "text", text: result }] };
} catch (error) {
  return {
    isError: true,
    content: [{
      type: "text",
      text: `Error: ${error.message}. Try using filter='active_only' to reduce results.`
    }]
  };
}
```

---

## Testing requirements

Comprehensive testing should cover:

- **Functional testing**: verify correct execution with valid/invalid input data
- **Integration testing**: verify interaction with external systems
- **Security testing**: validate authentication, input sanitization, rate limiting
- **Performance testing**: verify behavior under load and timeouts
- **Error handling**: ensure correct error reporting and resource cleanup

---

## Documentation requirements

- Provide clear documentation for all tools and capabilities
- Include working examples (at least 3 per major capability)
- Document security considerations
- Specify required permissions and access levels
- Document rate limits and performance characteristics
