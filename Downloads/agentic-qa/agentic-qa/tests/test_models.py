"""Tests for core/models.py — SourceModule dataclass."""

import pytest
from pathlib import Path
from core.models import SourceModule


class TestSourceModuleDefaults:
    def test_default_language_is_python(self):
        sm = SourceModule(path=Path("/a/b.py"), relative_path=Path("b.py"), source_code="x=1")
        assert sm.language == "python"

    def test_default_functions_is_empty_list(self):
        sm = SourceModule(path=Path("/a/b.py"), relative_path=Path("b.py"), source_code="")
        assert sm.functions == []

    def test_default_classes_is_empty_list(self):
        sm = SourceModule(path=Path("/a/b.py"), relative_path=Path("b.py"), source_code="")
        assert sm.classes == []

    def test_default_imports_is_empty_list(self):
        sm = SourceModule(path=Path("/a/b.py"), relative_path=Path("b.py"), source_code="")
        assert sm.imports == []

    def test_default_docstring_is_empty_string(self):
        sm = SourceModule(path=Path("/a/b.py"), relative_path=Path("b.py"), source_code="")
        assert sm.docstring == ""

    def test_mutable_defaults_not_shared(self):
        sm1 = SourceModule(path=Path("/a/b.py"), relative_path=Path("b.py"), source_code="")
        sm2 = SourceModule(path=Path("/a/c.py"), relative_path=Path("c.py"), source_code="")
        sm1.functions.append("foo")
        assert sm2.functions == []


class TestSourceModuleFields:
    def test_all_fields_assigned(self):
        p = Path("/a/b.py")
        rp = Path("b.py")
        sm = SourceModule(
            path=p,
            relative_path=rp,
            source_code="def foo(): pass",
            language="python",
            functions=["foo"],
            classes=["Bar"],
            imports=["import os"],
            docstring="A module.",
        )
        assert sm.path == p
        assert sm.relative_path == rp
        assert sm.source_code == "def foo(): pass"
        assert sm.language == "python"
        assert sm.functions == ["foo"]
        assert sm.classes == ["Bar"]
        assert sm.imports == ["import os"]
        assert sm.docstring == "A module."

    def test_custom_language(self):
        sm = SourceModule(
            path=Path("/a/b.ts"),
            relative_path=Path("b.ts"),
            source_code="",
            language="typescript",
        )
        assert sm.language == "typescript"

    def test_path_is_pathlib_path(self):
        sm = SourceModule(path=Path("/x/y.py"), relative_path=Path("y.py"), source_code="")
        assert isinstance(sm.path, Path)
        assert isinstance(sm.relative_path, Path)
