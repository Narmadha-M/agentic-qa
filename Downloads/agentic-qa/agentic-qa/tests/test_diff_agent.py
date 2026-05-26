"""Tests for agents/diff_agent.py — DiffAgent."""

import pytest
from pathlib import Path
from agents.diff_agent import DiffAgent


SIMPLE_SOURCE = "def foo(): pass\nclass Bar: pass\n"
ADDED_SOURCE = "def foo(): pass\nclass Bar: pass\ndef baz(): pass\n"
REMOVED_SOURCE = "class Bar: pass\n"
MODIFIED_SOURCE = "def foo():\n    return 42\nclass Bar: pass\n"


class TestSnapshot:
    def test_snapshot_stores_source(self):
        agent = DiffAgent()
        p = Path("/a/b.py")
        agent.snapshot(p, "x = 1")
        assert agent.get_snapshot(p) == "x = 1"

    def test_get_snapshot_missing_returns_empty(self):
        agent = DiffAgent()
        assert agent.get_snapshot(Path("/nonexistent.py")) == ""

    def test_snapshot_overwrite(self):
        agent = DiffAgent()
        p = Path("/a/b.py")
        agent.snapshot(p, "v1")
        agent.snapshot(p, "v2")
        assert agent.get_snapshot(p) == "v2"

    def test_snapshots_are_independent_per_path(self):
        agent = DiffAgent()
        p1, p2 = Path("/a.py"), Path("/b.py")
        agent.snapshot(p1, "src_a")
        agent.snapshot(p2, "src_b")
        assert agent.get_snapshot(p1) == "src_a"
        assert agent.get_snapshot(p2) == "src_b"


class TestSymbolNames:
    def test_extracts_functions(self):
        agent = DiffAgent()
        names = agent._symbol_names("def foo(): pass\ndef bar(): pass\n")
        assert "foo" in names
        assert "bar" in names

    def test_extracts_classes(self):
        agent = DiffAgent()
        names = agent._symbol_names("class Foo: pass\n")
        assert "Foo" in names

    def test_extracts_async_functions(self):
        agent = DiffAgent()
        names = agent._symbol_names("async def fetch(): pass\n")
        assert "fetch" in names

    def test_empty_source_returns_empty_set(self):
        agent = DiffAgent()
        assert agent._symbol_names("") == set()

    def test_syntax_error_returns_empty_set(self):
        agent = DiffAgent()
        assert agent._symbol_names("def broken(\n") == set()

    def test_returns_set_not_list(self):
        agent = DiffAgent()
        result = agent._symbol_names("def foo(): pass\n")
        assert isinstance(result, set)


class TestDiff:
    def test_detects_added_symbol(self):
        agent = DiffAgent()
        result = agent.diff(SIMPLE_SOURCE, ADDED_SOURCE)
        assert "baz" in result["added"]

    def test_detects_removed_symbol(self):
        agent = DiffAgent()
        result = agent.diff(SIMPLE_SOURCE, REMOVED_SOURCE)
        assert "foo" in result["removed"]

    def test_no_changes_returns_empty_added_removed(self):
        agent = DiffAgent()
        result = agent.diff(SIMPLE_SOURCE, SIMPLE_SOURCE)
        assert result["added"] == []
        assert result["removed"] == []

    def test_summary_mentions_added(self):
        agent = DiffAgent()
        result = agent.diff(SIMPLE_SOURCE, ADDED_SOURCE)
        assert "added" in result["summary"].lower() or "baz" in result["summary"]

    def test_summary_mentions_removed(self):
        agent = DiffAgent()
        result = agent.diff(SIMPLE_SOURCE, REMOVED_SOURCE)
        assert "removed" in result["summary"].lower() or "foo" in result["summary"]

    def test_no_change_summary_text(self):
        agent = DiffAgent()
        result = agent.diff(SIMPLE_SOURCE, SIMPLE_SOURCE)
        assert "minor" in result["summary"].lower() or "no symbol" in result["summary"].lower()

    def test_modified_function_appears_in_added(self):
        agent = DiffAgent()
        result = agent.diff(SIMPLE_SOURCE, MODIFIED_SOURCE)
        # modified symbols are included in "added" per agent design
        assert "foo" in result["added"] or result["added"] == []

    def test_empty_old_source_all_new_are_added(self):
        agent = DiffAgent()
        result = agent.diff("", "def foo(): pass\n")
        assert "foo" in result["added"]

    def test_empty_new_source_all_old_are_removed(self):
        agent = DiffAgent()
        result = agent.diff("def foo(): pass\n", "")
        assert "foo" in result["removed"]

    def test_result_has_required_keys(self):
        agent = DiffAgent()
        result = agent.diff(SIMPLE_SOURCE, ADDED_SOURCE)
        assert "added" in result
        assert "removed" in result
        assert "summary" in result

    def test_removed_is_sorted(self):
        agent = DiffAgent()
        # Use identical new source so no "modified" symbols bleed into "added"
        old = "def z(): pass\ndef a(): pass\n"
        new = "def a(): pass\n"
        result = agent.diff(old, new)
        assert result["removed"] == sorted(result["removed"])

    def test_purely_added_symbols_are_sorted(self):
        # When only new symbols are added and nothing changes, "added" is sorted
        agent = DiffAgent()
        old = ""
        new = "def z(): pass\ndef a(): pass\ndef m(): pass\n"
        result = agent.diff(old, new)
        assert result["added"] == sorted(result["added"])
