from __future__ import annotations

import os
import pytest
from pathlib import Path
from heidi_cli.config import find_project_root

class TestFindProjectRoot:
    def test_find_project_root_current_dir(self, tmp_path):
        """Test finding root when CWD contains .git"""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            (tmp_path / ".git").mkdir()
            result = find_project_root()
            assert result == tmp_path
        finally:
            os.chdir(original_cwd)

    def test_find_project_root_parent_dir(self, tmp_path):
        """Test finding root when CWD is a subdirectory of root"""
        original_cwd = os.getcwd()
        try:
            # Structure:
            # tmp_path/.git
            # tmp_path/subdir/

            (tmp_path / ".git").mkdir()
            subdir = tmp_path / "subdir"
            subdir.mkdir()

            os.chdir(subdir)
            result = find_project_root()
            assert result == tmp_path
        finally:
            os.chdir(original_cwd)

    def test_find_project_root_explicit_path(self, tmp_path):
        """Test finding root using an explicit start_path"""
        # Structure:
        # tmp_path/.git
        # tmp_path/subdir/deep/

        (tmp_path / ".git").mkdir()
        deep_subdir = tmp_path / "subdir" / "deep"
        deep_subdir.mkdir(parents=True)

        result = find_project_root(start_path=deep_subdir)
        assert result == tmp_path

    def test_find_project_root_no_git(self, tmp_path):
        """Test fallback to CWD when no .git is found"""
        original_cwd = os.getcwd()
        try:
            # Structure:
            # tmp_path/subdir/
            # CWD = tmp_path/subdir

            subdir = tmp_path / "subdir"
            subdir.mkdir()

            os.chdir(subdir)

            # Ensure no .git exists in parent chain up to tmp_path
            # (Note: tmp_path is guaranteed to be clean)

            result = find_project_root()
            assert result == subdir  # Should return CWD
        finally:
            os.chdir(original_cwd)

    def test_find_project_root_start_path_is_root(self, tmp_path):
        """Test when start_path is the root itself"""
        (tmp_path / ".git").mkdir()
        result = find_project_root(start_path=tmp_path)
        assert result == tmp_path

    def test_find_project_root_file_path(self, tmp_path):
        """Test when start_path points to a file inside the project"""
        # Structure:
        # tmp_path/.git
        # tmp_path/file.txt

        (tmp_path / ".git").mkdir()
        file_path = tmp_path / "file.txt"
        file_path.touch()

        result = find_project_root(start_path=file_path)
        assert result == tmp_path

    def test_find_project_root_nested_git(self, tmp_path):
        """Test finding the nearest .git when nested"""
        # Structure:
        # tmp_path/.git (outer)
        # tmp_path/inner/.git (inner)
        # tmp_path/inner/subdir

        (tmp_path / ".git").mkdir()
        inner = tmp_path / "inner"
        inner.mkdir()
        (inner / ".git").mkdir()
        subdir = inner / "subdir"
        subdir.mkdir()

        result = find_project_root(start_path=subdir)
        assert result == inner  # Should find the closest one
