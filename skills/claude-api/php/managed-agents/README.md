# Managed Agents — PHP

> **Bindings not shown here:** This README covers the most common managed-agents flows for PHP. If you need a class, method, namespace, field, or behavior not shown here, WebFetch the PHP SDK repository **or the corresponding documentation page** from `shared/live-sources.md` rather than guessing. Do not extrapolate from cURL forms or another language's SDK.

> **Agents are persistent — create once, reference by ID.** Save the agent ID returned by `$client->beta->agents->create` and pass it to every subsequent `->sessions->create`; do not call `agents->create` in the request path. The Anthropic CLI is one convenient way to create agents and environments from version-controlled YAML — its URL is in `shared/live-sources.md`. The examples below show in-code creation for completeness; in production the create call belongs to the setup phase, not the request path.

## Installation

```bash
composer require "anthropic-ai/sdk"
```

## Client Initialization

```php
use Anthropic\Client;

// Default (uses the ANTHROPIC_API_KEY environment variable)
$client = new Client();

// Explicit API key
$client = new Client(apiKey: 'your-api-key');
```

---

## Creating an Environment

```php
$environment = $client->beta->environments->create(
    name: 'my-dev-env',
    config: ['type' => 'cloud', 'networking' => ['type' => 'unrestricted']],
);
echo "Environment ID: {$environment->id}\n"; // env_...
```

---

## Creating an Agent (Mandatory First Step)

> ⚠️ **There is no inline agent configuration.** `model`/`system`/`tools` live on the agent object, not on the session. Always start with `$client->beta->agents->create()` — the session accepts either `agent: $agent->id` or the typed `BetaManagedAgentsAgentParams::with(type: 'agent', id: $agent->id, version: $agent->version)`.

### Minimal

```php
use Anthropic\Beta\Agents\BetaManagedAgentsAgentToolset20260401Params;

// 1. Create the agent (reusable, versionable)
$agent = $client->beta->agents->create(
    name: 'Coding Assistant',
    model: 'claude-opus-4-7',
    system: 'You are a helpful coding assistant.',
    tools: [
        BetaManagedAgentsAgentToolset20260401Params::with(
            type: 'agent_toolset_20260401',
        ),
    ],
);

// 2. Start a session
$session = $client->beta->sessions->create(
    agent: ['type' => 'agent', 'id' => $agent->id, 'version' => $agent->version],
    environmentID: $environment->id,
    title: 'Quickstart session',
);
echo "Session ID: {$session->id}\n";
```

### Updating an Agent

Updates create new versions; the agent object is immutable per version.

```php
$updatedAgent = $client->beta->agents->update(
    $agent->id,
    version: $agent->version,
    system: 'You are a helpful coding agent. Always write tests.',
);
echo "New version: {$updatedAgent->version}\n";

// List all versions
foreach ($client->beta->agents->versions->list($agent->id)->pagingEachItem() as $version) {
    echo "Version {$version->version}: {$version->updatedAt->format(DateTimeInterface::ATOM)}\n";
}

// Archive the agent
$archived = $client->beta->agents->archive($agent->id);
echo "Archived at: {$archived->archivedAt->format(DateTimeInterface::ATOM)}\n";
```

---

## Sending a User Message

```php
$client->beta->sessions->events->send(
    $session->id,
    events: [
        [
            'type' => 'user.message',
            'content' => [['type' => 'text', 'text' => 'Review the auth module']],
        ],
    ],
);
```

> 💡 **Stream-first:** Open the stream *before* (or simultaneously with) sending the message. The stream only delivers events that occur after it is opened — stream-after-send means early events arrive buffered in a single batch. See [Steering Patterns](../../shared/managed-agents-events.md#steering-patterns).

---

## Streaming Events (SSE)

> ℹ️ **Streaming transporter:** PHP's default buffered PSR-18 client never returns control for an open session event stream. Use a streaming Guzzle transporter for `streamStream()` calls — leave other calls on the default client.

```php
$streamingClient = new GuzzleHttp\Client(['stream' => true]);

// Open the stream first, then send the user message
$stream = $client->beta->sessions->events->streamStream(
    $session->id,
    requestOptions: ['transporter' => $streamingClient],
);
$client->beta->sessions->events->send(
    $session->id,
    events: [
        [
            'type' => 'user.message',
            'content' => [['type' => 'text', 'text' => 'Summarize the repo README']],
        ],
    ],
);

foreach ($stream as $event) {
    match ($event->type) {
        'agent.message' => array_walk(
            $event->content,
            static fn($block) => $block->type === 'text' ? print($block->text) : null,
        ),
        'agent.tool_use' => print("\n[Using tool: {$event->name}]\n"),
        'session.error' => printf("\n[Error: %s]", $event->error?->message ?? 'unknown'),
        default => null,
    };
    if ($event->type === 'session.status_idle' || $event->type === 'session.error') {
        break;
    }
}
$stream->close();
```

### Reconnecting and Tailing

When reconnecting mid-session, first list past events for deduplication, then read live events:

```php
$stream = $client->beta->sessions->events->streamStream(
    $session->id,
    requestOptions: ['transporter' => $streamingClient],
);

// The stream is open and buffering. List history before reading live.
$seenEventIds = [];
foreach ($client->beta->sessions->events->list($session->id)->pagingEachItem() as $event) {
    $seenEventIds[$event->id] = true;
}

// Read live events, skipping ones already seen
foreach ($stream as $event) {
    if (isset($seenEventIds[$event->id])) {
        continue;
    }
    $seenEventIds[$event->id] = true;
    match ($event->type) {
        'agent.message' => array_walk(
            $event->content,
            static fn($block) => $block->type === 'text' ? print($block->text) : null,
        ),
        default => null,
    };
    if ($event->type === 'session.status_idle') {
        break;
    }
}
$stream->close();
```

---

## Submitting a Custom Tool Result

> ℹ️ The PHP managed-agents bindings for `user.custom_tool_result` are not yet documented in this skill or in the source app examples. See `shared/managed-agents-events.md` for the wire format and the `anthropic-ai/sdk` PHP repository for the corresponding params.

---

## Polling Events

```php
foreach ($client->beta->sessions->events->list($session->id)->pagingEachItem() as $event) {
    echo "{$event->type}: {$event->id}\n";
}
```

---

## Uploading a File

> ℹ️ **PHP file upload:** The beta managed-agents binding for file upload in the PHP SDK is not shown in the source app examples; the canonical PHP example uses raw cURL to `POST /v1/files`. If your codebase prefers the SDK, WebFetch the `anthropic-ai/sdk` PHP repository for the latest binding before writing code.

```php
use Anthropic\Beta\Sessions\BetaManagedAgentsFileResourceParams;

// Raw cURL upload (canonical example from the apps source)
$csvPath = 'data.csv';
$ch = curl_init('https://api.anthropic.com/v1/files');
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => [
        'x-api-key: ' . getenv('ANTHROPIC_API_KEY'),
        'anthropic-version: 2023-06-01',
        'anthropic-beta: files-api-2025-04-14',
    ],
    CURLOPT_POSTFIELDS => ['file' => new CURLFile($csvPath, 'text/csv', 'data.csv')],
]);
$file = json_decode(curl_exec($ch));
echo "File ID: {$file->id}\n";

// Mount in a session
$session = $client->beta->sessions->create(
    agent: $agent->id,
    environmentID: $environment->id,
    resources: [
        BetaManagedAgentsFileResourceParams::with(
            type: 'file',
            fileID: $file->id,
            mountPath: '/workspace/data.csv',
        ),
    ],
);
```

### Adding and Managing Resources on an Existing Session

```php
// Attach an additional file to an open session
$resource = $client->beta->sessions->resources->add(
    $session->id,
    type: 'file',
    fileID: $file->id,
);
echo "{$resource->id}\n"; // "sesrsc_01ABC..."

// List session resources
$listed = $client->beta->sessions->resources->list($session->id);
foreach ($listed->data as $entry) {
    echo "{$entry->id} {$entry->type}\n";
}

// Detach a resource
$client->beta->sessions->resources->delete($resource->id, sessionID: $session->id);
```

---

## List and Download Session Files

> ℹ️ Listing and downloading files the agent wrote during the session is not yet documented for PHP in this skill or in the source app examples. See `shared/managed-agents-events.md` and the `anthropic-ai/sdk` PHP repository for file list/download bindings.

---

## Managing Sessions

```php
// List environments
$environments = $client->beta->environments->list();

// Get a specific environment
$env = $client->beta->environments->retrieve($environment->id);

// Archive an environment (read-only; existing sessions keep working)
$client->beta->environments->archive($environment->id);

// Delete an environment (only if no sessions reference it)
$client->beta->environments->delete($environment->id);

// Delete a session
$client->beta->sessions->delete($session->id);
```

---

## MCP Server Integration

```php
use Anthropic\Beta\Agents\BetaManagedAgentsAgentToolset20260401Params;
use Anthropic\Beta\Agents\BetaManagedAgentsMCPToolsetParams;
use Anthropic\Beta\Agents\BetaManagedAgentsUrlmcpServerParams;
use Anthropic\Beta\Sessions\BetaManagedAgentsAgentParams;

// The agent declares the MCP server (no auth here — auth goes in the vault)
$agent = $client->beta->agents->create(
    name: 'GitHub Assistant',
    model: 'claude-opus-4-7',
    mcpServers: [
        BetaManagedAgentsUrlmcpServerParams::with(
            type: 'url',
            name: 'github',
            url: 'https://api.githubcopilot.com/mcp/',
        ),
    ],
    tools: [
        BetaManagedAgentsAgentToolset20260401Params::with(type: 'agent_toolset_20260401'),
        BetaManagedAgentsMCPToolsetParams::with(
            type: 'mcp_toolset',
            mcpServerName: 'github',
        ),
    ],
);

// The session attaches the vault(s) containing credentials for those MCP server URLs
$session = $client->beta->sessions->create(
    agent: BetaManagedAgentsAgentParams::with(
        type: 'agent',
        id: $agent->id,
        version: $agent->version,
    ),
    environmentID: $environment->id,
    vaultIDs: [$vault->id],
);
```

See `shared/managed-agents-tools.md` §Vaults for creating vaults and adding credentials.

---

## Vaults

```php
// Create a vault
$vault = $client->beta->vaults->create(
    displayName: 'Alice',
    metadata: ['external_user_id' => 'usr_abc123'],
);
echo $vault->id . "\n"; // "vlt_01ABC..."

// Add an OAuth credential
$credential = $client->beta->vaults->credentials->create(
    vaultID: $vault->id,
    displayName: "Alice's Slack",
    auth: [
        'type' => 'mcp_oauth',
        'mcp_server_url' => 'https://mcp.slack.com/mcp',
        'access_token' => 'xoxp-...',
        'expires_at' => '2026-04-15T00:00:00Z',
        'refresh' => [
            'token_endpoint' => 'https://slack.com/api/oauth.v2.access',
            'client_id' => '1234567890.0987654321',
            'scope' => 'channels:read chat:write',
            'refresh_token' => 'xoxe-1-...',
            'token_endpoint_auth' => [
                'type' => 'client_secret_post',
                'client_secret' => 'abc123...',
            ],
        ],
    ],
);

// Rotate a credential (e.g., after a token refresh)
$client->beta->vaults->credentials->update(
    $credential->id,
    vaultID: $vault->id,
    auth: [
        'type' => 'mcp_oauth',
        'access_token' => 'xoxp-new-...',
        'expires_at' => '2026-05-15T00:00:00Z',
        'refresh' => ['refresh_token' => 'xoxe-1-new-...'],
    ],
);

// Archive the vault
$client->beta->vaults->archive($vault->id);
```

---

## GitHub Repository Integration

Mount a GitHub repository as a session resource (the vault holds the GitHub MCP credential):

```php
$session = $client->beta->sessions->create(
    agent: $agent->id,
    environmentID: $environment->id,
    vaultIDs: [$vault->id],
    resources: [
        [
            'type' => 'github_repository',
            'url' => 'https://github.com/org/repo',
            'mountPath' => '/workspace/repo',
            'authorizationToken' => 'ghp_your_github_token',
        ],
    ],
);
```

Multiple repositories in a single session:

```php
$resources = [
    [
        'type' => 'github_repository',
        'url' => 'https://github.com/org/frontend',
        'mountPath' => '/workspace/frontend',
        'authorizationToken' => 'ghp_your_github_token',
    ],
    [
        'type' => 'github_repository',
        'url' => 'https://github.com/org/backend',
        'mountPath' => '/workspace/backend',
        'authorizationToken' => 'ghp_your_github_token',
    ],
];
```

Rotating a repository's authorization token:

```php
$listed = $client->beta->sessions->resources->list($session->id);
$repoResourceId = $listed->data[0]->id;

$client->beta->sessions->resources->update(
    $repoResourceId,
    sessionID: $session->id,
    authorizationToken: 'ghp_your_new_github_token',
);
```
