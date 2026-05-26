"""Tests for agents/ingest_agent.py — IngestAgent."""

import pytest
import tempfile
import os
from pathlib import Path
from agents.ingest_agent import IngestAgent, SKIP_DIRS
from core.models import SourceModule


@pytest.fixture
def tmp_codebase(tmp_path):
    """Return a temp dir with a simple Python file."""
    src = tmp_path / "hello.py"
    src.write_text('"""Module doc."""\nimport os\n\ndef greet(name): pass\n\nclass Foo: pass\n', encoding="utf-8")
    return tmp_path


class TestCollectFiles:
    def test_finds_py_files(self, tmp_codebase):
        agent = IngestAgent(tmp_codebase, [".py"])
        files = agent._collect_files()
        assert any(f.name == "hello.py" for f in files)

    def test_respects_extensions_filter(self, tmp_path):
        (tmp_path / "a.py").write_text("", encoding="utf-8")
        (tmp_path / "b.txt").write_text("", encoding="utf-8")
        agent = IngestAgent(tmp_path, [".txt"])
        files = agent._collect_files()
        assert all(f.suffix == ".txt" for f in files)
        assert not any(f.suffix == ".py" for f in files)

    def test_skips_pycache_dir(self, tmp_path):
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "mod.cpython-312.py").write_text("", encoding="utf-8")
        agent = IngestAgent(tmp_path, [".py"])
        files = agent._collect_files()
        assert not any("__pycache__" in str(f) for f in files)

    def test_skips_venv_dir(self, tmp_path):
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        (venv_dir / "script.py").write_text("", encoding="utf-8")
        agent = IngestAgent(tmp_path, [".py"])
        files = agent._collect_files()
        assert not any(".venv" in str(f) for f in files)

    def test_skips_git_dir(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "hooks.py").write_text("", encoding="utf-8")
        agent = IngestAgent(tmp_path, [".py"])
        files = agent._collect_files()
        assert not any(".git" in str(f) for f in files)

    def test_empty_codebase_returns_empty(self, tmp_path):
        agent = IngestAgent(tmp_path, [".py"])
        assert agent._collect_files() == []

    def test_result_is_sorted(self, tmp_path):
        for name in ["z.py", "a.py", "m.py"]:
            (tmp_path / name).write_text("", encoding="utf-8")
        agent = IngestAgent(tmp_path, [".py"])
        files = agent._collect_files()
        names = [f.name for f in files]
        assert names == sorted(names)


class TestParsePython:
    def test_extracts_function_names(self):
        src = "def foo(): pass\ndef bar(): pass\n"
        agent = IngestAgent(Path("."), [".py"])
        funcs, classes, imports, doc = agent._parse_python(src)
        assert "foo" in funcs
        assert "bar" in funcs

    def test_extracts_class_names(self):
        src = "class Foo: pass\nclass Bar: pass\n"
        agent = IngestAgent(Path("."), [".py"])
        funcs, classes, imports, doc = agent._parse_python(src)
        assert "Foo" in classes
        assert "Bar" in classes

    def test_extracts_import_lines(self):
        src = "import os\nfrom pathlib import Path\n"
        agent = IngestAgent(Path("."), [".py"])
        funcs, classes, imports, doc = agent._parse_python(src)
        assert any("import os" in i for i in imports)

    def test_extracts_module_docstring(self):
        src = '"""My module docstring."""\n\ndef foo(): pass\n'
        agent = IngestAgent(Path("."), [".py"])
        funcs, classes, imports, doc = agent._parse_python(src)
        assert "My module docstring." in doc

    def test_no_docstring_returns_empty(self):
        src = "x = 1\n"
        agent = IngestAgent(Path("."), [".py"])
        funcs, classes, imports, doc = agent._parse_python(src)
        assert doc == ""

    def test_syntax_error_returns_empty_lists(self):
        src = "def foo(\n"  # broken syntax
        agent = IngestAgent(Path("."), [".py"])
        funcs, classes, imports, doc = agent._parse_python(src)
        assert funcs == []
        assert classes == []
        assert imports == []

    def test_nested_functions_detected(self):
        src = "def outer():\n    def inner(): pass\n"
        agent = IngestAgent(Path("."), [".py"])
        funcs, classes, imports, doc = agent._parse_python(src)
        assert "outer" in funcs
        assert "inner" in funcs

    def test_async_functions_detected(self):
        src = "async def fetch(): pass\n"
        agent = IngestAgent(Path("."), [".py"])
        funcs, classes, imports, doc = agent._parse_python(src)
        assert "fetch" in funcs

    def test_docstring_truncated_at_500_chars(self):
        long_doc = "x" * 600
        src = f'"""{long_doc}"""\n'
        agent = IngestAgent(Path("."), [".py"])
        funcs, classes, imports, doc = agent._parse_python(src)
        assert len(doc) <= 500


class TestIngestFile:
    def test_returns_source_module(self, tmp_codebase):
        agent = IngestAgent(tmp_codebase, [".py"])
        result = agent.ingest_file(tmp_codebase / "hello.py")
        assert isinstance(result, SourceModule)

    def test_source_module_has_correct_path(self, tmp_codebase):
        agent = IngestAgent(tmp_codebase, [".py"])
        result = agent.ingest_file(tmp_codebase / "hello.py")
        assert result.path == tmp_codebase / "hello.py"

    def test_source_module_has_relative_path(self, tmp_codebase):
        agent = IngestAgent(tmp_codebase, [".py"])
        result = agent.ingest_file(tmp_codebase / "hello.py")
        assert result.relative_path == Path("hello.py")

    def test_source_module_populates_functions(self, tmp_codebase):
        agent = IngestAgent(tmp_codebase, [".py"])
        result = agent.ingest_file(tmp_codebase / "hello.py")
        assert "greet" in result.functions

    def test_source_module_populates_classes(self, tmp_codebase):
        agent = IngestAgent(tmp_codebase, [".py"])
        result = agent.ingest_file(tmp_codebase / "hello.py")
        assert "Foo" in result.classes

    def test_nonexistent_file_returns_none(self, tmp_path):
        agent = IngestAgent(tmp_path, [".py"])
        result = agent.ingest_file(tmp_path / "ghost.py")
        assert result is None

    def test_non_python_file_has_empty_functions(self, tmp_path):
        f = tmp_path / "config.txt"
        f.write_text("key=value\n", encoding="utf-8")
        agent = IngestAgent(tmp_path, [".txt"])
        result = agent.ingest_file(f)
        assert result is not None
        assert result.functions == []

    def test_language_set_from_extension(self, tmp_path):
        f = tmp_path / "app.txt"
        f.write_text("hello", encoding="utf-8")
        agent = IngestAgent(tmp_path, [".txt"])
        result = agent.ingest_file(f)
        assert result.language == "txt"


class TestIngestRun:
    def test_run_returns_list_of_modules(self, tmp_codebase):
        agent = IngestAgent(tmp_codebase, [".py"])
        modules = agent.run()
        assert isinstance(modules, list)
        assert len(modules) >= 1
        assert all(isinstance(m, SourceModule) for m in modules)

    def test_run_empty_codebase_returns_empty(self, tmp_path):
        agent = IngestAgent(tmp_path, [".py"])
        assert agent.run() == []

    def test_run_skips_unreadable_logs_and_continues(self, tmp_path):
        (tmp_path / "good.py").write_text("def f(): pass", encoding="utf-8")
        agent = IngestAgent(tmp_path, [".py"])
        modules = agent.run()
        assert len(modules) == 1
