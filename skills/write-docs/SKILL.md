---
name: write-docs
description: Walk the user through a structured collaborative documentation workflow. Use when the user wants to write documentation, proposals, technical specs, decision documents, or similar structured content. The workflow helps users transfer context efficiently, refine content iteratively, and verify the document works for its readers. Triggers when the user mentions writing documentation, drafting proposals, sketching specs, or similar documentation tasks.
---

# Doc Co-Authoring Workflow

This skill provides a structured workflow for guiding users through collaborative document creation. Act as an active guide, walking users through three stages: Context Gathering, Refinement and Structure, and Reader Testing.

## When to propose this workflow

**Trigger conditions:**
- User mentions writing documentation: "write a doc", "draft a proposal", "create a spec", "write up"
- User mentions specific document types: "PRD", "design doc", "decision doc", "RFC"
- User appears to be starting a substantial writing task

**Initial offer:**
Offer the user a structured workflow for collaborating on the document. Explain the three stages:

1. **Context Gathering**: The user provides all relevant context while Claude asks clarifying questions
2. **Refinement and Structure**: We iteratively build each section through brainstorming and editing
3. **Reader Testing**: We test the document with a fresh Claude (no context) to catch blind spots before others read it

Explain that this approach helps ensure the document works well when others read it (including when they paste it into Claude). Ask whether they want to try this workflow or prefer to work freeform.

If the user declines, work freeform. If they agree, proceed to Stage 1.

## Stage 1: Context Gathering

**Goal:** Close the gap between what the user knows and what Claude knows, so smart prompts can be given afterward.

### Initial questions

Begin by asking the user to provide meta-context about the document:

1. What type of document is this? (e.g., technical spec, decision doc, proposal)
2. Who is the primary audience?
3. What is the desired impact when someone reads it?
4. Is there a template or specific format to follow?
5. Are there other constraints or context that should be known?

Tell them they can answer in shorthand or dump information however is convenient.

**If the user provides a template or mentions a document type:**
- Ask whether they have a template document to share
- If they share a link to a shared document, use the appropriate integration to fetch it
- If they provide a file, read it

**If the user mentions editing an existing shared document:**
- Use the appropriate integration to read its current state
- Check for images without alt-text
- If there are images without alt-text, explain that when others use Claude to understand the document, Claude won't be able to see them. Ask if they want alt-text generated. If yes, ask them to paste each image into the chat for descriptive alt-text generation.

### Information dump

Once initial questions are answered, encourage the user to dump all the context they have. Request information such as:
- Background on the project/problem
- Related team discussions or shared documents
- Why alternative solutions are not being used
- Organizational context (team dynamics, past incidents, politics)
- Deadline pressure or constraints
- Technical architecture or dependencies
- Stakeholder concerns

Advise them not to worry about organization — just get it all out. Offer several ways to provide context:
- Stream-of-consciousness dump
- Pointing to team channels or threads to read
- Linking to shared documents

**If integrations are available** (e.g., Slack, Teams, Google Drive, SharePoint, or other MCP servers), mention they can be used to pull context directly.

**If no integrations are detected and Claude.ai or the Claude app is in use:** Offer to enable connectors in Claude settings to allow pulling context from chat tools and document stores directly.

Tell them clarifying questions will follow once they finish their initial dump.

**During context gathering:**

- If the user mentions team channels or shared documents:
  - If integrations are available: Tell them the content will be read now, then use the appropriate integration
  - If integrations are unavailable: Explain the lack of access. Suggest enabling connectors in Claude settings or pasting the relevant content directly.

- If the user mentions entities/projects that are unfamiliar:
  - Ask whether to search connected tools to learn more
  - Wait for user confirmation before searching

- As the user provides context, track what is being learned and what remains unclear

**Asking clarifying questions:**

When the user signals they have finished the initial dump (or after substantial context has been provided), ask clarifying questions to confirm understanding:

Generate 5-10 numbered questions based on context gaps.

Tell them they can answer in shorthand (e.g., "1: yes, 2: see #channel, 3: no because backwards compat"), link to more documents, point to channels to read, or just keep dumping. Whatever is most efficient.

**Exit condition:**
Sufficient context has been gathered when the questions reveal understanding — when edge cases and trade-offs can be discussed without needing to explain the basics.

**Transition:**
Ask whether there is more context to provide at this stage, or whether it is time to move on to drafting the document.

If the user wants to add more, allow it. When ready, move to Stage 2.

## Stage 2: Refinement and Structure

**Goal:** Build the document section by section through brainstorming, selection, and iterative refinement.

**Instructions to the user:**
Explain that the document will be built section by section. For each section:
1. Clarifying questions about what to include will be asked
2. 5-20 options will be brainstormed
3. The user indicates what to keep/remove/combine
4. The section is drafted
5. It is refined through surgical edits

Begin with the section that has the most unknowns (usually the main decision/proposal), then work through the rest.

**Section order:**

If the document structure is clear:
Ask which section they would like to start with.

Suggest starting with the section with the most unknowns. For decision documents this is usually the main proposal. For specs this is usually the technical approach. Summary sections are best left for the end.

If the user does not know which sections they need:
Based on document type and template, suggest 3-5 sections appropriate for the document type.

Ask whether this structure works, or whether they want to adjust it.

**Once the structure is agreed upon:**

Create an initial document structure with placeholder text for all sections.

**If artifact access is available:**
Use `create_file` to create an artifact. This gives both Claude and the user a skeleton to work from.

Tell them an initial structure will be created with placeholders for all sections.

Create the artifact with all section headings and brief placeholder text such as "[To be written]" or "[Content here]".

Provide a link to the skeleton and indicate it is time to fill in each section.

**If artifact access is not available:**
Create a markdown file in the working directory. Name it appropriately (e.g., `decision-doc.md`, `technical-spec.md`).

Tell them an initial structure will be created with placeholders for all sections.

Create the file with all section headings and placeholder text.

Confirm a file with that name was created and indicate it is time to fill in each section.

**For each section:**

### Step 1: Clarifying questions

Announce that work is starting on section [SECTION NAME]. Ask 5-10 clarifying questions about what to include:

Generate 5-10 specific questions based on the context and the section's purpose.

Tell them they can answer in shorthand or just point to what is important to cover.

### Step 2: Brainstorm

For section [SECTION NAME], brainstorm 5-20 things that could be included, depending on section complexity. Look for:
- Context that has been shared and may have been forgotten
- Angles or considerations not yet mentioned

Generate 5-20 numbered options based on the complexity of the section. At the end, offer to brainstorm more if they want additional options.

### Step 3: Selection

Ask which items to keep, remove, or combine. Request short rationale to help learn priorities for subsequent sections.

Provide examples:
- "Keep 1,4,7,9"
- "Remove 3 (duplicates 1)"
- "Remove 6 (audience already knows this)"
- "Combine 11 and 12"

**If the user gives freeform feedback** (e.g., "looks good" or "I like most of it, but...") instead of numbered choices, extract their preferences and continue. Parse what they want to keep/remove/change and apply it.

### Step 4: Gap check

Based on what they selected, ask whether there is anything important missing for section [SECTION NAME].

### Step 5: Draft

Use `str_replace` to replace the placeholder text for this section with the actual drafted content.

Announce that section [SECTION NAME] will now be drafted based on what they selected.

**If using artifacts:**
After drafting, provide a link to the artifact.

Ask them to read it and indicate what to change. Note that specificity helps in learning for subsequent sections.

**If using a file (no artifacts):**
After drafting, confirm completion.

Tell them section [SECTION NAME] is drafted in [filename]. Ask them to read it and indicate what to change. Note that specificity helps in learning for subsequent sections.

**Key instruction to the user (include while drafting the first section):**
Note: Instead of editing the document directly, ask them to indicate what to change. This helps learn their style for future sections. For example: "Remove the X bullet - already covered by Y" or "Make the third paragraph more concise".

### Step 6: Iterative refinement

As the user gives feedback:
- Use `str_replace` to make edits (never retype the whole document)
- **If using artifacts:** Provide a link to the artifact after each edit
- **If using files:** Just confirm that the edits are complete
- If the user edits the document directly and asks for it to be re-read: mentally note the changes they made and keep them in mind for future sections (this reveals their preferences)

**Continue iterating** until the user is satisfied with the section.

### Quality check

After 3 consecutive iterations without substantive changes, ask whether anything can be removed without losing important information.

When the section is ready, confirm that [SECTION NAME] is complete. Ask whether they are ready to move on to the next section.

**Repeat for all sections.**

### Approaching the end

As you approach completion (80%+ of sections done), announce the intent to re-read the entire document and check:
- Flow and consistency between sections
- Redundancy or contradictions
- Anything that feels "slop" or generic filler
- Whether each sentence carries weight

Read the full document and provide feedback.

**When all sections are drafted and refined:**
Announce that all sections are drafted. Indicate the intent to walk through the full document once more.

Review for overall coherence, flow, and completeness.

Provide any final suggestions.

Ask whether they are ready to move to Reader Testing, or whether they want to refine more.

## Stage 3: Reader Testing

**Goal:** Test the document with a fresh Claude (without leaking context) to verify it works for readers.

**Instructions to the user:**
Explain that testing will now happen to see whether the document actually works for readers. This catches blind spots — things that make sense to the authors but may confuse others.

### Testing approach

**If sub-agent access is available (e.g., in Claude Code):**

Carry out testing directly, without user involvement.

### Step 1: Predict reader questions

Announce the intent to predict what questions readers might ask while trying to evaluate this document.

Generate 5-10 questions readers would realistically ask.

### Step 2: Test with a sub-agent

Announce that these questions will be tested with a fresh Claude instance (no context from this conversation).

For each question, invoke a sub-agent, passing only the document content and the question.

Summarize what Reader Claude got right/wrong on each question.

### Step 3: Run additional checks

Announce that additional checks will be run.

Invoke a sub-agent to check for ambiguity, false assumptions, contradictions.

Summarize the issues found.

### Step 4: Report back and fix

If issues are found:
Report that Reader Claude struggled with specific issues.

List the specific problems.

Indicate the intent to fix these gaps.

Return to refining the problematic sections.

---

**If no sub-agent access is available (e.g., the claude.ai web interface):**

The user will need to run the test manually.

### Step 1: Predict reader questions

Ask what questions people might ask while trying to evaluate this document. What would they type into Claude.ai?

Generate 5-10 questions readers would realistically ask.

### Step 2: Set up the test

Provide testing instructions:
1. Open a fresh Claude conversation: https://claude.ai
2. Paste or share the document content (if a shared document platform with connectors enabled is in use, share the link)
3. Ask Reader Claude the generated questions

For each question, instruct Reader Claude to provide:
- An answer
- Whether anything was ambiguous or unclear
- What knowledge/context the document assumes is already known

Check whether Reader Claude gives correct answers or misinterprets anything.

### Step 3: Additional checks

Also ask Reader Claude:
- "What in this document might be ambiguous or unclear to readers?"
- "What knowledge or context does this document assume readers already have?"
- "Are there any internal contradictions or inconsistencies?"

### Step 4: Iterate based on results

Ask what Reader Claude got wrong or struggled with. Indicate the intent to fix these gaps.

Return to refining any problematic sections.

---

### Exit condition (for both approaches)

When Reader Claude consistently answers questions correctly and surfaces no new gaps or ambiguities, the document is ready.

## Final review

When Reader Testing is complete:
Announce that the document has passed Reader Claude testing. Before completion:

1. Recommend that they do a final read themselves — they own this document and are responsible for its quality
2. Suggest double-checking any facts, links, or technical details
3. Ask them to verify it achieves the desired impact

Ask whether they want one more review, or whether the work is finished.

**If the user wants a final review, give it. Otherwise:**
Announce document completion. Provide some final tips:
- Consider attaching a link to this conversation as an appendix so readers can see how the document was developed
- Use appendices to add depth without bloating the main document
- Update the document as feedback arrives from real readers

## Tips for effective guidance

**Tone:**
- Be direct and procedural
- Briefly explain rationale when it affects user behavior
- Don't try to "sell" the approach — just execute it

**Handling deviations:**
- If the user wants to skip a stage: Ask whether they want to skip it and write freeform
- If the user appears frustrated: Acknowledge it is taking longer than expected. Suggest ways to move faster
- Always give the user the chance to adjust the process

**Context management:**
- Throughout, if context on something mentioned is missing, proactively ask
- Do not let gaps accumulate — address them as they emerge

**Artifact management:**
- Use `create_file` to draft full sections
- Use `str_replace` for all edits
- Provide a link to the artifact after each change
- Never use artifacts for brainstorm lists — those are just conversation

**Quality over speed:**
- Do not rush through stages
- Each iteration should bring meaningful improvement
- The goal is a document that actually works for readers
