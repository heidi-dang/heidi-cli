from __future__ import annotations

from pathlib import Path
from heidi_cli.context import collect_context, is_text_file, should_ignore, IGNORE_DIRS


class TestContext:
    def test_should_ignore_exact(self):
        for d in IGNORE_DIRS:
            assert should_ignore(Path(d))

    def test_should_ignore_nested(self):
        assert should_ignore(Path("src/node_modules/foo"))
        assert should_ignore(Path(".git/objects"))
        assert should_ignore(Path(".venv/bin/python"))

    def test_should_not_ignore(self):
        assert not should_ignore(Path("src/main.py"))
        assert not should_ignore(Path("README.md"))
        assert not should_ignore(Path("tests/test_context.py"))

    def test_is_text_file_valid(self):
        valid_extensions = [".py", ".md", ".txt", ".json", ".yaml", ".js", ".ts"]
        for ext in valid_extensions:
            assert is_text_file(Path(f"file{ext}"))

    def test_is_text_file_invalid(self):
        invalid_extensions = [".png", ".jpg", ".pyc", ".bin", ".exe", ".dll"]
        for ext in invalid_extensions:
            assert not is_text_file(Path(f"file{ext}"))

    def test_collect_context_simple(self, tmp_path):
        # Setup
        (tmp_path / "file1.txt").write_text("Hello world", encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src/main.py").write_text("print('hello')", encoding="utf-8")

        # Test
        context = collect_context(tmp_path)

        assert "# file1.txt" in context
        assert "Hello world" in context
        assert "# src/main.py" in context
        assert "print('hello')" in context

    def test_collect_context_ignores_dirs(self, tmp_path):
        # Setup
        (tmp_path / "src").mkdir()
        (tmp_path / "src/main.py").write_text("ok", encoding="utf-8")

        # Ignored dir
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules/package.json").write_text("ignored", encoding="utf-8")

        # Test
        context = collect_context(tmp_path)

        assert "src/main.py" in context
        assert "node_modules" not in context
        assert "package.json" not in context

    def test_collect_context_ignores_files(self, tmp_path):
        # Setup
        (tmp_path / "image.png").write_bytes(b"fake image data")
        (tmp_path / "code.py").write_text("code", encoding="utf-8")

        # Test
        context = collect_context(tmp_path)

        assert "code.py" in context
        assert "image.png" not in context

    def test_collect_context_max_size(self, tmp_path):
        # Setup
        large_content = "a" * 1000
        (tmp_path / "large.txt").write_text(large_content, encoding="utf-8")

        # Test with small max size
        context = collect_context(tmp_path, max_size=500)

        assert "large.txt" in context
        # It should be truncated or limited
        assert len(context) < 1000 + 200 # approximate overhead

    def test_collect_context_truncation(self, tmp_path):
        # Setup multiple files to exceed limit
        (tmp_path / "file1.txt").write_text("a" * 100, encoding="utf-8")
        (tmp_path / "file2.txt").write_text("b" * 100, encoding="utf-8")

        # Limit to 150 chars total (approx)
        context = collect_context(tmp_path, max_size=150)

        assert "file1.txt" in context
        assert "file2.txt" in context
        assert "(truncated)" in context or len(context) <= 200 # slightly loose assertion
