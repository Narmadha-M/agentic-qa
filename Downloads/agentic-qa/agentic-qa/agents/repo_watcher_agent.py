"""
RepoWatcherAgent — Scenario B continuous polling.

Polls a remote GitHub repo every N seconds using `git ls-remote` (no
full clone needed for the check). When a new commit is detected it
clones fresh, diffs the file tree against the previous clone, and
yields (new_clone_path, list_of_changed_paths) to the caller.

Old temp clones are deleted automatically after each cycle.
"""

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from utils.logger import log

DEFAULT_POLL_INTERVAL = 60  # seconds


class RepoWatcherAgent:
    def __init__(
        self,
        repo_url: str,
        branch: str = "",
        extensions: list[str] | None = None,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ):
        self.repo_url = repo_url
        self.branch = branch
        self.extensions = extensions or [".py"]
        self.poll_interval = poll_interval
        self._last_commit: str = ""

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def get_current_head(self) -> str:
        """Return the latest commit SHA from the remote (lightweight — no clone)."""
        cmd = ["git", "ls-remote", self.repo_url]
        if self.branch:
            cmd.append(f"refs/heads/{self.branch}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0 or not result.stdout.strip():
            return ""
        for line in result.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                if self.branch:
                    if parts[1] == f"refs/heads/{self.branch}":
                        return parts[0]
                else:
                    return parts[0]
        return ""

    def watch(self, initial_clone: Path):
        """
        Generator. Polls every poll_interval seconds.
        Yields (new_clone_path, [changed_file_paths]) when a new commit
        is found. The caller is responsible for NOT deleting initial_clone
        while this generator is running; this agent will clean up clones
        it creates itself.
        """
        self._last_commit = self.get_current_head()
        branch_label = f" ({self.branch})" if self.branch else ""
        log(
            f"[RepoWatcher] Monitoring {self.repo_url}{branch_label} — "
            f"current HEAD {self._last_commit[:8] or 'unknown'}"
        )
        log(f"[RepoWatcher] Polling every {self.poll_interval}s  (Ctrl+C to stop)")

        prev_clone = initial_clone

        while True:
            time.sleep(self.poll_interval)

            try:
                head = self.get_current_head()
            except Exception as exc:
                log(f"[RepoWatcher] ls-remote failed: {exc} — retrying next cycle")
                continue

            if not head or head == self._last_commit:
                log("[RepoWatcher] No new commits.")
                continue

            log(
                f"[RepoWatcher] New commit → {head[:8]}  "
                f"(was {self._last_commit[:8] or 'unknown'})"
            )

            new_clone = self._clone_fresh()
            if new_clone is None:
                continue  # clone failed; try again next cycle

            changed = self._diff_trees(prev_clone, new_clone)
            log(f"[RepoWatcher] {len(changed)} file(s) changed/added.")

            # Clean up previous clone only if WE created it (not the initial one)
            if prev_clone != initial_clone:
                shutil.rmtree(prev_clone, ignore_errors=True)

            prev_clone = new_clone
            self._last_commit = head

            yield new_clone, changed

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _clone_fresh(self) -> Path | None:
        tmp = tempfile.mkdtemp(prefix="agentic-qa-watch-")
        cmd = ["git", "clone", "--depth", "1"]
        if self.branch:
            cmd += ["--branch", self.branch]
        cmd += [self.repo_url, tmp]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log(f"[RepoWatcher] Clone failed: {result.stderr.strip()}")
            shutil.rmtree(tmp, ignore_errors=True)
            return None
        return Path(tmp)

    def _diff_trees(self, old_root: Path, new_root: Path) -> list[Path]:
        """Return paths (in new_root) that are new or modified vs old_root."""
        changed = []
        for ext in self.extensions:
            for new_file in new_root.rglob(f"*{ext}"):
                rel = _safe_relative(new_file, new_root)
                if rel is None:
                    continue
                old_file = old_root / rel
                if not old_file.exists():
                    changed.append(new_file)  # new file
                    continue
                try:
                    new_src = new_file.read_text(encoding="utf-8", errors="replace")
                    old_src = old_file.read_text(encoding="utf-8", errors="replace")
                    if new_src != old_src:
                        changed.append(new_file)
                except OSError:
                    changed.append(new_file)
        return changed


def _safe_relative(path: Path, root: Path) -> Path | None:
    try:
        return path.relative_to(root)
    except ValueError:
        return None
