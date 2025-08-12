"""Utilities for handling diffs and version reconstruction."""

import subprocess
import re
from typing import Optional, List, Tuple
from pathlib import Path


class DiffUtils:
    @staticmethod
    def generate_unified_diff(old_file: Path, new_file: Path, context_lines: int = 3) -> Optional[str]:
        """Generate a unified diff between two files."""
        try:
            result = subprocess.run(
                [
                    'git', 'diff',
                    '--no-index',
                    '--no-prefix',
                    f'--unified={context_lines}',
                    '-w',  # Ignore whitespace changes
                    str(old_file),
                    str(new_file)
                ],
                capture_output=True,
                text=True
            )

            if result.returncode in [0, 1]:  # 0 = no diff, 1 = diff exists
                return DiffUtils.clean_diff_output(result.stdout)
            return None
        except Exception:
            return None

    @staticmethod
    def clean_diff_output(diff_text: str) -> str:
        """Clean up git diff output for storage."""
        lines = diff_text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Skip git diff metadata
            if line.startswith('diff --git') or line.startswith('index '):
                continue
            if line.startswith('---') or line.startswith('+++'):
                continue

            # Keep actual diff content
            if line.startswith('@@') or line.startswith('+') or line.startswith('-') or line.startswith(' '):
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    @staticmethod
    def generate_reverse_diff(forward_diff: str) -> str:
        """Generate a reverse diff from a forward diff."""
        lines = forward_diff.split('\n')
        reversed_lines = []

        for line in lines:
            if line.startswith('@@'):
                # Swap the line numbers in the hunk header
                match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@(.*)', line)
                if match:
                    old_start, old_count, new_start, new_count, rest = match.groups()
                    # Swap old and new
                    reversed_header = f"@@ -{new_start}"
                    if new_count:
                        reversed_header += f",{new_count}"
                    reversed_header += f" +{old_start}"
                    if old_count:
                        reversed_header += f",{old_count}"
                    reversed_header += f" @@{rest}"
                    reversed_lines.append(reversed_header)
            elif line.startswith('+'):
                # Added lines become removed lines
                reversed_lines.append('-' + line[1:])
            elif line.startswith('-'):
                # Removed lines become added lines
                reversed_lines.append('+' + line[1:])
            else:
                # Context lines stay the same
                reversed_lines.append(line)

        return '\n'.join(reversed_lines)

    @staticmethod
    def parse_diff_hunks(diff_text: str) -> List[Tuple[int, int, List[str]]]:
        """Parse a diff into hunks with line numbers and content."""
        hunks = []
        lines = diff_text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]
            if line.startswith('@@'):
                match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
                if match:
                    new_start = int(match.group(3))
                    new_count = int(match.group(4) or '1')

                    # Collect hunk lines
                    hunk_lines = []
                    i += 1
                    while i < len(lines) and not lines[i].startswith('@@'):
                        hunk_lines.append(lines[i])
                        i += 1

                    hunks.append((new_start, new_count, hunk_lines))
                    continue
            i += 1

        return hunks

    @staticmethod
    def validate_diff(diff_text: str) -> bool:
        """Validate that a diff is well-formed."""
        if not diff_text:
            return True

        # Check for at least one hunk
        if '@@ ' not in diff_text:
            return False

        # Check that each line starts with valid prefix
        for line in diff_text.split('\n'):
            if line and not any(line.startswith(prefix) for prefix in ['@@', '+', '-', ' ']):
                return False

        return True