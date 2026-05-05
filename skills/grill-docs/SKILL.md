---
name: grill-docs
description: A "grilling" session that stress-tests your plan against the existing domain model, sharpens terminology, and updates documentation (CONTEXT.md, ADRs) as decisions crystallize. Use when the user wants to stress-test a plan against the project's language and documented decisions.
---

<what-to-do>

Relentlessly interrogate me on every aspect of the plan until we reach a shared understanding. Walk every branch of the design tree, resolving dependencies between decisions one by one.
For each question, offer your recommended answer.

Ask one question at a time, waiting for feedback on each before moving on.

If a question can be answered by exploring the codebase, explore it instead of asking.

</what-to-do>

<supporting-info>

## Domain knowledge

While exploring the codebase, also look for existing documentation:

### File structure

In most repositories there is a single context:

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If the root contains `CONTEXT-MAP.md`, the repository has multiple contexts. The map indicates where each one lives:

```
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/                          ← system-wide decisions
├── src/
│   ├── ordering/
│   │   ├── CONTEXT.md
│   │   └── docs/adr/                 ← context-specific decisions
│   └── billing/
│       ├── CONTEXT.md
│       └── docs/adr/
```

Create files lazily — only when there is something to record. If there is no `CONTEXT.md`, create it when the first term is resolved. If there is no `docs/adr/`, create the directory when the first ADR is needed.

## During the session

### Cross-check with the glossary

When the user uses a term that contradicts the language already captured in `CONTEXT.md`, flag it immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is correct?"

### Sharpen vague language

When the user uses fuzzy or overloaded terms, propose a precise canonical term. "You said 'account' — do you mean Customer or User? They are different entities."

### Walk through concrete scenarios

When domain relationships are being discussed, stress-test them with concrete scenarios. Invent scenarios that probe edge cases and force the user to pin down the boundaries between concepts.

### Cross-check against the code

When the user asserts how something works, check whether the code agrees. If you find a contradiction, point it out: "Your code cancels the entire Order, but you just said partial cancellation is possible — which is correct?"

### Update CONTEXT.md as you go

When a term is resolved, update `CONTEXT.md` immediately. Do not batch — record as you go. Use the format from [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md).

Do not tie `CONTEXT.md` to implementation details. Include only terms meaningful to domain experts.

### Propose ADRs sparingly

Only propose creating an ADR when all three of the following hold:

1. **Hard to reverse** — the cost of changing your mind later is significant
2. **Surprising without context** — a future reader will wonder "why did they do it that way?"
3. **Outcome of a real trade-off** — there were genuine alternatives, and you chose one for specific reasons

If any of the three is missing, skip the ADR. Use the format from [ADR-FORMAT.md](./ADR-FORMAT.md).

</supporting-info>
