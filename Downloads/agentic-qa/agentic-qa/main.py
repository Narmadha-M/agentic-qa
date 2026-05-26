"""
Agentic QA System
=================

TWO SCENARIOS
─────────────
Scenario A — One-shot  (default):
    Clone repo → generate tests → run → HTML report → exit.
    Command:  python main.py --no-watch

Scenario B — Continuous repo watch  (default when --watch is active):
    Scenario A first, then poll the remote GitHub repo every N seconds.
    When a new commit is pushed: pull changes, update only affected
    test files, rerun, refresh HTML report — automatically.
    Command:  python main.py  (or python main.py --watch)
    Stop with Ctrl+C.

CONFIG
──────
Edit  repo.env  to set the target repository (no CLI arg needed):

    GITHUB_REPO_URL=https://github.com/owner/repo
    GITHUB_BRANCH=main          # optional; defaults to repo default branch
    POLL_INTERVAL=60            # optional; seconds between remote checks

Or pass the URL directly:
    python main.py https://github.com/owner/repo
    python main.py path/to/local/codebase  --no-watch

RESULTS
───────
HTML report:  tests_output/report.html  (opens automatically in browser)
Console log:  printed to terminal in real time
"""

import argparse
import shutil
import subprocess
import sys
import webbrowser
import tempfile
from pathlib import Path
from core.orchestrator import Orchestrator

_REPO_ENV = Path(__file__).parent / "repo.env"


# ──────────────── helpers ────────────────

def _is_github_url(value: str) -> bool:
    return value.startswith("https://github.com") or value.startswith("git@github.com")


def _clone_repo(url: str, branch: str = "") -> Path:
    tmp = tempfile.mkdtemp(prefix="agentic-qa-")
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
        print(f"[Ingest] Cloning {url}  (branch: {branch}) → {tmp}")
    else:
        print(f"[Ingest] Cloning {url} → {tmp}")
    cmd += [url, tmp]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"[ERROR] git clone failed:\n{result.stderr}")
        sys.exit(1)
    return Path(tmp)


def _read_repo_env() -> tuple[str, str, int]:
    """Parse repo.env and return (url, branch, poll_interval)."""
    if not _REPO_ENV.exists():
        print(
            f"[ERROR] No codebase path given and {_REPO_ENV.name} not found.\n"
            f"Create {_REPO_ENV} with:\n  GITHUB_REPO_URL=https://github.com/owner/repo"
        )
        sys.exit(1)

    url, branch, poll_interval = "", "", 60
    for line in _REPO_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key == "GITHUB_REPO_URL":
            url = value
        elif key == "GITHUB_BRANCH":
            branch = value
        elif key == "POLL_INTERVAL":
            try:
                poll_interval = int(value)
            except ValueError:
                pass

    if not url:
        print(
            f"[ERROR] GITHUB_REPO_URL not set in {_REPO_ENV.name}.\n"
            f"Edit {_REPO_ENV.name} and set:  GITHUB_REPO_URL=https://github.com/owner/repo"
        )
        sys.exit(1)
    return url, branch, poll_interval


# ──────────────── entry point ────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Agentic QA — Scenario A: generate + run tests once.  "
            "Scenario B: also watch repo for changes and auto-update tests."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "codebase_path",
        nargs="?",
        default=None,
        help=(
            "GitHub URL or local folder. "
            "Omit to read GITHUB_REPO_URL from repo.env."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="tests_output",
        help="Where generated tests and report.html are saved (default: tests_output)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        default=True,
        help="Scenario B: after initial run, keep polling repo for changes (default: on)",
    )
    parser.add_argument(
        "--no-watch",
        action="store_false",
        dest="watch",
        help="Scenario A only: generate + run once, then exit",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=None,
        help="Seconds between remote-repo checks in watch mode (default: 60 or from repo.env)",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".py"],
        help="File extensions to scan (default: .py)",
    )
    args = parser.parse_args()

    # ── 1. resolve target codebase ──────────────────────────────────
    branch = ""
    poll_interval = 60

    if args.codebase_path:
        raw_path = args.codebase_path
    else:
        raw_path, branch, poll_interval = _read_repo_env()

    # CLI --poll-interval overrides repo.env
    if args.poll_interval is not None:
        poll_interval = args.poll_interval

    cloned_tmp: Path | None = None
    if _is_github_url(raw_path):
        codebase = _clone_repo(raw_path, branch=branch)
        cloned_tmp = codebase
    else:
        codebase = Path(raw_path).resolve()
        if not codebase.exists():
            print(f"[ERROR] Path not found: {codebase}")
            sys.exit(1)

    # ── 2. set up output directory ──────────────────────────────────
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    orchestrator = Orchestrator(
        codebase_path=codebase,
        output_dir=output_dir,
        extensions=args.extensions,
        repo_url=raw_path,
    )

    try:
        # ── Scenario A: generate + run + report ─────────────────────
        orchestrator.run_initial()

        report = output_dir / "report.html"
        if report.exists():
            print(f"\n[Report] Opening {report}")
            webbrowser.open(report.as_uri())

        # ── Scenario B: watch for remote changes ─────────────────────
        if args.watch:
            if cloned_tmp is not None:
                # GitHub URL → poll remote repo for new commits
                orchestrator.start_repo_watch(
                    initial_clone=cloned_tmp,
                    repo_url=raw_path,
                    branch=branch,
                    poll_interval=poll_interval,
                )
            else:
                # Local path → watch filesystem directly
                orchestrator.start_watch()

    finally:
        # Clean up the INITIAL clone; RepoWatcherAgent cleans its own clones
        if cloned_tmp:
            shutil.rmtree(cloned_tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
