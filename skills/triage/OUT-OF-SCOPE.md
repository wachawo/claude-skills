# Out-of-Scope knowledge base

The repository's `.out-of-scope/` directory holds persistent records of rejected feature requests. It serves two purposes:

1. **Institutional memory** — why a feature was rejected, so the reasoning is not lost when the issue is closed
2. **Deduplication** — when a new issue matches a prior rejection, the skill can surface the previous decision instead of re-litigating it

## Directory structure

```
.out-of-scope/
├── dark-mode.md
├── plugin-system.md
└── graphql-api.md
```

One file per **concept**, not per issue. Several issues that ask for the same thing are grouped into a single file.

## File format

The file should be written in a free, readable style — more like a short design note than a database entry. Use paragraphs, code examples, and scenarios so the reasoning is clear and useful to someone encountering it for the first time.

```markdown
# Dark Mode

This project does not support dark mode or user-facing theming.

## Why this is out of scope

The rendering pipeline assumes a single color palette defined in
`ThemeConfig`. Supporting multiple themes would require:

- A theme context provider wrapping the entire component tree
- Per-component theme-aware style resolution
- A persistence layer for user theme preferences

This is a significant architectural change that doesn't align with the
project's focus on content authoring. Theming is a concern for downstream
consumers who embed or redistribute the output.

```ts
// The current ThemeConfig interface is not designed for runtime switching:
interface ThemeConfig {
  colors: ColorPalette; // single palette, resolved at build time
  fonts: FontStack;
}
```

## Prior requests

- #42 — "Add dark mode support"
- #87 — "Night theme for accessibility"
- #134 — "Dark theme option"
```

### File name

Use a short, descriptive kebab-case name for the concept: `dark-mode.md`, `plugin-system.md`, `graphql-api.md`. The name should be recognizable enough that someone scanning the directory understands what was rejected without opening the file.

### How to write the reason

The reason must be substantive — not "we don't want this", but why. Good reasons reference:

- Project scope or philosophy ("This project is focused on X; theming is a concern for downstream consumers")
- Technical constraints ("Supporting this would require Y, which conflicts with our Z architecture")
- Strategic decisions ("We chose A over B because...")

The reason must be durable. Avoid references to temporary circumstances ("we're too busy right now") — those are not real rejections, they are deferrals.

## When to check `.out-of-scope/`

During triage (Step 1: Gather context), read every file under `.out-of-scope/`. When assessing a new issue:

- Check whether the request matches an existing out-of-scope concept
- Match by concept similarity, not keywords — "night theme" matches `dark-mode.md`
- If there is a match, raise it with the maintainer: "This looks like `.out-of-scope/dark-mode.md` — we rejected this before because [reason]. Do you still feel that way?"

The maintainer can:

- **Confirm** — append the new issue to the "Prior requests" list of the existing file, then close it
- **Reconsider** — delete or update the out-of-scope file, and run the issue through normal triage
- **Disagree** — the issues are related but distinct; continue normal triage

## When to write to `.out-of-scope/`

Only when an **enhancement** (not a bug) is rejected as `wontfix`. Flow:

1. The maintainer decides the feature request is out of scope
2. Check whether a matching `.out-of-scope/` file already exists
3. If yes: append the new issue to the "Prior requests" list
4. If no: create a new file with the concept name, decision, reason, and first prior request
5. Post a comment on the issue explaining the decision and referencing the `.out-of-scope/` file
6. Close the issue with the `wontfix` label

## Updating or removing out-of-scope files

If the maintainer changes their mind about a previously rejected concept:

- Delete the `.out-of-scope/` file
- The skill is not obligated to reopen old issues — they are historical records
- The new issue that triggered the reconsideration goes through normal triage
