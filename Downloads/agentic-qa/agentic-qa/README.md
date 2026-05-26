# Agentic QA System

Automatically generates, runs, and updates tests whenever your code changes — powered by Claude.

## How it works

### Phase 1 — Initial run
1. **Ingest**: scans every `.py` file in your codebase
2. **Generate**: calls Claude to write a complete `pytest` test file per source file
3. **Run**: executes all tests and prints a pass/fail summary

### Phase 2 — Watch loop (runs continuously after Phase 1)
1. **Watch**: polls for any file modification
2. **Diff**: analyses which functions/classes were added, changed, or removed
3. **Update**: calls Claude to patch only the affected tests (preserving existing good tests)
4. **Retest**: re-runs pytest on the updated test file and reports results

---

## Setup

```bash
# 1. Clone / unzip this folder
cd agentic-qa

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Usage

```bash
# Run on your own codebase (watches for changes by default)
python main.py path/to/your/codebase

# Run on the included example
python main.py example_codebase

# Run once, no watching
python main.py path/to/your/codebase --no-watch

# Scan specific extensions
python main.py path/to/your/codebase --extensions .py .pyw

# Custom output directory
python main.py path/to/your/codebase --output-dir my_tests
```

Generated test files appear in `tests_output/` (or your chosen `--output-dir`).

---

## Project structure

```
agentic-qa/
├── main.py                   ← entry point
├── core/
│   ├── orchestrator.py       ← coordinates all agents
│   └── models.py             ← SourceModule data class
├── agents/
│   ├── ingest_agent.py       ← parse source files
│   ├── test_writer_agent.py  ← Claude-powered test generation + update
│   ├── test_runner_agent.py  ← pytest runner
│   ├── file_watcher_agent.py ← polls for changes
│   └── diff_agent.py         ← detects added/removed/changed symbols
├── utils/
│   ├── claude_client.py      ← Anthropic API wrapper
│   └── logger.py             ← timestamped print
├── example_codebase/
│   └── bank.py               ← demo source to test against
├── tests_output/             ← auto-created; holds generated tests
└── requirements.txt
```

---

## Extending to other languages

Currently supports Python. To add JavaScript/TypeScript:
1. Add `.js` / `.ts` to `--extensions`
2. In `IngestAgent._parse_python`, add a branch for JS parsing (e.g. using `tree-sitter`)
3. Update prompts in `TestWriterAgent` to request `jest` / `vitest` tests

---

## Tips

- The agent skips `__pycache__`, `.venv`, `.git`, `node_modules` automatically.
- If a generated test has import errors, check that the `sys.path` insertion in the test file points to your codebase root.
- You can manually edit generated tests — the update step merges your edits with new AI-generated sections.
