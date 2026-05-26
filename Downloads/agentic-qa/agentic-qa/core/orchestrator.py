"""
Orchestrator: coordinates ingest → generate → run (Phase 1)
and watch → diff → update → rerun (Phase 2).
"""

import time
from pathlib import Path
from agents.ingest_agent import IngestAgent
from agents.test_writer_agent import TestWriterAgent
from agents.test_runner_agent import TestRunnerAgent
from agents.file_watcher_agent import FileWatcherAgent
from agents.diff_agent import DiffAgent
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

        # Track which source file maps to which test file
        self.source_to_test: dict[Path, Path] = {}

    # ------------------------------------------------------------------
    # Phase 1
    # ------------------------------------------------------------------

    def run_initial(self):
        log("=== Phase 1: Initial ingestion and test generation ===")

        modules = self.ingest.run()
        if not modules:
            log("[WARN] No source files found. Check --extensions and path.")
            return

        log(f"[Ingest] Found {len(modules)} source file(s).")

        for module in modules:
            log(f"[Writer] Generating tests for: {module.relative_path}")
            test_file = self.writer.generate(module)
            self.source_to_test[module.path] = test_file
            log(f"[Writer] Saved -> {test_file.name}")

        log("[Runner] Running all generated tests...")
        results = self.runner.run_all()
        self._print_summary(results)

        # Generate HTML report
        report_path = generate_report(
            results,
            self.output_dir / "report.html",
            repo_url=self.repo_url,
        )
        log(f"[Report] HTML report → {report_path}")

    # ------------------------------------------------------------------
    # Phase 2
    # ------------------------------------------------------------------

    def start_watch(self):
        log("\n=== Phase 2: Watching for file changes (Ctrl+C to quit) ===")
        try:
            for changed_path in self.watcher.watch():
                log(f"\n[Watcher] Change detected: {changed_path}")
                self._handle_change(changed_path)
        except KeyboardInterrupt:
            log("\n[Watcher] Stopped.")

    def _handle_change(self, changed_path: Path):
        module = self.ingest.ingest_file(changed_path)
        if module is None:
            log(f"[Skip] Could not parse {changed_path.name}")
            return

        existing_test = self.source_to_test.get(changed_path)

        if existing_test and existing_test.exists():
            log("[Diff] Analysing what changed...")
            old_source = self.differ.get_snapshot(changed_path)
            changes = self.differ.diff(old_source, module.source_code)
            log(f"[Diff] {changes['summary']}")

            log("[Writer] Updating tests for changed functions/classes...")
            test_file = self.writer.update(module, existing_test, changes)
        else:
            log("[Writer] No existing test file — generating from scratch...")
            test_file = self.writer.generate(module)
            self.source_to_test[changed_path] = test_file

        self.differ.snapshot(changed_path, module.source_code)

        log("[Runner] Retesting affected file...")
        result = self.runner.run_file(test_file)
        self._print_file_result(test_file.name, result)

        # Refresh the report after every watched change
        all_results = self.runner.run_all()
        generate_report(
            all_results,
            self.output_dir / "report.html",
            repo_url=self.repo_url,
        )
        log(f"[Report] Report updated → {self.output_dir / 'report.html'}")

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
        log("="*50)

    def _print_file_result(self, filename: str, result: dict):
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        log(f"\n  {status}  {filename}")
        if not result["passed"] and result.get("output"):
            for line in result["output"].splitlines()[-15:]:
                log(f"     {line}")
