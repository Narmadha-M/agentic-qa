"""
FileWatcherAgent: polls the codebase for file modifications and yields changed paths.
Uses watchdog if available, falls back to polling.
"""

import time
from pathlib import Path
from utils.logger import log

POLL_INTERVAL = 1.5  # seconds


class FileWatcherAgent:
    def __init__(self, codebase_path: Path, extensions: list[str]):
        self.codebase_path = codebase_path
        self.extensions = extensions
        self._snapshots: dict[Path, float] = {}
        self._init_snapshots()

    def watch(self):
        """Generator that yields Path objects whenever a file changes."""
        log(f"[Watcher] Polling every {POLL_INTERVAL}s for changes in {self.codebase_path}")
        while True:
            changed = self._check()
            for path in changed:
                yield path
            time.sleep(POLL_INTERVAL)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _init_snapshots(self):
        for path in self._all_files():
            self._snapshots[path] = path.stat().st_mtime

    def _check(self) -> list[Path]:
        changed = []
        current_files = set(self._all_files())

        # Check modified or new files
        for path in current_files:
            mtime = path.stat().st_mtime
            if path not in self._snapshots or self._snapshots[path] != mtime:
                self._snapshots[path] = mtime
                changed.append(path)

        # Forget deleted files (don't trigger — handled separately if needed)
        deleted = set(self._snapshots) - current_files
        for path in deleted:
            del self._snapshots[path]

        return changed

    def _all_files(self) -> list[Path]:
        skip = {".git", "__pycache__", ".venv", "venv", "node_modules"}
        results = []
        for ext in self.extensions:
            for f in self.codebase_path.rglob(f"*{ext}"):
                if not any(s in f.parts for s in skip):
                    results.append(f)
        return results
