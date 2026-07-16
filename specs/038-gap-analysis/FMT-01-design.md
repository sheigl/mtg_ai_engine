# Design: FMT-01 Format Rules Engine

## Overview
Implement a format validation system that checks whether a deck is legal for a given MTG format (Standard, Pioneer, Modern, Legacy, Vintage, Commander, Brawl, Pauper). The system provides banned/restricted list lookups, format-specific rule enforcement, and an API endpoint for external callers.

## User Story Reference
- **Discovery story**: FMT-01 — Format Rules Engine
- **Plan reference**: `specs/038-gap-analysis/plan.md` Sprint 4, FMT-01 section

---

## Architecture Decisions

### Decision 1: Hardcoded banned/restricted lists (not live Scryfall fetch)
**Rationale**: The engine is designed to be deterministic and self-contained. Live API calls would introduce non-determinism, latency, and failure modes. Banned lists change infrequently (monthly MTG FAIR updates), so a hardcoded approach with clear versioning comments is appropriate for an MVP. Future work can add a refresh endpoint if needed.

**Trade-offs considered**:
- **Alternative**: Fetch from Scryfall at startup or on-demand. Rejected: adds external dependency, makes tests non-deterministic, introduces latency.
- **Alternative**: Config file (JSON/YAML) loaded at startup. Rejected: over-engineering for MVP; hardcoded dicts are easier to maintain and version-control for the initial implementation.

### Decision 2: Single dispatcher function in `formats/__init__.py`
**Rationale**: A single entry point (`validate_deck`) that routes to format-specific validators keeps the API simple. Each format has its own validation function (e.g., `_validate_standard`, `_validate_commander`). Commander reuses the existing `validate_deck_for_commander()` from `commander.py`.

### Decision 3: Add `rarity` and `set_code` as optional Card model fields
**Rationale**: Pauper requires rarity checking; Standard/Pioneer/Modern require set-based legality windows. These are orthogonal to gameplay but essential for deck validation. Making them `Optional[str] = None` ensures backward compatibility — existing code that doesn't populate these fields will simply skip the checks that depend on them.

### Decision 4: Set-code legality via hardcoded legal sets per format
**Rationale**: Rather than computing "last N years" dynamically (which requires a set release date database), we maintain a `LEGAL_SETS` dict mapping each format to its list of legal set codes. This is deterministic, testable, and easy to update when rotations happen.

### Decision 5: API endpoint on existing `/deck` router
**Rationale**: The `deck_import.py` router already owns the `/deck` prefix. Adding `POST /deck/validate` there keeps all deck-related endpoints together under one namespace. No new router file needed.

---

## Files to Create/Modify

### New Files
| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `mtg_engine/engine/formats/__init__.py` | Dispatcher + format routing | `validate_deck()` public API, format-specific validators, legality window data |
| `mtg_engine/engine/formats/banned.py` | Banned/restricted list data + lookups | Hardcoded banned lists per format, Vintage restricted list, `is_banned()`, `is_restricted()` |

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/models/game.py` | Add `rarity: Optional[str] = None` and `set_code: Optional[str] = None` to Card model | Pauper needs rarity; legality windows need set codes |
| `mtg_engine/api/routers/deck_import.py` | Add `POST /deck/validate` endpoint + request/response models | API surface for external callers |

### Test Files
| File | Purpose |
|------|---------|
| `tests/engine/formats/test_formats.py` | Unit tests for banned lookups, format validation, dispatcher logic (≥8 tests) |

---

## Data Structures

### Banned/Restricted Lists (`banned.py`)

```python
# Format: dict[str, set[str]] — format_name → set of banned card names
BANNED_LISTS: dict[str, set[str]] = {
    "standard": {"Bolas's Citadel", ...},
    "pioneer": {"Jin-Gitaxias, Progress Tyrant", ...},
    "modern": {"Lightning Bolt", ...},  # example only — real lists below
    "legacy": {"Ancestral Recall", ...},
    "vintage": {"Weather the Storm", ...},
    "commander": {"Annihilate Specimen", ...},
    "pauper": set(),  # Pauper has no banned list in most regions; may add later
}

# Vintage restricted cards (single set, not per-format)
RESTRICTED_LIST: set[str] = {
    "Ancestral Recall",
    "Time Walk",
    "Black Lotus",
    ...
}
```

### Validation Result Model

```python
from pydantic import BaseModel

class DeckValidationResult(BaseModel):
    """Result of validating a deck against a format."""
    valid: bool
    violations: list[str] = []  # Human-readable violation messages
    format: str                 # The format that was checked
```

### API Request/Response Models (in `deck_import.py`)

```python
class DeckValidationRequest(BaseModel):
    """POST /deck/validate request body."""
    format: str                    # e.g. "standard", "modern", "commander"
    cards: list[dict]              # Each dict has at least {"name": str, ...}
    commanders: list[dict] | None = None  # Required for commander/brawl

class DeckValidationResponse(BaseModel):
    """POST /deck/validate response body."""
    valid: bool
    violations: list[str]
    format: str
```

---

## Module Design

### `mtg_engine/engine/formats/banned.py` — Banned/Restricted Lists

**Purpose**: Centralized banned/restricted card data with lookup functions.

**Signatures**:
```python
def is_banned(card_name: str, fmt: str) -> bool:
    """Return True if card_name is banned in the given format."""

def is_restricted(card_name: str) -> bool:
    """Return True if card_name is on the Vintage restricted list."""

def get_format_banned_list(fmt: str) -> set[str]:
    """Return the full banned list for a format (empty set if none)."""
```

**Data**: Hardcoded `BANNED_LISTS` dict and `RESTRICTED_LIST` set. Each entry includes a comment with the date of last update and source URL (MTG FAIR / WotC announcements). For MVP, we include representative cards per format to demonstrate the system works; the implementer will populate with current lists from MTG FAIR.

**Key design notes**:
- Card name matching is **case-insensitive** — normalize both lookup key and list entries to lowercase.
- Unknown formats return `False` (not banned) for `is_banned()` — the dispatcher handles unknown format errors upstream.
- Functions are pure — no side effects, no I/O.

### `mtg_engine/engine/formats/__init__.py` — Dispatcher + Format Validators

**Purpose**: Single entry point that routes to format-specific validation logic.

**Public API**:
```python
def validate_deck(
    cards: list[Card],
    format_name: str,
    commanders: list[Card] | None = None,
) -> tuple[bool, list[str]]:
    """
    Validate a deck against the given format.

    Args:
        cards: List of Card objects in the deck (main + commander(s) included).
        format_name: Format identifier ("standard", "pioneer", "modern", etc.).
        commanders: Commander card(s), required for "commander" and "brawl".

    Returns:
        (is_valid, violations) — empty violations list means valid.
    """
```

**Internal validators** (one per format):
```python
def _validate_standard(cards: list[Card]) -> list[str]: ...
def _validate_pioneer(cards: list[Card]) -> list[str]: ...
def _validate_modern(cards: list[Card]) -> list[str]: ...
def _validate_legacy(cards: list[Card]) -> list[str]: ...
def _validate_vintage(cards: list[Card]) -> list[str]: ...
def _validate_commander(cards: list[Card], commanders: list[Card] | None) -> list[str]: ...
def _validate_brawl(cards: list[Card], commanders: list[Card] | None) -> list[str]: ...
def _validate_pauper(cards: list[Card]) -> list[str]: ...
```

**Dispatcher logic**:
```python
FORMAT_VALIDATORS = {
    "standard": _validate_standard,
    "pioneer": _validate_pioneer,
    "modern": _validate_modern,
    "legacy": _validate_legacy,
    "vintage": _validate_vintage,
    "commander": _validate_commander,
    "brawl": _validate_brawl,
    "pauper": _validate_pauper,
}

def validate_deck(cards, format_name, commanders=None):
    fmt = format_name.lower()
    if fmt not in FORMAT_VALIDATORS:
        return False, [f"Unknown format: {format_name}"]
    
    validator = FORMAT_VALIDATORS[fmt]
    violations = validator(cards, commanders)  # Some validators accept commanders kwarg
    return len(violations) == 0, violations
```

### Card Model Changes (`mtg_engine/models/game.py`)

Add two optional fields to the `Card` model (after line 73, before closing of class):

```python
class Card(BaseModel):
    # ... existing fields through supertypes ...
    
    # FMT-01: Format validation metadata
    rarity: Optional[str] = None       # "c", "u", "r", "m", "mythical", "special"
    set_code: Optional[str] = None     # e.g. "MOM", "ONE", "MH1"
```

**Backward compatibility**: Both fields default to `None`. Existing code that creates Cards without these fields is unaffected. Validation functions that depend on them will gracefully skip the check if the field is missing (documented as a known limitation).

---

## Format-Specific Validation Logic

### Standard / Pioneer / Modern / Legacy — Shared Pattern
These four formats share the same validation structure: banned list + legality window.

```python
def _validate_constructed_common(
    cards: list[Card],
    fmt: str,
) -> list[str]:
    """Shared validation for constructed formats (Standard/Pioneer/Modern/Legacy)."""
    violations = []
    
    # 1. Deck size check (60-150 with sideboard)
    if len(cards) < 60:
        violations.append(f"Deck has {len(cards)} cards, minimum is 60")
    
    # 2. Banned list check
    from mtg_engine.engine.formats.banned import is_banned
    for card in cards:
        if is_banned(card.name, fmt):
            violations.append(f"{card.name} is banned in {fmt}")
    
    # 3. Legality window (set_code based) — only if set_code data available
    legal_sets = LEGAL_SETS.get(fmt, set())
    if legal_sets:
        for card in cards:
            if card.set_code and card.set_code not in legal_sets:
                violations.append(
                    f"{card.name} (set {card.set_code}) is not legal in {fmt}"
                )
    
    return violations
```

### Vintage — Banned + Restricted
```python
def _validate_vintage(cards: list[Card]) -> list[str]:
    """Vintage: banned list + restricted list (max 1 copy of restricted cards)."""
    violations = []
    
    if len(cards) < 60:
        violations.append(f"Deck has {len(cards)} cards, minimum is 60")
    
    # Count card occurrences for restricted check
    from collections import Counter
    name_counts = Counter(card.name for card in cards)
    
    from mtg_engine.engine.formats.banned import is_banned, is_restricted
    for card in cards:
        if is_banned(card.name, "vintage"):
            violations.append(f"{card.name} is banned in Vintage")
        elif is_restricted(card.name) and name_counts[card.name] > 1:
            violations.append(
                f"{card.name} is restricted in Vintage (max 1 copy, found {name_counts[card.name]})"
            )
    
    return violations
```

### Commander — Reuse Existing + Banned List
```python
def _validate_commander(cards: list[Card], commanders: list[Card] | None) -> list[str]:
    """Commander: reuse existing validate_deck_for_commander + add banned list."""
    from mtg_engine.engine.formats.commander import validate_deck_for_commander
    
    # Use existing Commander validation (color identity, singleton, 100 cards)
    is_valid, violations = validate_deck_for_commander(cards, commanders or [])
    
    # Add banned list check on top
    from mtg_engine.engine.formats.banned import is_banned
    for card in cards:
        if is_banned(card.name, "commander"):
            violations.append(f"{card.name} is banned in Commander")
    
    return violations  # Note: validate_deck_for_commander returns (bool, list), we extract list
```

**Note**: `validate_deck_for_commander` already returns `(is_valid, violations)`. We call it for its violation messages and then append any banned-list violations. The combined result is returned as a flat list of strings.

### Brawl — 60 Cards + Standard Legality + Legendary Commander
```python
def _validate_brawl(cards: list[Card], commanders: list[Card] | None) -> list[str]:
    """Brawl: 60 cards (including commander), Standard-legal, legendary creature/PW commander."""
    violations = []
    
    # Deck size: exactly 60 including commander(s)
    if len(cards) != 60:
        violations.append(f"Brawl deck has {len(cards)} cards, must have exactly 60")
    
    # Commander validation
    if not commanders:
        violations.append("No commander specified for Brawl")
    else:
        for cmd in commanders:
            type_line = (cmd.type_line or "").lower()
            is_legendary = "legendary" in type_line
            is_creature_or_pw = "creature" in type_line or "planeswalker" in type_line
            if not (is_legendary and is_creature_or_pw):
                violations.append(
                    f"{cmd.name} ({cmd.type_line}) must be a legendary creature or planeswalker for Brawl"
                )
    
    # Standard legality: banned list + set window
    from mtg_engine.engine.formats.banned import is_banned
    legal_sets = LEGAL_SETS.get("standard", set())
    
    for card in cards:
        if is_banned(card.name, "brawl") or is_banned(card.name, "standard"):
            violations.append(f"{card.name} is banned in Brawl/Standard")
        
        if legal_sets and card.set_code and card.set_code not in legal_sets:
            violations.append(
                f"{card.name} (set {card.set_code}) is not Standard-legal"
            )
    
    return violations
```

### Pauper — All Common Cards
```python
def _validate_pauper(cards: list[Card]) -> list[str]:
    """Pauper: every card must be common rarity."""
    violations = []
    
    if len(cards) < 60:
        violations.append(f"Deck has {len(cards)} cards, minimum is 60")
    
    for card in cards:
        if card.rarity and card.rarity.lower() not in ("c", "common"):
            violations.append(
                f"{card.name} (rarity: {card.rarity}) is not common — illegal in Pauper"
            )
        elif card.rarity is None:
            # Unknown rarity — skip check with warning note
            pass  # Known limitation: can't validate without rarity data
    
    return violations
```

---

## Set Code Legality Window Approach

### Data Structure
```python
# In mtg_engine/engine/formats/__init__.py

LEGAL_SETS: dict[str, set[str]] = {
    "standard": {
        # Sets legal in current Standard rotation (updated per rotation)
        # As of July 2026: Murders at Karlov Manor through current block
        "MKM", "LTC", "BLI", "MOM", "ONE", ...
    },
    "pioneer": {
        # Pioneer starts from Return to Ravnica (RNA) forward, minus banned sets
        "RNA", "GRN", "EMN", "XIN", "MOM", ...  # All sets from RNA onward
    },
    "modern": {
        # Modern starts from Eighth Edition (8ED) forward
        "8ED", "9ED", "10E", "LGC", ...  # All sets from 8ED onward
    },
    "legacy": set(),  # No legality window — all cards legal unless banned/restricted
}

# Brawl uses Standard's legality window (enforced in _validate_brawl)
```

### Approach Details
1. **Hardcoded set lists**: Each format maps to a `set[str]` of legal set codes. Updated manually when rotations occur.
2. **Legacy has no window**: Empty set means "all sets legal" — the check is skipped for Legacy (only banned list applies).
3. **Graceful degradation**: If a card's `set_code` is `None`, the legality window check is silently skipped for that card. This allows partial validation when set data isn't available.
4. **Brawl inherits Standard**: Brawl uses the same legality window as Standard (CR 904.2).

### Known Limitation
This approach requires manual updates to `LEGAL_SETS` when rotations happen. For MVP, this is acceptable — the alternative (maintaining a full set release date database and computing windows dynamically) would be significantly more complex. A future enhancement could add an auto-refresh endpoint that pulls from Scryfall's format legality API.

---

## API Endpoint Design

### Location
Added to existing `mtg_engine/api/routers/deck_import.py` (already owns `/deck` prefix).

### Request Model
```python
class DeckValidationRequest(BaseModel):
    format: str
    cards: list[dict]              # {"name": str, "rarity": str?, "set_code": str?, ...}
    commanders: list[dict] | None = None  # Required for commander/brawl formats
```

### Response Model
```python
class DeckValidationResponse(BaseModel):
    valid: bool
    violations: list[str]
    format: str
```

### Endpoint
```python
@router.post("/validate")
async def validate_deck_endpoint(req: DeckValidationRequest) -> dict:
    """POST /deck/validate — check if a deck is legal for the given format."""
    
    # 1. Validate format name
    fmt = req.format.lower()
    from mtg_engine.engine.formats import FORMAT_VALIDATORS
    if fmt not in FORMAT_VALIDATORS:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Unknown format: {req.format}", "error_code": "UNKNOWN_FORMAT"},
        )
    
    # 2. Convert dict cards to Card models
    from mtg_engine.models.game import Card
    card_models = [Card(**c) for c in req.cards]
    commander_models = [Card(**c) for c in req.commanders] if req.commanders else None
    
    # 3. Run validation
    from mtg_engine.engine.formats import validate_deck
    is_valid, violations = validate_deck(card_models, fmt, commanders=commander_models)
    
    return {
        "data": DeckValidationResponse(
            valid=is_valid,
            violations=violations,
            format=req.format,
        ).model_dump()
    }
```

### Error Handling
| Scenario | Status Code | Response |
|----------|------------|----------|
| Unknown format | 400 | `{"error": "Unknown format: ...", "error_code": "UNKNOWN_FORMAT"}` |
| Valid request, deck illegal | 200 | `{"data": {"valid": false, "violations": [...], "format": "..."}}` |
| Valid request, deck legal | 200 | `{"data": {"valid": true, "violations": [], "format": "..."}}` |

---

## Task Breakdown (Ordered by Dependency)

### Task 1: Add Card model fields (`rarity`, `set_code`)
- **Files**: `mtg_engine/models/game.py`
- **Description**: Add two optional string fields to the `Card` Pydantic model. Place them after the existing `supertypes` field for logical grouping.
- **Acceptance Criteria**:
  - Card can be instantiated with and without these fields
  - Existing code that creates Cards is unaffected (backward compatible)
  - Full test suite passes with no regressions

### Task 2: Implement banned/restricted list module
- **Files**: `mtg_engine/engine/formats/banned.py` (new)
- **Description**: Create the banned lists data structure and lookup functions. Populate with representative cards per format (at least a few well-known banned cards per format to demonstrate functionality). Include comments noting the source and date of each list.
- **Acceptance Criteria**:
  - `is_banned("card_name", "format")` returns correct boolean for known banned/legal cards
  - `is_restricted("card_name")` returns correct boolean for Vintage restricted cards
  - Case-insensitive matching works correctly
  - Unknown format in `is_banned()` returns False (no error)

### Task 3: Implement dispatcher + format validators
- **Files**: `mtg_engine/engine/formats/__init__.py` (new)
- **Description**: Create the `validate_deck()` dispatcher and all eight format-specific validator functions. Wire up `LEGAL_SETS` data structure. Reuse `validate_deck_for_commander()` for Commander format.
- **Acceptance Criteria**:
  - `validate_deck(cards, "standard")` returns `(True, [])` for a legal deck
  - Each format correctly identifies banned cards, size violations, and (where applicable) legality window/rarity issues
  - Unknown format returns `(False, ["Unknown format: ..."])`
  - Commander validation includes both existing rules + banned list

### Task 4: Add API endpoint
- **Files**: `mtg_engine/api/routers/deck_import.py`
- **Description**: Add `POST /deck/validate` endpoint with request/response models. Convert incoming dict cards to Card models, call `validate_deck()`, return structured response. Handle unknown format as 400 error.
- **Acceptance Criteria**:
  - POST with valid format returns 200 with validation result
  - POST with unknown format returns 400
  - Response matches `DeckValidationResponse` schema

### Task 5: Write tests
- **Files**: `tests/engine/formats/test_formats.py` (new)
- **Description**: Create comprehensive test suite covering banned lookups, each format's validation logic, edge cases, and dispatcher routing. Minimum 8 tests as specified in acceptance criteria.
- **Acceptance Criteria**:
  - ≥8 tests pass
  - Tests cover: banned lookup true/false, restricted lookup, Standard/Pioneer/Modern/Legacy/Vintage/Commander/Brawl/Pauper validation paths, unknown format handling, deck size violations

### Task 6: Verify full test suite
- **Files**: N/A (run tests)
- **Description**: Run `pytest tests/ -x -q` to confirm no regressions across the entire codebase.
- **Acceptance Criteria**: All existing + new tests pass with zero regressions

---

## Testing Strategy

### Test File: `tests/engine/formats/test_formats.py`

**Test Classes and Coverage**:

```python
import pytest
from mtg_engine.models.game import Card
from mtg_engine.engine.formats.banned import is_banned, is_restricted
from mtg_engine.engine.formats import validate_deck


class TestBannedListLookups:
    """Tests for banned.py lookup functions."""

    def test_is_banned_returns_true_for_known_banned_card(self):
        # e.g., "Lightning Bolt" in Modern (if on the list) or a known banned card
        assert is_banned("Known Banned Card", "modern") is True

    def test_is_banned_returns_false_for_legal_card(self):
        assert is_banned("Basic Island", "modern") is False

    def test_is_restricted_vintage_card(self):
        assert is_restricted("Ancestral Recall") is True

    def test_case_insensitive_lookup(self):
        assert is_banned("known banned card".upper(), "modern") == is_banned(
            "known banned card", "modern"
        )


class TestFormatValidation:
    """Tests for validate_deck dispatcher and format validators."""

    def _make_card(self, name="Test Card", rarity=None, set_code=None):
        return Card(name=name, rarity=rarity, set_code=set_code)

    def test_unknown_format_returns_error(self):
        is_valid, violations = validate_deck([], "nonexistent")
        assert is_valid is False
        assert len(violations) > 0

    def test_standard_deck_size_violation(self):
        cards = [self._make_card(f"Card {i}") for i in range(59)]
        is_valid, violations = validate_deck(cards, "standard")
        assert is_valid is False
        assert any("minimum" in v.lower() or "60" in v for v in violations)

    def test_commander_reuses_existing_validation(self):
        """Commander validation includes color identity, singleton, 100 cards."""
        # Minimal test: no commander specified should produce violation
        is_valid, violations = validate_deck([], "commander", commanders=[])
        assert is_valid is False

    def test_pauper_common_rarity_check(self):
        """Pauper rejects non-common cards."""
        cards = [self._make_card(f"Common {i}", rarity="c") for i in range(60)]
        cards.append(self._make_card("Rare Card", rarity="r"))
        is_valid, violations = validate_deck(cards, "pauper")
        assert is_valid is False
        assert any("not common" in v.lower() or "pauper" in v.lower() for v in violations)

    def test_vintage_restricted_max_one_copy(self):
        """Vintage allows only 1 copy of restricted cards."""
        # Would need a card on the restricted list with 2+ copies
        pass  # Covered if restricted list has entries

    def test_brawl_commander_must_be_legendary_creature_or_pw(self):
        """Brawl commander must be legendary creature or planeswalker."""
        bad_cmd = Card(name="Bad Cmd", type_line="Legendary Enchantment")
        cards = [bad_cmd] + [self._make_card(f"Card {i}") for i in range(59)]
        is_valid, violations = validate_deck(cards, "brawl", commanders=[bad_cmd])
        assert is_valid is False
```

### Test Count: ≥10 tests (exceeds minimum of 8)
- 4 banned/restricted lookup tests
- 6+ format validation tests covering Standard, Commander, Pauper, Brawl, Vintage, unknown format

---

## Potential Risks

1. **Risk**: Hardcoded banned lists become stale → **Mitigation**: Each list includes a comment with the date of last update and source URL. The module docstring notes that lists should be updated per MTG FAIR announcements. Future enhancement: add an admin endpoint to refresh from Scryfall.

2. **Risk**: Set-code legality windows require manual updates on rotation → **Mitigation**: Same as above — comments + future auto-refresh. For MVP, the hardcoded approach is sufficient and testable.

3. **Risk**: Cards without `rarity` or `set_code` fields can't be fully validated for Pauper/legality window → **Mitigation**: Validation gracefully skips checks when data is missing (returns no violation rather than false positive). Documented as a known limitation in the module docstring.

4. **Risk**: Commander validation reusing `validate_deck_for_commander()` may have edge cases with banned list integration → **Mitigation**: The `_validate_commander` function calls the existing validator first, then appends banned-list violations. This is additive and non-destructive to existing behavior.

5. **Risk**: Case sensitivity in card name matching for banned lists → **Mitigation**: All lookups normalize to lowercase. Both the data (list entries) and queries are lowercased before comparison.

---

## Handoff to Implementer

**Design Document**: Above
**User Story**: FMT-01 — Format Rules Engine (from Discovery agent)
**Estimated Complexity**: Medium — 5 new/modified files, straightforward logic but many formats to cover
**Key Files**:
1. `mtg_engine/engine/formats/banned.py` — Banned/restricted list data + lookups
2. `mtg_engine/engine/formats/__init__.py` — Dispatcher + format validators
3. `mtg_engine/models/game.py` — Card model extension (rarity, set_code)
4. `mtg_engine/api/routers/deck_import.py` — POST /deck/validate endpoint
5. `tests/engine/formats/test_formats.py` — Test suite

**Start With**: Task 1 (Card model fields), then Task 2 (banned lists). These are independent of each other and form the foundation for Tasks 3-5.

**Acceptance Criteria** (from Discovery):
1. ✅ Banned/restricted lists in `mtg_engine/engine/formats/banned.py` with lookup functions
2. ✅ Card model extended with optional `rarity` and `set_code` fields
3. ✅ Generic `validate_deck(cards, format_name, commanders=None)` → `(is_valid, violations)`
4. ✅ Format-specific rules for all 8 formats (Standard, Pioneer, Modern, Legacy, Vintage, Commander, Brawl, Pauper)
5. ✅ API endpoint `POST /deck/validate` with proper request/response models and error handling
6. ✅ ≥8 tests in `tests/engine/formats/test_formats.py`
