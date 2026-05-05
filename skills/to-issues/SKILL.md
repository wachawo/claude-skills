---
name: to-issues
description: Breaks a plan, spec, or PRD into independently pickable tasks in the project's issue tracker, using vertical "tracer bullet" slices. Use when the user wants to convert a plan into tasks,
  create implementation tickets, or split work into issues.
---

# To Issues

Break a plan into independently pickable tasks using vertical slices (tracer bullets).

The issue tracker and triage label vocabulary should have already been provided to you — if not, run `/setup-matt-pocock-skills`.

## Process

### 1. Gather context

Work with what is already in the conversation context. If the user passes an issue reference (number, URL, or path) as an argument, fetch it from the tracker and read the full body and comments.

### 2. Explore the codebase (optional)

If you have not yet explored the codebase, do so to understand the current state of the code. Issue titles and descriptions should use the project's domain glossary and respect ADRs in the area you are touching.

### 3. Sketch vertical slices

Break the plan into **tracer bullet** tasks. Each task is a thin vertical slice that goes through ALL integration layers end-to-end, NOT a horizontal slice of a single layer.

Slices can be 'HITL' or 'AFK'. HITL slices require human involvement, e.g. an architectural decision or design review. AFK slices can be implemented and merged without human involvement. Where possible, prefer AFK over HITL.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A finished slice can be demonstrated or verified on its own
- Many thin slices are better than a few thick ones
</vertical-slice-rules>

### 4. Interview the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories this covers (if the source material has them)

Ask the user:

- Is the level of detail right? (too coarse / too fine)
- Are the dependencies correct?
- Should any slices be merged or split further?
- Are slices correctly marked as HITL vs. AFK?

Iterate until the user approves the breakdown.

### 5. Publish issues to the tracker

For each approved slice, publish a new task to the tracker. Use the issue body template below. Apply the `needs-triage` label so each task enters the standard triage flow.

Publish issues in dependency order (blockers first), so you can reference real issue IDs in the "Blocked by" field.

<issue-template>
## Parent

Link to the parent task in the tracker (if the source was an existing task; otherwise omit this section).

## What to build

Brief description of this vertical slice. Describe end-to-end behavior, not a layer-by-layer implementation.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by

- Link to the blocking ticket (if any)

Or "None - can start immediately" if there are no blockers.

</issue-template>

Do NOT close or modify the parent task.
