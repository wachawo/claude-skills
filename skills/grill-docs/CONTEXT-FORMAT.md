# CONTEXT.md format

## Structure

```md
# {Context name}

{One- or two-sentence description: what this context is and why it exists.}

## Language

**Order**:
{Short description of the term}
_Avoid_: Purchase, transaction

**Invoice**:
A request for payment sent to a customer after delivery.
_Avoid_: Bill, payment request

**Customer**:
A person or organization that places orders.
_Avoid_: Client, buyer, account

## Relationships

- An **Order** produces one or more **Invoices**
- An **Invoice** belongs to exactly one **Customer**

## Example dialogue

> **Dev:** "When a **Customer** places an **Order**, do we create the **Invoice** immediately?"
> **Domain expert:** "No — an **Invoice** is only generated once a **Fulfillment** is confirmed."

## Flagged ambiguities

- "account" was used to mean both **Customer** and **User** — resolved: these are distinct concepts.
```

## Rules

- **Be opinionated.** When several words exist for the same concept, pick the best one and list the rest as aliases to avoid.
- **Flag conflicts explicitly.** If a term is used ambiguously, record it under "Flagged ambiguities" with a clear resolution.
- **Keep definitions concise.** One sentence at most. Describe what the entity IS, not what it does.
- **Show relationships.** Use bold term names and indicate cardinality where it is obvious.
- **Include only terms specific to the project's context.** General programming concepts (timeouts, error kinds, utility patterns) do not belong here, even if the project uses them heavily. Before adding a term, ask: is this concept unique to this context, or general programming? Only the first qualifies.
- **Group terms under subheadings** when natural clusters emerge. If all terms belong to a single coherent area, a flat list is fine too.
- **Write an example dialogue.** A conversation between a developer and a domain expert that shows how the terms interact naturally and clarifies the boundaries between related concepts.

## Single or multiple contexts

**Single context (most repositories):** one `CONTEXT.md` at the root.

**Multiple contexts:** the root contains `CONTEXT-MAP.md`, listing the contexts, their locations, and the relationships between them:

```md
# Context Map

## Contexts

- [Ordering](./src/ordering/CONTEXT.md) — receives and tracks customer orders
- [Billing](./src/billing/CONTEXT.md) — generates invoices and processes payments
- [Fulfillment](./src/fulfillment/CONTEXT.md) — manages warehouse picking and shipping

## Relationships

- **Ordering → Fulfillment**: Ordering emits `OrderPlaced` events; Fulfillment consumes them to start picking
- **Fulfillment → Billing**: Fulfillment emits `ShipmentDispatched` events; Billing consumes them to generate invoices
- **Ordering ↔ Billing**: Shared types for `CustomerId` and `Money`
```

The skill determines which structure applies:

- If `CONTEXT-MAP.md` exists, read it to find the contexts
- If only a root `CONTEXT.md` exists, this is a single context
- If neither exists, create the root `CONTEXT.md` lazily once the first term is resolved

If there are multiple contexts, determine which one the current topic belongs to. If it is not clear, ask.
