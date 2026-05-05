# Language

A shared vocabulary for every sentence this skill produces. Use these terms exactly — don't substitute them with "component", "service", "API", or "boundary". Consistent language is the whole point.

## Terms

**Module**
Anything that has an interface and an implementation. Deliberately scale-independent — applies equally to a function, a class, a package, or a slice that spans multiple layers.
_Avoid_: unit, component, service.

**Interface**
Everything the caller must know to use the module correctly. Includes the type signature, but also invariants, ordering constraints, error modes, required configuration, and performance characteristics.
_Avoid_: API, signature (too narrow — refers only to the type-level surface).

**Implementation**
What's inside the module — its body of code. Distinct from **Adapter**: you can have a small adapter with a large implementation (Postgres repository) or a large adapter with a small implementation (in-memory fake).
Reach for "adapter" when talking about a seam; "implementation" otherwise.

**Depth**
The leverage of an interface — the amount of behavior the caller (or test) can exercise per unit of interface they had to learn. A module is **deep** when there is a large amount of behavior behind a small interface.
A module is **shallow** when the interface is almost as complex as the implementation.

**Seam** _(from Michael Feathers)_
A place where you can change behavior without editing the code at that very place. The *location* where a module's interface lives. Choosing where to place a seam is a design decision separate from what will sit behind it.
_Avoid_: boundary (overloaded with the DDD bounded-context meaning).

**Adapter**
A concrete entity that satisfies an interface at a seam. Describes a *role* (which slot it fills), not an essence (what's inside).

**Leverage**
What callers gain from depth. More capability per unit of learned interface. One implementation pays off across N call sites and M tests.

**Locality**
What maintainers gain from depth. Changes, bugs, knowledge, and verification concentrate in one place rather than scattering across callers. Fix once — fixed everywhere.

## Principles

- **Depth is a property of the interface, not the implementation.** A deep module may internally be composed of small, mockable, replaceable parts — they just aren't part of the interface.
  A module can have **internal seams** (private to its implementation, used by its own tests) as well as an **external seam** at its interface.
- **The deletion test.** Imagine you deleted the module. If the complexity disappears, the module was hiding nothing (it was a pass-through). If the complexity surfaces at N callers, the module was earning its keep.
- **The interface is the test surface.** Callers and tests cross the same seam. If you want to test *behind* the interface, the module is probably the wrong shape.
- **One adapter means a hypothetical seam. Two adapters mean a real one.** Don't introduce a seam until something actually varies across it.

## Relationships

- A **Module** has exactly one **Interface** (the surface it presents to callers and tests).
- **Depth** is a property of a **Module**, measured relative to its **Interface**.
- A **Seam** is the place where some **Module**'s **Interface** lives.
- An **Adapter** sits at a **Seam** and satisfies the **Interface**.
- **Depth** yields **Leverage** for callers and **Locality** for maintainers.

## Rejected interpretations

- **Depth as the ratio of implementation lines to interface lines** (Ousterhout): encourages bloated implementations. We use depth-as-leverage.
- **"Interface" as the TypeScript `interface` keyword or a class's public methods**: too narrow — here the interface includes every fact the caller must know.
- **"Boundary"**: overloaded by DDD's bounded context. Say **seam** or **interface**.
