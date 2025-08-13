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

            if result.returncode == 1:  # 1 = diff exists
                return DiffUtils.clean_diff_output(result.stdout)
            elif result.returncode == 0:  # 0 = no diff
                return ""
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
            # Skip "No newline at end of file" messages
            if line == '\\ No newline at end of file':
                continue

            # Keep actual diff content
            if line.startswith('@@') or line.startswith('+') or line.startswith('-') or line.startswith(' '):
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)