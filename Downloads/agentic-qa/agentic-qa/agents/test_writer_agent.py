"""
TestWriterAgent: calls the Claude API to generate and update pytest test files.
Self-heals truncated output: validates generated code and retries once if
the result has a SyntaxError.
"""

import ast
import re
from pathlib import Path
from core.models import SourceModule
from utils.claude_client import ask_claude
from utils.logger import log

_DJANGO_MARKERS = {"django", "from django", "import django"}


class TestWriterAgent:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    # ------------------------------------------------------------------
    # Generate tests from scratch
    # ------------------------------------------------------------------

    def generate(self, module: SourceModule) -> Path:
        test_code = self._generate_with_retry(module)
        test_file = self._test_path(module)
        test_file.write_text(test_code, encoding="utf-8")
        return test_file

    def _generate_with_retry(self, module: SourceModule) -> str:
        prompt = self._build_generate_prompt(module)
        raw = ask_claude(prompt)
        code = self._extract_code(raw)

        if not self._is_valid_python(code):
            log(f"[Writer] Generated code has SyntaxError — retrying with brevity hint for {module.relative_path}")
            prompt = self._build_generate_prompt(module, brevity_hint=True)
            raw = ask_claude(prompt)
            code = self._extract_code(raw)
            if not self._is_valid_python(code):
                log(f"[Writer] Retry still invalid — writing placeholder for {module.relative_path}")
                code = self._placeholder(module)

        return code

    # ------------------------------------------------------------------
    # Update existing tests after a change
    # ------------------------------------------------------------------

    def update(self, module: SourceModule, test_file: Path, changes: dict) -> Path:
        existing_tests = test_file.read_text(encoding="utf-8")
        prompt = self._build_update_prompt(module, existing_tests, changes)
        raw = ask_claude(prompt)
        code = self._extract_code(raw)

        if not self._is_valid_python(code):
            log(f"[Writer] Update has SyntaxError — keeping existing tests for {module.relative_path}")
            return test_file  # Don't overwrite with broken code

        test_file.write_text(code, encoding="utf-8")
        return test_file

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_generate_prompt(self, module: SourceModule, brevity_hint: bool = False) -> str:
        funcs = ", ".join(module.functions) or "none detected"
        classes = ", ".join(module.classes) or "none detected"
        is_django = self._is_django_module(module)

        django_note = ""
        if is_django:
            django_note = """
IMPORTANT — this is a Django module. Add this block at the top of the test file,
BEFORE any Django imports, so settings are configured:

    import django
    from django.conf import settings
    if not settings.configured:
        settings.configure(
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth", "ecom"],
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        )
        django.setup()
"""

        brevity_note = ""
        if brevity_hint:
            brevity_note = "\nCRITICAL: Keep the total output under 200 lines. Write fewer, focused tests — do NOT pad with repetition.\n"

        return f"""You are an expert software testing engineer. Generate a pytest test file for the Python module below.
{django_note}{brevity_note}
FILE: {module.relative_path}
FUNCTIONS: {funcs}
CLASSES: {classes}
MODULE DOCSTRING: {module.docstring or 'N/A'}

SOURCE CODE:
```python
{module.source_code}
```

Requirements:
1. Write pytest tests covering every public function and class method.
2. Include edge cases, boundary values, and error/exception paths.
3. Use descriptive names: test_<function>_<scenario>.
4. Add sys.path setup before imports: `import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`
5. Use pytest.raises for expected exceptions.
6. Group related tests in classes when testing class methods.
7. Output ONLY valid, complete Python code — no explanation, no markdown fences.
8. The file must be syntactically complete — every open parenthesis/bracket/quote MUST be closed.
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
6. Output ONLY the full, syntactically complete Python file — no explanation, no markdown fences.
"""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_code(self, raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        return raw.strip() + "\n"

    def _is_valid_python(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _is_django_module(self, module: SourceModule) -> bool:
        src_lower = module.source_code[:2000].lower()
        return any(marker in src_lower for marker in _DJANGO_MARKERS)

    def _placeholder(self, module: SourceModule) -> str:
        return (
            f'"""Placeholder: test generation failed for {module.relative_path}."""\n'
            f"# Could not generate valid tests — check source file manually.\n\n"
            f"def test_placeholder():\n"
            f"    pass\n"
        )

    def _test_path(self, module: SourceModule) -> Path:
        safe_name = str(module.relative_path).replace("/", "_").replace("\\", "_")
        safe_name = safe_name.replace(".py", "")
        return self.output_dir / f"test_{safe_name}.py"
