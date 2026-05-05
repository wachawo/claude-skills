"""Filesystem-touching tests — md5, find_installed, cleanup_empty_dirs, assess."""

from claude_skills import cli


def test_md5_file_consistent(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"hello world")
    assert cli.md5_file(f) == cli.md5_file(f)


def test_md5_file_differs_for_different_content(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_bytes(b"hello")
    b.write_bytes(b"world")
    assert cli.md5_file(a) != cli.md5_file(b)


def test_find_installed_local_priority(tmp_path, monkeypatch):
    local = tmp_path / "local"
    user  = tmp_path / "user"
    (local / "skill1").mkdir(parents=True)
    (local / "skill1" / "SKILL.md").write_text("local")
    (user / "skill1").mkdir(parents=True)
    (user / "skill1" / "SKILL.md").write_text("user")

    monkeypatch.setattr(cli, "INSTALL_SEARCH_ORDER", (local, user))

    found = cli.find_installed("skill1", "SKILL.md")
    assert found == local / "skill1" / "SKILL.md"


def test_find_installed_user_fallback(tmp_path, monkeypatch):
    local = tmp_path / "local"
    user  = tmp_path / "user"
    (user / "skill1").mkdir(parents=True)
    (user / "skill1" / "SKILL.md").write_text("user")

    monkeypatch.setattr(cli, "INSTALL_SEARCH_ORDER", (local, user))

    found = cli.find_installed("skill1", "SKILL.md")
    assert found == user / "skill1" / "SKILL.md"


def test_find_installed_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "INSTALL_SEARCH_ORDER", (tmp_path / "a", tmp_path / "b"))
    assert cli.find_installed("skill1", "SKILL.md") is None


def test_cleanup_empty_dirs_removes_chain(tmp_path):
    nested = tmp_path / "skills" / "skill1" / "subdir" / "file.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("x")
    nested.unlink()

    cli.cleanup_empty_dirs(nested, tmp_path)

    assert not (tmp_path / "skills" / "skill1" / "subdir").exists()
    assert not (tmp_path / "skills" / "skill1").exists()
    assert not (tmp_path / "skills").exists()
    assert tmp_path.exists()  # never removed


def test_cleanup_empty_dirs_stops_on_nonempty(tmp_path):
    skill = tmp_path / "skill1"
    skill.mkdir()
    (skill / "kept.md").write_text("kept")
    removed = skill / "gone.md"
    removed.write_text("x")
    removed.unlink()

    cli.cleanup_empty_dirs(removed, tmp_path)

    assert skill.exists()
    assert (skill / "kept.md").exists()


def test_assess_new_when_dest_missing():
    entry = {"src": None, "dest": None, "state": cli.STATE_NEW, "plus": 0, "minus": 0}
    cli.assess(entry)
    assert entry["state"] == cli.STATE_NEW


def test_assess_synced_when_md5_matches(tmp_path):
    src  = tmp_path / "src.md"
    dest = tmp_path / "dest.md"
    src.write_bytes(b"same content")
    dest.write_bytes(b"same content")
    entry = {"src": src, "dest": dest, "state": cli.STATE_NEW, "plus": 0, "minus": 0}
    cli.assess(entry)
    assert entry["state"] == cli.STATE_SYNCED


def test_assess_diff_with_counts(tmp_path):
    src  = tmp_path / "src.md"
    dest = tmp_path / "dest.md"
    dest.write_text("line1\nline2\nline3\n")
    src.write_text("line1\nLINE2\nline3\nline4\n")
    entry = {"src": src, "dest": dest, "state": cli.STATE_NEW, "plus": 0, "minus": 0}
    cli.assess(entry)
    assert entry["state"] == cli.STATE_DIFF
    # one line replaced + one line added → at least one + and one -
    assert entry["plus"] >= 1
    assert entry["minus"] >= 1
