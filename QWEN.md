# MTG Rules Engine — Qwen Code Context

## What This Project Is

A Python REST API that enforces the full Magic: The Gathering
Comprehensive Rules, allowing AI agents to play complete games against
each other. The output is structured training data (game state snapshots,
play-by-play transcripts, rules Q&A pairs, win/loss outcomes) consumed
by a downstream MTG model fine-tuning pipeline.

The engine does NOT make strategic decisions. It enforces legality,
resolves actions, and reports state. Strategy is entirely the AI
agent's responsibility.

---

## First-Run Setup

Before starting any task, check whether `cr.txt` exists in the
project root. If it does not exist, download it now:

```bash
curl -L "https://media.wizards.com/2025/downloads/MagicCompRules_20250404.txt" \
     -o cr.txt
```

If that URL fails (Wizards occasionally rotates filenames), try:

```bash
# Check the rules page for the current URL
curl -s "https://magic.wizards.com/en/rules" | grep -o 'MagicCompRules[^"]*\.txt' | head -1
```

Then download using the URL found. The file is ~900KB plain text.
Do not proceed with any rules engine task until `cr.txt` is present.

---

## Always Read Before Starting Any Task

Before writing any code, read these files in order:

1. `spec.md` — architecture, purpose, what is out of scope
2. `requirements.md` — precise numbered requirements (REQ-XXX)
   that every implementation must satisfy
3. `tasks.md` — current task list, status, and "Done when" conditions

When a requirement number is referenced in a task (e.g. REQ-R01),
look it up in `requirements.md` before implementing. Do not guess
what a requirement means.

---

## Comprehensive Rules Reference

The full MTG Comprehensive Rules are in `cr.txt` at the project root.
Use grep to extract relevant sections before implementing any rules
module. Do not rely solely on training knowledge for rules details —
always verify against the CR text.

Key sections and how to find them:

```bash
# Turn structure and phases
grep -n "^5" cr.txt | head -30

# Zones (CR 400-407)
grep -n "^40[0-7]\." cr.txt | head -20

# Spells, abilities, effects (CR 601-609)
grep -n "^60[1-9]\." cr.txt | head -30

# Layer system — READ THIS IN FULL before TASK-13
grep -n "^613" cr.txt

# Dependency rule within layers
grep -n "613\.8" cr.txt

# Replacement effects — READ THIS IN FULL before TASK-14
grep -n "^616" cr.txt

# State-based actions — READ THIS IN FULL before TASK-09
grep -n "^704" cr.txt

# Triggered abilities and APNAP ordering
grep -n "^603" cr.txt

# Combat damage and trample
grep -n "^510\|^702\.19" cr.txt

# Keywords
grep -n "^702\." cr.txt | head -60
```

To read a full section (e.g. all of CR 613):
```bash
awk '/^613\./{found=1} found{print} /^614\./{exit}' cr.txt
```

To read a specific rule (e.g. CR 613.8):
```bash
awk '/^613\.8/{found=1} found{print} /^613\.9/{exit}' cr.txt
```

**Before implementing TASK-09 (SBAs):** read CR 704 in full.
**Before implementing TASK-11 (stack):** read CR 601-608 in full.
**Before implementing TASK-12 (triggers):** read CR 603 in full.
**Before implementing TASK-13 (layers):** read CR 613 in full.
**Before implementing TASK-14 (replacement):** read CR 616 in full.
**Before implementing TASK-15 (combat):** read CR 508-511 in full.

---

## Project Structure

```
mtg_engine/
  api/            FastAPI routers and app entry point
  engine/         Rules logic — zones, turns, stack, SBAs, layers,
                  replacement effects, combat, triggers, mana
  models/         Pydantic v2 models for all game objects
  card_data/      ScryfallClient, ability parser, local cache
  export/         Training data recorders and export endpoints
  tests/
    rules/        Rules interaction test suite (50 known-tricky cases)
    api/          Integration tests via HTTP
spec.md
requirements.md
tasks.md
QWEN.md           (this file)
```

---

## Tech Stack

- Python 3.11+
- FastAPI — REST layer
- Pydantic v2 — all game state models; enables clean JSON serialization
- uvicorn — local server (`uvicorn mtg_engine.api.main:app --reload`)
- pytest — test runner
- httpx — async HTTP client for Scryfall and for integration tests
- pymongo — MongoDB writes for training data export
- sqlite3 (stdlib) — local Scryfall card cache

---

## Coding Rules

### General
- Type hint everything. All functions must have full type annotations.
- Use Pydantic v2 models for all data that crosses a function boundary
  or is serialized to JSON. No raw dicts for game objects.
- All game state must be fully serializable to JSON at any point —
  test this if in doubt by calling `model.model_dump_json()`.
- The engine must be deterministic given a fixed random seed.
  Use `random.Random(seed)` instances, never the global `random` module.
- Never use global mutable state. `GameManager` in `api/` holds the
  game dict; everything else is pure functions or method calls on
  passed-in state objects.

### Rules Logic
- Every rules decision must cite the relevant requirement number
  in a comment, e.g. `# REQ-R01: SBAs checked before priority grant`
- The layer system (engine/layers.py) is the most complex module.
  Build and test it in isolation before integrating with the rest
  of the engine. Reference CR 613 explicitly in comments.
- Replacement effects (engine/replacement.py) must intercept events
  before they happen, not after. An event that has already occurred
  cannot be replaced.
- State-based actions run in a loop until no more apply, then
  priority is granted. Never grant priority mid-SBA check.

### FastAPI
- All request bodies are Pydantic models, never raw dicts or
  `Body(...)` with arbitrary types.
- Illegal game actions return HTTP 422 with a JSON body containing
  `error` (human-readable) and `error_code` (machine-readable string).
- All successful responses return HTTP 200 with a `data` key.
- Include a `dry_run: bool = False` field on all action request models.

### Dependencies

Install all dependencies with plain pip — no editable installs:

```bash
pip install fastapi uvicorn pydantic httpx pymongo pytest pytest-asyncio
```

Do NOT run `pip install -e .` or `pip install -e .[dev]` or any
editable install variant. Do NOT create or modify `setup.py`,
`setup.cfg`, or `pyproject.toml` for the purpose of installing the
package. The project is not installed as a package.

### Running Tests

Always run tests with PYTHONPATH set to the project root so that
`import mtg_engine` resolves correctly without an editable install:

```bash
PYTHONPATH=. pytest tests/
```

For a specific test file:
```bash
PYTHONPATH=. pytest tests/rules/test_sba.py -v
```

Use this exact command every time. Never use plain `pytest tests/`
without the PYTHONPATH prefix — it will fail with ImportError.

All `conftest.py` files must also use relative imports or
`sys.path` manipulation if needed — never assume the package
is installed.

### Writing Tests
- Tests for rules logic go in `tests/rules/`. Each test file maps
  to one engine module (e.g. `test_sba.py`, `test_layers.py`).
- API integration tests go in `tests/api/` and use `httpx.AsyncClient`
  against a live test app instance.
- A task's "Done when" condition is the minimum bar. Write at least
  one additional edge case test beyond the stated condition.
- Every test file must begin with:
  ```python
  import sys, os
  sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
  ```
  This guarantees imports work regardless of how pytest is invoked.

---

## Task Workflow

1. Read `tasks.md` and identify the target task(s).
2. Read `spec.md` and `requirements.md` for relevant context.
3. Plan the implementation — identify which files are affected and
   what interfaces need to exist before writing any code.
4. Install any missing dependencies with plain pip (no `-e` flag).
5. Implement the task.
6. Run `PYTHONPATH=. pytest tests/ -v` — fix all failures before
   proceeding. Never use plain `pytest` without PYTHONPATH.
7. Update the checkbox in `tasks.md` from `[ ]` to `[x]`.
8. Do not start the next task until the current one is marked done
   and tests pass.

When multiple tasks in the same phase have no dependencies on each
other (e.g. TASK-01, TASK-02, TASK-03 in Phase 1), they may be
implemented in parallel using sub-agents.

---

## Phase Guidance

### Phases 1–2 (Scaffold, Models, Scryfall)
Low risk. These are pure data modeling and API integration tasks.
Auto-approval is fine here.

### Phase 3 (Core Rules Engine)
Moderate complexity. The stack (TASK-11) and trigger detection
(TASK-12) interact — build the stack first, triggers second.
Request approval before committing each task's implementation.

### Phase 4 (Layer System & Replacement Effects)
High complexity. This is the hardest part of the project.
- TASK-13 (layers): implement layers 1–7 in strict order.
  Do not skip ahead to test layer 7 before layer 4 works.
- TASK-14 (replacement): build around an event interception pattern,
  not a post-hoc correction pattern.
- TASK-15 (combat): first strike and double strike require two
  separate damage steps with SBA checks between them.
Always request approval before committing Phase 4 work.

### Phases 5–6 (API & Export)
Moderate complexity. Phase 5 is mostly wiring; Phase 6 is recording
hooks. Approval mode recommended for Phase 5, auto-approval fine
for Phase 6 boilerplate.

### Phase 7 (Validation)
Do not skip TASK-24 (50 rules interaction tests). These are the
real correctness signal for the whole engine.

---

## Known Hard Problems — Read Before Implementing

### The Layer System (TASK-13)
CR 613 defines seven layers applied in order. Within a layer,
effects are ordered by timestamp unless a dependency exists.
A dependency exists when applying effect A changes what effect B
applies to — in that case, B depends on A and applies after it.

The classic test case is Humility + Opalescence:
- Humility: all creatures lose all abilities and are 1/1
- Opalescence: enchantments are creatures with P/T = CMC
- Humility is an enchantment; Opalescence makes it a creature
- Layer 6: Humility removes Opalescence's ability to make it a
  creature — but Opalescence's effect is already applied at layer 4
- Layer 7b: Humility sets all creatures to 1/1 — including itself
  if it became a creature
The engine must produce the correct result for this interaction.

### Replacement Effect Ordering (TASK-14)
When two replacement effects both apply to the same event,
the controller of the affected object chooses the order.
This requires the API to surface a `choice` request to the
client before the event resolves. The `POST /game/{id}/choice`
endpoint handles this. Build the choice queue before implementing
multi-replacement scenarios.

### Combat Damage Assignment (TASK-15)
Minimum lethal damage rule: a player must assign at least lethal
damage to each blocker before assigning trample damage past it.
"Lethal" means damage >= toughness, OR any damage if the source
has deathtouch. The engine validates the full assignment, not just
the total.

### Triggered Ability APNAP Ordering (TASK-12)
When multiple triggers fire simultaneously, the active player
puts all of their triggers on the stack first (in the order they
choose), then the non-active player does the same. This means
the non-active player's triggers resolve first (LIFO stack).
This is counterintuitive — double-check the implementation
against CR 603.3b.

---

## What NOT to Do

- Do not hard-code card names anywhere in the rules engine.
  Card behavior comes from the ability parser reading oracle text.
- Do not use the global `random` module. Use seeded instances.
- Do not apply SBAs inside stack resolution. SBAs are checked
  after resolution completes, before priority is granted.
- Do not grant priority during the untap step.
- Do not let mana persist between steps/phases (except mana abilities
  activated in response to something on the stack).
- Do not implement Commander, multiplayer, or any out-of-scope rules.
  If a game action would require out-of-scope rules, raise a
  `NotImplementedError` with a clear message.
- Do not write requirements.md. Only read it.
- Do not run `pip install -e .` or any editable install variant.
  Do not create setup.py, setup.cfg, or pyproject.toml for package
  installation purposes. Use `PYTHONPATH=. pytest tests/` instead.
- Do not run plain `pytest tests/` without the PYTHONPATH prefix —
  it will always fail with ImportError on this project.
  validation. Type annotations are still required in code but do not
  run mypy to check them.
- Do not ask the user questions mid-task via AskUserQuestion. If a
  tool or dependency is missing, install it with pip and continue.
  Only stop if a task is fundamentally blocked with no workaround.
