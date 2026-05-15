# QA Multi-Agent System

This project implements a multi-agent QA pipeline using Claude sub-agents.

## Architecture

```
qa-orchestrator
├── natural-language-test-author   (Scenario 4: NL Test Authoring)
└── visual-regression-detector     (Scenario 5: Visual Regression Detection)
```

## Agents

| Agent | File | Role |
|---|---|---|
| `qa-orchestrator` | `.claude/agents/qa-orchestrator.md` | Root coordinator |
| `natural-language-test-author` | `.claude/agents/natural-language-test-author.md` | Converts plain English to Playwright tests |
| `visual-regression-detector` | `.claude/agents/visual-regression-detector.md` | Baseline capture + pixel diff regression detection |

## Project Structure

```
.
├── CLAUDE.md
├── package.json
├── .claude/
│   └── agents/
│       ├── qa-orchestrator.md
│       ├── natural-language-test-author.md
│       └── visual-regression-detector.md
├── tests/
│   └── generated/          # Playwright tests written by natural-language-test-author
└── .visual-regression/
    ├── baseline/            # Mode A screenshots
    ├── current/             # Mode B screenshots
    └── report.html          # Side-by-side diff report
```

## Quick Start

Invoke the orchestrator from a Claude Code session:

```
@qa-orchestrator Write a test that logs in with valid credentials and checks the dashboard loads
```

```
@qa-orchestrator Capture baseline screenshots of all pages
```

```
@qa-orchestrator A code change was just deployed — check for visual regressions
```

## Dependencies

- `@playwright/test` — browser automation and test runner
- `pixelmatch` — pixel-level image diffing
- `pngjs` — PNG read/write for diff images
- `typescript` — typed test authoring
