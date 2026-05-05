# ADR format

ADRs live in `docs/adr/` and use sequential numbering: `0001-slug.md`, `0002-slug.md`, etc.

Create the `docs/adr/` directory lazily — only when the first ADR is needed.

## Template

```md
# {Short decision title}

{1-3 sentences: what the context is, what we decided, and why.}
```

That's it. An ADR can be a single paragraph. The value is in recording *that* the decision was made and *why* — not in filling in sections.

## Optional sections

Include these only when they add real value. Most ADRs do not need them.

- **Status** frontmatter (`proposed | accepted | deprecated | superseded by ADR-NNNN`) — useful when decisions get revisited
- **Considered Options** — only if the rejected alternatives are worth remembering
- **Consequences** — only if there are non-obvious downstream effects to flag

## Numbering

Scan `docs/adr/` for the highest existing number and increment by one.

## When to propose an ADR

All three conditions must hold:

1. **Hard to reverse** — the cost of changing your mind later is significant
2. **Surprising without context** — a future reader will look at the code and think "why on earth did they do it this way?"
3. **Outcome of a real trade-off** — there were genuine alternatives, and you chose one for specific reasons

If the decision is easy to reverse, skip it — you will just reverse it. If it is not surprising, no one will ask "why". If there was no real alternative, there is little to record beyond "we did the obvious thing".

### What qualifies

- **Architectural shape.** "We use a monorepo." "The write model is event-sourced; the read model is projected to Postgres."
- **Integration patterns between contexts.** "Ordering and Billing communicate through domain events, not synchronous HTTP."
- **Technology choices with lock-in.** Database, message bus, authentication provider, target deployment platform. Not every library — only the ones that would take a quarter to replace.
- **Boundary and scope decisions.** "Customer data is owned by the Customer context; other contexts reference it only by ID." Explicit "no"s are as valuable as "yes"es.
- **Deliberate departures from the obvious path.** "We use hand-written SQL instead of an ORM because X." Anything where a reasonable reader would assume the opposite. This stops the next engineer from "fixing" something that was intentional.
- **Constraints not visible in the code.** "We cannot use AWS because of compliance requirements." "Response time must be under 200 ms due to a partner API contract."
- **Rejected alternatives where the rejection is non-obvious.** If you considered GraphQL and chose REST for subtle reasons, record it — otherwise someone will propose GraphQL again in six months.
