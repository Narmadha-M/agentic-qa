"""Tests for core/orchestrator.py — Orchestrator."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from core.orchestrator import Orchestrator
from core.models import SourceModule


def make_module(tmp_path, name="mod.py"):
    return SourceModule(
        path=tmp_path / name,
        relative_path=Path(name),
        source_code="def foo(): pass\n",
        functions=["foo"],
    )


@pytest.fixture
def mock_orchestrator(tmp_path):
    with patch("core.orchestrator.IngestAgent") as MockIngest, \
         patch("core.orchestrator.TestWriterAgent") as MockWriter, \
         patch("core.orchestrator.TestRunnerAgent") as MockRunner, \
         patch("core.orchestrator.FileWatcherAgent") as MockWatcher, \
         patch("core.orchestrator.DiffAgent") as MockDiff:

        orch = Orchestrator(
            codebase_path=tmp_path,
            output_dir=tmp_path / "out",
            extensions=[".py"],
        )
        orch.ingest = MockIngest.return_value
        orch.writer = MockWriter.return_value
        orch.runner = MockRunner.return_value
        orch.watcher = MockWatcher.return_value
        orch.differ = MockDiff.return_value
        yield orch, tmp_path


class TestRunInitial:
    def test_calls_ingest_run(self, mock_orchestrator):
        orch, tmp = mock_orchestrator
        orch.ingest.run.return_value = []
        orch.run_initial()
        orch.ingest.run.assert_called_once()

    def test_no_modules_skips_writer_and_runner(self, mock_orchestrator):
        orch, tmp = mock_orchestrator
        orch.ingest.run.return_value = []
        orch.run_initial()
        orch.writer.generate.assert_not_called()
        orch.runner.run_all.assert_not_called()

    def test_generates_test_per_module(self, mock_orchestrator):
        orch, tmp = mock_orchestrator
        modules = [make_module(tmp, "a.py"), make_module(tmp, "b.py")]
        test_file = tmp / "test_a.py"
        test_file.touch()
        orch.ingest.run.return_value = modules
        orch.writer.generate.return_value = test_file
        orch.runner.run_all.return_value = [{"passed": True, "file": "test_a.py"}]
        orch.run_initial()
        assert orch.writer.generate.call_count == 2

    def test_runs_all_tests_after_generation(self, mock_orchestrator):
        orch, tmp = mock_orchestrator
        modules = [make_module(tmp)]
        test_file = tmp / "test_mod.py"
        test_file.touch()
        orch.ingest.run.return_value = modules
        orch.writer.generate.return_value = test_file
        orch.runner.run_all.return_value = [{"passed": True, "file": "test_mod.py"}]
        orch.run_initial()
        orch.runner.run_all.assert_called_once()

    def test_source_to_test_mapping_populated(self, mock_orchestrator):
        orch, tmp = mock_orchestrator
        module = make_module(tmp)
        test_file = tmp / "test_mod.py"
        test_file.touch()
        orch.ingest.run.return_value = [module]
        orch.writer.generate.return_value = test_file
        orch.runner.run_all.return_value = [{"passed": True, "file": "test_mod.py"}]
        orch.run_initial()
        assert module.path in orch.source_to_test


class TestHandleChange:
    def test_generates_new_test_when_no_existing(self, mock_orchestrator):
        orch, tmp = mock_orchestrator
        module = make_module(tmp)
        test_file = tmp / "test_mod.py"
        test_file.touch()
        orch.ingest.ingest_file.return_value = module
        orch.writer.generate.return_value = test_file
        orch.runner.run_file.return_value = {"passed": True, "file": "test_mod.py", "output": ""}
        orch._handle_local_change(tmp / "mod.py")
        orch.writer.generate.assert_called_once()

    def test_updates_existing_test_when_present(self, mock_orchestrator):
        orch, tmp = mock_orchestrator
        module = make_module(tmp)
        test_file = tmp / "test_mod.py"
        test_file.write_text("def test_foo(): pass\n", encoding="utf-8")
        orch.source_to_test[module.path] = test_file
        orch.ingest.ingest_file.return_value = module
        orch.differ.get_snapshot.return_value = "old source"
        orch.differ.diff.return_value = {"summary": "changed", "added": [], "removed": []}
        orch.writer.update.return_value = test_file
        orch.runner.run_file.return_value = {"passed": True, "file": "test_mod.py", "output": ""}
        orch._handle_local_change(module.path)
        orch.writer.update.assert_called_once()

    def test_skips_when_ingest_returns_none(self, mock_orchestrator):
        orch, tmp = mock_orchestrator
        orch.ingest.ingest_file.return_value = None
        orch._handle_local_change(tmp / "ghost.py")
        orch.writer.generate.assert_not_called()

    def test_snapshots_new_version_after_change(self, mock_orchestrator):
        orch, tmp = mock_orchestrator
        module = make_module(tmp)
        test_file = tmp / "test_mod.py"
        test_file.touch()
        orch.ingest.ingest_file.return_value = module
        orch.writer.generate.return_value = test_file
        orch.runner.run_file.return_value = {"passed": True, "file": "test_mod.py", "output": ""}
        orch._handle_local_change(module.path)
        orch.differ.snapshot.assert_called_once_with(module.path, module.source_code)


class TestPrintSummary:
    def test_mixed_results_counted_correctly(self, mock_orchestrator, capsys):
        orch, _ = mock_orchestrator
        results = [
            {"passed": True, "file": "test_a.py"},
            {"passed": False, "file": "test_b.py", "output": "FAILED"},
        ]
        orch._print_summary(results)
        captured = capsys.readouterr()
        assert "1 passed" in captured.out
        assert "1 failed" in captured.out

    def test_all_passed_summary(self, mock_orchestrator, capsys):
        orch, _ = mock_orchestrator
        results = [{"passed": True, "file": "test_a.py"}, {"passed": True, "file": "test_b.py"}]
        orch._print_summary(results)
        captured = capsys.readouterr()
        assert "2 passed" in captured.out
        assert "0 failed" in captured.out

    def test_empty_results(self, mock_orchestrator, capsys):
        orch, _ = mock_orchestrator
        orch._print_summary([])
        captured = capsys.readouterr()
        assert "0 passed" in captured.out
