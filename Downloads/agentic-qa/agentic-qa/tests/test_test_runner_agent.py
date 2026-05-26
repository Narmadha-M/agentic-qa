"""Tests for agents/test_runner_agent.py — TestRunnerAgent."""

import pytest
from pathlib import Path
from agents.test_runner_agent import TestRunnerAgent


@pytest.fixture
def runner(tmp_path):
    return TestRunnerAgent(output_dir=tmp_path, codebase_path=tmp_path)


def _write_test(tmp_path, name, content):
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return f


class TestRunFile:
    def test_passing_test_returns_passed_true(self, runner, tmp_path):
        f = _write_test(tmp_path, "test_pass.py", "def test_ok(): assert 1 + 1 == 2\n")
        result = runner.run_file(f)
        assert result["passed"] is True

    def test_failing_test_returns_passed_false(self, runner, tmp_path):
        f = _write_test(tmp_path, "test_fail.py", "def test_bad(): assert False\n")
        result = runner.run_file(f)
        assert result["passed"] is False

    def test_result_contains_file_name(self, runner, tmp_path):
        f = _write_test(tmp_path, "test_x.py", "def test_ok(): pass\n")
        result = runner.run_file(f)
        assert result["file"] == "test_x.py"

    def test_result_contains_returncode(self, runner, tmp_path):
        f = _write_test(tmp_path, "test_rc.py", "def test_ok(): pass\n")
        result = runner.run_file(f)
        assert "returncode" in result
        assert result["returncode"] == 0

    def test_result_contains_output(self, runner, tmp_path):
        f = _write_test(tmp_path, "test_out.py", "def test_ok(): pass\n")
        result = runner.run_file(f)
        assert "output" in result
        assert isinstance(result["output"], str)

    def test_failing_test_has_nonzero_returncode(self, runner, tmp_path):
        f = _write_test(tmp_path, "test_fail2.py", "def test_bad(): assert 1 == 2\n")
        result = runner.run_file(f)
        assert result["returncode"] != 0

    def test_syntax_error_test_returns_failed(self, runner, tmp_path):
        f = _write_test(tmp_path, "test_syntax.py", "def test_broken(\n")
        result = runner.run_file(f)
        assert result["passed"] is False

    def test_codebase_path_injected_into_pythonpath(self, tmp_path):
        codebase = tmp_path / "src"
        codebase.mkdir()
        (codebase / "mymod.py").write_text("VALUE = 42\n", encoding="utf-8")
        out_dir = tmp_path / "tests"
        out_dir.mkdir()
        test_file = out_dir / "test_import.py"
        test_file.write_text(
            "import sys, os\n"
            f"sys.path.insert(0, r'{codebase}')\n"
            "from mymod import VALUE\n"
            "def test_import(): assert VALUE == 42\n",
            encoding="utf-8",
        )
        runner = TestRunnerAgent(output_dir=out_dir, codebase_path=codebase)
        result = runner.run_file(test_file)
        assert result["passed"] is True


class TestRunAll:
    def test_run_all_empty_dir_returns_empty(self, runner, tmp_path):
        results = runner.run_all()
        assert results == []

    def test_run_all_runs_all_test_files(self, runner, tmp_path):
        _write_test(tmp_path, "test_a.py", "def test_ok(): pass\n")
        _write_test(tmp_path, "test_b.py", "def test_ok(): pass\n")
        results = runner.run_all()
        assert len(results) == 2

    def test_run_all_ignores_non_test_files(self, runner, tmp_path):
        _write_test(tmp_path, "helper.py", "x = 1\n")
        results = runner.run_all()
        assert results == []

    def test_run_all_returns_list_of_dicts(self, runner, tmp_path):
        _write_test(tmp_path, "test_c.py", "def test_ok(): pass\n")
        results = runner.run_all()
        assert isinstance(results, list)
        assert all(isinstance(r, dict) for r in results)

    def test_run_all_mixed_pass_fail(self, runner, tmp_path):
        _write_test(tmp_path, "test_pass.py", "def test_ok(): pass\n")
        _write_test(tmp_path, "test_fail.py", "def test_bad(): assert False\n")
        results = runner.run_all()
        passed = [r for r in results if r["passed"]]
        failed = [r for r in results if not r["passed"]]
        assert len(passed) == 1
        assert len(failed) == 1
