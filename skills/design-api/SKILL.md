---
name: design-api
description: Generate several radically different interface design options for a module via parallel sub-agents. Use when the user wants to design an API, evaluate interface options, compare module shapes, or mentions "design it twice".
---

# Design an Interface

Built on the "Design It Twice" principle from "A Philosophy of Software Design": your first idea is unlikely to be the best one. Generate several radically different design options, then compare.

## Workflow

### 1. Gather requirements

Before designing, understand:

- [ ] What problem does this module solve?
- [ ] Who calls it? (other modules, external users, tests)
- [ ] What are the key operations?
- [ ] Are there any constraints? (performance, compatibility, existing patterns)
- [ ] What should be hidden internally vs. exposed?

Ask: "What should this module do? Who will use it?"

### 2. Generate designs (parallel sub-agents)

Launch 3+ sub-agents simultaneously via the Task tool. Each must produce a **radically different** approach.

```
Prompt template for each sub-agent:

Design an interface for: [module description]

Requirements: [gathered requirements]

Constraints for this design: [assign a different constraint to each agent]
- Agent 1: "Minimize method count - aim for 1-3 methods max"
- Agent 2: "Maximize flexibility - support many use cases"
- Agent 3: "Optimize for the most common case"
- Agent 4: "Take inspiration from [specific paradigm/library]"

Output format:
1. Interface signature (types/methods)
2. Usage example (how caller uses it)
3. What this design hides internally
4. Trade-offs of this approach
```

### 3. Present the designs

Show each design with:

1. **Interface signature** — types, methods, parameters
2. **Usage examples** — how the calling code actually uses it
3. **What it hides** — internal complexity left under the hood

Present the designs sequentially so the user can absorb each approach before comparing.

### 4. Compare the designs

After showing all options, compare them by:

- **Interface simplicity**: fewer methods, simpler parameters
- **Generality vs. specialization**: flexibility vs. focus
- **Implementation efficiency**: does the shape allow efficient internals?
- **Depth**: a small interface that hides significant complexity (good) vs. a large interface with a thin implementation (bad)
- **Easy to use correctly** vs. **easy to misuse**

Discuss trade-offs in prose, not tables. Highlight the points where the designs diverge most.

### 5. Synthesize

Often the best design combines ideas from several options. Ask:

- "Which design fits your primary case best?"
- "Are there elements from other designs worth incorporating?"

## Evaluation criteria

From "A Philosophy of Software Design":

**Interface simplicity**: fewer methods, simpler parameters — easier to learn and use correctly.

**Generality**: capable of handling future scenarios without changes. But beware of over-generalization.

**Implementation efficiency**: does the interface shape allow an efficient implementation? Or does it force awkward internals?

**Depth**: a small interface hiding significant complexity = a deep module (good). A large interface with a thin implementation = a shallow module (avoid).

## Anti-patterns

- Don't let sub-agents produce similar designs — insist on radical differentiation
- Don't skip the comparison — the value is in the contrast
- Don't implement — this is only about interface shape
- Don't evaluate by implementation effort
