# MCP Server Evaluation Guide

## Overview

This document provides guidance for building comprehensive evaluations of MCP servers. Evaluations verify that LLMs can effectively use your MCP server to answer realistic, complex questions using only the provided tools.

---

## Quick reference

### Evaluation requirements
- Build 10 human-readable questions
- Questions must be READ-ONLY, INDEPENDENT, NON-DESTRUCTIVE
- Each question requires multiple tool calls (potentially dozens)
- Answers must be single verifiable values
- Answers must be STABLE (not change over time)

### Output format
```xml
<evaluation>
   <qa_pair>
      <question>Your question here</question>
      <answer>Single verifiable answer</answer>
   </qa_pair>
</evaluation>
```

---

## Purpose of evaluations

The measure of an MCP server's quality is NOT how well or fully the server implements its tools, but how well those implementations (input/output schemas, docstrings/descriptions, functionality) let an LLM, given no other context and access ONLY to MCP servers, answer realistic and difficult questions.

## Evaluation overview

Build 10 human-readable questions that require ONLY READ-ONLY, INDEPENDENT, NON-DESTRUCTIVE, and IDEMPOTENT operations to answer. Each question must be:
- Realistic
- Clear and concise
- Unambiguous
- Complex, requiring potentially dozens of tool calls or steps
- Answerable with a single verifiable value that you determine in advance

## Question guidelines

### Core requirements

1. **Questions MUST be independent**
   - Each question must NOT depend on the answer to another question
   - Must not assume prior write operations performed while answering another question

2. **Questions MUST require ONLY NON-DESTRUCTIVE AND IDEMPOTENT tools**
   - Must not require or imply state changes to obtain the correct answer

3. **Questions must be REALISTIC, CLEAR, CONCISE, and COMPLEX**
   - Must require another LLM to use many (potentially dozens of) tools or steps

### Complexity and depth

4. **Questions must require deep exploration**
   - Consider multi-hop questions that require multiple sub-questions and sequential tool calls
   - Each step should build on information from previous ones

5. **Questions may require extensive pagination**
   - May require paging through several pages of results
   - May require querying older data (1-2 years old) for niche information
   - Questions must be COMPLEX

6. **Questions must require deep understanding**
   - Not surface-level knowledge
   - May pose complex ideas as True/False questions that require evidence
   - May use multiple-choice format where the LLM must explore different hypotheses

7. **Questions must not be solvable with simple keyword search**
   - Don't include specific keywords from the target content
   - Use synonyms, related concepts, or paraphrasing
   - Require multiple searches, analysis of several related items, context extraction, then deriving the answer

### Tool stress-testing

8. **Questions must stress tool return values**
   - May call tools that return large JSON objects or lists, overloading the LLM
   - Must require understanding of multiple data modalities:
     - IDs and names
     - Timestamps and datetimes (months, days, years, seconds)
     - File IDs, names, extensions, and mimetypes
     - URLs, GIDs, etc.
   - Must verify the tool's ability to return all useful forms of data

9. **Questions should MOSTLY reflect real user scenarios**
   - The kinds of information-retrieval tasks that PEOPLE care about when working with LLMs

10. **Questions may require dozens of tool calls**
    - This stresses an LLM with limited context
    - Encourages MCP-server tools to reduce returned information

11. **Include ambiguous questions**
    - May be ambiguous OR require complex tool-selection decisions
    - Force the LLM to potentially err or misinterpret
    - Make sure that despite the AMBIGUITY there is still ONE VERIFIABLE ANSWER

### Stability

12. **Questions must be designed so the answer DOES NOT CHANGE**
    - Don't ask questions that rely on "current state", which is dynamic
    - For example, don't count:
      - Number of reactions on a post
      - Number of replies in a thread
      - Number of channel members

13. **DO NOT ALLOW the MCP server to LIMIT the kinds of questions you create**
    - Build complex and difficult questions
    - Some may not be solvable with the available MCP-server tools
    - Questions may require specific output formats (datetime vs. epoch time, JSON vs. MARKDOWN)
    - Questions may require dozens of tool calls

## Answer guidelines

### Verifiability

1. **Answers must be checkable via direct string comparison**
   - If the answer can be written in many formats, clearly specify the output format in the QUESTION
   - Examples: "Use YYYY/MM/DD.", "Respond True or False.", "Answer A, B, C, or D and nothing else."
   - The answer must be a single VERIFIABLE value, e.g.:
     - User ID, user name, display name, first name, last name
     - Channel ID, channel name
     - Message ID, string
     - URL, title
     - Numeric value
     - Timestamp, datetime
     - Boolean (for True/False questions)
     - Email, phone number
     - File ID, file name, extension
     - Multiple-choice answer
   - Answers must not require special formatting or complex structured output
   - The answer will be checked by DIRECT STRING COMPARISON

### Readability

2. **Answers should generally be in HUMAN-READABLE formats**
   - Examples: names, first/last name, datetime, file name, message string, URL, yes/no, true/false, a/b/c/d
   - Rather than opaque IDs (although IDs are acceptable)
   - The OVERWHELMING MAJORITY of answers should be human-readable

### Stability

3. **Answers must be STABLE/UNCHANGING**
   - Look at older content (e.g. completed conversations, launched projects, answered questions)
   - Build QUESTIONS around "closed" concepts that always return the same answer
   - Questions may ask the LLM to consider a fixed time window to guard against unstable answers
   - Rely on context that IS UNLIKELY TO CHANGE
   - Example: when searching for an article title, be SPECIFIC so the answer is not confused with articles published later

4. **Answers must be CLEAR and UNAMBIGUOUS**
   - Questions must be phrased so a single, clear answer exists
   - The answer must be obtainable using the MCP server's tools

### Diversity

5. **Answers must be DIVERSE**
   - The answer must be a single VERIFIABLE value across various modalities and formats
   - User entity: user ID, user name, display name, first name, last name, email, phone
   - Channel entity: channel ID, channel name, channel topic
   - Message entity: message ID, message string, timestamp, month, day, year

6. **Answers MUST NOT be complex structures**
   - Not a list of values
   - Not a complex object
   - Not a list of IDs or strings
   - Not natural-language text
   - UNLESS the answer can simply be checked by DIRECT STRING COMPARISON
   - And can realistically be reproduced
   - It is unlikely an LLM will return the same list in a different order or format

## Evaluation process

### Step 1: Documentation inspection

Read the target API's documentation to understand:
- Available endpoints and functionality
- If there is ambiguity, get additional information from the web
- Parallelize this step AS MUCH AS POSSIBLE
- Make sure each sub-agent only studies documentation from the file system or the web

### Step 2: Tool inspection

List the tools available in the MCP server:
- Inspect the MCP server directly
- Understand input/output schemas, docstrings, and descriptions
- WITHOUT calling the tools themselves at this stage

### Step 3: Build understanding

Repeat steps 1 and 2 until you have a good understanding:
- Iterate several times
- Think about the kinds of tasks you want to create
- Refine your understanding
- AT NO POINT read the MCP server's implementation code
- Use intuition and understanding to build reasonable, realistic, but VERY difficult tasks

### Step 4: Read-only content inspection

After understanding the API and tools, USE the MCP server's tools:
- Inspect content using ONLY READ-ONLY and non-destructive operations
- Goal: surface concrete content (e.g. users, channels, messages, projects, tasks) for building realistic questions
- MUST NOT call tools that change state
- DO NOT read the MCP server's implementation code
- Parallelize this step with separate sub-agents conducting independent investigations
- Make sure each sub-agent only performs READ-ONLY, NON-DESTRUCTIVE, and IDEMPOTENT operations
- WARNING: SOME TOOLS may return LOTS OF DATA, which can cause CONTEXT overflow
- Make INCREMENTAL, SMALL, and TARGETED tool calls during exploration
- In every tool call, use the `limit` parameter to bound results (<10)
- Use pagination

### Step 5: Task generation

After inspecting the content, build 10 human-readable questions:
- An LLM must be able to answer them using the MCP server
- Follow all the question and answer guidelines above

## Output format

Each QA pair consists of a question and an answer. The output must be an XML file with this structure:

```xml
<evaluation>
   <qa_pair>
      <question>Find the project created in Q2 2024 with the highest number of completed tasks. What is the project name?</question>
      <answer>Website Redesign</answer>
   </qa_pair>
   <qa_pair>
      <question>Search for issues labeled as "bug" that were closed in March 2024. Which user closed the most issues? Provide their username.</question>
      <answer>sarah_dev</answer>
   </qa_pair>
   <qa_pair>
      <question>Look for pull requests that modified files in the /api directory and were merged between January 1 and January 31, 2024. How many different contributors worked on these PRs?</question>
      <answer>7</answer>
   </qa_pair>
   <qa_pair>
      <question>Find the repository with the most stars that was created before 2023. What is the repository name?</question>
      <answer>data-pipeline</answer>
   </qa_pair>
</evaluation>
```

## Evaluation examples

### Good questions

**Example 1: Multi-hop question requiring deep investigation (GitHub MCP)**
```xml
<qa_pair>
   <question>Find the repository that was archived in Q3 2023 and had previously been the most forked project in the organization. What was the primary programming language used in that repository?</question>
   <answer>Python</answer>
</qa_pair>
```

This question is good because:
- It requires multiple searches to find archived repositories
- You must determine which had the most forks before archival
- It requires inspecting repository details for the language
- The answer is a simple, verifiable value
- Based on historical (closed) data that won't change

**Example 2: Requires context understanding without keyword matching (Project Management MCP)**
```xml
<qa_pair>
   <question>Locate the initiative focused on improving customer onboarding that was completed in late 2023. The project lead created a retrospective document after completion. What was the lead's role title at that time?</question>
   <answer>Product Manager</answer>
</qa_pair>
```

This question is good because:
- It doesn't use the project's actual title ("initiative focused on improving customer onboarding")
- Requires finding completed projects in a specific time window
- Must determine the project lead and their role
- Requires context understanding from retrospective documents
- The answer is human-readable and stable
- Based on completed work (won't change)

**Example 3: Complex aggregation requiring multiple steps (Issue Tracker MCP)**
```xml
<qa_pair>
   <question>Among all bugs reported in January 2024 that were marked as critical priority, which assignee resolved the highest percentage of their assigned bugs within 48 hours? Provide the assignee's username.</question>
   <answer>alex_eng</answer>
</qa_pair>
```

This question is good because:
- Requires filtering bugs by date, priority, and status
- Must group by assignee and compute resolution rate
- Requires understanding timestamps to determine the 48-hour window
- Stresses pagination (potentially many bugs)
- The answer is a single username
- Based on historical data from a specific period

**Example 4: Requires synthesis across data types (CRM MCP)**
```xml
<qa_pair>
   <question>Find the account that upgraded from the Starter to Enterprise plan in Q4 2023 and had the highest annual contract value. What industry does this account operate in?</question>
   <answer>Healthcare</answer>
</qa_pair>
```

This question is good because:
- Requires understanding subscription tier changes
- Must surface upgrade events in a specific time window
- Requires comparing contract values
- Must access industry information
- The answer is simple and verifiable
- Based on completed historical transactions

### Bad questions

**Example 1: Answer changes over time**
```xml
<qa_pair>
   <question>How many open issues are currently assigned to the engineering team?</question>
   <answer>47</answer>
</qa_pair>
```

This question is bad because:
- The answer changes when issues are created, closed, or reassigned
- Not based on stable/unchanging data
- Relies on "current state", which is dynamic

**Example 2: Too easy via keyword search**
```xml
<qa_pair>
   <question>Find the pull request with title "Add authentication feature" and tell me who created it.</question>
   <answer>developer123</answer>
</qa_pair>
```

This question is bad because:
- Solvable with a simple search for the exact title
- Doesn't require deep investigation or understanding
- No synthesis or analysis needed

**Example 3: Ambiguous answer format**
```xml
<qa_pair>
   <question>List all the repositories that have Python as their primary language.</question>
   <answer>repo1, repo2, repo3, data-pipeline, ml-tools</answer>
</qa_pair>
```

This question is bad because:
- The answer is a list that can be returned in any order
- Hard to verify with direct string comparison
- The LLM may format it differently (JSON array, comma-separated, newline-separated)
- It's better to ask for a specific aggregate (count) or superlative (most stars)

## Verification process

After building the evaluations:

1. **Read the XML file** to understand the schema
2. **Load each task instruction** and, in parallel using the MCP server and its tools, determine the correct answer by trying to solve the task YOURSELF
3. **Flag any operation** that requires WRITE or DESTRUCTIVE actions
4. **Accumulate all CORRECT answers** and replace incorrect answers in the document
5. **Remove any `<qa_pair>`** that requires WRITE or DESTRUCTIVE operations

Remember: parallelize task solving so you don't exhaust context, then accumulate all answers and apply the changes to the file at the end.

## Tips for building quality evaluations

1. **Think hard and plan ahead** before generating tasks
2. **Parallelize where possible** to speed things up and manage context
3. **Focus on real scenarios** that people actually want to solve
4. **Build complex questions** that probe the limits of the MCP server's capabilities
5. **Ensure stability** by using historical data and closed concepts
6. **Verify answers** by solving the questions yourself with the MCP server's tools
7. **Iteratively refine** based on what you learn during the process

---

# Running evaluations

Once you've created an evaluation file, you can use the provided harness to test your MCP server.

## Setup

1. **Install dependencies**

   ```bash
   pip install -r scripts/requirements.txt
   ```

   Or install manually:
   ```bash
   pip install anthropic mcp
   ```

2. **Set the API key**

   ```bash
   export ANTHROPIC_API_KEY=your_api_key_here
   ```

## Evaluation file format

Evaluation files use an XML format with `<qa_pair>` elements:

```xml
<evaluation>
   <qa_pair>
      <question>Find the project created in Q2 2024 with the highest number of completed tasks. What is the project name?</question>
      <answer>Website Redesign</answer>
   </qa_pair>
   <qa_pair>
      <question>Search for issues labeled as "bug" that were closed in March 2024. Which user closed the most issues? Provide their username.</question>
      <answer>sarah_dev</answer>
   </qa_pair>
</evaluation>
```

## Running evaluations

The evaluation script (`scripts/evaluation.py`) supports three transport types:

**Important:**
- **stdio transport**: the evaluation script automatically launches and manages the MCP server process. Don't start the server manually.
- **sse/http transports**: you must start the MCP server separately before running the evaluation. The script connects to the already-running server at the specified URL.

### 1. Local STDIO server

For locally launched MCP servers (the script starts the server automatically):

```bash
python scripts/evaluation.py \
  -t stdio \
  -c python \
  -a my_mcp_server.py \
  evaluation.xml
```

With environment variables:
```bash
python scripts/evaluation.py \
  -t stdio \
  -c python \
  -a my_mcp_server.py \
  -e API_KEY=abc123 \
  -e DEBUG=true \
  evaluation.xml
```

### 2. Server-Sent Events (SSE)

For SSE-based MCP servers (you must start the server first):

```bash
python scripts/evaluation.py \
  -t sse \
  -u https://example.com/mcp \
  -H "Authorization: Bearer token123" \
  -H "X-Custom-Header: value" \
  evaluation.xml
```

### 3. HTTP (Streamable HTTP)

For HTTP-based MCP servers (you must start the server first):

```bash
python scripts/evaluation.py \
  -t http \
  -u https://example.com/mcp \
  -H "Authorization: Bearer token123" \
  evaluation.xml
```

## Command-line options

```
usage: evaluation.py [-h] [-t {stdio,sse,http}] [-m MODEL] [-c COMMAND]
                     [-a ARGS [ARGS ...]] [-e ENV [ENV ...]] [-u URL]
                     [-H HEADERS [HEADERS ...]] [-o OUTPUT]
                     eval_file

positional arguments:
  eval_file             Path to evaluation XML file

optional arguments:
  -h, --help            Show help message
  -t, --transport       Transport type: stdio, sse, or http (default: stdio)
  -m, --model           Claude model to use (default: claude-3-7-sonnet-20250219)
  -o, --output          Output file for report (default: print to stdout)

stdio options:
  -c, --command         Command to run MCP server (e.g., python, node)
  -a, --args            Arguments for the command (e.g., server.py)
  -e, --env             Environment variables in KEY=VALUE format

sse/http options:
  -u, --url             MCP server URL
  -H, --header          HTTP headers in 'Key: Value' format
```

## Output

The evaluation script generates a detailed report including:

- **Summary statistics**:
  - Accuracy (correct/total)
  - Average task duration
  - Average tool calls per task
  - Total tool calls

- **Per-task results**:
  - The prompt and the expected answer
  - The agent's actual answer
  - Whether the answer was correct
  - Duration and tool-call details
  - The agent's summary of its approach
  - The agent's feedback on the tools

### Saving the report to a file

```bash
python scripts/evaluation.py \
  -t stdio \
  -c python \
  -a my_server.py \
  -o evaluation_report.md \
  evaluation.xml
```

## End-to-end workflow example

A complete example of building and running an evaluation:

1. **Create the evaluation file** (`my_evaluation.xml`):

```xml
<evaluation>
   <qa_pair>
      <question>Find the user who created the most issues in January 2024. What is their username?</question>
      <answer>alice_developer</answer>
   </qa_pair>
   <qa_pair>
      <question>Among all pull requests merged in Q1 2024, which repository had the highest number? Provide the repository name.</question>
      <answer>backend-api</answer>
   </qa_pair>
   <qa_pair>
      <question>Find the project that was completed in December 2023 and had the longest duration from start to finish. How many days did it take?</question>
      <answer>127</answer>
   </qa_pair>
</evaluation>
```

2. **Install dependencies**:

```bash
pip install -r scripts/requirements.txt
export ANTHROPIC_API_KEY=your_api_key
```

3. **Run the evaluation**:

```bash
python scripts/evaluation.py \
  -t stdio \
  -c python \
  -a github_mcp_server.py \
  -e GITHUB_TOKEN=ghp_xxx \
  -o github_eval_report.md \
  my_evaluation.xml
```

4. **Review the report** in `github_eval_report.md` to:
   - See which questions passed/failed
   - Read the agent's feedback on your tools
   - Identify areas for improvement
   - Iteratively refine the MCP server design

## Troubleshooting

### Connection errors

If you see connection errors:
- **STDIO**: check that the command and arguments are correct
- **SSE/HTTP**: verify the URL is reachable and the headers are correct
- Make sure required API keys are set in environment variables or headers

### Low accuracy

If many evaluations fail:
- Review the agent's feedback on each task
- Check whether tool descriptions are clear and complete
- Make sure input parameters are well documented
- Consider whether tools return too much or too little data
- Make sure error messages contain actionable hints

### Timeout issues

If tasks time out:
- Use a more capable model (e.g. `claude-3-7-sonnet-20250219`)
- Check whether tools return too much data
- Make sure pagination is working correctly
- Consider simplifying complex questions
