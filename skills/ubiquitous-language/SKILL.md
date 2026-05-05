---
name: ubiquitous-language
description: Extract a DDD ubiquitous language glossary from the current conversation, flag ambiguities, and propose canonical terms. Saves the result to UBIQUITOUS_LANGUAGE.md.
   Use when the user wants to define domain terms, build a glossary, normalize terminology, create a ubiquitous language, or mentions "domain model" or "DDD".
disable-model-invocation: true
---

# Ubiquitous Language

Extract and formalize the domain terminology from the current conversation into a consistent glossary, saved to a local file.

## Process

1. **Scan the conversation** for domain-relevant nouns, verbs, and concepts
2. **Surface problems**:
   - One word used for different concepts (ambiguity)
   - Different words used for the same concept (synonyms)
   - Vague or overloaded terms
3. **Propose a canonical glossary** with deliberately chosen terms
4. **Write to `UBIQUITOUS_LANGUAGE.md`** in the working directory using the format below
5. **Print a brief summary** directly in the conversation

## Output format

Write a `UBIQUITOUS_LANGUAGE.md` file with the following structure:

```md
# Ubiquitous Language

## Order lifecycle

| Term        | Definition                                              | Aliases to avoid      |
| ----------- | ------------------------------------------------------- | --------------------- |
| **Order**   | A customer's request to purchase one or more items      | Purchase, transaction |
| **Invoice** | A request for payment sent to a customer after delivery | Bill, payment request |

## People

| Term         | Definition                                  | Aliases to avoid       |
| ------------ | ------------------------------------------- | ---------------------- |
| **Customer** | A person or organization that places orders | Client, buyer, account |
| **User**     | An authentication identity in the system    | Login, account         |

## Relationships

- An **Invoice** belongs to exactly one **Customer**
- An **Order** produces one or more **Invoices**

## Example dialogue

> **Dev:** "When a **Customer** places an **Order**, do we create the **Invoice** immediately?"
> **Domain expert:** "No — an **Invoice** is only generated once a **Fulfillment** is confirmed. A single **Order** can produce multiple **Invoices** if items ship in separate **Shipments**."
> **Dev:** "So if a **Shipment** is cancelled before dispatch, no **Invoice** exists for it?"
> **Domain expert:** "Exactly. The **Invoice** lifecycle is tied to the **Fulfillment**, not the **Order**."

## Flagged ambiguities

- "account" was used to mean both **Customer** and **User** — these are distinct concepts: a **Customer** places orders, while a **User** is an authentication identity that may or may not represent a **Customer**.
```

## Rules

- **Be principled.** When several words exist for one concept, pick the best one and list the rest as aliases to avoid.
- **Flag conflicts explicitly.** If a term is used ambiguously in the conversation, surface it in the "Flagged ambiguities" section with a clear recommendation.
- **Include only terms that matter to domain experts.** Do not include module or class names unless they have meaning in the domain language.
- **Keep definitions tight.** One sentence at most. Define WHAT it is, not what it does.
- **Show relationships.** Use bold term names and express cardinality where it is obvious.
- **Include only domain terms.** Do not include generic programming concepts (array, function, endpoint) unless they have a domain-specific meaning.
- **Group terms into multiple tables** when natural clusters emerge (e.g., by sub-domain, lifecycle, or actor). Each group has its own heading and table.
  If all terms belong to a single coherent domain, one table is enough — do not split artificially.
- **Write an example dialogue.** A short conversation (3-5 lines) between a developer and a domain expert that demonstrates how the terms naturally interact.
  The dialogue should clarify boundaries between adjacent concepts and show the terms being used precisely.

<example>

## Example dialogue

> **Dev:** "How do I test the **sync service** without Docker?"

> **Domain expert:** "Provide the **filesystem layer** instead of the **Docker layer**. It implements the same **Sandbox service** interface but uses a local directory as the **sandbox**."

> **Dev:** "So **sync-in** still creates a **bundle** and unpacks it?"

> **Domain expert:** "Exactly. The **sync service** doesn't know which layer it's talking to. It calls `exec` and `copyIn` — the **filesystem layer** just runs those as local shell commands."

</example>

## Re-running

When invoked again in the same conversation:

1. Read the existing `UBIQUITOUS_LANGUAGE.md`
2. Incorporate new terms from subsequent discussion
3. Update definitions if understanding has changed
4. Re-flag any new ambiguities
5. Rewrite the example dialogue to reflect the new terms
