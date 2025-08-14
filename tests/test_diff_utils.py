"""Tests for diff utilities."""

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
