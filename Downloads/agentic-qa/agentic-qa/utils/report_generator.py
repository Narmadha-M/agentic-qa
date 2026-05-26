"""
Generates a self-contained HTML test report from pytest results.
Called by Orchestrator after Phase 1 runs finish.
"""

import re
import datetime
from collections import defaultdict
from pathlib import Path


def _parse_tests(output: str) -> list[dict]:
    """Extract individual test results from pytest -v output."""
    results = []
    pattern = re.compile(
        r'^(\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED)', re.MULTILINE
    )
    for m in pattern.finditer(output):
        results.append({"id": m.group(1), "status": m.group(2)})
    return results


def _parse_failure_details(output: str) -> dict:
    """Return {test_id: error_text} extracted from the FAILURES section."""
    details = {}
    # Each failure block is surrounded by lines of underscores
    blocks = re.split(r'\n_{5,}[^\n]*_{5,}\n', output)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # The last FAILED line in the block identifies the test
        for line in reversed(block.splitlines()):
            m = re.match(r'FAILED\s+(\S+::\S+)', line.strip())
            if m:
                details[m.group(1)] = block
                break
    return details


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate(results: list[dict], output_path: Path, repo_url: str = "") -> Path:
    """
    Build report.html from a list of TestRunnerAgent result dicts.

    Each dict: {"file": str, "passed": bool, "returncode": int, "output": str}
    Returns the path of the written HTML file.
    """
    # Collect all tests grouped by source file
    by_file: dict[str, list[dict]] = defaultdict(list)
    failure_details: dict[str, str] = {}

    for r in results:
        output = r.get("output", "")
        tests = _parse_tests(output)
        for t in tests:
            t["file"] = r["file"]
            by_file[r["file"]].append(t)
        failure_details.update(_parse_failure_details(output))

    all_tests = [t for ts in by_file.values() for t in ts]
    total = len(all_tests)
    passed = sum(1 for t in all_tests if t["status"] == "PASSED")
    failed = total - passed
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------ #
    # Build per-file card HTML
    # ------------------------------------------------------------------ #
    file_cards_html = ""
    for fname, tests in by_file.items():
        f_pass = sum(1 for t in tests if t["status"] == "PASSED")
        f_total = len(tests)
        card_cls = "all-pass" if f_pass == f_total else "has-fail"

        rows_html = ""
        for t in tests:
            short_id = t["id"].split("::", 1)[-1] if "::" in t["id"] else t["id"]
            status = t["status"]
            row_cls = "pass" if status == "PASSED" else ("skip" if status == "SKIPPED" else "fail")
            icon = "✓" if status == "PASSED" else ("–" if status == "SKIPPED" else "✗")

            # Failure detail block (inline pre)
            detail_html = ""
            if status not in ("PASSED", "SKIPPED") and t["id"] in failure_details:
                detail_html = (
                    f'<tr class="detail-row">'
                    f'<td colspan="2"><pre class="error-pre">{_escape(failure_details[t["id"]])}</pre></td>'
                    f'</tr>'
                )

            rows_html += (
                f'<tr class="{row_cls}">'
                f'<td><span class="icon">{icon}</span>{_escape(short_id)}</td>'
                f'<td class="status-cell">{status}</td>'
                f'</tr>'
                f'{detail_html}'
            )

        file_cards_html += f"""
        <div class="file-card {card_cls}">
          <div class="file-header">
            <span class="file-name">{_escape(fname)}</span>
            <span class="file-badge">{f_pass}/{f_total} passed</span>
          </div>
          <table class="test-table">
            <thead><tr><th>Test</th><th>Status</th></tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>"""

    if not file_cards_html:
        file_cards_html = '<p class="no-tests">No tests were generated or run.</p>'

    repo_line = (
        f'<a class="repo-link" href="{_escape(repo_url)}" target="_blank">{_escape(repo_url)}</a> &nbsp;|&nbsp;'
        if repo_url else ""
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agentic QA — Test Report</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f0f4f8; color: #1a202c; }}

    /* ---- Header ---- */
    header {{ background: #1a202c; color: #fff; padding: 22px 40px; }}
    header h1 {{ font-size: 1.5rem; font-weight: 700; letter-spacing: -0.3px; }}
    header .meta {{ font-size: 0.82rem; color: #a0aec0; margin-top: 5px; }}
    .repo-link {{ color: #63b3ed; text-decoration: none; }}
    .repo-link:hover {{ text-decoration: underline; }}

    /* ---- Summary bar ---- */
    .summary {{ display: flex; gap: 14px; padding: 22px 40px; flex-wrap: wrap; }}
    .badge {{ padding: 14px 26px; border-radius: 10px; font-size: 1.2rem; font-weight: 700;
              display: flex; align-items: center; gap: 8px; }}
    .badge.total {{ background: #ebf4ff; color: #2b6cb0; }}
    .badge.pass  {{ background: #f0fff4; color: #276749; }}
    .badge.fail  {{ background: #fff5f5; color: #9b2c2c; }}

    /* ---- File cards ---- */
    .container {{ padding: 0 40px 48px; }}
    .file-card {{ background: #fff; border-radius: 10px; margin-bottom: 18px;
                  overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }}
    .file-header {{ display: flex; justify-content: space-between; align-items: center;
                    padding: 13px 20px; background: #f7fafc;
                    border-bottom: 1px solid #e2e8f0; }}
    .file-card.has-fail  .file-header {{ border-left: 4px solid #fc8181; }}
    .file-card.all-pass  .file-header {{ border-left: 4px solid #68d391; }}
    .file-name  {{ font-weight: 600; font-size: 0.92rem; color: #2d3748; }}
    .file-badge {{ font-size: 0.8rem; color: #718096;
                  background: #edf2f7; padding: 2px 10px; border-radius: 20px; }}

    /* ---- Test table ---- */
    .test-table {{ width: 100%; border-collapse: collapse; font-size: 0.86rem; }}
    .test-table thead th {{ background: #f1f5f9; padding: 7px 16px;
                            text-align: left; font-weight: 600; color: #4a5568;
                            border-bottom: 1px solid #e2e8f0; }}
    .test-table td {{ padding: 7px 16px; border-bottom: 1px solid #f7fafc; }}
    tr.pass  td {{ color: #2d3748; }}
    tr.fail  td {{ color: #c53030; font-weight: 500; }}
    tr.skip  td {{ color: #718096; font-style: italic; }}
    .icon       {{ margin-right: 7px; font-size: 0.9rem; }}
    tr.pass .icon {{ color: #48bb78; }}
    tr.fail .icon {{ color: #fc8181; }}
    tr.skip .icon {{ color: #a0aec0; }}
    .status-cell {{ width: 80px; font-weight: 600; }}

    /* ---- Error detail ---- */
    tr.detail-row td {{ padding: 0; }}
    .error-pre {{ background: #1a202c; color: #e2e8f0; padding: 12px 18px;
                  font-size: 0.78rem; overflow-x: auto; white-space: pre-wrap;
                  word-break: break-all; border-top: 1px solid #2d3748; line-height: 1.5; }}

    .no-tests {{ color: #718096; padding: 20px 0; font-style: italic; }}
  </style>
</head>
<body>
  <header>
    <h1>Agentic QA &mdash; Test Report</h1>
    <div class="meta">{repo_line}Generated: {ts}</div>
  </header>

  <div class="summary">
    <div class="badge total">🧪 {total}&nbsp;Tests</div>
    <div class="badge pass">✓ {passed}&nbsp;Passed</div>
    <div class="badge fail">✗ {failed}&nbsp;Failed</div>
  </div>

  <div class="container">
    {file_cards_html}
  </div>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
