# Pipeline Status

Last updated: 2026-06-12

## Active Pipeline

| Feature | Dev Status | QA Status | Notes |
|---------|-----------|-----------|-------|
| *(no active features)* | ⏳ Pending | ⏳ Pending | Invoke `project-manager` agent to start |

## Completed Features

| Feature | Completed | QA Result | Notes |
|---------|-----------|-----------|-------|
| *(none yet)* | — | — | — |

## How to Use

1. Ask the **Project Manager** agent to start a pipeline cycle
2. PM reads `tasks.md` and assigns features to Developer
3. Developer implements → QA tests → loop until pass
4. Status updates automatically after each cycle

## Quick Start

```
# Option 1: Let PM read from tasks.md
"Run the project-manager agent to implement pending features"

# Option 2: Specify a feature directly  
"Run the dev-pipeline skill for {feature name}"
```
