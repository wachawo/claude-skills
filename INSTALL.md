# Installation

`claude-skills` is a directory of Claude Code skills plus a small interactive
installer (`claude-skills.py`). Pick one of the install paths below.

## 1. From PyPI

```bash
pip install claude-skills
claude-skills
```

The package bundles the skill catalog. The console script `claude-skills`
opens the curses picker; the LOCAL destination resolves against your current
working directory (`./.claude/skills/`).

`pipx` works the same way:

```bash
pipx install claude-skills
claude-skills
```

## 2. From source (`git clone`)

```bash
git clone https://github.com/wachawo/claude-skills.git
cd claude-skills
pip install -e .
claude-skills
```

Or zero-install — the repo ships a thin entry point at the root:

```bash
git clone https://github.com/wachawo/claude-skills.git
cd claude-skills
python3 claude-skills.py
```

## Using the installer

`claude-skills` opens an mc-style picker. Skills already installed appear at
the top. Two-pane layout: file tree on the left, diff against the installed
copy on the right.

Keys:

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
| `enter` | Apply (then choose USER or LOCAL destination) |
| `q` | Quit without changes |

Status labels:

- `new` — file is in the catalog but not installed.
- `installed` — file matches the installed copy.
- `updated +X -Y` — installed copy drifts from the catalog (`+` lines added,
  `-` lines removed if you apply the catalog version).

Detection priority: the picker looks for an existing copy first in
`./.claude/skills/` (LOCAL — per-project), then in `~/.claude/skills/` (USER —
machine-wide).

## Non-interactive apply

Pass a destination flag and the destination prompt is skipped:

```bash
claude-skills --user      # apply to ~/.claude/skills
claude-skills --local     # apply to ./.claude/skills
```

The TUI still opens — flags only preselect the destination for the apply step.

## Move semantics: LOCAL → USER only

When you apply with USER as the destination and the same file already exists
in LOCAL, the LOCAL copy is removed after the USER copy is written (one-way
move — promote a project-local override to global).

The reverse never happens automatically: applying to LOCAL while a USER copy
exists installs into LOCAL and leaves the USER copy untouched.

## Uninstall

Run the picker, untick the skills you want gone (selection is at skill level
— pressing `space` on any row toggles the whole skill), press `enter`. Each
unticked skill is removed from every location its files were found in (LOCAL
and/or USER), and empty skill directories are cleaned up.

## What ends up on disk

For each selected skill, files are copied to `<destination>/<name>/<same path>`:

```
~/.claude/skills/<name>/SKILL.md
~/.claude/skills/<name>/<other resources>
```

or, with `--local`:

```
./.claude/skills/<name>/SKILL.md
./.claude/skills/<name>/<other resources>
```

Claude Code picks up both locations: USER skills are available everywhere,
LOCAL skills only inside the project directory.

## Requirements

- Python ≥ 3.10 (modern type hints, f-strings).
- A real terminal (`curses`). Running over a pipe / non-tty session exits
  with an error.
- No third-party dependencies — the installer uses only the standard library
  (`curses`, `pathlib`, `hashlib`, `difflib`, `shutil`).

## Releasing (maintainer)

```bash
git tag v0.0.1
git push --tags
```

The `publish` workflow (`.github/workflows/publish.yml`) runs on the tag,
builds sdist + wheel via `python -m build`, runs `twine check`, and publishes
to PyPI via [trusted publishing](https://docs.pypi.org/trusted-publishers/)
(no API token needed; configure once on pypi.org).
