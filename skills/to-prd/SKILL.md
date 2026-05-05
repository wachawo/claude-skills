---
name: to-prd
description: Turns the current conversation context into a PRD and publishes it to the project's issue tracker. Use when the user wants to create a PRD from the current context.
---

This skill takes the current conversation context and codebase understanding and produces a PRD. Do NOT interview the user — just synthesize what you already know.

The issue tracker and triage label vocabulary should have already been provided to you — if not, run `/setup-matt-pocock-skills`.

## Process

1. Explore the repository to understand the current state of the codebase, if you have not done so already. Use the project's domain glossary throughout the PRD and respect any ADRs in the area you are touching.

2. Sketch the main modules you will need to build or modify to complete the implementation. Actively look for opportunities to factor out deep modules that can be tested in isolation.

A deep module (as opposed to a shallow one) encapsulates a lot of functionality behind a simple, testable interface that rarely changes.

Confirm with the user whether these modules match their expectations. Confirm which modules they want tests written for.

3. Write the PRD using the template below, then publish it to the project's issue tracker. Apply the `needs-triage` label so it enters the standard triage flow.

<prd-template>

## Problem Statement

The problem the user faces, from the user's perspective.

## Solution

The solution to the problem from the user's perspective.

## User Stories

A LONG numbered list of user stories. Each story should be in the format:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be very extensive and cover every aspect of the functionality.

## Implementation Decisions

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
- Test precedents (i.e., similar kinds of tests in the codebase)

## Out of Scope

A description of things that are outside the scope of this PRD.

## Further Notes

Any additional notes about the functionality.

</prd-template>
