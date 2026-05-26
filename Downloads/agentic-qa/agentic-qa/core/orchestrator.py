"""
Orchestrator — coordinates all agents.

Scenario A  (run_initial):
    ingest → generate tests → run → HTML report  (one shot, then exit)

Scenario B  (start_repo_watch):
    run_initial, then poll the remote GitHub repo every N seconds;
    on new commit → diff changed files → update only those tests →
    rerun → refresh HTML report  (runs until Ctrl+C)

Local watch  (start_watch):
    same update loop but triggered by local filesystem changes instead
    of remote commits (useful when codebase is a local folder).
"""

import shutil
from pathlib import Path

from agents.diff_agent import DiffAgent
from agents.file_watcher_agent import FileWatcherAgent
from agents.ingest_agent import IngestAgent
from agents.test_runner_agent import TestRunnerAgent
from agents.test_writer_agent import TestWriterAgent
from utils.logger import log
from utils.report_generator import generate as generate_report


class Orchestrator:
    def __init__(
        self,
        codebase_path: Path,
        output_dir: Path,
        extensions: list[str],
        repo_url: str = "",
    ):
        self.codebase_path = codebase_path
        self.output_dir = output_dir
        self.extensions = extensions
        self.repo_url = repo_url

        self.ingest = IngestAgent(codebase_path, extensions)
        self.writer = TestWriterAgent(output_dir)
        self.runner = TestRunnerAgent(output_dir, codebase_path=codebase_path)
        self.watcher = FileWatcherAgent(codebase_path, extensions)
        self.differ = DiffAgent()

        # absolute source path → generated test file
        self.source_to_test: dict[Path, Path] = {}

    # ================================================================
    # Scenario A — one-shot
    # ================================================================

    def run_initial(self):
        log("=== Phase 1: Ingesting codebase and generating tests ===")

        modules = self.ingest.run()
        if not modules:
            log("[WARN] No source files found. Check --extensions and codebase path.")
            return

        log(f"[Ingest] Found {len(modules)} source file(s).")

        for module in modules:
            log(f"[Writer] Generating tests for: {module.relative_path}")
            test_file = self.writer.generate(module)
            self.source_to_test[module.path] = test_file
            # Snapshot source so Phase 2 can diff against it later
            self.differ.snapshot(module.path, module.source_code)
            log(f"[Writer] Saved → {test_file.name}")

        log("[Runner] Running all generated tests...")
        results = self.runner.run_all()
        self._print_summary(results)
        self._save_report(results)

    # ================================================================
    # Scenario B — continuous remote-repo polling
    # ================================================================

    def start_repo_watch(
        self,
        initial_clone: Path,
        repo_url: str,
        branch: str = "",
        poll_interval: int = 60,
    ):
        """
        Poll the remote GitHub repo for new commits.
        On each change: update only affected tests, rerun, refresh report.
        Runs forever until Ctrl+C.
        """
        from agents.repo_watcher_agent import RepoWatcherAgent

        log(
            f"\n=== Scenario B: Watching remote repo for changes "
            f"(every {poll_interval}s — Ctrl+C to stop) ==="
        )

        agent = RepoWatcherAgent(
            repo_url=repo_url,
            branch=branch,
            extensions=self.extensions,
            poll_interval=poll_interval,
        )

        try:
            for new_clone, changed_files in agent.watch(initial_clone):
                log(f"\n[RepoWatcher] Processing {len(changed_files)} changed file(s)...")

                # Re-point agents at the new clone
                old_clone = self.codebase_path
                self._switch_codebase(new_clone)

                for changed_path in changed_files:
                    self._handle_repo_change(changed_path, old_clone, new_clone)

                log("[Runner] Running all tests after update...")
                results = self.runner.run_all()
                self._print_summary(results)
                self._save_report(results)

        except KeyboardInterrupt:
            log("\n[RepoWatcher] Stopped.")

    # ================================================================
    # Local file-system watch (existing behaviour)
    # ================================================================

    def start_watch(self):
        log("\n=== Local watch: monitoring filesystem for changes (Ctrl+C to stop) ===")
        try:
            for changed_path in self.watcher.watch():
                log(f"\n[Watcher] Change detected: {changed_path}")
                self._handle_local_change(changed_path)
        except KeyboardInterrupt:
            log("\n[Watcher] Stopped.")

    # ================================================================
    # Internal helpers
    # ================================================================

    def _switch_codebase(self, new_path: Path):
        """Point all agents at a freshly cloned directory."""
        old_path = self.codebase_path
        self.codebase_path = new_path
        self.ingest.codebase_path = new_path
        self.runner.codebase_path = new_path
        # Remap source_to_test keys from old clone paths to new clone paths
        remapped = {}
        for old_abs, test_file in self.source_to_test.items():
            try:
                rel = old_abs.relative_to(old_path)
                remapped[new_path / rel] = test_file
            except ValueError:
                remapped[old_abs] = test_file
        self.source_to_test = remapped

    def _handle_repo_change(self, changed_path: Path, old_clone: Path, new_clone: Path):
        """Update or create the test file for one changed source file."""
        module = self.ingest.ingest_file(changed_path)
        if module is None:
            log(f"[Skip] Could not parse {changed_path.name}")
            return

        existing_test = self.source_to_test.get(changed_path)

        if existing_test and existing_test.exists():
            # Retrieve snapshot of the OLD version to diff against
            try:
                rel = changed_path.relative_to(new_clone)
                old_abs = old_clone / rel
            except ValueError:
                old_abs = changed_path

            old_source = self.differ.get_snapshot(old_abs)
            changes = self.differ.diff(old_source, module.source_code)
            log(f"[Diff]   {module.relative_path} → {changes['summary']}")
            test_file = self.writer.update(module, existing_test, changes)
        else:
            log(f"[Writer] New file — generating tests for {module.relative_path}")
            test_file = self.writer.generate(module)
            self.source_to_test[changed_path] = test_file

        self.differ.snapshot(changed_path, module.source_code)

    def _handle_local_change(self, changed_path: Path):
        """Handle a locally modified file (filesystem watch scenario)."""
        module = self.ingest.ingest_file(changed_path)
        if module is None:
            log(f"[Skip] Could not parse {changed_path.name}")
            return

        existing_test = self.source_to_test.get(changed_path)

        if existing_test and existing_test.exists():
            old_source = self.differ.get_snapshot(changed_path)
            changes = self.differ.diff(old_source, module.source_code)
            log(f"[Diff] {changes['summary']}")
            test_file = self.writer.update(module, existing_test, changes)
        else:
            test_file = self.writer.generate(module)
            self.source_to_test[changed_path] = test_file

        self.differ.snapshot(changed_path, module.source_code)

        log("[Runner] Retesting affected file...")
        result = self.runner.run_file(test_file)
        self._print_file_result(test_file.name, result)

        all_results = self.runner.run_all()
        self._save_report(all_results)

    def _save_report(self, results: list[dict]):
        report_path = generate_report(
            results,
            self.output_dir / "report.html",
            repo_url=self.repo_url,
        )
        log(f"[Report] HTML report → {report_path}")

    def _print_summary(self, results: list[dict]):
        passed = sum(1 for r in results if r["passed"])
        failed = len(results) - passed
        log(f"\n{'='*50}")
        log(f"Results: {passed} passed, {failed} failed out of {len(results)} test files")
        for r in results:
            status = "✓ PASS" if r["passed"] else "✗ FAIL"
            log(f"  {status}  {r['file']}")
            if not r["passed"] and r.get("output"):
                for line in r["output"].splitlines()[-10:]:
                    log(f"       {line}")
        log("=" * 50)

    def _print_file_result(self, filename: str, result: dict):
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        log(f"\n  {status}  {filename}")
        if not result["passed"] and result.get("output"):
            for line in result["output"].splitlines()[-15:]:
                log(f"     {line}")
