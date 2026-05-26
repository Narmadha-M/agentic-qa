"""
TestRunnerAgent: executes pytest on generated test files and collects results.
"""

import os
import subprocess
import sys
from pathlib import Path
from utils.logger import log


class TestRunnerAgent:
    def __init__(self, output_dir: Path, codebase_path: Path = None):
        self.output_dir = output_dir
        self.codebase_path = codebase_path

    def run_all(self) -> list[dict]:
        test_files = sorted(self.output_dir.glob("test_*.py"))
        if not test_files:
            log("[Runner] No test files found.")
            return []
        results = [self.run_file(f) for f in test_files]
        return results

    def run_file(self, test_file: Path) -> dict:
        env = os.environ.copy()
        if self.codebase_path:
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = str(self.codebase_path) + (os.pathsep + existing if existing else "")

        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest", str(test_file),
                    "-v", "--tb=short", "--no-header",
                    "--timeout=30",   # per-test timeout (requires pytest-timeout)
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=120,          # per-file hard kill after 2 minutes
            )
            passed = result.returncode == 0
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            passed = False
            output = f"[Runner] TIMEOUT: {test_file.name} exceeded 120s — killed.\n"
            log(f"[Runner] TIMEOUT: {test_file.name}")

        return {
            "file": test_file.name,
            "passed": passed,
            "returncode": 0 if passed else 1,
            "output": output,
        }
