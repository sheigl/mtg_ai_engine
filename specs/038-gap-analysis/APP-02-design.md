# Design: APP-02 Deck Building AI

## Overview
Build an automated deck construction engine that takes a card pool, format, and strategy description, then produces a legal, optimized MTG deck via `POST /ai/deck/build`. The system filters cards by format legality, scores them using baseline quality heuristics modified by strategy weights and CMC curve targeting, selects the best cards respecting singleton/restricted rules, validates the result against FMT-01, and returns both main deck and sideboard.

## User Story Reference
As a player or AI agent, I want to provide a card pool, format, and strategy description so that the system constructs a legal, optimized deck automatically.

---

## Architecture Decisions

### Decision 1: Filter → Score → Select → Validate Pipeline
The algorithm follows four sequential stages:
1. **Filter** — Remove banned cards, restricted cards (enforce max-1), cards outside legality window, and non-singleton duplicates for singleton formats. Commander color identity filtering applied here too.
2. **Score** — Each remaining card receives a composite score = `baseline_quality × strategy_multiplier × cmc_curve_bonus`. Baseline quality comes from existing `estimate_card_quality()` in `card_eval.py`. Strategy multipliers are hardcoded per-strategy/category tables. CMC curve bonus rewards cards that fill gaps in the target curve for the given strategy.
3. **Select** — Sort scored cards by composite score (descending), then deterministically pick top N respecting format constraints (deck size, singleton limits). Commander(s) are locked into the deck first if provided. Sideboard fills from remaining legal cards up to 15.
4. **Validate** — Run FMT-01's `validate_deck()` on the constructed deck. If validation fails, return errors in the response rather than an invalid deck.

### Decision 2: Extend card_eval.py, Don't Replace It
The existing `estimate_card_quality(card: dict) -> float` function (range 0-10) is used as-is for baseline scoring. We wrap it with strategy-aware multipliers in a new `score_card_for_strategy()` function rather than modifying the original. This keeps card_eval.py backward-compatible and testable independently.

### Decision 3: Stateless Engine, No GameState Dependency
Deck building operates on raw `Card` objects — no `GameState`, no game zones, no persistence. It mirrors FMT-01's stateless design. The API router handles request parsing and response formatting; the engine module is a pure function.

### Decision 4: Deterministic Tie-Breaking via Seeded Sort
To ensure reproducible results across identical inputs, we use `random.Random(seed)` for tie-breaking when two cards have equal composite scores. Default seed is derived from `(format + strategy + sorted card pool names)` hash. Users can optionally provide a `seed` parameter for explicit reproducibility.

### Decision 5: Commander Color Identity Filtering
For Commander format with `commander_names` provided, we use the existing `get_color_identity()` from `mtg_engine/engine/formats/commander.py`. Cards whose color identity is NOT a subset of the composite commander color identity are excluded during filtering. Commanders themselves are always included (locked) in the deck.

### Trade-offs Considered
- **Alternative: ML-based scoring** — Rejected for MVP. Regex/heuristic approach from card_eval.py is sufficient and deterministic. Can layer ML later.
- **Alternative: Iterative optimization** — Rejected for MVP. Single-pass greedy selection is simpler, faster, and produces good-enough results. Could add hill-climbing swap pass in future iterations.
- **Alternative: Return Card objects vs dicts** — Chose `list[dict]` with `{name, quantity}` format per acceptance criteria. Simpler serialization and matches existing deck import patterns.

---

## Files to Create/Modify

### New Files
| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `mtg_engine/ai/deck_builder.py` | Core deck building algorithm | Filter, score, select pipeline; strategy weights; CMC curve targeting; sideboard construction |
| `mtg_engine/api/routers/deck_build_ai.py` | FastAPI router for AI deck building | Request/response Pydantic models, endpoint handler, error handling |
| `tests/ai/test_deck_builder.py` | Test suite for deck builder engine | Unit tests for filter/score/select stages + integration test for full pipeline |

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/api/main.py` | Import and mount new `deck_build_ai.router` | Wire endpoint into FastAPI app |
| `.opencode/context/standards.md` | Add APP-02 coding standards section | Document deck builder patterns for future reference |

---

## Data Models / Interfaces

### Request Model (Pydantic v2)

```python
from pydantic import BaseModel, Field
from typing import Optional
from mtg_engine.models.game import Card

class DeckBuildRequest(BaseModel):
    """POST /ai/deck/build request body."""
    card_pool: list[Card] = Field(..., min_length=1, description="Pool of cards to build from")
    format: str = Field(..., description="MTG format (standard, pioneer, modern, legacy, vintage, commander, brawl, pauper)")
    strategy: str = Field(default="midrange", description="Strategy archetype (aggro, control, midrange, combo)")
    commander_names: Optional[list[str]] = Field(
        default=None,
        description="Commander card names for Commander/Brawl format. If provided, these cards are locked into the deck.",
    )
    seed: Optional[int] = Field(default=None, description="Optional random seed for deterministic results")

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        allowed = {"aggro", "control", "midrange", "combo"}
        if v.lower() not in allowed:
            raise ValueError(f"Strategy must be one of {allowed}, got '{v}'")
        return v.lower()

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        from mtg_engine.engine.formats import FORMAT_VALIDATORS
        if v.lower().strip() not in FORMAT_VALIDATORS:
            raise ValueError(f"Unknown format: '{v}'. Must be one of {list(FORMAT_VALIDATORS.keys())}")
        return v.lower().strip()
```

### Response Model (Pydantic v2)

```python
class DeckCardEntry(BaseModel):
    """Single card entry in the built deck."""
    name: str
    quantity: int = Field(..., ge=1)

class DeckBuildResponse(BaseModel):
    """POST /ai/deck/build response body."""
    deck: list[DeckCardEntry]  # Main deck cards with quantities
    sideboard: list[DeckCardEntry]  # Sideboard cards (empty for Commander/Brawl)
    validation: dict  # DeckValidationResponse.model_dump() from FMT-01
```

### Internal Scoring Data Structure

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ScoredCard:
    """Card with composite strategy-aware score."""
    card: Card
    baseline_quality: float       # From estimate_card_quality()
    category: str                 # "creature_low", "creature_high", "removal", etc.
    strategy_multiplier: float    # From STRATEGY_WEIGHTS table
    cmc_curve_bonus: float        # CMC curve targeting bonus (1.0-1.5x)
    composite_score: float        # baseline * multiplier * cmc_bonus

    def __lt__(self, other: "ScoredCard") -> bool:
        return self.composite_score < other.composite_score
```

---

## Algorithm Design

### Stage 1: Filter

Input: `card_pool: list[Card]`, `format_name: str`, `commander_names: Optional[list[str]]`

Steps:
1. **Banned card removal**: Use `is_banned(card.name, format_name)` from `mtg_engine/engine/formats/banned.py`. Remove all banned cards.
2. **Legality window filter**: For formats with legality windows (Standard, Pioneer, Modern, Brawl), check `card.set_code` against `LEGAL_SETS[format]`. Cards without a set_code are included (unknown provenance = assume legal). Cards with a set_code outside the window are excluded.
3. **Singleton enforcement**: For Legacy, Vintage, Commander, and Brawl formats:
   - Count occurrences of each card name in the pool
   - Keep only 1 copy of non-basic-land cards
   - Basic lands (Plains, Island, Swamp, Mountain, Forest, Snow-Covered variants, Wastes) are exempt from singleton
4. **Restricted enforcement** (Vintage only): Use `is_restricted(card.name)` — keep max 1 copy of restricted cards
5. **Commander color identity filter**: If format is "commander" or "brawl" and `commander_names` provided:
   - Look up commander cards from pool by name match
   - Compute composite color identity using `get_color_identity()` from `mtg_engine/engine/formats/commander.py`
   - Exclude non-commander cards whose color identity is NOT a subset of the composite identity
6. **Return**: Filtered list of legal candidate cards

### Stage 2: Score

Input: `filtered_cards: list[Card]`, `strategy: str`

For each card, compute:
1. **Baseline quality**: Call `estimate_card_quality(card.model_dump())` from `card_eval.py`. Returns float in [0, 10].
2. **Category classification**: Determine card category using existing helpers + type_line analysis:
   - `"creature_low"` — Creature with CMC <= 2
   - `"creature_mid"` — Creature with CMC 3-4
   - `"creature_high"` — Creature with CMC >= 5
   - `"removal"` — `is_removal_spell(card)` returns True (non-creature)
   - `"counterspell"` — `is_counterspell(card)` returns True
   - `"draw"` — `is_draw_spell(card)` returns True
   - `"ramp"` — `is_ramp(card)` returns True
   - `"board_wipe"` — `is_board_wipe(card)` returns True
   - `"land"` — Type line contains "Land" (no strategy multiplier, always 1.0x)
   - `"other"` — Everything else (multiplier 1.0x)

3. **Strategy multiplier**: Look up from `STRATEGY_WEIGHTS` table by `(strategy, category)` pair. Default 1.0 if not found.

4. **CMC curve bonus**: Target CMC distribution varies by strategy:
   - Aggro: peak at CMC 1-2 (bonus 1.3x for CMC<=2, 1.0x otherwise)
   - Control: peak at CMC 3-5 (bonus 1.2x for CMC 3-5, 1.0x otherwise)
   - Midrange: even distribution (bonus 1.1x for CMC 2-4, 1.0x otherwise)
   - Combo: peak at CMC 3+ (bonus 1.2x for CMC>=3, 1.0x otherwise)

5. **Composite score**: `baseline_quality × strategy_multiplier × cmc_curve_bonus`

6. **Return**: List of `ScoredCard` objects sorted by composite_score descending

### Stage 3: Select

Input: `scored_cards: list[ScoredCard]`, `format_name: str`, `commanders: Optional[list[Card]]`

Steps:
1. **Determine deck size target**:
   - Commander/Brawl: exactly 100 (Commander) or 60 (Brawl)
   - All others: at least 60
2. **Lock commanders** (if provided): Add commander cards to deck, decrement their count from scored pool
3. **Greedy selection**: Iterate scored_cards in descending order:
   - For singleton formats (Legacy/Vintage/Commander/Brawl): add card once if not already in deck
   - For Vintage restricted: add max 1 copy of restricted cards
   - For other formats: add up to 4 copies (standard MTG rule)
   - Stop when deck reaches target size
4. **Land balancing**: If fewer than 24% of selected cards are lands, fill remaining slots with highest-scored lands from pool
5. **Sideboard construction** (non-Commander/Brawl formats): From remaining scored cards not in main deck, select up to 15 best cards using same singleton/restricted rules

6. **Return**: `deck: list[Card]`, `sideboard: list[Card]`

### Stage 4: Validate

Input: `deck: list[Card]`, `format_name: str`, `commanders: Optional[list[Card]]`

Steps:
1. Call `validate_deck(deck, format_name, commanders)` from FMT-01
2. If valid: return success response with deck entries grouped by name/quantity
3. If invalid: return response with `validation.valid = False` and violations listed

### Deterministic Tie-Breaking

When two cards have equal composite scores, use a seeded random shuffle for ordering:
```python
import hashlib
seed_str = f"{format_name}:{strategy}:{','.join(sorted(c.name for c in card_pool))}"
seed_value = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16) if user_seed is None else user_seed
rng = random.Random(seed_value)
```

---

## Strategy Weight Configuration

### STRATEGY_WEIGHTS Table

| Category | Aggro | Control | Midrange | Combo |
|----------|-------|---------|----------|-------|
| `creature_low` (CMC 0-2) | 1.5x | 0.7x | 1.0x | 1.3x |
| `creature_mid` (CMC 3-4) | 1.0x | 1.0x | 1.2x | 1.0x |
| `creature_high` (CMC 5+) | 0.5x | 1.2x | 1.0x | 1.4x |
| `removal` | 1.0x | 1.5x | 1.1x | 0.8x |
| `counterspell` | 0.7x | 1.5x | 1.0x | 1.2x |
| `draw` | 1.0x | 1.3x | 1.2x | 1.5x |
| `ramp` | 1.2x | 1.0x | 1.1x | 1.3x |
| `board_wipe` | 0.5x | 1.4x | 1.0x | 0.6x |
| `land` | 1.0x | 1.0x | 1.0x | 1.0x |
| `other` | 1.0x | 1.0x | 1.0x | 1.0x |

### CMC Curve Targeting Bonuses

| Strategy | Bonus Range | Multiplier |
|----------|-------------|------------|
| Aggro | CMC <= 2 | 1.3x |
| Control | CMC 3-5 | 1.2x |
| Midrange | CMC 2-4 | 1.1x |
| Combo | CMC >= 3 | 1.2x |

All other CMC values receive 1.0x bonus (no penalty).

---

## API Contract

### Endpoint: `POST /ai/deck/build`

**Request Body**: `DeckBuildRequest` (Pydantic model)
```json
{
  "card_pool": [
    {"name": "Lightning Bolt", "mana_cost": "{R}", "type_line": "Instant", "oracle_text": "Lightning Bolt deals 3 damage to any target.", "cmc": 1, "colors": ["R"], "color_identity": ["R"]},
    {"name": "Mountain", "mana_cost": null, "type_line": "Land — Mountain", "cmc": 0, "colors": [], "color_identity": []}
  ],
  "format": "modern",
  "strategy": "aggro",
  "commander_names": null,
  "seed": 42
}
```

**Response Body**: `{"data": DeckBuildResponse}` (HTTP 200)
```json
{
  "data": {
    "deck": [
      {"name": "Lightning Bolt", "quantity": 4},
      {"name": "Mountain", "quantity": 25}
    ],
    "sideboard": [
      {"name": "Abrupt Decay", "quantity": 3}
    ],
    "validation": {
      "valid": true,
      "violations": [],
      "format": "modern"
    }
  }
}
```

**Error Response**: HTTP 400 (Pydantic validation failure) or HTTP 500 (internal error)
```json
{
  "detail": {
    "error": "Unknown format: 'uber'",
    "error_code": "UNKNOWN_FORMAT"
  }
}
```

**Validation Rules**:
- `card_pool` must have at least 1 card
- `format` must be one of the 8 supported formats (validated against `FORMAT_VALIDATORS`)
- `strategy` must be one of: aggro, control, midrange, combo
- If format is "commander" or "brawl", `commander_names` should be provided (not required — builder can auto-select if omitted)

---

## Task Breakdown (Ordered by Dependency)

### Task 1: Core Algorithm Module (`mtg_engine/ai/deck_builder.py`)
- **Files**: New file `mtg_engine/ai/deck_builder.py`
- **Description**: Implement the filter → score → select pipeline as pure functions. Export `build_deck(card_pool, format_name, strategy, commander_names=None, seed=None) -> DeckBuildResult`. Include STRATEGY_WEIGHTS table and CMC curve targeting logic. Integrate with existing `card_eval.py` for baseline scoring and `formats/banned.py` + `formats/__init__.py` for filtering/validation.
- **Acceptance Criteria**:
  - `filter_card_pool()` correctly removes banned cards, enforces legality windows, singleton rules, restricted limits, and commander color identity
  - `score_cards()` produces composite scores using baseline × strategy_multiplier × cmc_bonus
  - `select_deck()` greedily picks top N cards respecting format constraints
  - `build_deck()` orchestrates all stages and returns structured result with deck, sideboard, and validation

### Task 2: API Router (`mtg_engine/api/routers/deck_build_ai.py`)
- **Files**: New file `mtg_engine/api/routers/deck_build_ai.py`
- **Description**: Create FastAPI router with `POST /ai/deck/build` endpoint. Define Pydantic request/response models. Handle validation errors (unknown format, invalid strategy). Call engine module and return structured response. Follow existing patterns from `deck_import.py`.
- **Acceptance Criteria**:
  - Endpoint accepts valid requests and returns HTTP 200 with deck data
  - Unknown formats return HTTP 400 with descriptive error
  - Invalid strategies return HTTP 400 via Pydantic field validator
  - Response includes `deck`, `sideboard`, and `validation` fields

### Task 3: Wire Router into App (`mtg_engine/api/main.py`)
- **Files**: Modify `mtg_engine/api/main.py`
- **Description**: Import new router and mount it via `app.include_router(deck_build_ai.router)`. Follow existing import/mount pattern.
- **Acceptance Criteria**:
  - `GET /health` still works (no regressions)
  - `POST /ai/deck/build` is accessible at the expected path

### Task 4: Test Suite (`tests/ai/test_deck_builder.py`)
- **Files**: New file `tests/ai/test_deck_builder.py`
- **Description**: Create comprehensive test suite with >= 8 tests covering all acceptance criteria. Follow existing patterns from `tests/ai/test_card_eval.py`. Use module-level helper functions for card/game creation.
- **Acceptance Criteria**: All tests pass, no regressions in existing test suite

---

## Testing Strategy

### Unit Tests (Engine Layer) — `tests/ai/test_deck_builder.py`

| # | Test Name | What It Verifies | Acceptance Criterion Covered |
|---|-----------|-----------------|------------------------------|
| 1 | `test_filter_removes_banned_cards` | Banned cards excluded from filtered pool for given format | Banned cards excluded |
| 2 | `test_filter_enforces_singleton_legacy` | Legacy/Vintage/Commander/Brawl: max 1 copy of non-basic-land cards | Singleton enforcement |
| 3 | `test_filter_commander_color_identity` | Cards outside commander color identity excluded; commanders always included | Commander color identity validation |
| 4 | `test_score_aggro_boosts_low_cmc` | Aggro strategy gives higher composite scores to low-CMC creatures than high-CMC | Strategy weights work |
| 5 | `test_score_control_boosts_removal_counterspells` | Control strategy boosts removal and counterspell categories | Strategy weights work |
| 6 | `test_select_deck_size_minimum_60` | Non-Commander deck has at least 60 cards when pool is sufficient | Deck size minimums |
| 7 | `test_select_commander_deck_size_100` | Commander deck totals exactly 100 cards including commanders | Deck size for Commander |
| 8 | `test_sideboard_fills_to_15` | Sideboard populated with up to 15 best remaining legal cards (non-Commander) | Sideboard construction |
| 9 | `test_validation_failures_returned_in_response` | If FMT-01 validation fails, response includes violations and valid=False | Validation before return |
| 10 | `test_invalid_format_rejected` | Unknown format returns error in engine (400 at API layer) | Invalid format handling |
| 11 | `test_deterministic_results_with_seed` | Same inputs + seed produce identical deck output twice | Deterministic tie-breaking |
| 12 | `test_build_deck_full_pipeline_modern_aggro` | End-to-end: pool → filter → score → select → validate for Modern aggro | Full pipeline integration |

### API Integration Tests (API Layer) — same file or separate

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 13 | `test_api_endpoint_returns_deck` | POST /ai/deck/build returns HTTP 200 with valid deck structure |
| 14 | `test_api_unknown_format_400` | Unknown format returns HTTP 400 |

### Test Patterns (following existing conventions)

```python
import pytest
from mtg_engine.models.game import Card
from mtg_engine.ai.deck_builder import build_deck, filter_card_pool, score_cards

def _make_card(name: str, mana_cost: str = "{1}", type_line: str = "Creature — Beast",
               oracle_text: str = "", cmc: float = 1.0, colors: list[str] | None = None,
               color_identity: list[str] | None = None, keywords: list[str] | None = None,
               set_code: str | None = None, rarity: str | None = None) -> Card:
    return Card(
        name=name, mana_cost=mana_cost, type_line=type_line, oracle_text=oracle_text,
        cmc=cmc, colors=colors or [], color_identity=color_identity or [],
        keywords=keywords or [], set_code=set_code, rarity=rarity,
    )

def test_filter_removes_banned_cards():
    """Banned cards are excluded from the filtered pool."""
    pool = [
        _make_card("Legal Card", set_code="MOM"),
        _make_card("Bane of the Living", set_code="MOM"),  # Banned in Modern
    ]
    filtered = filter_card_pool(pool, "modern")
    names = {c.name for c in filtered}
    assert "Bane of the Living" not in names
    assert "Legal Card" in names

def test_score_aggro_boosts_low_cmc():
    """Aggro strategy gives higher scores to low-CMC creatures."""
    low_cmc = _make_card("Goblin", cmc=1, type_line="Creature — Goblin", oracle_text="")
    high_cmc = _make_card("Dragon", cmc=7, type_line="Creature — Dragon", oracle_text="")
    
    scored_low = score_cards([low_cmc], "aggro")[0]
    scored_high = score_cards([high_cmc], "aggro")[0]
    
    assert scored_low.composite_score > scored_high.composite_score

def test_build_deck_full_pipeline_modern_aggro():
    """End-to-end deck building for Modern aggro."""
    pool = []
    # Add 100+ legal cards with varied types
    for i in range(30):
        pool.append(_make_card(f"Aggro Creature {i}", cmc=2, mana_cost="{1}{R}", 
                               type_line="Creature — Goblin", oracle_text="", set_code="MOM"))
    for i in range(20):
        pool.append(_make_card(f"Mountain {i}", cmc=0, type_line="Land — Mountain", set_code="MOM"))
    for i in range(10):
        pool.append(_make_card(f"Lightning Bolt {i}", cmc=1, mana_cost="{R}",
                               type_line="Instant", oracle_text="deals 3 damage to any target.", set_code="MOM"))
    
    result = build_deck(pool, "modern", "aggro", seed=42)
    
    assert len(result.deck) >= 60
    assert result.validation["valid"] is True
```

---

## Potential Risks

1. **Risk**: Card pool too small to fill deck minimum → **Mitigation**: Return whatever cards were selected with validation errors explaining the shortfall. API returns HTTP 200 (not an error) — it's a valid response that the deck couldn't be completed.

2. **Risk**: Commander not found in card pool by name → **Mitigation**: If `commander_names` provided but no matching cards exist, log warning and proceed without locking commanders. Validation will catch missing commander if format requires one.

3. **Risk**: All lands filtered out (e.g., color identity mismatch) → **Mitigation**: Land balancing step in Stage 3 ensures minimum land count. If still insufficient, validation catches it.

4. **Risk**: Performance on large card pools (1000+ cards) → **Mitigation**: Single-pass greedy algorithm is O(n log n). For 1000 cards this is trivial. No async needed — response time < 100ms expected.

5. **Risk**: `estimate_card_quality()` accepts `dict` but we have `Card` objects → **Mitigation**: Use `card.model_dump()` to convert Card to dict before passing to card_eval.py functions. This matches the existing pattern in card_eval.py which expects dict input.

---

## Handoff to Implementer

**Design Document**: `specs/038-gap-analysis/APP-02-design.md` (this file)
**User Story**: APP-02 — Automated deck building from card pool, format, and strategy
**Estimated Complexity**: Medium
**Key Files**:
1. `mtg_engine/ai/deck_builder.py` — Core algorithm (new)
2. `mtg_engine/api/routers/deck_build_ai.py` — API endpoint (new)
3. `tests/ai/test_deck_builder.py` — Test suite (new)
4. `mtg_engine/api/main.py` — Router mounting (modify)

**Start With**: Task 1 — Implement the core algorithm module (`deck_builder.py`). This is the foundation; Tasks 2-4 depend on it being functional.

**Acceptance Criteria**:
- [ ] `POST /ai/deck/build` endpoint accepts card_pool, format, strategy, commander_names
- [ ] Returns deck (list of name/quantity), sideboard, and validation result
- [ ] Strategy parameter supports aggro/control/midrange/combo with different scoring weights
- [ ] Deck respects format rules: size minimums, banned cards excluded, singleton enforcement
- [ ] Commander format validates color identity and includes commanders in 100-card total
- [ ] Uses `estimate_card_quality()` as baseline, modified by strategy weights and CMC curve targeting
- [ ] Deck validated via FMT-01 before returning; errors included if validation fails
- [ ] Sideboard fills remaining legal cards up to 15 (non-Commander formats)
- [ ] Cards outside legality window excluded from consideration
- [ ] >= 8 tests covering all axes
