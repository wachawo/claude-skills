---
name: "playwright"
description: "Use when the task requires automating a real browser from the terminal (navigation, form filling, snapshots, screenshots, data extraction, debugging user scenarios) via `playwright-cli` or the bundled wrapper script."
---


# Playwright CLI Skill

Drive a real browser from the terminal with `playwright-cli`. Prefer the bundled wrapper script so the CLI works even without a global install.
Treat this skill as CLI-first automation. Do not switch to `@playwright/test` unless the user explicitly asks for test files.

## Prerequisite check (mandatory)

Before suggesting commands, check whether `npx` is available (the wrapper depends on it):

```bash
command -v npx >/dev/null 2>&1
```

If it is not available, stop and ask the user to install Node.js/npm (which provide `npx`). Give them these steps verbatim:

```bash
# Verify Node/npm are installed
node --version
npm --version

# If missing, install Node.js/npm, then:
npm install -g @playwright/cli@latest
playwright-cli --help
```

Once `npx` is available, switch to the wrapper script. A global `playwright-cli` install is optional.

## Skill path (set once)

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PWCLI="$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh"
```

User skills are installed under `$CODEX_HOME/skills` (default: `~/.codex/skills`).

## Quick start

Use the wrapper script:

```bash
"$PWCLI" open https://playwright.dev --headed
"$PWCLI" snapshot
"$PWCLI" click e15
"$PWCLI" type "Playwright"
"$PWCLI" press Enter
"$PWCLI" screenshot
```

If the user prefers a global install, that is also fine:

```bash
npm install -g @playwright/cli@latest
playwright-cli --help
```

## Core workflow

1. Open the page.
2. Take a snapshot to get stable element references.
3. Interact using the references from the latest snapshot.
4. Take a fresh snapshot after navigation or significant DOM changes.
5. Save artifacts (screenshot, pdf, traces) when useful.

Minimal cycle:

```bash
"$PWCLI" open https://example.com
"$PWCLI" snapshot
"$PWCLI" click e3
"$PWCLI" snapshot
```

## When to re-snapshot

Take a new snapshot after:

- navigation
- clicking elements that change the UI substantially
- opening/closing modals or menus
- switching tabs

References can go stale. If a command fails due to a missing reference, take a new snapshot.

## Recommended patterns

### Filling and submitting a form

```bash
"$PWCLI" open https://example.com/form
"$PWCLI" snapshot
"$PWCLI" fill e1 "user@example.com"
"$PWCLI" fill e2 "password123"
"$PWCLI" click e3
"$PWCLI" snapshot
```

### Debugging a user scenario with traces

```bash
"$PWCLI" open https://example.com --headed
"$PWCLI" tracing-start
# ...interactions...
"$PWCLI" tracing-stop
```

### Working with multiple tabs

```bash
"$PWCLI" tab-new https://example.com
"$PWCLI" tab-list
"$PWCLI" tab-select 0
"$PWCLI" snapshot
```

## Wrapper script

The wrapper script uses `npx --package @playwright/cli playwright-cli` so the CLI runs without a global install:

```bash
"$PWCLI" --help
```

Prefer the wrapper unless the repository has already standardized on a global install.

## Reference material

Open only what you need:

- CLI command reference: `references/cli.md`
- Practical scenarios and troubleshooting: `references/workflows.md`

## Guardrails

- Always take a snapshot before using identifiers like `e12`.
- Take a new snapshot whenever references look stale.
- Prefer explicit commands over `eval` and `run-code` unless necessary.
- If you don't have a fresh snapshot, use placeholder references like `eX` and explain why; don't bypass references with `run-code`.
- Use `--headed` when visual verification helps.
- When saving artifacts in this repository, use `output/playwright/` and don't create new top-level artifact folders.
- Default to CLI commands and scripts, not Playwright test specs.
