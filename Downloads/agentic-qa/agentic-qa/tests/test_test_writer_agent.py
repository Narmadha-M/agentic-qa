"""Tests for agents/test_writer_agent.py — TestWriterAgent."""

import pytest
from pathlib import Path
from unittest.mock import patch
from core.models import SourceModule
from agents.test_writer_agent import TestWriterAgent


def make_module(tmp_path, name="mod.py", source="def foo(): pass\n", funcs=None, classes=None):
    return SourceModule(
        path=tmp_path / name,
        relative_path=Path(name),
        source_code=source,
        functions=funcs or ["foo"],
        classes=classes or [],
        docstring="",
    )


class TestExtractCode:
    def test_returns_plain_code_unchanged(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        code = "import pytest\n\ndef test_foo(): pass\n"
        assert agent._extract_code(code).strip() == code.strip()

    def test_strips_python_markdown_fence(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        fenced = "```python\nimport pytest\n\ndef test_foo(): pass\n```"
        result = agent._extract_code(fenced)
        assert "```" not in result
        assert "def test_foo(): pass" in result

    def test_strips_plain_markdown_fence(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        fenced = "```\ndef test_foo(): pass\n```"
        result = agent._extract_code(fenced)
        assert "```" not in result

    def test_adds_trailing_newline(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        result = agent._extract_code("def test_foo(): pass")
        assert result.endswith("\n")

    def test_strips_leading_whitespace(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        result = agent._extract_code("   def test_foo(): pass   ")
        assert not result.startswith(" ")


class TestTestPath:
    def test_generates_test_prefix(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path, name="bank.py")
        result = agent._test_path(module)
        assert result.name.startswith("test_")

    def test_output_in_output_dir(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path, name="bank.py")
        result = agent._test_path(module)
        assert result.parent == tmp_path

    def test_slashes_replaced_in_nested_path(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = SourceModule(
            path=tmp_path / "sub" / "mod.py",
            relative_path=Path("sub/mod.py"),
            source_code="",
        )
        result = agent._test_path(module)
        assert "/" not in result.name
        assert "\\" not in result.name

    def test_py_extension_replaced(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path, name="bank.py")
        result = agent._test_path(module)
        assert result.suffix == ".py"
        assert "bank.py" not in result.stem  # .py stripped from stem


class TestGenerate:
    def test_generate_writes_file(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path)
        with patch("agents.test_writer_agent.ask_claude", return_value="def test_foo(): pass\n"):
            result = agent.generate(module)
        assert result.exists()

    def test_generate_returns_path(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path)
        with patch("agents.test_writer_agent.ask_claude", return_value="def test_foo(): pass\n"):
            result = agent.generate(module)
        assert isinstance(result, Path)

    def test_generate_file_contains_response(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path)
        with patch("agents.test_writer_agent.ask_claude", return_value="def test_foo(): pass\n"):
            result = agent.generate(module)
        assert "test_foo" in result.read_text(encoding="utf-8")

    def test_generate_strip_fences_from_response(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path)
        with patch("agents.test_writer_agent.ask_claude", return_value="```python\ndef test_foo(): pass\n```"):
            result = agent.generate(module)
        assert "```" not in result.read_text(encoding="utf-8")


class TestUpdate:
    def test_update_rewrites_file(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path)
        test_file = tmp_path / "test_mod.py"
        test_file.write_text("def test_old(): pass\n", encoding="utf-8")
        changes = {"summary": "added baz", "added": ["baz"], "removed": []}
        with patch("agents.test_writer_agent.ask_claude", return_value="def test_new(): pass\n"):
            result = agent.update(module, test_file, changes)
        assert "test_new" in result.read_text(encoding="utf-8")

    def test_update_returns_same_path(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path)
        test_file = tmp_path / "test_mod.py"
        test_file.write_text("def test_old(): pass\n", encoding="utf-8")
        changes = {"summary": "minor", "added": [], "removed": []}
        with patch("agents.test_writer_agent.ask_claude", return_value="def test_old(): pass\n"):
            result = agent.update(module, test_file, changes)
        assert result == test_file


class TestBuildGeneratePrompt:
    def test_prompt_includes_source_code(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path, source="def foo(): return 42\n")
        prompt = agent._build_generate_prompt(module)
        assert "def foo(): return 42" in prompt

    def test_prompt_includes_function_names(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path, funcs=["deposit", "withdraw"])
        prompt = agent._build_generate_prompt(module)
        assert "deposit" in prompt
        assert "withdraw" in prompt

    def test_prompt_includes_file_path(self, tmp_path):
        agent = TestWriterAgent(tmp_path)
        module = make_module(tmp_path, name="bank.py")
        prompt = agent._build_generate_prompt(module)
        assert "bank.py" in prompt
