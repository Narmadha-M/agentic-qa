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

        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short", "--no-header"],
            capture_output=True,
            text=True,
            env=env,
        )
        passed = result.returncode == 0
        output = result.stdout + result.stderr
        return {
            "file": test_file.name,
            "passed": passed,
            "returncode": result.returncode,
            "output": output,
        }
