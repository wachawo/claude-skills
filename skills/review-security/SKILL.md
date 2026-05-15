---
name: "review-security"
description: "Perform language- and framework-specific security best-practice reviews and propose improvements. Activate only when the user explicitly requests security best-practice guidance, a security review/report, or help writing secure-by-default code. Activate only for supported languages (python, javascript/typescript, go). Do not activate for general code review, debugging, or tasks unrelated to security."
---

# Security Best Practices

## Overview

This skill describes how to identify the language and frameworks used in the current context and then load language- and/or framework-specific security best-practice information from this skill's references directory.

When available, this information can be used to write new secure-by-default code, to passively detect serious issues in existing code, or (on user request) to produce a vulnerability report with proposed fixes.

## Workflow

The first step for this skill is to identify ALL languages and ALL frameworks you are being asked to use, or that already exist within the project you are working on. Focus on the primary, core frameworks. You will often need to identify both frontend and backend languages and frameworks.

Next, check this skill's references directory to determine whether suitable documentation exists for the language and/or frameworks. Make sure you read ALL reference files relevant to the specific framework or language. The filename format is `<language>-<framework>-<stack>-security.md`. It is also worth checking whether a `<language>-general-<stack>-security.md` file exists that is not tied to a specific framework.

If the work involves a web application that includes both a frontend and a backend, be sure to check the reference documents for BOTH the frontend AND the backend.

If you are asked to build a web application that includes both a frontend and a backend but the frontend framework is not specified, additionally consult `javascript-general-web-frontend-security.md`. It is important to understand how to secure both the frontend and the backend.

If the skill's references directory does not contain suitable information, briefly consider what you know about the language, the framework, and any well-known security best practices for them. If you are unsure, you can try searching for online documentation about security best practices.

From there, work can proceed in several modes.

1. The primary mode is to simply use this information to write secure-by-default code from this point forward. This is useful when starting a new project or when writing new code.

2. The secondary mode is to passively detect vulnerabilities while working in the project and writing code for the user. Critical or very important vulnerabilities, or significant deviations from security recommendations, can be flagged and reported to the user. This passive mode should focus on the highest-impact vulnerabilities and on secure defaults.

3. The user may request a security report or ask you to improve the security of the codebase. In this case, prepare a full report describing every case where the project does not follow security best-practice recommendations. The report must be prioritized and have clear sections by severity and urgency. Then offer to begin work on fixing these issues. See #fixes below.

## Workflow Decision Tree

- If the language/framework is unclear, examine the repository to determine it and present your reasoning.
- If suitable guidance exists in `references/`, load only the relevant files and follow their instructions.
- If no suitable guidance exists, consider whether you know any well-known security best practices for the chosen language and/or frameworks; if asked to generate a report, inform the user that no specific guidance is available (you can still generate a report or reliably flag critical vulnerabilities).

# Overrides

Although these references contain security best practices for languages and frameworks, customers may have cases where they need to bypass or override these practices. Pay attention to project-specific rules and instructions in project documentation and prompt files that may require you to override certain best practices. When overriding a best practice, you MAY inform the user, but do not argue with them. If a security best practice needs to be bypassed/ignored for a project-specific reason, you may also offer to add documentation about it to the project so it is clear why the practice is not being followed and so the exception applies going forward.

# Report Format

## Output File Naming

The result of a security review MUST be written to a markdown file named `REVIEW-SECURITY.md` (uppercase, hyphenated). This is the canonical filename for the output of this skill.

- Default location: project root (`./REVIEW-SECURITY.md`).
- If multiple reviews are produced over time, suffix with an ISO date: `REVIEW-SECURITY-2026-05-14.md`.
- If the review targets a specific subproject/package, place it at that subproject's root (e.g. `api/REVIEW-SECURITY.md`).
- The user may override the location, but the filename `REVIEW-SECURITY.md` (or its dated variant) MUST be preserved so the artifact is easy to discover by convention.

Do not use legacy names like `security_best_practices_report.md`, `security-report.md`, or `SECURITY_REVIEW.md` — always use `REVIEW-SECURITY.md`.

## Report Structure

The report should begin with a brief executive summary.

The report must be clearly divided into sections by vulnerability severity. The report should focus on the most critical findings, since they have the greatest impact on the user. All findings should be tagged with a numeric ID so they can be easily referenced.

For critical findings, include a one-sentence impact statement.

Once the report is written, also report it back to the user directly, although you may be less verbose. You may offer to clarify any of the findings or the reasoning behind the security best-practice recommendations if the user wants more information about any of them.

Important: when referencing code in the report, be sure to locate and include line numbers for the code you reference.

After the report file is written, briefly summarize the findings to the user.

Also tell the user where the final report was written.

# Fixes

If you have produced a report, allow the user to read it and ask you to begin applying fixes.

If you have passively detected a critical finding, notify the user and ask whether they would like you to fix that finding.

When applying fixes, focus on one finding at a time. Fixes should include short, clear comments explaining that the new code is based on a specific security best practice, and possibly a very brief explanation of why doing it differently would be unsafe.

Always consider whether the changes you make will affect the functionality of the user's code. Think about whether the changes might cause regressions in the project's current behavior. Often, insecure code is in place for other reasons (which is why insecure code persists for so long). Avoid breaking the user's project, since this may discourage them from applying security fixes in the future. It is better to write a thoughtful fix that is well-aligned with the rest of the project than to make a quick, careless change.

Always follow the user's normal change or commit process. When creating git commits, write clear commit messages explaining that the change is being made to comply with security best practices. Try not to combine multiple unrelated findings into a single commit.

Always follow the user's normal testing processes (if any) to ensure your changes do not introduce regressions. Be aware of side effects that may arise from the changes and inform the user about them before making them.

# General Security Recommendations

Below are a few secure-coding tips that apply to virtually any language or framework.

### Avoid Incremental IDs for Public Resource Identifiers

When assigning an ID to a resource that will subsequently be used or displayed on the internet, avoid small auto-incrementing IDs. Use longer random UUID4s or random hex strings. This prevents users from learning the number of resources and from guessing their IDs.

### A Note on TLS

Although TLS is important for production deployments, much development is done with TLS disabled or with TLS provided by some external TLS proxy. For this reason, be very careful not to report the absence of TLS as a security issue. Also be very careful with the use of "secure" cookies. They should only be set if the application is actually running over TLS. If they are set in an application without TLS (for example, during local development or testing), the application will break. You can introduce an env variable or another flag to override the secure setting and keep it disabled until rolled out to a TLS production environment. In addition, avoid recommending HSTS. Using it without a full understanding of its long-term consequences is dangerous (it can cause serious outages and lock users out), and it is generally not recommended for the scope of projects audited by codex.
