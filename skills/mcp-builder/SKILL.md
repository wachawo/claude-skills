---
name: mcp-builder
description: Guidance for building high-quality MCP (Model Context Protocol) servers that let LLMs interact with external services through well-designed tools. Use when building MCP servers that integrate external APIs or services in Python (FastMCP) or Node/TypeScript (MCP SDK).
---

# MCP Server Development Guide

## Overview

Build MCP (Model Context Protocol) servers that let LLMs interact with external services through well-designed tools. The quality of an MCP server is measured by how well it lets an LLM solve real tasks.

---

# Process

## High-level workflow

Building a high-quality MCP server has four main phases:

### Phase 1: Deep research and planning

#### 1.1 Understand modern MCP design

**API coverage vs. workflow tools:**
Balance full API endpoint coverage against specialized workflow tools. Workflow tools may be more convenient for specific tasks, while full coverage gives agents flexibility to combine operations. Performance depends on the client — some clients benefit from code execution that composes primitive tools, while others work better with higher-level tools. When in doubt, prioritize full API coverage.

**Tool naming and discoverability:**
Clear, descriptive tool names help agents quickly locate the tool they need. Use consistent prefixes (e.g. `github_create_issue`, `github_list_repos`) and action-oriented naming.

**Context management:**
Agents benefit from concise tool descriptions and the ability to filter or paginate results. Design tools to return focused, relevant data. Some clients support code execution, which helps agents filter and process data more efficiently.

**Actionable error messages:**
Error messages should guide the agent to a solution with concrete hints and next steps.

#### 1.2 Study the MCP protocol documentation

**Navigate the MCP specification:**

Start with the sitemap to find relevant pages: `https://modelcontextprotocol.io/sitemap.xml`

Then fetch specific pages with the `.md` suffix for markdown format (e.g. `https://modelcontextprotocol.io/specification/draft.md`).

Key pages to review:
- Specification overview and architecture
- Transport mechanisms (streamable HTTP, stdio)
- Tool, resource, and prompt definitions

#### 1.3 Study the framework documentation

**Recommended stack:**
- **Language**: TypeScript (high-quality SDK support and good compatibility across many runtimes such as MCPB. AI models also generate TypeScript code well, benefiting from its wide adoption, static typing, and strong linters)
- **Transport**: Streamable HTTP for remote servers using stateless JSON (easier to scale and operate than stateful sessions and streaming responses). stdio for local servers.

**Load the framework documentation:**

- **MCP Best Practices**: [Best practices](./reference/mcp_best_practices.md) — core recommendations

**For TypeScript (recommended):**
- **TypeScript SDK**: use WebFetch to load `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`
- [TypeScript guide](./reference/node_mcp_server.md) — TypeScript patterns and examples

**For Python:**
- **Python SDK**: use WebFetch to load `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- [Python guide](./reference/python_mcp_server.md) — Python patterns and examples

#### 1.4 Plan the implementation

**Understand the API:**
Study the service's API documentation to identify key endpoints, authentication requirements, and data models. Use web search and WebFetch as needed.

**Tool selection:**
Prioritize full API coverage. List the endpoints to implement, starting with the most common operations.

---

### Phase 2: Implementation

#### 2.1 Set up the project structure

See language-specific guides for project setup:
- [TypeScript guide](./reference/node_mcp_server.md) — project structure, package.json, tsconfig.json
- [Python guide](./reference/python_mcp_server.md) — module organization, dependencies

#### 2.2 Implement the base infrastructure

Create shared utilities:
- API client with authentication
- Error-handling helpers
- Response formatting (JSON/Markdown)
- Pagination support

#### 2.3 Implement the tools

For each tool:

**Input schema:**
- Use Zod (TypeScript) or Pydantic (Python)
- Include constraints and clear descriptions
- Add examples in field descriptions

**Output schema:**
- Where possible, define `outputSchema` for structured data
- Use `structuredContent` in tool responses (a TypeScript SDK capability)
- Helps clients understand and process tool output

**Tool description:**
- Brief summary of functionality
- Parameter descriptions
- Return type schema

**Implementation:**
- Async/await for I/O operations
- Proper error handling with actionable messages
- Pagination support where applicable
- Return both text content and structured data when using modern SDKs

**Annotations:**
- `readOnlyHint`: true/false
- `destructiveHint`: true/false
- `idempotentHint`: true/false
- `openWorldHint`: true/false

---

### Phase 3: Review and testing

#### 3.1 Code quality

Check for:
- No code duplication (DRY principle)
- Consistent error handling
- Full type coverage
- Clear tool descriptions

#### 3.2 Build and test

**TypeScript:**
- Run `npm run build` to verify compilation
- Test with MCP Inspector: `npx @modelcontextprotocol/inspector`

**Python:**
- Verify syntax: `python -m py_compile your_server.py`
- Test with MCP Inspector

See language-specific guides for detailed testing approaches and quality checklists.

---

### Phase 4: Build evaluations

After implementing the MCP server, build comprehensive evaluations to verify its effectiveness.

**Load the [Evaluation guide](./reference/evaluation.md) for the complete evaluation guide.**

#### 4.1 Understand the purpose of evaluations

Use evaluations to verify that LLMs can effectively use your MCP server to answer realistic, complex questions.

#### 4.2 Build 10 evaluation questions

To build effective evaluations, follow the process from the evaluation guide:

1. **Tool inspection**: list available tools and understand their capabilities
2. **Content exploration**: use READ-ONLY operations to explore the available data
3. **Question generation**: produce 10 complex, realistic questions
4. **Answer verification**: solve each question yourself to verify the answers

#### 4.3 Evaluation requirements

Make sure each question is:
- **Independent**: doesn't depend on other questions
- **Read-only**: requires only non-destructive operations
- **Complex**: requires multiple tool calls and deep exploration
- **Realistic**: grounded in real scenarios that matter to people
- **Verifiable**: has a single clear answer that can be checked by string comparison
- **Stable**: the answer doesn't change over time

#### 4.4 Output format

Produce an XML file with this structure:

```xml
<evaluation>
  <qa_pair>
    <question>Find discussions about AI model launches with animal codenames. One model needed a specific safety designation that uses the format ASL-X. What number X was being determined for the model named after a spotted wild cat?</question>
    <answer>3</answer>
  </qa_pair>
<!-- More qa_pairs... -->
</evaluation>
```

---

# Reference files

## Documentation library

Load these resources as needed during development:

### Core MCP documentation (load first)
- **MCP protocol**: start with the sitemap `https://modelcontextprotocol.io/sitemap.xml`, then fetch specific pages with the `.md` suffix
- [MCP best practices](./reference/mcp_best_practices.md) — universal MCP recommendations, including:
  - Server and tool naming conventions
  - Response format guidance (JSON vs Markdown)
  - Pagination best practices
  - Transport selection (streamable HTTP vs stdio)
  - Security and error-handling standards

### SDK documentation (load in phases 1/2)
- **Python SDK**: fetch from `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- **TypeScript SDK**: fetch from `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`

### Language-specific implementation guides (load in phase 2)
- [Python implementation guide](./reference/python_mcp_server.md) — full Python/FastMCP guide, including:
  - Server initialization patterns
  - Pydantic model examples
  - Tool registration via `@mcp.tool`
  - Complete working examples
  - Quality checklist

- [TypeScript implementation guide](./reference/node_mcp_server.md) — full TypeScript guide, including:
  - Project structure
  - Zod schema patterns
  - Tool registration via `server.registerTool`
  - Complete working examples
  - Quality checklist

### Evaluation guide (load in phase 4)
- [Evaluation guide](./reference/evaluation.md) — full guide to building evaluations, including:
  - Question-writing guidance
  - Answer-verification strategies
  - XML format specifications
  - Example questions and answers
  - Running the evaluation with the provided scripts
