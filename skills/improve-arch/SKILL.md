---
name: improve-arch
description: Find opportunities to deepen modules in the codebase, drawing on the domain language from CONTEXT.md and decisions recorded in docs/adr/.
  Use it when the user wants to improve architecture, find refactoring opportunities, merge tightly coupled modules, or make the codebase more testable and easier for an AI to navigate.
---

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. The goal is testability and AI-navigation ergonomics.

## Glossary

Use these terms in every sentence exactly as defined. Consistent language is the point; don't slide into "component", "service", "API", or "boundary". Full definitions are in [LANGUAGE.md](LANGUAGE.md).

- **Module** — anything that has an interface and an implementation (function, class, package, slice).
- **Interface** — everything the caller must know to use the module: types, invariants, error modes, call ordering, configuration. Not just the type signature.
- **Implementation** — the code inside.
- **Depth** — leverage at the interface: lots of behavior behind a small interface. **Deep** = high leverage. **Shallow** = the interface is almost as complex as the implementation.
- **Seam** — the place where the interface lives; the point at which behavior can be changed without editing it in place. (Use this word, not "boundary".)
- **Adapter** — a concrete entity that satisfies the interface at a seam.
- **Leverage** — what callers gain from depth.
- **Locality** — what maintainers gain: changes, bugs, and knowledge concentrate in one place.

Key principles (full list in [LANGUAGE.md](LANGUAGE.md)):

- **The deletion test**: imagine you deleted the module. If the complexity disappears, it was a pass-through. If complexity surfaces at N callers, it was earning its keep.
- **The interface is the test surface.**
- **One adapter = a hypothetical seam. Two adapters = a real seam.**

This skill is _informed_ by the project's domain model. The domain language supplies names for good seams; ADRs record decisions that the skill should not rediscover.

## Process

### 1. Exploration

First read the project's domain glossary and any ADRs in the area you are touching.

Then use the Agent tool with `subagent_type=Explore` to walk the codebase. Don't follow rigid heuristics — explore organically and note places where friction is felt:

- Where does understanding a single concept require jumping across many small modules?
- Where are modules **shallow** — interface almost as complex as implementation?
- Where have pure functions been extracted for testability, but real bugs hide in how they are called (no **locality**)?
- Where do tightly coupled modules leak across their seams?
- Which parts of the codebase are untested or poorly testable through the current interface?

Apply the **deletion test** to anything you suspect is shallow: does removing it concentrate complexity or just move it around? "Yes, it concentrates" is the signal you want.

### 2. Presenting candidates

Show a numbered list of deepening opportunities. For each candidate:

- **Files** — which files/modules are affected
- **Problem** — why the current architecture creates friction
- **Solution** — a description of the change in plain language
- **Benefits** — explanation in terms of locality and leverage, and how tests will improve

**Use the CONTEXT.md vocabulary for the domain and the [LANGUAGE.md](LANGUAGE.md) vocabulary for architecture.** If `CONTEXT.md` defines "Order", say "the Order intake module" — not "the FooBarHandler" and not "the Order service".

**Conflicts with ADRs**: if a candidate contradicts an existing ADR, raise it only when the friction is actually serious enough to justify revisiting the ADR. Flag it explicitly (e.g. _"contradicts ADR-0007 — but worth reopening because…"_).
Don't enumerate every theoretical refactor an ADR forbids.

Do NOT propose interfaces yet. Ask the user: "Which of these would you like to explore?"

### 3. The grilling loop

Once the user picks a candidate, move into a grilling conversation. Walk the design tree with them — constraints, dependencies, the shape of the deepened module, what sits behind the seam, which tests survive.

Side effects happen in stride, as decisions crystallize:

- **Naming the deepened module after a concept that isn't in `CONTEXT.md`?** Add the term to `CONTEXT.md` — same discipline as `/grill-with-docs` (see [CONTEXT-FORMAT.md](../grill-with-docs/CONTEXT-FORMAT.md)). Create the file lazily if it doesn't exist.
- **Sharpening a fuzzy term during the conversation?** Update `CONTEXT.md` right there.
- **The user rejected a candidate with a substantive reason?** Offer an ADR with the wording: _"Want me to record this as an ADR so future architecture reviews don't re-suggest it?"_ Only offer when the reason will actually be useful
   to a future explorer to avoid re-proposing the same thing — skip ephemeral reasons ("not worth it right now") and self-evident ones. See [ADR-FORMAT.md](../grill-with-docs/ADR-FORMAT.md).
- **Want to consider alternative interfaces for the deepened module?** See [INTERFACE-DESIGN.md](INTERFACE-DESIGN.md).
