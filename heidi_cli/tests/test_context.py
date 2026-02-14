from __future__ import annotations

from pathlib import Path
from heidi_cli.context import should_ignore, IGNORE_DIRS


def test_should_ignore_exact_matches():
    """Test that ignored directories are ignored."""
    for ignored in IGNORE_DIRS:
        assert should_ignore(Path(ignored))


def test_should_ignore_nested_matches():
    """Test that ignored directories nested in a path are ignored."""
    for ignored in IGNORE_DIRS:
        path = Path(f"src/{ignored}/file.txt")
        assert should_ignore(path)


def test_should_ignore_deep_nested_matches():
    """Test that ignored directories deeply nested in a path are ignored."""
    for ignored in IGNORE_DIRS:
        path = Path(f"src/deep/nested/{ignored}/file.txt")
        assert should_ignore(path)


def test_should_ignore_mixed_case():
    """
    Test mixed case matching.
    Currently, the implementation checks `ignored in path.parts`.
    If `IGNORE_DIRS` contains lowercase strings, uppercase paths won't match unless `path.parts` somehow canonicalizes.
    Let's verify the behavior. Pathlib preserves case on Linux.
    So `should_ignore(Path('.GIT'))` should be False if `IGNORE_DIRS` has `.git`.
    """
    assert not should_ignore(Path(".GIT"))
    assert not should_ignore(Path("NODE_MODULES"))


def test_should_not_ignore_normal_files():
    """Test that normal files and directories are not ignored."""
    assert not should_ignore(Path("src/main.py"))
    assert not should_ignore(Path("README.md"))
    assert not should_ignore(Path("tests/test_context.py"))
    assert not should_ignore(Path("heidi_cli/context.py"))


def test_should_not_ignore_similar_names():
    """Test that names similar to ignored directories are not ignored."""
    # "git" is not ".git"
    assert not should_ignore(Path("git"))
    # "venv" is not ".venv"
    assert not should_ignore(Path("venv"))
    # "my_node_modules" contains "node_modules" but as a substring, not a path part
    assert not should_ignore(Path("my_node_modules"))
    assert not should_ignore(Path("node_modules_backup"))
    assert not should_ignore(Path("__pycache__backup"))


def test_should_ignore_multiple_ignored_parts():
    """Test paths with multiple ignored parts."""
    assert should_ignore(Path("node_modules/.bin"))
    assert should_ignore(Path(".venv/lib/python3.10/site-packages"))


def test_should_ignore_root_ignored():
    """Test when the ignored directory is the root of the path."""
    assert should_ignore(Path(".git/config"))
    assert should_ignore(Path(".venv/bin/activate"))
