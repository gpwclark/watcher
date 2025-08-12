"""Tests for diff utilities."""

import pytest
from pathlib import Path
import tempfile
from watcher.core.diff_utils import DiffUtils


class TestDiffUtils:
    def test_clean_diff_output(self):
        """Test cleaning git diff output."""
        raw_diff = """diff --git a/old.txt b/new.txt
index 1234567..890abcd 100644
--- a/old.txt
+++ b/new.txt
@@ -1,3 +1,3 @@
 line 1
-line 2
+line 2 modified
 line 3"""

        cleaned = DiffUtils.clean_diff_output(raw_diff)
        assert "diff --git" not in cleaned
        assert "index" not in cleaned
        assert "---" not in cleaned
        assert "+++" not in cleaned
        assert "@@ -1,3 +1,3 @@" in cleaned
        assert "-line 2" in cleaned
        assert "+line 2 modified" in cleaned

    def test_generate_reverse_diff(self):
        """Test generating reverse diff from forward diff."""
        forward_diff = """@@ -1,3 +1,3 @@
 line 1
-line 2
+line 2 modified
 line 3"""

        reverse_diff = DiffUtils.generate_reverse_diff(forward_diff)
        assert "@@ -1,3 +1,3 @@" in reverse_diff
        assert "+line 2" in reverse_diff  # Was removed, now added
        assert "-line 2 modified" in reverse_diff  # Was added, now removed

    def test_parse_diff_hunks(self):
        """Test parsing diff into hunks."""
        diff_text = """@@ -1,3 +1,3 @@
 line 1
-line 2
+line 2 modified
 line 3
@@ -5,2 +5,3 @@
 line 5
+line 5.5
 line 6"""

        hunks = DiffUtils.parse_diff_hunks(diff_text)
        assert len(hunks) == 2

        # First hunk
        assert hunks[0][0] == 1  # start line
        assert hunks[0][1] == 3  # line count
        assert len(hunks[0][2]) == 4  # number of lines in hunk

        # Second hunk
        assert hunks[1][0] == 5
        assert hunks[1][1] == 3

    def test_validate_diff(self):
        """Test diff validation."""
        # Valid diff
        valid_diff = """@@ -1,3 +1,3 @@
 line 1
-line 2
+line 2 modified
 line 3"""
        assert DiffUtils.validate_diff(valid_diff) is True

        # Invalid - no hunk header
        invalid_diff = """line 1
-line 2
+line 2 modified"""
        assert DiffUtils.validate_diff(invalid_diff) is False

        # Invalid - bad line prefix
        invalid_diff2 = """@@ -1,3 +1,3 @@
line 1
*line 2"""
        assert DiffUtils.validate_diff(invalid_diff2) is False

        # Empty diff is valid
        assert DiffUtils.validate_diff("") is True

    def test_generate_unified_diff_with_files(self):
        """Test generating unified diff between actual files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_file = Path(tmpdir) / "old.txt"
            new_file = Path(tmpdir) / "new.txt"

            old_file.write_text("line 1\nline 2\nline 3\n")
            new_file.write_text("line 1\nline 2 modified\nline 3\n")

            diff = DiffUtils.generate_unified_diff(old_file, new_file)
            assert diff is not None
            assert "-line 2" in diff
            assert "+line 2 modified" in diff
            assert "@@ " in diff