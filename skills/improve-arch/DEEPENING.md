# Deepening

How to safely deepen a cluster of shallow modules given its dependencies. Builds on the vocabulary from [LANGUAGE.md](LANGUAGE.md) — **module**, **interface**, **seam**, **adapter**.

## Dependency categories

When evaluating a candidate for deepening, classify its dependencies. The category determines how the deepened module is tested through its seam.

### 1. In-process

Pure computation, in-memory state, no I/O. Always deepenable — merge the modules and test directly through the new interface. No adapter needed.

### 2. Local-substitutable

Dependencies that have local test substitutes (PGLite instead of Postgres, in-memory file system). Deepenable if such a substitute exists. The deepened module is tested with the substitute running inside the test suite.
The seam is internal; the module's external interface exposes no port.

### 3. Remote but owned (Ports & Adapters)

Your own services across a network boundary (microservices, internal APIs). Define a **port** (interface) at the seam. The deep module owns the logic; transport is injected as an **adapter**. Tests use an in-memory adapter.
In production, the adapter is HTTP/gRPC/queue.

Recommendation form: *"Define a port at the seam, implement an HTTP adapter for production and an in-memory adapter for testing, so the logic sits in one deep module even though it's deployed across a network."*

### 4. True external (Mock)

Third-party services (Stripe, Twilio, etc.) that you don't control. The deepened module accepts the external dependency as an injectable port; tests supply a mock adapter.

## Seam discipline

- **One adapter means a hypothetical seam. Two adapters mean a real one.** Don't introduce a port until at least two adapters are justified (typically production + test). A seam with one adapter is just indirection.
- **Internal seams vs external seams.** A deep module can have internal seams (private to its implementation, used by its own tests) as well as an external seam at its interface.
  Don't expose internal seams through the interface just because tests use them.

## Testing strategy: replace, don't layer

- Old unit tests on shallow modules become garbage the moment tests on the deepened module's interface appear — delete them.
- Write new tests against the deepened module's interface. **The interface is the test surface.**
- Tests verify observable results through the interface, not internal state.
- Tests should survive internal refactors — they describe behavior, not implementation. If a test has to change when the implementation changes, it is testing what lies behind the interface.
