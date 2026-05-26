"""
Agentic QA System
-----------------
Phase 1: Ingest codebase → generate tests → run tests → produce HTML report
Phase 2: Watch for file changes → update tests → rerun (local paths only)

Usage:
  python main.py                          # reads GITHUB_REPO_URL from repo.env
  python main.py https://github.com/...  # explicit URL
  python main.py path/to/local/codebase  # local folder
"""

import argparse
import shutil
import subprocess
import sys
import webbrowser
import tempfile
from pathlib import Path
from core.orchestrator import Orchestrator

# Location of the user-editable config file
_REPO_ENV = Path(__file__).parent / "repo.env"


def _is_github_url(value: str) -> bool:
    return value.startswith("https://github.com") or value.startswith("git@github.com")


def _clone_repo(url: str) -> Path:
    tmp = tempfile.mkdtemp(prefix="agentic-qa-")
    print(f"[Ingest] Cloning {url} → {tmp}")
    result = subprocess.run(
        ["git", "clone", "--depth", "1", url, tmp],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"[ERROR] git clone failed:\n{result.stderr}")
        sys.exit(1)
    return Path(tmp)


def _read_repo_env() -> str:
    """Read GITHUB_REPO_URL from repo.env; exit with helpful message if missing."""
    if not _REPO_ENV.exists():
        print(
            f"[ERROR] No codebase path given and {_REPO_ENV.name} not found.\n"
            f"Create {_REPO_ENV} with:\n  GITHUB_REPO_URL=https://github.com/owner/repo"
        )
        sys.exit(1)

    for line in _REPO_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "GITHUB_REPO_URL":
            url = value.strip()
            if url:
                return url

    print(
        f"[ERROR] GITHUB_REPO_URL not set in {_REPO_ENV.name}.\n"
        f"Edit {_REPO_ENV.name} and set:  GITHUB_REPO_URL=https://github.com/owner/repo"
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Agentic QA — auto-generate and auto-update tests for your codebase"
    )
    parser.add_argument(
        "codebase_path",
        nargs="?",
        default=None,
        help=(
            "Local folder path OR GitHub URL (https://github.com/owner/repo). "
            "If omitted, GITHUB_REPO_URL is read from repo.env."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="tests_output",
        help="Directory where generated tests are saved (default: tests_output)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        default=True,
        help="After initial run, keep watching for file changes (default: true)",
    )
    parser.add_argument(
        "--no-watch",
        action="store_false",
        dest="watch",
        help="Run once and exit without watching",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".py"],
        help="File extensions to scan (default: .py)",
    )
    args = parser.parse_args()

    # Resolve codebase path
    raw_path = args.codebase_path or _read_repo_env()

    cloned_tmp = None
    if _is_github_url(raw_path):
        codebase = _clone_repo(raw_path)
        cloned_tmp = codebase
    else:
        codebase = Path(raw_path).resolve()
        if not codebase.exists():
            print(f"[ERROR] Path not found: {codebase}")
            sys.exit(1)

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    orchestrator = Orchestrator(
        codebase_path=codebase,
        output_dir=output_dir,
        extensions=args.extensions,
        repo_url=raw_path,
    )

    try:
        # Phase 1 — ingest, generate, run, report
        orchestrator.run_initial()

        report = output_dir / "report.html"
        if report.exists():
            print(f"\n[Report] Opening {report}")
            webbrowser.open(report.as_uri())

        # Phase 2 — watch loop (skip for cloned repos; files won't change locally)
        if args.watch and cloned_tmp is None:
            orchestrator.start_watch()
    finally:
        if cloned_tmp:
            shutil.rmtree(cloned_tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
