"""Pure-function tests — no filesystem, no curses."""

from claude_skills import cli


def test_truncate_short_string_unchanged():
    assert cli.truncate("hello", 10) == "hello"


def test_truncate_long_string_gets_dot():
    assert cli.truncate("hello world", 6) == "hello."


def test_truncate_exact_width():
    assert cli.truncate("abcde", 5) == "abcde"


def test_truncate_zero_width():
    assert cli.truncate("anything", 0) == ""


def test_is_under_basic(tmp_path):
    root = tmp_path / "root"
    inside = root / "a" / "b.txt"
    assert cli.is_under(inside, root)


def test_is_under_sibling_not_under(tmp_path):
    root = tmp_path / "root"
    other = tmp_path / "other" / "x"
    assert not cli.is_under(other, root)


def test_is_under_prefix_collision(tmp_path):
    """`/foo/barX` is NOT under `/foo/bar`."""
    root = tmp_path / "bar"
    fake = tmp_path / "barX" / "x"
    assert not cli.is_under(fake, root)


def _entry(state, plus=0, minus=0):
    return {"state": state, "plus": plus, "minus": minus}


def test_aggregate_skill_all_synced():
    entries = [_entry(cli.STATE_SYNCED), _entry(cli.STATE_SYNCED)]
    (state, plus, minus), check = cli.aggregate_skill([0, 1], entries, set())
    assert state == cli.STATE_SYNCED
    assert (plus, minus) == (0, 0)
    assert check == "[ ]"


def test_aggregate_skill_all_new():
    entries = [_entry(cli.STATE_NEW), _entry(cli.STATE_NEW)]
    agg, check = cli.aggregate_skill([0, 1], entries, {0, 1})
    assert agg[0] == cli.STATE_NEW
    assert check == "[x]"


def test_aggregate_skill_mixed_sums_plus_minus():
    entries = [
        _entry(cli.STATE_DIFF, plus=3, minus=1),
        _entry(cli.STATE_SYNCED),
        _entry(cli.STATE_DIFF, plus=2, minus=4),
    ]
    (state, plus, minus), check = cli.aggregate_skill([0, 1, 2], entries, {0})
    assert state == cli.STATE_DIFF
    assert (plus, minus) == (5, 5)
    assert check == "[-]"


def test_build_rows_groups_by_skill():
    entries = [
        {"rel": "alpha/SKILL.md"},
        {"rel": "alpha/extra.md"},
        {"rel": "beta/SKILL.md"},
    ]
    rows = cli.build_rows(entries, expanded=set())
    assert [r["type"] for r in rows] == ["skill", "skill"]
    assert [r["skill"] for r in rows] == ["alpha", "beta"]


def test_build_rows_emits_files_only_for_expanded():
    entries = [
        {"rel": "alpha/SKILL.md"},
        {"rel": "alpha/extra.md"},
        {"rel": "beta/SKILL.md"},
    ]
    rows = cli.build_rows(entries, expanded={"alpha"})
    types = [r["type"] for r in rows]
    assert types == ["skill", "file", "file", "skill"]


def test_relocate_cursor_skill_match():
    rows = [
        {"type": "skill", "skill": "alpha", "files": []},
        {"type": "skill", "skill": "beta", "files": []},
    ]
    idx = cli.relocate_cursor({"type": "skill", "skill": "beta"}, rows)
    assert rows[idx]["skill"] == "beta"


def test_relocate_cursor_file_falls_back_to_skill_when_collapsed():
    rows = [
        {"type": "skill", "skill": "alpha", "files": [0]},
        {"type": "skill", "skill": "beta", "files": [1]},
    ]
    idx = cli.relocate_cursor({"type": "file", "idx": 1, "skill": "beta"}, rows)
    assert rows[idx] == rows[1]


def test_wrap_lines_no_overflow():
    out = cli.wrap_lines([("hello", 0)], width=10)
    assert out == [("hello", 0)]


def test_wrap_lines_wraps_with_continuation_indent():
    out = cli.wrap_lines([("abcdefghij", 0)], width=4)
    # first chunk: 4 chars, then 2-space indent + 2 chars (room=4-2=2)
    assert out[0] == ("abcd", 0)
    assert out[1][0].startswith("  ")


def test_wrap_lines_preserves_blank_lines():
    out = cli.wrap_lines([("", 5)], width=10)
    assert out == [("", 5)]
