# Interface Design

When the user wants to consider alternative interfaces for a chosen deepening candidate, use this parallel sub-agent pattern. Based on "Design It Twice" (Ousterhout) — your first idea is unlikely to be the best one.

Uses the vocabulary from [LANGUAGE.md](LANGUAGE.md) — **module**, **interface**, **seam**, **adapter**, **leverage**.

## Process

### 1. Outline the problem space

Before launching sub-agents, write the user an explanation of the problem space for the chosen candidate:

- Constraints any new interface must satisfy
- Dependencies it will rely on, and which category they fall into (see [DEEPENING.md](DEEPENING.md))
- A rough illustrative code sketch to ground the constraints — not a proposal, just a way to make the constraints concrete

Show this to the user and immediately move to step 2. The user reads and reflects while sub-agents run in parallel.

### 2. Launch sub-agents

Launch 3+ sub-agents in parallel via the Agent tool. Each must produce a **radically different** interface for the deepened module.

Give each sub-agent a separate technical brief (file paths, coupling details, dependency category per [DEEPENING.md](DEEPENING.md), what sits behind the seam).
The brief is independent of the problem-space explanation given to the user in step 1. Give each agent its own design constraint:

- Agent 1: "Minimize the interface — aim for 1–3 entry points max. Maximise leverage per entry point."
- Agent 2: "Maximise flexibility — support many use cases and extension."
- Agent 3: "Optimise for the most common caller — make the default case trivial."
- Agent 4 (if applicable): "Design around ports & adapters for cross-seam dependencies."

Include the vocabulary from [LANGUAGE.md](LANGUAGE.md) and the vocabulary from CONTEXT.md in the brief, so each sub-agent names things consistently with the architectural language and the project's domain language.

Each sub-agent produces:

1. The interface (types, methods, parameters — plus invariants, ordering, error modes)
2. A usage example showing how callers work with it
3. What the implementation hides behind the seam
4. Dependency strategy and adapters (see [DEEPENING.md](DEEPENING.md))
5. Trade-offs — where leverage is high, where it is thin

### 3. Present and compare

Present the designs sequentially so the user can absorb each one, then compare them in prose. Contrast on **depth** (leverage at the interface), **locality** (where changes concentrate), and **seam placement**.

After the comparison, give your own recommendation: which design you consider strongest and why. If elements from different designs combine well, propose a hybrid. Be opinionated — the user wants a clear stance, not a menu.
