## claude-skills

[![CI](https://github.com/wachawo/claude-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/wachawo/claude-skills/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/wachawo/claude-skills/branch/main/graph/badge.svg)](https://codecov.io/gh/wachawo/claude-skills?branch=main)
[![PyPI](https://img.shields.io/pypi/v/claude-skills.svg)](https://pypi.org/project/claude-skills/)
[![Downloads](https://img.shields.io/pypi/dm/claude-skills.svg)](https://pypi.org/project/claude-skills/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/wachawo/claude-skills/blob/main/LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/claude-skills.svg)](https://pypi.org/project/claude-skills/)

**[English](README.md)** | [Русский](docs/README_RU.md)

Claude Skills for software engineers and developers across the stack — a curated collection of practical skills that turns Claude into a powerful technical teammate.

This repository brings together high-value skills for everyday engineering work: **software development**, **Python tooling**, **architecture**, **DevOps**, **code review**, **debugging**, **security**, **browser automation**, **data analysis**, and **project workflows**. Pick the skills you need and install them globally or per project in just a few commands.

Each skill is more than just a prompt — it is a ready-to-use workflow that helps Claude better understand developer tasks, write cleaner code, navigate codebases faster, and support stronger engineering decisions.

Found a powerful skill or a repository worth sharing? Feel free to add it to this collection via Pull Request — together, we can build the best Claude Skills toolkit for real-world development.

![docs/image.png](docs/image.png)

### Installation

#### 1. From PyPI

```bash
pip install claude-skills
claude-skills
```

The package bundles the skill catalog. `claude-skills` opens the picker; the
LOCAL destination resolves against your current working directory
(`./.claude/skills/`).

#### 2. From source (`git clone`)

```bash
git clone https://github.com/wachawo/claude-skills.git
cd claude-skills
pip install -e .
claude-skills
```

Or zero-install — the repo ships a thin entry point:

```bash
git clone https://github.com/wachawo/claude-skills.git
cd claude-skills
python3 claude-skills.py
```

#### Requirements

- Python ≥ 3.10 (modern type hints, f-strings).
- A real terminal — `curses`, so SSH / interactive shell only.
- No third-party dependencies — `claude-skills.py` uses only the standard
  library (`curses`, `pathlib`, `hashlib`, `difflib`, `shutil`).

See [INSTALL.md](INSTALL.md) for keys, the `--user` / `--local`
non-interactive flags, and uninstall.

### Quick start

```bash
claude-skills              # interactive picker, asks USER vs LOCAL on apply
claude-skills --user       # preselect ~/.claude/skills
claude-skills --local      # preselect ./.claude/skills
```

Picker keys:

| Key | Action |
|---|---|
| `Tab` | Switch focus between skill list (left) and diff pane (right) |
| `↑` / `↓` | Focus left: move cursor. Focus right: scroll diff one line. |
| `PgUp` / `PgDn` | Same dispatch by focus, page-sized step |
| `Home` / `End` | Same dispatch by focus, jump to top / bottom |
| `←` / `→` | Collapse / expand a skill (left focus only) |
| `Shift+↑` / `Shift+↓` | Scroll diff pane (works in any focus) |
| `space` | Toggle the whole skill — selection is per-skill, never per-file |
| `a` / `n` | Select all / none |
| `enter` | Apply (then choose USER or LOCAL) |
| `q` | Quit without changes |

Skills already installed appear at the top. Status is detected by checking
`./.claude/skills/<skill>/SKILL.md` first, then `~/.claude/skills/<skill>/SKILL.md`:

- `new` — file is in the catalog but not on disk.
- `installed` — file matches the installed copy byte-for-byte.
- `updated +X -Y` — installed copy drifts from the catalog.

When you apply with USER as the destination and the same file is already in
LOCAL, the LOCAL copy is removed after the USER copy is written (one-way
LOCAL → USER move). Reverse direction never auto-deletes from USER.

Unticking a previously installed skill marks all its files for removal on
apply (from any location they were found in). Selection is at skill level —
expanding a skill is for browsing the per-file diff, not for picking
individual files. Empty skill directories are cleaned up.

### Components

| File / dir | Purpose |
|---|---|
| `claude-skills` (console script) | curses installer: two-pane picker, MD5-based `installed` / `updated +X -Y` / `new` status, LOCAL → USER move on apply. |
| `src/claude_skills/cli.py` | Implementation of the installer. |
| `skills/<name>/SKILL.md` (+ resources) | The skills themselves — one folder per skill, picked up by Claude Code. |
| `claude-skills.py` (repo root) | Thin entry point so `python3 claude-skills.py` works from a fresh clone without `pip install`. |
| `INSTALL.md` | Detailed install guide, key bindings, non-interactive flags, move/uninstall semantics. |
| `tests/` | pytest suite — 27 tests covering pure functions (`truncate`, `aggregate_skill`, `build_rows`, `wrap_lines`) and filesystem helpers (`md5_file`, `find_installed`, `assess`, `cleanup_empty_dirs`). Run via `pip install -e ".[dev]" && pytest`. |
| `.github/workflows/publish.yml` | On `vX.Y.Z` tag push: builds sdist + wheel and publishes to PyPI via trusted publishing (OIDC). |
| `.github/workflows/ci.yml` | On every push / PR: validates skill layout, runs pytest with coverage, uploads to Codecov, builds the package. |

### Releasing

```bash
git tag v0.0.1
git push --tags
```

The `publish` workflow runs on the tag: builds sdist + wheel via `python -m
build`, runs `twine check`, and publishes to PyPI. PyPI must be configured
once with [trusted publishing](https://docs.pypi.org/trusted-publishers/) for
this repo (no API token needed afterwards).

---

### Skills catalog

#### [/diagnose](skills/diagnose/SKILL.md) — 9.5

A disciplined debugging loop: reproduce → minimize → hypothesize → instrument → fix → close with a regression test. Keeps you from jumping straight to a "fix" and locks the bug behind a test so it stays gone. Language- and stack-agnostic — a daily driver for bugs and performance regressions.

#### [/qa](skills/qa/SKILL.md) — 9.5

Interactive QA session: the user reports problems in plain language, the agent asks short clarifying questions, explores the codebase in the background for domain language, and files durable GitHub issues via `gh`. Knows how to split a compound problem into multiple issues with proper `Blocked by` links. The best way to turn "this doesn't work" into a real ticket.

#### [/drilldown-analyzer](skills/drilldown-analyzer/SKILL.md) — 9.5

Systematic investigation of metric changes and anomalies: validate the change via z-score → timeline → metric decomposition → drill-down across dimensions → **explicit hypotheses accepted/rejected with evidence** → RCA report. Includes the `drilldown_analyzer.py` script, [`references/hypothesis_testing_guide.md`](skills/drilldown-analyzer/references/hypothesis_testing_guide.md), and a report template. From the `nimrodfisher/data-analytics-skills` repository.

#### [/data-analyzer](skills/data-analyzer/SKILL.md) — 9.0

Deep dive into a dataset: null profile, outliers (IQR + z-score), distributions, correlations (flags `|r| > 0.8` as multicollinearity). Scripts `data_overview.py`, `null_profiler.py`, `outlier_detector.py`, `distribution_summary.py`, `correlation_explorer.py`, plus a checklist and a report template. Ideal as the first step before [`/drilldown-analyzer`](skills/drilldown-analyzer/SKILL.md). Same source repo.

#### [/tdd](skills/tdd/SKILL.md) — 9.0

Classic red-green-refactor with an emphasis on integration tests and proper mocking. Ships separate guides on [deep modules](skills/tdd/deep-modules.md), [interface design](skills/tdd/interface-design.md), and [refactoring](skills/tdd/refactoring.md). Useful for both new features and bugs: the test reproduces the problem first, then gets fixed. Fits any stack, including Flask.

#### [/refactor](skills/refactor/SKILL.md) — 9.0

A user interview becomes an RFC-style refactoring plan, broken into tiny safe commits and filed as GitHub issues. Protects against "big rewrites" and keeps progress visible. Pairs with [`/to-issues`](skills/to-issues/SKILL.md) and [`/triage`](skills/triage/SKILL.md).

#### [/improve-arch](skills/improve-arch/SKILL.md) — 9.0

Hunts for opportunities to deepen modules, leveraging `CONTEXT.md` and ADRs in `docs/adr/`. DDD-flavored, focused on testability and AI-friendly navigation. Bundled with [`DEEPENING.md`](skills/improve-arch/DEEPENING.md), [`INTERFACE-DESIGN.md`](skills/improve-arch/INTERFACE-DESIGN.md), [`LANGUAGE.md`](skills/improve-arch/LANGUAGE.md) — a methodological foundation, not just a prompt.

#### [/claude-api](skills/claude-api/SKILL.md) — 9.0

Building and tuning apps on the Anthropic SDK: prompt caching, thinking, tool use, batch, model-version migrations. Supports Python/TS/Go/Java/Ruby/PHP/C#/curl. If you're writing anything against the Claude API — mandatory.

#### [/python-code](skills/python-code/SKILL.md) — 9.0

A detailed guide to Python code quality: Ruff (lint + format), MyPy (strict mode), modern type-hint syntax (`list[str]`, `int | None`, Generic, Callable, Protocol), anti-patterns (mutable defaults, bare except), Pythonic idioms, module organization with `py.typed`. Includes [`RUFF_CONFIG.md`](skills/python-code/RUFF_CONFIG.md), [`MYPY_CONFIG.md`](skills/python-code/MYPY_CONFIG.md), [`TYPE_PATTERNS.md`](skills/python-code/TYPE_PATTERNS.md), and a final checklist. From the `wdm0006/python-skills` repo, based on the mcginniscommawill.com guide.

#### [/python-fp](skills/python-fp/SKILL.md) — 8.5

A guide to functional style in Python: pure functions, immutability (`NamedTuple`, dict factories, `MappingProxyType`), HOFs, closures and currying, `functools` (`lru_cache`, `partial`, `reduce`, `singledispatch`), `itertools` (`groupby`, `accumulate`, `pairwise`), `operator` instead of lambdas, composition, typing via `Callable`/`ParamSpec`/`Protocol`, anti-patterns, and the **immutable core — mutable shell** architectural pattern. Aligns with the CLAUDE.md rule "functional style instead of classes".

#### [/python-pep8](skills/python-pep8/SKILL.md) — 8.5

A detailed guide to [PEP 8](https://peps.python.org/pep-0008/) with do/don't examples for every rule: layout (indentation, line length, blank lines, line breaks at binary operators), imports, naming (snake_case / PascalCase / UPPER_CASE), whitespace (including the nuance of `=` in kwargs vs annotated defaults), comments and docstrings, programming recommendations (`is None`, `isinstance`, `startswith`, `"".join`, specific excepts). Final checklist plus a `ruff` config for automation.

#### [/write-skill](skills/write-skill/SKILL.md) — 9.0

Meta-skill: creates new skills with the right structure, progressive disclosure, and bundled resources. Reach for it as soon as a repeatable prompt deserves to live in `skills/`.

#### [/grill-me](skills/grill-me/SKILL.md) — 8.5

Mercilessly grills you on a plan/design until every branch of the decision tree is resolved. Catches holes before they become code. Good for vetting architectural decisions up-front.

#### [/to-issues](skills/to-issues/SKILL.md) — 8.5

Turns a plan/PRD/spec into independently shippable tickets along "tracer-bullet" vertical slices. Enables parallelism and visible progress.

#### [/triage](skills/triage/SKILL.md) — 8.5

A state machine for issue triage with role-based stages: creation, bug/feature triage, prep for AFK agents. Paired with [`AGENT-BRIEF.md`](skills/triage/AGENT-BRIEF.md) and [`OUT-OF-SCOPE.md`](skills/triage/OUT-OF-SCOPE.md), it gives a durable workflow.

#### [/mcp-builder](skills/mcp-builder/SKILL.md) — 8.5

Guide to building high-quality MCP servers (FastMCP / Node SDK) with an emphasis on tool design. Reach for it when integrating external services for LLMs.

#### [/grill-docs](skills/grill-docs/SKILL.md) — 8.0

Same "grilling" idea, but syncs the plan against [`CONTEXT-FORMAT.md`](skills/grill-docs/CONTEXT-FORMAT.md) and [`ADR-FORMAT.md`](skills/grill-docs/ADR-FORMAT.md): sharpens terminology and updates documentation as decisions crystallize. Useful in projects with a fixed domain model.

#### [/to-prd](skills/to-prd/SKILL.md) — 8.0

Turns the current conversation context into a PRD and publishes it to the tracker. Handy when a feature has already been discussed and just needs to be "saved".

#### [/ubiquitous-language](skills/ubiquitous-language/SKILL.md) — 8.0

Extracts a DDD glossary from a conversation, flags ambiguities, suggests canonical terms, and saves to `UBIQUITOUS_LANGUAGE.md`. Foundation for [`/grill-docs`](skills/grill-docs/SKILL.md) and [`/improve-arch`](skills/improve-arch/SKILL.md).

#### [/write-docs](skills/write-docs/SKILL.md) — 8.0

A structured workflow for writing documentation, specs, and decision docs with iterative refinement and a "does this work for the reader" check. Better than just asking an LLM to "write docs".

#### [/sec-review](skills/sec-review/SKILL.md) — 8.0

Security review for Python/JS/TS/Go with concrete improvements. Triggered explicitly — not for general code review, only for a security pass.

#### [/webapp-testing](skills/webapp-testing/SKILL.md) — 8.0

Playwright toolkit for testing local web apps: frontend verification, UI debugging, screenshots, logs. Fits Vue/SPA stacks well.

#### [/playwright](skills/playwright/SKILL.md) — 8.0

Browser automation from the terminal via `playwright-cli`: navigation, form filling, screenshots, data extraction. The baseline tool for anything involving a real browser.

#### [/design-api](skills/design-api/SKILL.md) — 7.5

Generates several radically different API/interface variants for a module via parallel sub-agents. Good for "design it twice" — when you need to compare shapes rather than commit to the first idea.

#### [/playwright-interactive](skills/playwright-interactive/SKILL.md) — 7.5

Persistent browser session (including Electron) via `js_repl` for fast iterations during UI debugging. Niche, but nothing beats it in that niche.

#### [/setup-pre-commit](skills/setup-pre-commit/SKILL.md) — 7.5

Husky + lint-staged + Prettier + types + tests on pre-commit. Configured once per project, then forgotten. Useful, but a one-shot.

#### [/xlsx](skills/xlsx/SKILL.md) — 7.5

Read/edit/create `.xlsx`/`.csv`/`.tsv`: formulas, formatting, charts, cleanup of messy tabular data. Must-have if you work with spreadsheets, otherwise unnecessary.

#### [/pdf](skills/pdf/SKILL.md) — 7.5

Full PDF toolkit: read, merge, split, forms, watermarks, OCR. Narrow but powerful for its specific format.
