# Claude API — PHP

> **Note:** The PHP SDK is Anthropic's official SDK for PHP. The beta tool runner is available via `$client->beta->messages->toolRunner()`. Structured output helpers are supported through `StructuredOutputModel` classes. An Agent SDK is not available. Bedrock, Vertex AI, and Foundry clients are supported.

## Installation

```bash
composer require "anthropic-ai/sdk"
```

## Client Initialization

```php
use Anthropic\Client;

// With API key from an environment variable
$client = new Client(apiKey: getenv("ANTHROPIC_API_KEY"));
```

### Amazon Bedrock

```php
use Anthropic\Bedrock;

// The constructor is private — use the static factory. Reads AWS credentials from the environment.
$client = Bedrock\Client::fromEnvironment(region: 'us-east-1');
```

### Google Vertex AI

```php
use Anthropic\Vertex;

// The constructor is private. The parameter is `location`, not `region`.
$client = Vertex\Client::fromEnvironment(
    location: 'us-east5',
    projectId: 'my-project-id',
);
```

### Anthropic Foundry

```php
use Anthropic\Foundry;

// The constructor is private. Either baseUrl or resource is required.
$client = Foundry\Client::withCredentials(
    authToken: getenv('ANTHROPIC_FOUNDRY_AUTH_TOKEN'),
    baseUrl: 'https://<resource>.services.ai.azure.com/anthropic',
);
```

---

## Basic Message Request

```php
$message = $client->messages->create(
    model: 'claude-opus-4-7',
    maxTokens: 16000,
    messages: [
        ['role' => 'user', 'content' => 'What is the capital of France?'],
    ],
);

// content is an array of polymorphic blocks (TextBlock, ToolUseBlock,
// ThinkingBlock). Accessing ->text on content[0] without checking the
// block type will throw if the first block is not a TextBlock (for example,
// when extended thinking is on and ThinkingBlock comes first). Always check:
foreach ($message->content as $block) {
    if ($block->type === 'text') {
        echo $block->text;
    }
}
```

If you only need the first text block:

```php
foreach ($message->content as $block) {
    if ($block->type === 'text') {
        echo $block->text;
        break;
    }
}
```

---

## Streaming

> **Requires SDK v0.5.0+.** v0.4.0 and earlier used a single `$params` array; calling with named arguments throws `Unknown named parameter $model`. Upgrade: `composer require "anthropic-ai/sdk:^0.7"`

```php
use Anthropic\Messages\RawContentBlockDeltaEvent;
use Anthropic\Messages\TextDelta;

$stream = $client->messages->createStream(
    model: 'claude-opus-4-7',
    maxTokens: 64000,
    messages: [
        ['role' => 'user', 'content' => 'Write a haiku'],
    ],
);

foreach ($stream as $event) {
    if ($event instanceof RawContentBlockDeltaEvent && $event->delta instanceof TextDelta) {
        echo $event->delta->text;
    }
}
```

---

## Tool Use

### Tool Runner (Beta)

**Beta:** The PHP SDK provides a tool runner via `$client->beta->messages->toolRunner()`. Define tools with `BetaRunnableTool` — a definition array plus a `run` closure:

```php
use Anthropic\Lib\Tools\BetaRunnableTool;

$weatherTool = new BetaRunnableTool(
    definition: [
        'name' => 'get_weather',
        'description' => 'Get the current weather for a location.',
        'input_schema' => [
            'type' => 'object',
            'properties' => [
                'location' => ['type' => 'string', 'description' => 'City and state'],
            ],
            'required' => ['location'],
        ],
    ],
    run: function (array $input): string {
        return "The weather in {$input['location']} is sunny and 72°F.";
    },
);

$runner = $client->beta->messages->toolRunner(
    maxTokens: 16000,
    messages: [['role' => 'user', 'content' => 'What is the weather in Paris?']],
    model: 'claude-opus-4-7',
    tools: [$weatherTool],
);

foreach ($runner as $message) {
    foreach ($message->content as $block) {
        if ($block->type === 'text') {
            echo $block->text;
        }
    }
}
```

### Manual Loop

Tools are passed as arrays. **The SDK uses camelCase keys** (`inputSchema`, `toolUseID`, `stopReason`) and automatically maps them to snake_case on the wire — starting with v0.5.0. See [shared tool use concepts](../shared/tool-use-concepts.md) for the loop pattern.

```php
use Anthropic\Messages\ToolUseBlock;

$tools = [
    [
        'name' => 'get_weather',
        'description' => 'Get the current weather in a given location',
        'inputSchema' => [  // camelCase, not input_schema
            'type' => 'object',
            'properties' => [
                'location' => ['type' => 'string', 'description' => 'City and state'],
            ],
            'required' => ['location'],
        ],
    ],
];

$messages = [['role' => 'user', 'content' => 'What is the weather in SF?']];

$response = $client->messages->create(
    model: 'claude-opus-4-7',
    maxTokens: 16000,
    tools: $tools,
    messages: $messages,
);

while ($response->stopReason === 'tool_use') {  // camelCase property
    $toolResults = [];
    foreach ($response->content as $block) {
        if ($block instanceof ToolUseBlock) {
            // $block->name  : string               — tool name for dispatch
            // $block->input : array<string,mixed>  — parsed JSON input
            // $block->id    : string               — passed back as toolUseID
            $result = executeYourTool($block->name, $block->input);
            $toolResults[] = [
                'type' => 'tool_result',
                'toolUseID' => $block->id,  // camelCase, not tool_use_id
                'content' => $result,
            ];
        }
    }

    // Append the assistant turn + the user turn with tool results
    $messages[] = ['role' => 'assistant', 'content' => $response->content];
    $messages[] = ['role' => 'user', 'content' => $toolResults];

    $response = $client->messages->create(
        model: 'claude-opus-4-7',
        maxTokens: 16000,
        tools: $tools,
        messages: $messages,
    );
}

// Final text response
foreach ($response->content as $block) {
    if ($block->type === 'text') {
        echo $block->text;
    }
}
```

`$block->type === 'tool_use'` also works; `instanceof ToolUseBlock` narrows for PHPStan.


---

## Extended Thinking

**Adaptive thinking is the recommended mode for Claude 4.6+ models.** Claude dynamically decides when and how much to think.

```php
use Anthropic\Messages\ThinkingBlock;

$message = $client->messages->create(
    model: 'claude-opus-4-7',
    maxTokens: 16000,
    thinking: ['type' => 'adaptive'],
    messages: [
        ['role' => 'user', 'content' => 'Solve: 27 * 453'],
    ],
);

// ThinkingBlock(s) precede TextBlock in content
foreach ($message->content as $block) {
    if ($block instanceof ThinkingBlock) {
        echo "Thinking:\n{$block->thinking}\n\n";
        // $block->signature is an opaque string — preserve it verbatim when
        // passing thinking blocks back in multi-step conversations
    } elseif ($block->type === 'text') {
        echo "Answer: {$block->text}\n";
    }
}
```

> **Deprecated:** `['type' => 'enabled', 'budgetTokens' => N]` (extended thinking with a fixed budget) still works on Claude 4.6 but is deprecated. Use adaptive thinking above.

`$block->type === 'thinking'` also works for the check; `instanceof` narrows for PHPStan.

---

## Prompt Caching

`system:` accepts an array of text blocks; set `cacheControl` on the last block. The array-shape syntax (camelCase keys) is idiomatic. For placement patterns and a silent-invalidator audit checklist, see `shared/prompt-caching.md`.

```php
$message = $client->messages->create(
    model: 'claude-opus-4-7',
    maxTokens: 16000,
    system: [
        ['type' => 'text', 'text' => $longSystemPrompt, 'cacheControl' => ['type' => 'ephemeral']],
    ],
    messages: [['role' => 'user', 'content' => 'Summarize the key points']],
);
```

For 1-hour TTL: `'cacheControl' => ['type' => 'ephemeral', 'ttl' => '1h']`. There is also a top-level `cacheControl:` on `messages->create(...)` that automatically places on the last cacheable block.

Verify hits via `$message->usage->cacheCreationInputTokens` / `$message->usage->cacheReadInputTokens`.

---

## Structured Outputs

### Using StructuredOutputModel (recommended)

Define a PHP class implementing `StructuredOutputModel` and pass it as `outputConfig`:

```php
use Anthropic\Lib\Contracts\StructuredOutputModel;
use Anthropic\Lib\Concerns\StructuredOutputModelTrait;
use Anthropic\Lib\Attributes\Constrained;

class Person implements StructuredOutputModel
{
    use StructuredOutputModelTrait;

    #[Constrained(description: 'Full name')]
    public string $name;

    public int $age;

    public ?string $email = null;  // nullable = optional field
}

$message = $client->messages->create(
    model: 'claude-opus-4-7',
    maxTokens: 16000,
    messages: [['role' => 'user', 'content' => 'Generate a profile for Alice, age 30']],
    outputConfig: ['format' => Person::class],
);

$person = $message->parsedOutput();  // a Person instance
echo $person->name;
```

Types are inferred from PHP type hints. Use `#[Constrained(description: '...')]` to add descriptions. Nullable properties (`?string`) become optional fields.

### Raw Schema

```php
$message = $client->messages->create(
    model: 'claude-opus-4-7',
    maxTokens: 16000,
    messages: [['role' => 'user', 'content' => 'Extract: John (john@co.com), Enterprise plan']],
    outputConfig: [
        'format' => [
            'type' => 'json_schema',
            'schema' => [
                'type' => 'object',
                'properties' => [
                    'name' => ['type' => 'string'],
                    'email' => ['type' => 'string'],
                    'plan' => ['type' => 'string'],
                ],
                'required' => ['name', 'email', 'plan'],
                'additionalProperties' => false,
            ],
        ],
    ],
);

// The first text block contains valid JSON
foreach ($message->content as $block) {
    if ($block->type === 'text') {
        $data = json_decode($block->text, true);
        break;
    }
}
```

---

## Beta Features and Server-Side Tools

**`betas:` is NOT a parameter on `$client->messages->create()`** — it exists only in the beta namespace. Use it for features that require an explicit opt-in header:

```php
use Anthropic\Beta\Messages\BetaRequestMCPServerURLDefinition;

$response = $client->beta->messages->create(
    model: 'claude-opus-4-7',
    maxTokens: 16000,
    mcpServers: [
        BetaRequestMCPServerURLDefinition::with(
            name: 'my-server',
            url: 'https://example.com/mcp',
        ),
    ],
    betas: ['mcp-client-2025-11-20'],  // valid only on ->beta->messages
    messages: [['role' => 'user', 'content' => 'Use the MCP tools']],
);
```

**Server-side tools** (bash, web_search, text_editor, code_execution) are GA and work on both paths — `Anthropic\Messages\ToolBash20250124` / `WebSearchTool20260209` / `ToolTextEditor20250728` / `CodeExecutionTool20260120` for non-beta, and `Anthropic\Beta\Messages\BetaToolBash20250124` / `BetaWebSearchTool20260209` / `BetaToolTextEditor20250728` / `BetaCodeExecutionTool20260120` for beta. The `betas:` header is not required for these.
