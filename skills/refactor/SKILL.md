---
name: refactor
description: Produces a detailed refactoring plan with tiny commits via a user interview, captured as a GitHub issue. Use when the user wants to plan a refactor,
  create a refactoring RFC, or break a refactor into safe incremental steps.
---

This skill is invoked when the user wants to create a refactoring request. Walk through the steps below. Some steps may be skipped if you consider them unnecessary.

1. Ask the user for a long, detailed description of the problem they want to solve and any possible ideas for a solution.

2. Explore the repository to verify their claims and to understand the current state of the codebase.

3. Ask whether they have considered alternatives, and propose other options.

4. Interview the user about the implementation. Be extremely detailed and thorough.

5. Clearly capture the exact scope of the implementation. Specify what you plan to change and what you will not.

6. Look into the codebase to assess the test coverage of the area. If coverage is insufficient, ask the user about their testing plans.

7. Break the implementation into a plan of tiny commits. Recall Martin Fowler's advice: "make each refactoring step as small as possible, so that you can always see the program working."

8. Create a GitHub issue with the refactoring plan. Use the following template for the issue body:

<refactor>

## Problem Statement

The problem the developer faces, from the developer's perspective.

## Solution

The solution to the problem from the developer's perspective.

## Commits

A LONG, detailed implementation plan. Write the plan in plain English, breaking the implementation into the tiniest possible commits. Each commit must leave the codebase in a working state.

## Decision Document

A list of accepted implementation decisions. This may include:

- Modules that will be built/modified
- Interfaces of those modules that will be changed
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include concrete file paths or code snippets. They can become stale very quickly.

## Testing Decisions

A list of accepted testing decisions. Include:

- A description of what makes a good test (test only external behavior, not implementation details)
- Which modules will be tested
- Precedents for the tests (i.e., similar kinds of tests in the codebase)

## Out of Scope

A description of what is outside the scope of this refactor.

## Further Notes (optional)

Any additional notes about the refactor.

</refactor>
