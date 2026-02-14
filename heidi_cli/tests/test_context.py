from __future__ import annotations

import os
from pathlib import Path
import pytest
from heidi_cli.context import collect_context, should_ignore, is_text_file, summarize_context

class TestContext:
    def test_should_ignore_true(self):
        assert should_ignore(Path("foo/.git/bar"))
        assert should_ignore(Path("node_modules/package"))
        assert should_ignore(Path(".venv/bin/python"))

    def test_should_ignore_false(self):
        assert not should_ignore(Path("foo/bar"))
        assert not should_ignore(Path("src/main.py"))

    def test_is_text_file_true(self):
        assert is_text_file(Path("file.py"))
        assert is_text_file(Path("readme.md"))
        assert is_text_file(Path("config.json"))

    def test_is_text_file_false(self):
        assert not is_text_file(Path("image.png"))
        assert not is_text_file(Path("archive.zip"))
        assert not is_text_file(Path("binary.exe"))

    def test_collect_context_non_existent(self, tmp_path):
        non_existent = tmp_path / "non_existent"
        assert collect_context(non_existent) == ""

    def test_collect_context_file(self, tmp_path):
        f = tmp_path / "test.py"
        content = "print('hello')"
        f.write_text(content, encoding="utf-8")

        result = collect_context(f)
        assert f"# {f.name}" in result
        assert content in result

    def test_collect_context_directory(self, tmp_path):
        # Create structure:
        # root/
        #   file1.py
        #   ignored_dir/
        #     file2.py
        #   subdir/
        #     file3.md

        (tmp_path / "file1.py").write_text("content1", encoding="utf-8")

        ignored = tmp_path / ".git"
        ignored.mkdir()
        (ignored / "file2.py").write_text("content2", encoding="utf-8")

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.md").write_text("content3", encoding="utf-8")

        result = collect_context(tmp_path)

        assert "file1.py" in result
        assert "content1" in result
        assert "file3.md" in result
        assert "content3" in result

        assert "file2.py" not in result
        assert "content2" not in result

    def test_collect_context_max_size(self, tmp_path):
        f = tmp_path / "large.py"
        # Create content slightly larger than typical chunk but smaller than total max size for this test
        # wait, max_size is 400KB default.
        # I'll pass a small max_size to test truncation logic easily.

        max_size = 10
        content = "123456789012345"
        f.write_text(content, encoding="utf-8")

        # Test directory mode
        result = collect_context(tmp_path, max_size=max_size)
        assert "(truncated)" in result
        assert len(result.split("\n\n")[1].strip()) <= max_size

    def test_collect_context_binary(self, tmp_path):
        f = tmp_path / "image.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n")

        result = collect_context(tmp_path)
        assert "image.png" not in result

    def test_summarize_context(self):
        long_context = "line\n" * 100
        # max_length small enough to trigger summary
        summary = summarize_context(long_context, max_length=50)
        assert "... (" in summary
        assert "more lines)" in summary
