#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mc-style installer that copies selected skill files to ~/.claude/skills.

Left pane lists every file under skills/ with a checkbox and an MD5-derived
status (new / synced / modified +N -M). Right pane shows the unified diff of
the highlighted file against its installed copy. Selection is per-file; on
confirmation the script copies (not symlinks) selected files and removes
unchecked ones that were previously installed.
"""

import curses
import difflib
import hashlib
import os
import shutil
import sys
from pathlib import Path

def _resolve_skills_dir() -> Path:
    """Locate the bundled skills/ catalog.

    1. <package>/skills/ — bundled into the wheel via hatch force-include.
    2. <repo>/skills/    — editable install / git clone running from source.
    """
    here = Path(__file__).resolve().parent
    pkg_skills = here / "skills"
    if pkg_skills.is_dir() and any(pkg_skills.glob("*/SKILL.md")):
        return pkg_skills
    for ancestor in here.parents:
        candidate = ancestor / "skills"
        if candidate.is_dir() and any(candidate.glob("*/SKILL.md")):
            return candidate
    raise FileNotFoundError("Cannot locate skills/ directory.")


SKILLS_DIR = _resolve_skills_dir()
DEST_USER  = Path.home() / ".claude" / "skills"
DEST_LOCAL = Path.cwd() / ".claude" / "skills"
INSTALL_SEARCH_ORDER = (DEST_LOCAL, DEST_USER)

STATE_NEW    = "new"
STATE_SYNCED = "installed"
STATE_DIFF   = "updated"

C_NEW      = 1
C_SYNCED   = 2
C_DIFF     = 3
C_HEADER   = 4
C_HINT     = 5
C_DIFF_ADD = 6
C_DIFF_DEL = 7
C_DIFF_HDR = 8


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def find_installed(skill: str, inner: str):
    """Return the existing install path for skill/inner, or None.

    LOCAL (./.claude/skills/) takes priority over USER (~/.claude/skills/).
    """
    for root in INSTALL_SEARCH_ORDER:
        candidate = root / skill / inner
        if candidate.exists():
            return candidate
    return None


def is_under(path: Path, root: Path) -> bool:
    return str(path).startswith(str(root) + os.sep)


def label_root(path: Path) -> str:
    if is_under(path, DEST_LOCAL):
        return "LOCAL"
    if is_under(path, DEST_USER):
        return "USER"
    return str(path.parent)


def cleanup_empty_dirs(start: Path, stop_at: Path):
    """Walk up from `start.parent` removing empty dirs, stopping at `stop_at`."""
    parent = start.parent
    try:
        while parent != stop_at and is_under(parent, stop_at):
            if any(parent.iterdir()):
                return
            parent.rmdir()
            parent = parent.parent
    except OSError:
        pass


def discover():
    """Return one entry per file under every skills/<skill>/ tree.

    Skills already installed (their SKILL.md present in LOCAL or USER) are
    listed first, so the user immediately sees what's already on disk.
    """
    skill_dirs = [p.parent for p in SKILLS_DIR.glob("*/SKILL.md")]
    skill_dirs.sort(
        key=lambda sd: (find_installed(sd.name, "SKILL.md") is None, sd.name)
    )

    entries = []
    for sd in skill_dirs:
        for root, _, files in os.walk(sd):
            for fn in sorted(files):
                src   = Path(root) / fn
                inner = src.relative_to(sd).as_posix()
                rel   = src.relative_to(SKILLS_DIR).as_posix()
                dest  = find_installed(sd.name, inner)
                entries.append({
                    "rel":   rel,
                    "src":   src,
                    "dest":  dest,
                    "state": STATE_NEW,
                    "plus":  0,
                    "minus": 0,
                })
    return entries


def assess(entry):
    src, dest = entry["src"], entry["dest"]
    if dest is None or not dest.exists():
        entry["state"] = STATE_NEW
        return
    if md5_file(src) == md5_file(dest):
        entry["state"] = STATE_SYNCED
        return
    entry["state"] = STATE_DIFF
    try:
        a = dest.read_text(errors="replace").splitlines()
        b = src.read_text(errors="replace").splitlines()
        diff = list(difflib.unified_diff(a, b, lineterm=""))
        entry["plus"]  = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        entry["minus"] = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    except Exception:
        pass


def make_diff(entry):
    """Return [(text, color_pair_index)] lines for the right-hand pane."""
    src, dest, state = entry["src"], entry["dest"], entry["state"]
    if state == STATE_SYNCED:
        return [("(installed - no changes)", 0)]
    if state == STATE_NEW:
        try:
            text = src.read_text(errors="replace")
        except Exception as exc:
            return [(f"(cannot read source: {exc})", 0)]
        out = [(f"(new file: {entry['rel']})", C_DIFF_HDR), ("", 0)]
        for line in text.splitlines():
            out.append(("+ " + line, C_DIFF_ADD))
        return out
    try:
        a = dest.read_text(errors="replace").splitlines()
        b = src.read_text(errors="replace").splitlines()
    except Exception as exc:
        return [(f"(cannot read: {exc})", 0)]
    out = []
    for line in difflib.unified_diff(
        a, b, fromfile=str(dest), tofile=str(src), lineterm=""
    ):
        if line.startswith(("+++", "---", "@@")):
            out.append((line, C_DIFF_HDR))
        elif line.startswith("+"):
            out.append((line, C_DIFF_ADD))
        elif line.startswith("-"):
            out.append((line, C_DIFF_DEL))
        else:
            out.append((line, 0))
    return out


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_NEW,      curses.COLOR_WHITE,  -1)
    curses.init_pair(C_SYNCED,   curses.COLOR_GREEN,  -1)
    curses.init_pair(C_DIFF,     curses.COLOR_YELLOW, -1)
    curses.init_pair(C_HEADER,   curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(C_HINT,     curses.COLOR_CYAN,   -1)
    curses.init_pair(C_DIFF_ADD, curses.COLOR_GREEN,  -1)
    curses.init_pair(C_DIFF_DEL, curses.COLOR_RED,    -1)
    curses.init_pair(C_DIFF_HDR, curses.COLOR_CYAN,   -1)


def state_attr(state):
    base = {
        STATE_NEW:    curses.color_pair(C_NEW)    | curses.A_DIM,
        STATE_SYNCED: curses.color_pair(C_SYNCED),
        STATE_DIFF:   curses.color_pair(C_DIFF)   | curses.A_BOLD,
    }
    return base[state]


def wrap_lines(lines, width):
    """Wrap (text, color) lines to width; continuations are indented by 2 spaces."""
    if width <= 0:
        return []
    out = []
    for text, color in lines:
        if text == "":
            out.append(("", color))
            continue
        i = 0
        first = True
        while i < len(text):
            if first:
                chunk = text[i:i + width]
                out.append((chunk, color))
                i += len(chunk)
                first = False
            else:
                room  = max(1, width - 2)
                chunk = text[i:i + room]
                out.append(("  " + chunk, color))
                i += len(chunk)
    return out


def truncate(s, w):
    if w <= 0:
        return ""
    return s if len(s) <= w else s[: max(0, w - 1)] + "."


def build_rows(entries, expanded):
    """Group file entries by skill folder; emit file rows only for expanded skills."""
    rows = []
    by_skill = {}
    order    = []
    for i, e in enumerate(entries):
        skill = e["rel"].split("/", 1)[0]
        if skill not in by_skill:
            by_skill[skill] = []
            order.append(skill)
        by_skill[skill].append(i)
    for skill in order:
        rows.append({"type": "skill", "skill": skill, "files": by_skill[skill]})
        if skill in expanded:
            for fi in by_skill[skill]:
                rows.append({"type": "file", "idx": fi, "skill": skill})
    return rows


def relocate_cursor(old_row, new_rows):
    """Find the row index in new_rows that best matches the previously focused row."""
    if old_row["type"] == "skill":
        for i, r in enumerate(new_rows):
            if r["type"] == "skill" and r["skill"] == old_row["skill"]:
                return i
    else:
        for i, r in enumerate(new_rows):
            if r["type"] == "file" and r["idx"] == old_row["idx"]:
                return i
        for i, r in enumerate(new_rows):
            if r["type"] == "skill" and r["skill"] == old_row["skill"]:
                return i
    return 0


def aggregate_skill(files, entries, selected):
    states = [entries[i]["state"] for i in files]
    if all(s == STATE_SYNCED for s in states):
        agg = (STATE_SYNCED, 0, 0)
    elif all(s == STATE_NEW for s in states):
        agg = (STATE_NEW, 0, 0)
    else:
        plus  = sum(entries[i]["plus"]  for i in files)
        minus = sum(entries[i]["minus"] for i in files)
        agg = (STATE_DIFF, plus, minus)
    sel = sum(1 for i in files if i in selected)
    if sel == 0:                check = "[ ]"
    elif sel == len(files):     check = "[x]"
    else:                       check = "[-]"
    return agg, check


def make_skill_summary(row, entries):
    files = row["files"]
    plus  = sum(entries[i]["plus"]  for i in files)
    minus = sum(entries[i]["minus"] for i in files)
    out = [
        (f"Skill: {row['skill']}", C_DIFF_HDR),
        (f"{len(files)} files   +{plus} -{minus}", C_DIFF_HDR),
        ("", 0),
    ]
    for fi in files:
        e = entries[fi]
        if e["state"] == STATE_DIFF:
            tag, col = f"updated +{e['plus']} -{e['minus']}", C_DIFF
        elif e["state"] == STATE_SYNCED:
            tag, col = "installed", C_SYNCED
        else:
            tag, col = "new", C_NEW
        inner = e["rel"][len(row["skill"]) + 1:]
        out.append((f"  {inner.ljust(40)} {tag}", col))
    return out


def run(stdscr, entries):
    curses.curs_set(0)
    init_colors()
    stdscr.keypad(True)

    # Skill -> list of entry indices, used for skill-level selection.
    by_skill = {}
    for i, e in enumerate(entries):
        skill = e["rel"].split("/", 1)[0]
        by_skill.setdefault(skill, []).append(i)

    # Initial selection at skill level: pre-select any skill with at least
    # one already-installed file (anything not STATE_NEW).
    selected = set()
    for skill, idxs in by_skill.items():
        if any(entries[i]["state"] != STATE_NEW for i in idxs):
            selected.update(idxs)

    expanded    = set()
    rows        = build_rows(entries, expanded)
    cursor      = 0
    diff_offset = 0
    view_start  = 0
    focus       = "left"   # "left" = skill list, "right" = diff pane

    while True:
        h, w = stdscr.getmaxyx()
        left_w  = (w - 1) // 2
        right_w = w - left_w - 1
        top, bottom = 1, h - 2
        body_h = bottom - top

        if cursor < view_start:
            view_start = cursor
        if cursor >= view_start + body_h:
            view_start = cursor - body_h + 1

        stdscr.erase()

        focus_marker = "[tab -> diff]" if focus == "left" else "[tab -> skills]"
        title = (f" Install skills   {len(entries)} files,  "
                 f"{len(selected)} selected   {focus_marker} ")
        stdscr.addstr(0, 0, truncate(title.ljust(w), w),
                      curses.color_pair(C_HEADER) | curses.A_BOLD)

        for screen_row in range(body_h):
            ridx = view_start + screen_row
            if ridx >= len(rows):
                break
            row = rows[ridx]
            if row["type"] == "skill":
                (state, plus, minus), check = aggregate_skill(row["files"], entries, selected)
                if state == STATE_DIFF:
                    tag = f"updated +{plus} -{minus}"
                elif state == STATE_SYNCED:
                    tag = "installed"
                else:
                    tag = "new"
                marker = "v" if row["skill"] in expanded else ">"
                head   = f" {marker} {check} {row['skill']}/"
                attr   = state_attr(state) | curses.A_BOLD
            else:
                e = entries[row["idx"]]
                state = e["state"]
                # File-level checkbox mirrors the parent skill — no per-file toggle.
                check = "[x]" if row["idx"] in selected else "[ ]"
                if state == STATE_DIFF:
                    tag = f"updated +{e['plus']} -{e['minus']}"
                elif state == STATE_SYNCED:
                    tag = "installed"
                else:
                    tag = "new"
                inner = e["rel"][len(row["skill"]) + 1:]
                head  = f"     {check} {inner}"
                attr  = state_attr(state)
            pad  = max(1, left_w - len(head) - len(tag) - 1)
            line = head + " " * pad + tag + " "
            line = truncate(line, left_w)
            if ridx == cursor:
                attr |= curses.A_REVERSE
            try:
                stdscr.addstr(top + screen_row, 0, line, attr)
            except curses.error:
                pass

        for r in range(top, bottom):
            try:
                stdscr.addch(r, left_w, curses.ACS_VLINE)
            except curses.error:
                pass

        cur_row = rows[cursor]
        if cur_row["type"] == "skill":
            diff_raw = make_skill_summary(cur_row, entries)
        else:
            diff_raw = make_diff(entries[cur_row["idx"]])
        diff_lines = wrap_lines(diff_raw, right_w)
        max_off    = max(0, len(diff_lines) - body_h)
        diff_offset = min(max(diff_offset, 0), max_off)
        for screen_row in range(body_h):
            di = diff_offset + screen_row
            if di >= len(diff_lines):
                break
            text, color = diff_lines[di]
            try:
                stdscr.addnstr(top + screen_row, left_w + 1, text, right_w,
                               curses.color_pair(color))
            except curses.error:
                pass

        if cur_row["type"] == "skill":
            (state, plus, minus), _ = aggregate_skill(cur_row["files"], entries, selected)
            if state == STATE_DIFF:
                sb = f" {cur_row['skill']}/   updated  +{plus} -{minus}   ({len(cur_row['files'])} files) "
            elif state == STATE_SYNCED:
                sb = f" {cur_row['skill']}/   installed   ({len(cur_row['files'])} files) "
            else:
                sb = f" {cur_row['skill']}/   new   ({len(cur_row['files'])} files) "
        else:
            e = entries[cur_row["idx"]]
            if e["state"] == STATE_DIFF:
                sb = f" {e['rel']}   updated  +{e['plus']} -{e['minus']} "
            elif e["state"] == STATE_SYNCED:
                sb = f" {e['rel']}   installed "
            else:
                sb = f" {e['rel']}   new "
        stdscr.addstr(bottom, 0, truncate(sb.ljust(w), w),
                      curses.color_pair(C_HEADER))

        if focus == "left":
            hint = (" tab: focus diff   up/down move   left/right collapse/expand   "
                    "space toggle skill   a all   n none   enter apply   q quit ")
        else:
            hint = (" tab: focus skills   up/down scroll diff   pgup/pgdn page   "
                    "home/end top/bottom   q quit ")
        try:
            stdscr.addstr(h - 1, 0, truncate(hint.ljust(w - 1), w - 1),
                          curses.color_pair(C_HINT))
        except curses.error:
            pass

        stdscr.refresh()
        key = stdscr.getch()

        if key == ord('q'):
            return None
        elif key in (9, curses.KEY_BTAB):
            focus = "right" if focus == "left" else "left"
        elif key in (curses.KEY_UP, ord('k')):
            if focus == "left":
                cursor = max(0, cursor - 1)
                diff_offset = 0
            else:
                diff_offset = max(0, diff_offset - 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            if focus == "left":
                cursor = min(len(rows) - 1, cursor + 1)
                diff_offset = 0
            else:
                diff_offset += 1
        elif key == curses.KEY_PPAGE:
            if focus == "left":
                cursor = max(0, cursor - body_h)
                diff_offset = 0
            else:
                diff_offset = max(0, diff_offset - body_h)
        elif key == curses.KEY_NPAGE:
            if focus == "left":
                cursor = min(len(rows) - 1, cursor + body_h)
                diff_offset = 0
            else:
                diff_offset += body_h
        elif key == curses.KEY_HOME:
            if focus == "left":
                cursor = 0
            diff_offset = 0
        elif key == curses.KEY_END:
            if focus == "left":
                cursor = len(rows) - 1
                diff_offset = 0
            else:
                diff_offset = max_off
        elif key == ord(' '):
            # Always toggles the whole skill — even on file rows.
            target_skill = rows[cursor]["skill"]
            files = by_skill[target_skill]
            if all(i in selected for i in files):
                selected.difference_update(files)
            else:
                selected.update(files)
        elif key in (curses.KEY_RIGHT, ord('l')) and focus == "left":
            cur_row = rows[cursor]
            if cur_row["type"] == "skill" and cur_row["skill"] not in expanded:
                expanded.add(cur_row["skill"])
                rows = build_rows(entries, expanded)
                diff_offset = 0
        elif key in (curses.KEY_LEFT, ord('h')) and focus == "left":
            cur_row = rows[cursor]
            target  = cur_row["skill"]
            if cur_row["type"] == "file" or target in expanded:
                expanded.discard(target)
                rows = build_rows(entries, expanded)
                cursor = relocate_cursor({"type": "skill", "skill": target}, rows)
                diff_offset = 0
        elif key == ord('a'):
            selected = set(range(len(entries)))
        elif key == ord('n'):
            selected = set()
        elif key == curses.KEY_SR:
            diff_offset = max(0, diff_offset - max(1, body_h // 2))
        elif key == curses.KEY_SF:
            diff_offset += max(1, body_h // 2)
        elif key in (10, 13, curses.KEY_ENTER):
            return sorted(selected)


def picker(stdscr, title, options):
    """Arrow-key picker. Returns selected index, or None on Esc/q."""
    curses.curs_set(0)
    init_colors()
    stdscr.keypad(True)
    cursor = 0
    while True:
        stdscr.erase()
        stdscr.addstr(0, 0, f" {title} ",
                      curses.color_pair(C_HEADER) | curses.A_BOLD)
        for i, opt in enumerate(options):
            attr = curses.A_REVERSE | curses.A_BOLD if i == cursor else curses.A_NORMAL
            stdscr.addstr(2 + i, 2, f" {opt} ", attr)
        hint = " ↑/↓ select   Enter confirm   Esc/q cancel "
        stdscr.addstr(2 + len(options) + 1, 0, hint, curses.color_pair(C_HINT))
        stdscr.refresh()
        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')):
            cursor = (cursor - 1) % len(options)
        elif key in (curses.KEY_DOWN, ord('j')):
            cursor = (cursor + 1) % len(options)
        elif key in (10, 13, curses.KEY_ENTER):
            return cursor
        elif key in (27, ord('q')):
            return None


def confirm_and_apply(entries, chosen):
    chosen_set = set(chosen)

    cli_dest = None
    if "--user" in sys.argv[1:]:
        cli_dest = DEST_USER
    elif "--local" in sys.argv[1:]:
        cli_dest = DEST_LOCAL

    if cli_dest is not None:
        dest_root = cli_dest
    else:
        options = [
            f"Install to USER   ({DEST_USER})",
            f"Install to LOCAL  ({DEST_LOCAL})",
            "Cancel",
        ]
        choice = curses.wrapper(
            lambda s: picker(s, "Apply changes? Choose destination:", options)
        )
        if choice is None or choice == 2:
            print("Aborted.")
            return
        dest_root = DEST_USER if choice == 0 else DEST_LOCAL

    install, update, move, remove = [], [], [], []
    for i, e in enumerate(entries):
        target     = dest_root / e["rel"]
        prev_paths = [r / e["rel"] for r in INSTALL_SEARCH_ORDER
                      if (r / e["rel"]).exists()]
        target_exists = target.exists()
        target_synced = target_exists and md5_file(e["src"]) == md5_file(target)

        if i in chosen_set:
            # Auto-cleanup of stale copies only one direction: LOCAL -> USER.
            # Never delete from USER while installing to LOCAL.
            if is_under(target, DEST_USER):
                stale = [p for p in prev_paths
                         if p != target and is_under(p, DEST_LOCAL)]
            else:
                stale = []

            if target_exists and not target_synced:
                e["target"], e["stale"] = target, stale
                update.append(e)
            elif not target_exists:
                e["target"], e["stale"] = target, stale
                (move if stale else install).append(e)
            elif target_synced and stale:
                e["target"], e["stale"] = None, stale
                move.append(e)
            # else: target already in sync, no stale to remove -> noop
        else:
            if prev_paths:
                e["target"], e["stale"] = None, prev_paths
                remove.append(e)

    print()
    print(f"Destination: {dest_root}")
    if not (install or update or move or remove):
        print("Nothing to do.")
        return
    if install:
        print(f"\033[32mInstall ({len(install)}):\033[0m")
        for e in install:
            print(f"  + {e['rel']}  -> {label_root(e['target'])}")
    if update:
        print(f"\033[33mUpdate ({len(update)}):\033[0m")
        for e in update:
            extra = ""
            if e["stale"]:
                extra = f"   (drop {', '.join(label_root(p) for p in e['stale'])})"
            print(f"  ~ {e['rel']}  +{e['plus']} -{e['minus']}  -> {label_root(e['target'])}{extra}")
    if move:
        print(f"\033[36mMove ({len(move)}):\033[0m")
        for e in move:
            sources = ", ".join(label_root(p) for p in e["stale"])
            if e["target"] is None:
                print(f"  > {e['rel']}  (drop {sources}; target already in sync)")
            else:
                print(f"  > {e['rel']}  ({sources} -> {label_root(e['target'])})")
    if remove:
        print(f"Remove ({len(remove)}):")
        for e in remove:
            sources = ", ".join(label_root(p) for p in e["stale"])
            print(f"  - {e['rel']}  (from {sources})")
    print()

    dest_root.mkdir(parents=True, exist_ok=True)
    for e in install + update + move:
        if e["target"] is not None:
            e["target"].parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(e["src"], e["target"])
            print(f"  ok {label_root(e['target'])}: {e['rel']}")
        for p in e["stale"]:
            try:
                p.unlink()
                print(f"  rm {label_root(p)}: {e['rel']}")
                for root in INSTALL_SEARCH_ORDER:
                    if is_under(p, root):
                        cleanup_empty_dirs(p, root)
                        break
            except FileNotFoundError:
                pass
    for e in remove:
        for p in e["stale"]:
            try:
                p.unlink()
                print(f"  rm {label_root(p)}: {e['rel']}")
                for root in INSTALL_SEARCH_ORDER:
                    if is_under(p, root):
                        cleanup_empty_dirs(p, root)
                        break
            except FileNotFoundError:
                pass


def main():
    if not SKILLS_DIR.is_dir():
        print(f"Error: {SKILLS_DIR} not found.", file=sys.stderr)
        sys.exit(1)
    if not sys.stdin.isatty():
        print("Error: interactive terminal required.", file=sys.stderr)
        sys.exit(1)

    entries = discover()
    if not entries:
        print("No skill files found.")
        return

    print(f"Computing MD5 for {len(entries)} files...", end="\r", flush=True)
    for e in entries:
        assess(e)

    chosen = curses.wrapper(lambda s: run(s, entries))
    if chosen is None:
        print("Cancelled.")
        return
    confirm_and_apply(entries, chosen)


if __name__ == "__main__":
    main()
