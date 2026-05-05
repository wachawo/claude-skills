---
name: tdd
description: Test-driven development with the red-green-refactor cycle. Use when the user wants to develop features or fix bugs via TDD, mentions "red-green-refactor", asks for integration tests, or requests a test-first approach.
---

# Test-Driven Development

## Philosophy

**Core principle**: tests must verify behavior through public interfaces, not implementation details. The code may change completely; the tests should not.

**Good tests** are integration-style: they exercise real code paths through public APIs. They describe _what_ the system does, not _how_. A good test reads like a specification: "user can checkout with valid cart"
  immediately tells you which capability exists. Such tests survive refactorings because they are indifferent to internal structure.

**Bad tests** are coupled to implementation. They mock internal collaborators, test private methods, or verify state through external means (e.g. reaching directly into the database instead of using the interface).
A red flag: the test breaks during a refactor even though behavior did not change. If renaming an internal function breaks the tests, those tests were testing implementation, not behavior.

For examples see [tests.md](tests.md); for the mocking guide see [mocking.md](mocking.md).

## Anti-pattern: horizontal slicing

**Do NOT write all the tests first and then all the implementation.** That is "horizontal slicing" — interpreting RED as "write all the tests" and GREEN as "write all the code".

This produces **bad tests**:

- Tests written in a batch test _imagined_ behavior, not _real_ behavior
- You end up testing the _shape_ of things (data structures, function signatures) rather than user-facing behavior
- Tests become insensitive to real changes — they pass when behavior is broken, and fail when it is fine
- You outrun your headlights, fixating on test structure before understanding the implementation

**The right approach**: vertical slices via tracer bullets. One test → one implementation → repeat. Each test responds to what you learned in the previous cycle.
  Because you have just written the code, you know exactly which behavior matters and how to verify it.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
  ...
```

## Workflow

### 1. Planning

When exploring the codebase, use the project's domain glossary so that test names and interface vocabulary match the project's language, and follow the ADRs in the area you are modifying.

Before writing code:

- [ ] Confirm with the user which interface changes are required
- [ ] Confirm with the user which behaviors to test (prioritize them)
- [ ] Look for opportunities for [deep modules](deep-modules.md) (narrow interface, deep implementation)
- [ ] Design interfaces for [testability](interface-design.md)
- [ ] List behaviors to test (not implementation steps)
- [ ] Get the plan approved by the user

Ask: "What should the public interface be? Which behaviors are most important to test?"

**You cannot test everything.** Clarify with the user which behaviors matter most. Focus testing on critical paths and complex logic, not every possible edge case.

### 2. Tracer Bullet

Write ONE test that confirms ONE fact about the system:

```
RED:   Write test for first behavior → test fails
GREEN: Write minimal code to pass → test passes
```

This is your tracer bullet — it proves the path works end-to-end.

### 3. Incremental cycle

For each remaining behavior:

```
RED:   Write next test → fails
GREEN: Minimal code to pass → passes
```

Rules:

- One test at a time
- Just enough code to pass the current test
- Do not anticipate future tests
- Tests focus on observable behavior

### 4. Refactor

Once all tests pass, look for [refactor candidates](refactoring.md):

- [ ] Extract duplication
- [ ] Deepen modules (hide complexity behind simple interfaces)
- [ ] Apply SOLID principles where natural
- [ ] Consider what the new code reveals about existing code
- [ ] Run the tests after every refactoring step

**Never refactor on RED.** Get to GREEN first.

## Per-cycle checklist

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```
