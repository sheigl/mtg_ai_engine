---
name: dev-pipeline
description: "Orchestrate the MTG AI Engine development pipeline with Project Manager, Developer, and QA Tester agents. Use when: running the dev pipeline, starting a sprint, implementing multiple features, coordinating agents, managing feature delivery workflow."
argument-hint: "Feature or task to work on"
user-invocable: true
---

# Development Pipeline Orchestration

## Overview

This skill orchestrates the three-agent development pipeline for MTG AI Engine:

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Project Manager │────▶│  Developer   │────▶│  QA Tester   │
│  (orchestrator)  │◀────│  (implements)│     │  (verifies)  │
└─────────────────┘     └──────────────┘     └──────────────┘
        ▲                                              │
        │          ┌───────────────────────────────────┘
        │          │  (if tests fail, bugs sent back)
        └──────────┘  (PM reassigns to Developer)
```

## Agents

| Agent | File | Role |
|-------|------|------|
| Project Manager | `.github/agents/project-manager.agent.md` | Orchestrates workflow, assigns tasks |
| Developer | `.github/agents/developer.agent.md` | Implements features, writes code |
| QA Tester | `.github/agents/qa-tester.agent.md` | Tests with pytest + Playwright e2e |

## How to Use

### Option 1: Invoke Project Manager directly

Ask the Project Manager agent to start a pipeline cycle:

```
Run the project-manager agent to implement features from tasks.md
```

The PM will:
1. Read `tasks.md` for pending items
2. Assign first feature to Developer
3. Hand completed work to QA Tester
4. Handle rework loops until QA passes
5. Update `.github/pipeline/status.md`

### Option 2: Manual Pipeline Steps

Run each stage manually:

#### Step 1: Develop
```
Run the developer agent with task: "{feature description}"
```

#### Step 2: Test
```
Run the qa-tester agent to verify: "{feature name}"
Review these changes: {list of files changed}
```

#### Step 3: Review Results
- If QA passes → Feature is done ✓
- If QA fails → Send bug report back to Developer

## Pipeline Status

Track progress in `.github/pipeline/status.md`:

| Column | Description |
|--------|-------------|
| Feature | Name/ID of the feature |
| Dev Status | ✅ Complete / 🔄 In Progress / ⏳ Pending |
| QA Status | ✅ Passed / ❌ Failed — {bugs} / ⏳ Pending |
| Notes | Additional context |

## Typical Workflow

```markdown
1. User: "Run the pipeline for features in tasks.md"
2. PM reads backlog, identifies next feature
3. PM → Developer: "Implement Feature X"
4. Developer writes code + unit tests, reports complete
5. PM → QA Tester: "Verify Feature X implementation"
6. QA runs pytest + Playwright tests

   If PASS:
     PM marks complete, moves to next feature
   
   If FAIL:
     QA sends bug report to PM
     PM → Developer: "Fix bugs in Feature X: {details}"
     Developer fixes, reports complete
     Go to step 5 (re-test)
```

## Commands Reference

| Action | Command |
|--------|---------|
| Run Python tests | `cd src && pytest -x -q` |
| Lint code | `ruff check .` |
| Run Playwright e2e | `npx playwright test tests/e2e/` |
| Build frontend | `cd frontend && npm run build` |

## Troubleshooting

- **Agent not found**: Ensure `.github/agents/*.agent.md` files exist and have valid frontmatter
- **Tests fail on first run**: Check that dependencies are installed (`pip install -r requirements.txt`)
- **Playwright errors**: Run `npx playwright install chromium` in frontend directory
- **Circular loops**: If Dev↔QA cycles more than 3 times, escalate to human review
