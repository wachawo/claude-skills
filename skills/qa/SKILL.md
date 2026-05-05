---
name: qa
description: Interactive QA session in which the user freely reports bugs or issues, and the agent files the corresponding GitHub issues. Explores the codebase in the background to gather context and domain language. Use when the user wants to report bugs, run QA, file issues conversationally, or mentions a "QA session".
---

# QA Session

Run an interactive QA session. The user describes problems they have encountered. You ask clarifying questions, explore the codebase for context, and file GitHub issues that are durable, user-focused, and use the project's domain language.

## For each issue the user raises

### 1. Listen and clarify lightly

Let the user describe the problem in their own words. Ask **at most 2-3 short clarifying questions**, focused on:

- What they expected and what actually happened
- Reproduction steps (if not obvious)
- Whether the behavior is stable or flaky

Do NOT interrogate. If the description is enough to file an issue, move on.

### 2. Explore the codebase in the background

While talking with the user, launch an agent (subagent_type=Explore) in the background to investigate the relevant area. The goal is NOT to find a fix, but to:

- Learn the domain language used in this area (check UBIQUITOUS_LANGUAGE.md)
- Understand what the feature is supposed to do
- Identify the boundary of user-facing behavior

This context helps write a higher-quality issue, but the issue itself MUST NOT reference specific files, line numbers, or internal implementation details.

### 3. Assess scope: single issue or breakdown?

Before filing, decide: is this **one issue** or should it be **broken down** into several?

Break down when:

- The fix touches multiple independent areas (e.g., "form validation is wrong AND the success message is missing AND the redirect is broken")
- There are clearly separable tasks that different people could work on in parallel
- The user describes something with several distinct failure modes or symptoms

Keep it as one issue when:

- It is a single behavior that is wrong in one place
- All symptoms stem from the same root behavior

### 4. File the GitHub issue

Create issues via `gh issue create`. Do NOT ask the user to review first — just file and share the URL.

Issues should be **durable** — they should remain meaningful after major refactors. Write from the user's point of view.

#### For a single issue

Use this template:

```
## What happened

[Describe the actual behavior the user experienced, in plain language]

## What I expected

[Describe the expected behavior]

## Steps to reproduce

1. [Concrete, numbered steps a developer can follow]
2. [Use domain terms from the codebase, not internal module names]
3. [Include relevant inputs, flags, or configuration]

## Additional context

[Any extra observations from the user or from codebase exploration that help frame the issue — e.g. "this only happens when using the Docker layer, not the filesystem layer" — use domain language but don't cite files]
```

#### For a breakdown (multiple issues)

Create issues in dependency order (blockers first), so you can reference real issue numbers.

Use this template for each sub-issue:

```
## Parent issue

#<parent-issue-number> (if you created a tracking issue) or "Reported during QA session"

## What's wrong

[Describe this specific behavior problem — just this slice, not the whole report]

## What I expected

[Expected behavior for this specific slice]

## Steps to reproduce

1. [Steps specific to THIS issue]

## Blocked by

- #<issue-number> (if this issue can't be fixed until another is resolved)

Or "None — can start immediately" if no blockers.

## Additional context

[Any extra observations relevant to this slice]
```

When breaking down:

- **Prefer many thin issues over a few thick ones** — each should be independently fixable and verifiable
- **Be honest about blocking relationships** — if issue B truly cannot be tested until issue A is fixed, say so. If they are independent, mark both as "None — can start immediately"
- **Create issues in dependency order**, so you can reference real numbers in "Blocked by"
- **Maximize parallelism** — the goal is for several people (or agents) to be able to pick up different issues simultaneously

#### Rules for all issue bodies

- **No file paths or line numbers** — they go stale
- **Use the project's domain language** (check UBIQUITOUS_LANGUAGE.md if it exists)
- **Describe behavior, not code** — "the sync service fails to apply the patch", not "applyPatch() throws on line 42"
- **Reproduction steps are required** — if you cannot determine them, ask the user
- **Be concise** — a developer should be able to read the issue in 30 seconds

After filing, print all issue URLs (with a brief summary of blocking relationships) and ask: "Next issue, or are we done?"

### 5. Continue the session

Continue until the user says they are done. Each issue is independent — do not batch them.
