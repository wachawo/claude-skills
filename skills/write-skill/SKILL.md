---
name: write-skill
description: Create new agent skills with the right structure, progressive disclosure, and bundled resources. Use when the user wants to create, write, or assemble a new skill.
---

# Writing a Skill

## Process

1. **Gather requirements** — ask the user:
   - What task or area does the skill cover?
   - What specific use cases must it handle?
   - Are executable scripts needed, or are instructions enough?
   - What reference material should be included?

2. **Draft the skill** — create:
   - SKILL.md with concise instructions
   - Additional reference files if content exceeds 500 lines
   - Utility scripts when deterministic operations are required

3. **Review with the user** — present the draft and ask:
   - Does this cover your use cases?
   - What is missing or unclear?
   - Should any section be more or less detailed?

## Skill structure

```
skill-name/
├── SKILL.md           # Main instructions (required)
├── REFERENCE.md       # Detailed docs (if needed)
├── EXAMPLES.md        # Usage examples (if needed)
└── scripts/           # Utility scripts (if needed)
    └── helper.js
```

## SKILL.md template

```md
---
name: skill-name
description: Brief description of capability. Use when [specific triggers].
---

# Skill Name

## Quick start

[Minimal working example]

## Workflows

[Step-by-step processes with checklists for complex tasks]

## Advanced features

[Link to separate files: See [REFERENCE.md](REFERENCE.md)]
```

## Description requirements

The description is **the only thing your agent sees** when choosing which skill to load. It appears in the system prompt alongside every other installed skill. The agent reads these descriptions and picks the right skill based on the user's request.

**Goal**: give the agent just enough information to understand:

1. What capability this skill provides
2. When and why to invoke it (specific keywords, contexts, file types)

**Format**:

- Maximum 1024 characters
- Written in third person
- First sentence: what the skill does
- Second sentence: "Use when [specific triggers]"

**Good example**:

```
Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when user mentions PDFs, forms, or document extraction.
```

**Bad example**:

```
Helps with documents.
```

The bad example gives the agent no way to distinguish this skill from any other document-handling skill.

## When to add scripts

Add utility scripts when:

- The operation is deterministic (validation, formatting)
- The same code would have to be regenerated repeatedly
- Errors require explicit handling

Scripts save tokens and improve reliability compared to generated code.

## When to split files

Split into separate files when:

- SKILL.md exceeds 100 lines
- Content spans different domains (financial schemas vs. sales schemas)
- Advanced features are rarely needed

## Review checklist

After drafting, verify:

- [ ] The description contains triggers ("Use when...")
- [ ] SKILL.md is under 100 lines
- [ ] No time-bound information
- [ ] Consistent terminology
- [ ] Concrete examples included
- [ ] Links go no deeper than one level
