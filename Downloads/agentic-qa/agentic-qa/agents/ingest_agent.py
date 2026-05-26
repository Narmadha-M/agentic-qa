"""
IngestAgent: walks the codebase, parses Python files, and returns SourceModule objects.
"""

import ast
from pathlib import Path
from core.models import SourceModule
from utils.logger import log

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".tox", "dist", "build"}


class IngestAgent:
    def __init__(self, codebase_path: Path, extensions: list[str]):
        self.codebase_path = codebase_path
        self.extensions = extensions

    def run(self) -> list[SourceModule]:
        modules = []
        files = self._collect_files()
        for f in files:
            m = self.ingest_file(f)
            if m:
                modules.append(m)
        return modules

    def ingest_file(self, path: Path) -> SourceModule | None:
        try:
            source = path.read_text(encoding="utf-8")
        except Exception as e:
            log(f"[Ingest] Cannot read {path}: {e}")
            return None

        relative = path.relative_to(self.codebase_path)

        functions, classes, imports, docstring = [], [], [], ""

        if path.suffix == ".py":
            functions, classes, imports, docstring = self._parse_python(source)

        return SourceModule(
            path=path,
            relative_path=relative,
            source_code=source,
            language="python" if path.suffix == ".py" else path.suffix.lstrip("."),
            functions=functions,
            classes=classes,
            imports=imports,
            docstring=docstring,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collect_files(self) -> list[Path]:
        results = []
        for ext in self.extensions:
            for f in self.codebase_path.rglob(f"*{ext}"):
                if not any(skip in f.parts for skip in SKIP_DIRS):
                    results.append(f)
        return sorted(results)

    def _parse_python(self, source: str):
        functions, classes, imports = [], [], []
        docstring = ""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return functions, classes, imports, docstring

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.unparse(node))

        # Module-level docstring
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
        ):
            docstring = str(tree.body[0].value.value)[:500]

        return functions, classes, imports, docstring
