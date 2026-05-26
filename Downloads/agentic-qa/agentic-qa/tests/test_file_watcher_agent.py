"""Tests for agents/file_watcher_agent.py — FileWatcherAgent."""

import time
import pytest
from pathlib import Path
from agents.file_watcher_agent import FileWatcherAgent


@pytest.fixture
def watched_dir(tmp_path):
    (tmp_path / "a.py").write_text("x = 1", encoding="utf-8")
    (tmp_path / "b.py").write_text("y = 2", encoding="utf-8")
    return tmp_path


class TestInitSnapshots:
    def test_snapshots_populated_on_init(self, watched_dir):
        agent = FileWatcherAgent(watched_dir, [".py"])
        assert len(agent._snapshots) == 2

    def test_snapshot_keys_are_paths(self, watched_dir):
        agent = FileWatcherAgent(watched_dir, [".py"])
        for key in agent._snapshots:
            assert isinstance(key, Path)

    def test_empty_dir_has_no_snapshots(self, tmp_path):
        agent = FileWatcherAgent(tmp_path, [".py"])
        assert agent._snapshots == {}


class TestAllFiles:
    def test_returns_py_files(self, watched_dir):
        agent = FileWatcherAgent(watched_dir, [".py"])
        files = agent._all_files()
        assert all(f.suffix == ".py" for f in files)

    def test_skips_pycache(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "mod.py").write_text("", encoding="utf-8")
        agent = FileWatcherAgent(tmp_path, [".py"])
        files = agent._all_files()
        assert not any("__pycache__" in str(f) for f in files)

    def test_skips_venv(self, tmp_path):
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "run.py").write_text("", encoding="utf-8")
        agent = FileWatcherAgent(tmp_path, [".py"])
        files = agent._all_files()
        assert not any(".venv" in str(f) for f in files)

    def test_multi_extension(self, tmp_path):
        (tmp_path / "a.py").write_text("", encoding="utf-8")
        (tmp_path / "b.txt").write_text("", encoding="utf-8")
        agent = FileWatcherAgent(tmp_path, [".py", ".txt"])
        files = agent._all_files()
        suffixes = {f.suffix for f in files}
        assert ".py" in suffixes
        assert ".txt" in suffixes


class TestCheck:
    def test_no_change_returns_empty(self, watched_dir):
        agent = FileWatcherAgent(watched_dir, [".py"])
        changed = agent._check()
        assert changed == []

    def test_modified_file_detected(self, watched_dir):
        agent = FileWatcherAgent(watched_dir, [".py"])
        time.sleep(0.05)
        (watched_dir / "a.py").write_text("x = 99", encoding="utf-8")
        changed = agent._check()
        assert watched_dir / "a.py" in changed

    def test_new_file_detected(self, watched_dir):
        agent = FileWatcherAgent(watched_dir, [".py"])
        (watched_dir / "new.py").write_text("z = 3", encoding="utf-8")
        changed = agent._check()
        assert watched_dir / "new.py" in changed

    def test_deleted_file_removed_from_snapshots(self, watched_dir):
        agent = FileWatcherAgent(watched_dir, [".py"])
        (watched_dir / "a.py").unlink()
        agent._check()
        assert watched_dir / "a.py" not in agent._snapshots

    def test_second_check_after_modification_returns_empty(self, watched_dir):
        agent = FileWatcherAgent(watched_dir, [".py"])
        time.sleep(0.05)
        (watched_dir / "a.py").write_text("x = 99", encoding="utf-8")
        agent._check()  # consume the change
        changed = agent._check()
        assert watched_dir / "a.py" not in changed
