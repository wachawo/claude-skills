# Installation

`claude-skills` is a directory of Claude Code skills plus a small interactive
installer (`claude-skills.py`). Pick one of the install paths below.

> Replace `OWNER/REPO` with the actual GitHub coordinates of this repository.

## 1. Install from a GitHub Release (recommended)

Each tagged release attaches `claude-skills-<tag>.tar.gz` and `.zip`. Download,
unpack, run:

```bash
REPO=OWNER/REPO
TAG=v0.2.0
curl -fsSL "https://github.com/${REPO}/releases/download/${TAG}/claude-skills-${TAG}.tar.gz" \
  | tar -xz
cd "claude-skills-${TAG}"
python3 claude-skills.py
```

With the GitHub CLI:

```bash
gh release download v0.2.0 --repo OWNER/REPO --pattern '*.tar.gz'
tar -xzf claude-skills-v0.2.0.tar.gz
cd claude-skills-v0.2.0
python3 claude-skills.py
```

## 2. Install from source (latest `main`)

```bash
git clone https://github.com/OWNER/REPO.git
cd REPO
python3 claude-skills.py
```

## Using the installer

`claude-skills.py` opens an mc-style picker. Skills already installed appear at
the top. Two-pane layout: file tree on the left, diff against the installed
copy on the right.

Keys:

| Key | Action |
|---|---|
| `↑` / `↓` | Move cursor |
| `←` / `→` | Collapse / expand a skill |
| `Shift+↑` / `Shift+↓` | Scroll diff pane |
| `space` | Toggle selection (file or whole skill) |
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
python3 claude-skills.py --user    # apply to ~/.claude/skills
python3 claude-skills.py --local   # apply to ./.claude/skills
```

The TUI still opens — flags only preselect the destination for the apply step.

## Move semantics: LOCAL → USER only

When you apply with USER as the destination and the same file already exists
in LOCAL, the LOCAL copy is removed after the USER copy is written (one-way
move — promote a project-local override to global).

The reverse never happens automatically: applying to LOCAL while a USER copy
exists installs into LOCAL and leaves the USER copy untouched.

## Uninstall

Run the picker, untick the skills you want gone, press `enter`. Each unticked
file is removed from every location it was found in (LOCAL and/or USER), and
empty skill directories are cleaned up.

## What ends up on disk

For each selected `skills/<name>/...` file, the installer copies it to
`<destination>/<name>/<same path>`:

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

- Python 3.10+ (uses `pathlib`, f-strings, modern type hints; no third-party
  deps).
- A real terminal (`curses`). Running over a pipe / non-tty session exits with
  an error.

## Building a release locally

If you want to build the same archive the workflow produces:

```bash
VERSION=v0.2.0
NAME="claude-skills-${VERSION}"
mkdir -p "dist/${NAME}"
cp -r skills "dist/${NAME}/"
cp claude-skills.py README.md INSTALL.md "dist/${NAME}/"
tar -czf "dist/${NAME}.tar.gz" -C dist "${NAME}"
```

The GitHub workflow (`.github/workflows/release.yml`) does exactly this on
every `v*` tag push and attaches the archive to the matching GitHub Release.
