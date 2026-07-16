# mtg_ai_engine Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)
All implementation MUST have passing tests before integration. Each feature requires: tests written → tests fail → then implement. New effect/trigger/keyword classes require 3-5 unit tests minimum.

### II. CR-Compliant Rules Engine
All game logic MUST follow the Magic: The Gathering Comprehensive Rules (CR). Implementation must cite the relevant CR section (e.g., CR 614 for replacement effects, CR 611 for layers). Deviations must be documented with rationale.

### III. Forge Parity Alignment
Engine subsystems should mirror Forge's architectural patterns where pragmatic. File-for-file parity is NOT required, but functional parity IS. Each gap category (G1-G13) must track implementation coverage quantitatively.

### IV. Modular Library Architecture
Core game logic lives in `mtg_engine/` as independent modules. Ability effects, keywords, triggers, and replacement effects each have their own subdirectory. No circular dependencies between engine modules.

### V. Incremental Delivery
Large gaps are addressed in phases. Each phase produces shippable, testable value. Deferred items are explicitly tracked in tasks.md with dependency chains. No phase exceeds 3 sprints without a checkpoint.

## Technology Stack

- **Language**: Python 3.11+
- **API layer**: FastAPI + Pydantic v2
- **Persistence**: motor (async MongoDB driver) — optional, game state is in-memory
- **Testing**: pytest (mandatory)
- **Linting**: ruff

## Development Workflow

1. **Specify**: Update SPEC.md with FR/SC identifiers for each gap category
2. **Plan**: Update plan.md with phases, dependencies, and measurable success criteria
3. **Task**: Break into testable tasks in tasks.md
4. **Implement**: Tests first → code → verify all tests pass
5. **Review**: Verify CR citation, test coverage, Forge functional parity

## Governance

This constitution supersedes all other development guidelines. Amendments require documentation, team approval, and a migration plan. Constitution conflicts are CRITICAL and require adjustment of the spec, plan, or tasks — not dilution of the principle.

**Version**: 1.0.0 | **Ratified**: 2026-05-21 | **Last Amended**: 2026-05-21
