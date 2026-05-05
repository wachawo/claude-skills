---
name: diagnose
description: Disciplined loop for diagnosing complex bugs and performance regressions. Reproduce → minimize → hypothesize → instrument → fix → close with a regression test.
  Use when the user says "diagnose this" / "debug this", reports a bug, says something is broken / crashing / not working, or describes a performance regression.
---

# Diagnose

A discipline for complex bugs. Skip phases only with explicit justification.

When exploring the codebase, use the project's domain glossary to build a clear mental model of the relevant modules, and check ADRs in the area you are touching.

## Phase 1 — Build the feedback loop

**This is where the craft lives.** Everything else is mechanics. If you have a fast, deterministic, agent-runnable pass/fail signal for the bug, you will find the cause — bisection, hypothesis testing, and instrumentation are just consumers of that signal.
Without such a signal, no amount of code reading will save you.

Spend disproportionate effort here. **Be aggressive. Be inventive. Don't give up.**

### Ways to build the loop — try roughly in this order

1. **Failing test** at any seam that reaches the bug — unit, integration, e2e.
2. **curl / HTTP script** against a running dev server.
3. **CLI invocation** with a fixture as input, comparing stdout to a reference snapshot.
4. **Headless browser script** (Playwright / Puppeteer) — drives the UI, asserts on DOM/console/network.
5. **Replay of a recorded trace.** Save a real network request / payload / event log to disk and replay it through the code in isolation.
6. **One-off harness.** Stand up a minimal slice of the system (a single service, mocked dependencies) that exercises the bug's code path with a single function call.
7. **Property / fuzz loop.** If the bug "sometimes returns the wrong result", run 1000 random inputs and look for the failure mode.
8. **Bisection harness.** If the bug appeared between two known states (commit, dataset, version), automate "load state X, check, repeat" so you can run `git bisect run`.
9. **Differential loop.** Run the same input through the old and new versions (or two configurations) and diff the outputs.
10. **HITL bash script.** Last resort. If a human must click, walk _them_ through `scripts/hitl-loop.template.sh` to keep the loop structured. The captured output comes back to you.

Build the right feedback loop and the bug is 90% fixed.

### Iterate on the loop itself

Treat the loop as a product. Once you have _some_ loop, ask:

- Can it be faster? (Cache setup, skip unneeded init, narrow the test scope.)
- Can the signal be sharper? (Assert on the specific symptom, not just "didn't crash".)
- Can it be more deterministic? (Pin time, seed RNG, isolate the FS, freeze the network.)

A flaky 30-second loop is barely better than no loop. A deterministic 2-second loop is a debugging superpower.

### Non-deterministic bugs

The goal is not a clean repro but **a higher repro rate**. Run the trigger 100 times, parallelize, add stress, narrow timing windows, insert sleeps.
A 50%-flaky bug is debuggable; a 1%-flaky one is not — push the rate up until it is.

### When you really cannot build a loop

Stop and say so explicitly. List what you tried. Ask the user for: (a) access to an environment where the bug reproduces, (b) a captured artifact (HAR file, log dump, core dump, screen recording with timestamps),
or (c) permission to add temporary instrumentation in production. **Do not** move to hypotheses without a loop.

Do not move to Phase 2 until you have a loop you trust.

## Phase 2 — Reproduction

Run the loop. Watch the bug manifest.

Confirm:

- [ ] The loop reproduces the failure mode the **user** described, not a similar nearby failure. Wrong bug = wrong fix.
- [ ] The failure is reproducible across multiple runs (or, for non-deterministic bugs, reproducible often enough to debug).
- [ ] You captured the exact symptom (error message, wrong output, slow timing) so later phases can verify the fix actually solves the problem.

Do not proceed until you have reproduced the bug.

## Phase 3 — Hypotheses

Formulate **3–5 ranked hypotheses** before testing any of them. Generating only one hypothesis anchors you to the first plausible idea.

Each hypothesis must be **falsifiable**: state the prediction it implies.

> Format: "If the cause is <X>, then <change Y> will make the bug disappear / <change Z> will make it worse."

If you cannot state a prediction, the hypothesis is just a vibe; drop it or sharpen it.

**Show the ranked list to the user before testing.** They often have domain knowledge that will instantly reshuffle priorities ("we just deployed a change to #3"), or they know hypotheses that have already been ruled out.
A cheap checkpoint, big time savings. Don't block on it — keep going by your ranking if the user is away.

## Phase 4 — Instrumentation

Each probe must correspond to a specific prediction from Phase 3. **Change one variable at a time.**

Preferred tools:

1. **Debugger / REPL inspection** if the environment supports it. One breakpoint beats ten log lines.
2. **Targeted logs** at boundaries that separate hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g., `[DEBUG-a4f2]`. At the end, cleanup is a single grep. Untagged logs stay; tagged ones are removed.

**Performance branch.** For performance regressions, logs are usually useless. Instead: establish a baseline measurement (timing harness, `performance.now()`, profiler, query plan), then bisect. Measure first, fix second.

## Phase 5 — Fix + regression test

Write the regression test **before the fix** — but only if there is a **correct seam** for it.

A correct seam is one where the test exercises the **real bug pattern** as it occurs at the call site. If the only available seam is too shallow (a single-caller test when the bug requires multiple callers; a unit test
that cannot reproduce the chain that triggered the bug), a regression test there gives false confidence.

**If no correct seam exists, that is itself a finding.** Record it. The codebase architecture prevents pinning the bug down with a test. Flag this for the next phase.

If a correct seam exists:

1. Turn the minimized repro into a failing test at that seam.
2. Verify it fails.
3. Apply the fix.
4. Verify it passes.
5. Re-run the Phase 1 feedback loop on the original (non-minimized) scenario.

## Phase 6 — Cleanup + post-mortem

Required before declaring the task done:

- [ ] The original repro no longer reproduces (re-run the Phase 1 loop)
- [ ] The regression test passes (or the missing seam is documented)
- [ ] All `[DEBUG-...]` instrumentation is removed (`grep` for the prefix)
- [ ] One-off prototypes are deleted (or moved to a clearly marked debugging location)
- [ ] The hypothesis that turned out to be correct is recorded in the commit / PR message — so the next debugger learns

**Then ask: what would have prevented this bug?** If the answer suggests an architectural change (no good test seam, tangled callers, hidden coupling), hand off to the `/improve-codebase-architecture` skill with specifics.
Make the recommendation **after** the fix, not before — you now have more information than you started with.
