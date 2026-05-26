"""
DiffAgent: computes what functions/classes changed, were added, or were removed
between two versions of a source file. Also maintains a snapshot cache so the
watcher can ask "what did this file look like before?".
"""

import ast
import difflib
from pathlib import Path


class DiffAgent:
    def __init__(self):
        self._snapshots: dict[Path, str] = {}

    def snapshot(self, path: Path, source: str):
        """Store the current source so next change can be diffed."""
        self._snapshots[path] = source

    def get_snapshot(self, path: Path) -> str:
        return self._snapshots.get(path, "")

    def diff(self, old_source: str, new_source: str) -> dict:
        old_names = self._symbol_names(old_source)
        new_names = self._symbol_names(new_source)

        added = sorted(new_names - old_names)
        removed = sorted(old_names - new_names)
        common = old_names & new_names

        # Detect modified: same name, different body (line diff)
        modified = []
        if old_source and new_source:
            old_lines = old_source.splitlines()
            new_lines = new_source.splitlines()
            diff_ratio = difflib.SequenceMatcher(None, old_lines, new_lines).ratio()
            if diff_ratio < 1.0:
                # Any common symbol could be modified; let Claude figure it out
                modified = sorted(common)

        parts = []
        if added:
            parts.append(f"added: {', '.join(added)}")
        if removed:
            parts.append(f"removed: {', '.join(removed)}")
        if modified:
            parts.append(f"possibly modified: {', '.join(modified)}")

        summary = "; ".join(parts) if parts else "minor changes (no symbol additions/removals)"

        return {
            "added": added + modified,
            "removed": removed,
            "summary": summary,
        }

    def _symbol_names(self, source: str) -> set[str]:
        names = set()
        if not source:
            return names
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return names
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
        return names
