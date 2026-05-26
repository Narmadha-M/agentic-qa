"""
TestWriterAgent: calls the Claude API to generate and update pytest test files.
"""

import re
from pathlib import Path
from core.models import SourceModule
from utils.claude_client import ask_claude
from utils.logger import log


class TestWriterAgent:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    # ------------------------------------------------------------------
    # Generate tests from scratch
    # ------------------------------------------------------------------

    def generate(self, module: SourceModule) -> Path:
        prompt = self._build_generate_prompt(module)
        raw = ask_claude(prompt)
        test_code = self._extract_code(raw)
        test_file = self._test_path(module)
        test_file.write_text(test_code, encoding="utf-8")
        return test_file

    # ------------------------------------------------------------------
    # Update existing tests after a change
    # ------------------------------------------------------------------

    def update(self, module: SourceModule, test_file: Path, changes: dict) -> Path:
        existing_tests = test_file.read_text(encoding="utf-8")
        prompt = self._build_update_prompt(module, existing_tests, changes)
        raw = ask_claude(prompt)
        test_code = self._extract_code(raw)
        test_file.write_text(test_code, encoding="utf-8")
        return test_file

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_generate_prompt(self, module: SourceModule) -> str:
        funcs = ", ".join(module.functions) or "none detected"
        classes = ", ".join(module.classes) or "none detected"
        return f"""You are an expert software testing engineer. Generate a comprehensive pytest test file for the Python module below.

FILE: {module.relative_path}
FUNCTIONS: {funcs}
CLASSES: {classes}
MODULE DOCSTRING: {module.docstring or 'N/A'}

SOURCE CODE:
```python
{module.source_code}
```

Requirements:
1. Write pytest tests covering every function and class method.
2. Include edge cases, boundary values, and error/exception paths.
3. Use descriptive test function names like test_<function>_<scenario>.
4. Add a module-level docstring explaining what is being tested.
5. Import the module using the correct relative path: use `import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` then import the module by name.
6. Use pytest.raises for expected exceptions.
7. Group related tests in classes when testing class methods.
8. Output ONLY the Python code — no explanation, no markdown fences.
"""

    def _build_update_prompt(
        self, module: SourceModule, existing_tests: str, changes: dict
    ) -> str:
        return f"""You are an expert software testing engineer. Update the existing pytest test file to reflect recent changes in the source module.

FILE: {module.relative_path}
CHANGE SUMMARY: {changes['summary']}
ADDED/CHANGED: {', '.join(changes.get('added', [])) or 'none'}
REMOVED: {', '.join(changes.get('removed', [])) or 'none'}

UPDATED SOURCE CODE:
```python
{module.source_code}
```

EXISTING TESTS:
```python
{existing_tests}
```

Requirements:
1. Keep all tests that are still valid.
2. Update tests for functions/classes that changed.
3. Add new tests for newly added functions/classes.
4. Remove tests for deleted functions/classes.
5. Keep the same import structure.
6. Output ONLY the full updated Python test file — no explanation, no markdown fences.
"""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_code(self, raw: str) -> str:
        # Strip markdown fences if the model adds them despite instructions
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        return raw.strip() + "\n"

    def _test_path(self, module: SourceModule) -> Path:
        # Flatten the relative path into a test filename
        safe_name = str(module.relative_path).replace("/", "_").replace("\\", "_")
        safe_name = safe_name.replace(".py", "")
        return self.output_dir / f"test_{safe_name}.py"
