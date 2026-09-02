# Technical Plan: Fortify Keyword Module (CR 702.54a)

**Story:** [SPRINT7-P0-fortify-keyword.md](../SPRINT7-P0-fortify-keyword.md)
**Status:** Planned
**Date:** 2026-08-25
**Estimate:** M (~1.5–2 days incl. tests)

---

## 1. Overview

Implement the **Fortify** keyword (CR 702.54a, current CR 702.67a) as a full keyword module. Fortify is an **activated ability of Fortification cards**: *"Fortify [cost]: Attach this Fortification to target land you control. Activate only as a sorcery."* A Fortification is an artifact with the land subtype `Fortification` (CR 301.7) — it is a **land** that can be played as a land drop and, once on the battlefield, can be attached to another land you control.

This plan reuses the engine's existing **attachment infrastructure** (built for Auras/Equipment): `Permanent.attached_to`, `Permanent.attachments`, the Equipment SBA unattach pattern, `check_attach_triggers`, and `_update_battlefield`.

**Out of scope (explicit):**
- **Equip** (7-5b) — attaches Equipment to creatures. Not designed or modified here.
- **"fortified land" reference resolution** — the static/triggered abilities on the two real cards that reference the attached land (e.g., "Fortified land has indestructible", "Whenever fortified land is tapped for mana…"). Follow-up story.

---

## 2. CR Rule-Text Adjudication

### 2.1 Correction to the draft
The draft story described Fortify as *"put +N/+N counters on target creature."* **That is wrong.** Authoritative sources confirm Fortify is an **attach-to-land** mechanic (the land-analogue of Equip), not a counters mechanic.

- **CR 702.54a** (old numbering; **702.67a** in the current CR as of TMNT, 2025-11-14):
  > "Fortify is an activated ability of Fortification cards. 'Fortify [cost]' means '[cost]: **Attach this Fortification to target land you control.** Activate this ability only any time you could cast a sorcery.'"
- **CR 301.7 (Fortifications):**
  > "A Fortification is an artifact with the land subtype Fortification. A Fortification enters the battlefield unattached and stays on the battlefield if the land it's attached to leaves."

The draft's "counters" text was a confusion with C.A.M.P.'s *triggered* ability ("…put a +1/+1 counter on target creature you control…"), which is a separate ability on the card, not the Fortify keyword.

### 2.2 Real card oracle texts
**Local Scryfall SQLite cache: ZERO Fortify cards** (`mtg_engine/card_data/cache.db` has 319 cards, none with "fortify" in `keywords` or oracle text). Per the task instructions this is documented here; rule text falls back to the CR text above. The following two real texts were retrieved from the **Scryfall API** (`keyword:fortify` returns exactly 2 cards in all of MTG) as supplementary evidence:

1. **Darksteel Garrison** (Future Sight, 2007) — `Artifact — Fortification`, `{2}`, CMC 2:
   > "Fortified land has indestructible.
   > Whenever fortified land becomes tapped, target creature gets +1/+1 until end of turn.
   > **Fortify {3}** ({3}: Attach to target land you control. Fortify only as a sorcery. This card enters unattached and stays on the battlefield if the land leaves.)"

2. **C.A.M.P.** (Fallout, 2024) — `Artifact — Fortification`, `{3}`, CMC 3:
   > "Whenever fortified land is tapped for mana, put a +1/+1 counter on target creature you control. If that creature shares a color with the mana that land produced, create a Junk token. (It's an artifact with '{T}, Sacrifice this token: Exile the top card of your library. You may play that card this turn. Activate only as a sorcery.')
   > **Fortify {3}** ({3}: Attach to target land you control. Fortify only as a sorcery.)"

Note: the Fortify reminder text is **"(Fortify only as a sorcery.)"** — not "(Activate only as a sorcery.)". This matters for the timing-restriction parser (see §4.4 and T2).

---

## 3. Current-State Findings (verified against source)

| # | Finding | Location | Consequence |
|---|---------|----------|-------------|
| F1 | "Fortify {3} (…)" is parsed as `KeywordAbility(name='fortify {3}')`, **not** `ActivatedAbility` | `ability_parser.py` — `_ACTIVATED_RE` (line 131) only matches lines that *start* with a `{cost}`; the Fortify line starts with the word "Fortify" | `/activate` (filters `isinstance(a, ActivatedAbility)`, line 1182) and `_compute_legal_actions` (line 3193) never see the Fortify ability → **silent no-op** |
| F2 | "fortify" is already in the `KEYWORDS` frozenset | `ability_parser.py:85` | The line falls through to the single-keyword branch, producing the useless `KeywordAbility(name='fortify {3}')` |
| F3 | `/activate` non-mana effect handling only covers "add {X}" and "regenerate" | `game.py:1236-1254` | Even if the ability were surfaced, the attach effect has no handler |
| F4 | Sorcery-speed guard (US20 T162) only fires when `ability.timing_restriction` is set | `game.py:1194-1209`; `_TIMING_RE` at `ability_parser.py:135` = `\(activate only (?:as a sorcery|during [^)]+)\)` | The Fortify reminder text "(Fortify only as a sorcery.)" does not match `_TIMING_RE` → guard would not fire |
| F5 | Attachment infra already exists: `Permanent.attached_to: Optional[str]`, `Permanent.attachments: list[str]` | `models/game.py:103-104` | Reused directly |
| F6 | `_apply_equip` is the exact pure-transform attach pattern to mirror | `stack.py:1565-1601` (sets `attached_to`, appends to `attachments`, `_update_battlefield`, fires `check_attach_triggers`) | `_apply_fortify` mirrors it |
| F7 | Equipment SBA unattach pattern (CR 704.5n): attached to illegal permanent → `attached_to = None`, stays on battlefield | `sba.py:277-298` | Fortification SBA mirrors it (attached to non-land → unattach) |
| F8 | No centralized `is_land()` helper; engine uses ad-hoc `"land" in type_line.lower()` | `game.py:564, 2681, 2789, 2879, 2909, 3006, 3027, 3119, 3167, 3400`; `stack.py:575, 1362`; `combat/core.py:220`; `triggers.py:346, 493` | A Fortification's type line "Artifact — Fortification" has no literal "land" → not playable as a land drop and not a legal Fortify target unless handled |
| F9 | `play_land` rejects non-lands via `"land" not in card.type_line.lower()` | `game.py:564-565` | Fortification cannot be played as a land drop today |
| F10 | `Dash(CostKeyword)`, `Ninjutsu(CostKeyword)`, `Equip(CostKeyword)` | `dash.py:26`, `ninjutsu.py:26`, `equip.py:21` | Base-class precedent for activated-ability-style keywords is `CostKeyword` |
| F11 | `_compute_legal_actions` activate section (line 3189-3268) surfaces `ActivatedAbility` instances but does **not** validate targets | `game.py:3189-3268` | Fortify must add target validation (only offer if a valid land target exists) |

---

## 4. Architecture Decisions (8-item adjudication)

| # | Item | Decision | Rationale |
|---|------|----------|-----------|
| 1 | **Rule text** | Attach-to-land (CR 702.54a / 702.67a), **not** counters | Scryfall + CR authoritative; draft was wrong (§2) |
| 2 | **Keyword base class** | `Fortify(CostKeyword)` | Matches Dash/Ninjutsu/Equip precedent (F10). `CostKeyword.applies()` checks `name in keywords` |
| 3 | **Human/AI split + state** | Human: direct `POST /activate` with chosen target land (no pending choice — cost is mandatory, unlike Dash/Ninjutsu's optional cost). AI: `resolve_fortify_with_ai` auto-attaches to first valid land. **State = the attachment only** (`attached_to`/`attachments`) | No `pending_fortify_choice` field needed on `GameState` |
| 4 | **Sorcery-speed guard** | Extend `_TIMING_RE` to also match "(Fortify only as a sorcery.)" so the existing US20 T162 guard (F4) applies unchanged | Minimal, localized parser change; reuses existing guard logic |
| 5 | **Atomic transform** | `model_copy`-based, mirroring `_apply_equip` (F6) | Consistent with the pure-transform standard |
| 6 | **API wiring** | (a) parser Fortify branch → `ActivatedAbility`; (b) `/activate` attach-effect handler; (c) `_compute_legal_actions` Fortify action + target validation; (d) Fortification treated as a land for land-drop | See §5 |
| 7 | **Test plan** | Unit (`test_fortify.py`) + integration (`test_fortify_integration.py`) | See §7 |
| 8 | **Scope guard** | Fortify only. Equip (7-5b) untouched. "fortified land" reference resolution deferred | Prevents scope creep |

### 4.1 Valid-target definition (assumption, documented)
A Fortify activation targets **"a land you control."** A Fortification *is* a land, but attaching it to itself is nonsensical. **Decision:** valid targets = all permanents the acting player controls whose type line is land-like (contains "land" **or** "fortification"), **excluding the source Fortification itself**. This is documented as an assumption; if a ruling later permits self-attach, only the exclusion predicate changes.

### 4.2 Fortification is a land (land-drop + target)
Add a small helper `is_land_card(card) -> bool` (returns `"land" in type_line.lower() or is_fortification(card)`) and use it in the **Fortify-relevant** paths only:
- `play_land` endpoint (F9) — allow Fortification as a land drop.
- `_compute_legal_actions` land-drop section (F8, line 2681) — offer `play_land` for a Fortification in hand.
- Fortify target validation (new) — a land target is land-like.

**Do not** refactor the other ~10 ad-hoc land checks (out of scope, risky). A Fortification also **remains a land while attached** (it does not lose the land subtype on attach), so it stays a legal Fortify target and a legal land for other purposes.

### 4.3 Verified edge cases (review pass)
- **Fortification → Fortification attach is legal.** Both are lands, so "target land you control" permits attaching one Fortification to another. The §4.1 valid-target rule (land-like, excluding *self*) already allows this. Intended; covered by a test.
- **`{T}` in the Fortify cost is handled for free.** The two real cards use mana-only costs, but `/activate` already processes a `{T}` in `ability.cost` (game.py:1220-1223: checks `perm.tapped`, sets it). So a hypothetical "Fortify {T}{3}" would work without extra code. No change needed; noted for robustness.
- **One-land-per-turn is respected.** `play_land` increments `player.lands_played_this_turn` (game.py:571); a Fortification played as a land counts toward it and blocks a second land drop that turn. Covered by a test.
- **`put_permanent_onto_battlefield` is safe for a Fortification.** Verified (zones.py:628-755): no land-specific behavior a Fortification trips over. Planeswalker/Saga/Fading/ETB-choice/enters-tapped branches are all N/A. Sunburst (line 746) is bypassed because a land drop uses `from_zone="hand"`, not `"stack"`. So reusing `play_land`'s `put_permanent_onto_battlefield(..., from_zone="hand")` call is correct as-is.
- **SBA must clean the host's `attachments` list** (see §5.4) — the Equipment SBA leaves a stale reference; we match the `zones.py` zone-change cleanup instead.

### 4.4 Parser extension vs. dedicated API path (decision + reasoning)
**Decision: extend the parser** (emit an `ActivatedAbility` for "Fortify {cost} (…)") rather than adding a dedicated Fortify API path that bypasses the parser.

Reasoning:
- Fortify **is** an activated ability (CR 602). The engine's entire activated-ability machinery — sorcery-speed guard (US20 T162), split-second (US32), mana-cost payment, and the `_compute_legal_actions` activate section — is built around `ActivatedAbility`. Routing Fortify through a dedicated path would **duplicate** all of that machinery.
- The parser change is **low-risk and surgical**: the new branch is gated on lines that *start* with "Fortify" (only 2 cards in all of MTG), and the `_TIMING_RE` change only *adds* a "fortify" alternative. It cannot affect any other card's parsing.
- It makes Fortify surface **automatically** in `_compute_legal_actions` (which iterates `ActivatedAbility` instances) and handleable by `/activate` (which filters `ActivatedAbility`), with only the small targeted additions in §5.5.
- The alternative (dedicated path) would leave "Fortify {3} (…)" mis-parsed as `KeywordAbility(name='fortify {3}')` forever, and require re-implementing timing/split-second/cost logic — strictly more code and more divergence from the codebase conventions.

---

## 5. Files to Create / Modify

### 5.1 NEW — `mtg_engine/ability/keywords/fortify.py`
```python
class Fortify(CostKeyword):
    name = "fortify"

    # Detection / parsing (module-level + static)
    @staticmethod
    def parse_fortify_cost(oracle_text: str) -> str | None:
        """'Fortify {3}' -> '{3}'; 'Fortify {2}{R}' -> '{2}{R}'; else None."""
    @staticmethod
    def has_fortify(card: Card) -> bool:
        """True if 'fortify' in card.keywords OR a 'Fortify {cost}' clause is present."""
    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """True if a 'Fortify {cost}' clause is present (matches Flashback/Escape/Dash convention)."""
    @staticmethod
    def is_fortification(card: Card) -> bool:
        """True if 'fortification' in card.type_line.lower() (CR 301.7 — it's a land)."""
    @staticmethod
    def is_land_card(card: Card) -> bool:
        """'land' in type_line OR is_fortification(card). Used for land-drop + Fortify targets."""

    def applies(self, game_state, permanent) -> bool: ...  # inherited CostKeyword
    def apply(self, game_state, permanent, target=None) -> GameState:
        """Full Fortify logic (CR 702.54a). Pure transform.
        - validate source is on battlefield + controlled by acting player
        - validate target is a land-like permanent the acting player controls (not self)
        - enforce sorcery speed
        - pay Fortify cost (mana only)
        - delegate attach to engine._apply_fortify (stack.py)
        """

# Module-level convenience functions (primary API surface, per Sprint-7 wiring convention)
def resolve_fortify_with_ai(game_state: GameState, permanent_id: str) -> GameState:
    """AI auto-attach to first valid land if affordable; no-op (same object) otherwise."""
```
- Register in the keyword registry (`register_keyword("fortify", Fortify)`) if the module's peers do so.
- Pure transforms throughout (`model_copy`); lazy imports to avoid circular deps (mirror `dash.py`).

### 5.2 MODIFY — `mtg_engine/card_data/ability_parser.py`
- **Add a Fortify branch** in the ability-parsing loop, checked **before** the single-keyword fall-through, so a line matching `^fortify\s*(\{[^}]+\})\b` produces:
  ```python
  ActivatedAbility(
      cost="<fortify cost>",                       # e.g. "{3}"
      effect="Attach this Fortification to target land you control",
      timing_restriction="(Fortify only as a sorcery.)",
      raw_text=line,
  )
  ```
- **Extend `_TIMING_RE`** (line 135) to also match the Fortify reminder text:
  ```python
  _TIMING_RE = re.compile(
      r"\((?:activate|fortify) only (?:as a sorcery|during [^)]+)\)",
      re.IGNORECASE,
  )
  ```
  This makes the existing US20 T162 sorcery-speed guard (F4) fire for Fortify with no further API change.

### 5.3 MODIFY — `mtg_engine/engine/stack.py`
- **Add `_apply_fortify(game_state, fortification_id, land_id) -> GameState`** mirroring `_apply_equip` (F6):
  - Find both permanents by ID; no-op if either missing.
  - Pure-transform the battlefield: `fortification.attached_to = land_id`; `land.attachments += [fortification_id]` (dedup).
  - `_update_battlefield(...)`.
  - Fire `check_attach_triggers(game_state, fortification_id)` (lazy import, as in `_apply_equip`).
  - Return new `GameState`.

### 5.4 MODIFY — `mtg_engine/engine/sba.py`
- **Add a Fortification unattach SBA** mirroring the Equipment SBA (F7, CR 704.5n / CR 301.7) but **also cleaning up the host's `attachments` list** (the Equipment SBA at sba.py:277-286 only sets `attached_to = None` and leaves a stale reference in the host's `attachments`; `zones.py:270-274` does clean it up on zone-change — we match the zones.py behavior):
  ```python
  # Fortification attached to a non-land (or missing) -> unattach, stays on battlefield
  for perm in game_state.battlefield:
      if is_fortification(perm.card) and perm.attached_to:
          target = next((p for p in game_state.battlefield if p.id == perm.attached_to), None)
          if not target or not is_land_card(target.card):
              perm.attached_to = None
              if target and perm.id in target.attachments:
                  target.attachments[:] = [a for a in target.attachments if a != perm.id]
              events.append(SBAEvent("fortification_detach", f"{perm.card.name} detached", [perm.id]))
  ```
  Place adjacent to the Equipment SBA block (after line 298). Note: this block is a **separate, self-contained loop**; a Fortification type line ("…Fortification") contains neither "aura" nor "equipment", so it does not overlap the existing Aura/Equipment SBA blocks (R4).

### 5.5 MODIFY — `mtg_engine/api/routers/game.py`
- **`/activate` endpoint (F3):** after the existing "add {X}"/"regenerate" handlers, add a Fortify attach branch:
  ```python
  fortify_attach = re.search(r"attach (?:this fortification )?to target land", ability.effect, re.I)
  if fortify_attach and req.targets:
      from mtg_engine.engine.stack import _apply_fortify
      gs = _apply_fortify(gs, perm.id, req.targets[0])
  ```
  (Cost payment + sorcery-speed + split-second are already handled by the existing machinery once the parser emits an `ActivatedAbility` with the timing restriction.)
- **`_compute_legal_actions` (F8, F11):**
  - Land-drop section (line 2681): use `is_land_card(card)` so a Fortification in hand is offered as `play_land`.
  - Activate section (line 3189+): for a Fortify `ActivatedAbility`, only offer the `activate` action if the player controls **at least one** valid land target (land-like, excluding the source) **and** can pay the Fortify cost. Add the target list to the action for the client.
- **`play_land` endpoint (F9):** replace `"land" not in card.type_line.lower()` with `not is_land_card(card)`.

### 5.6 NO CHANGE — `mtg_engine/models/game.py`
No new `GameState` field (no pending choice). `Permanent.attached_to`/`attachments` already exist (F5).

### 5.7 NEW — tests
- `tests/ability/keywords/test_fortify.py` (unit)
- `tests/engine/test_fortify_integration.py` (integration)

---

## 6. Task Breakdown

| Task | Description | Files | Deps |
|------|-------------|-------|------|
| **T1** | Fortify detection/parsing: `parse_fortify_cost`, `has_fortify`, `from_oracle_text`, `is_fortification`, `is_land_card`, `Fortify(CostKeyword)` skeleton + `applies()` | `fortify.py` | — |
| **T2** | Parser Fortify branch → `ActivatedAbility` + extend `_TIMING_RE` | `ability_parser.py` | — |
| **T3** | `_apply_fortify` pure-transform attach (mirror `_apply_equip`) + attach trigger | `stack.py` | T1 |
| **T4** | `Fortify.apply()` full logic (validate source/target/timing, pay cost, delegate to `_apply_fortify`) + `resolve_fortify_with_ai` | `fortify.py` | T1, T3 |
| **T5** | Fortification unattach SBA | `sba.py` | T1 |
| **T6** | Fortification land handling: `play_land` + `_compute_legal_actions` land-drop use `is_land_card` | `game.py` | T1 |
| **T7** | `/activate` Fortify attach-effect handler | `game.py` | T2, T3 |
| **T8** | `_compute_legal_actions` Fortify action + target validation + cost check | `game.py` | T2, T4 |
| **T9** | Unit tests (`test_fortify.py`) | tests | T1–T5 |
| **T10** | Integration tests (`test_fortify_integration.py`) | tests | T1–T8 |
| **T11** | Full regression run + ruff | — | all |

**Suggested order:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11.

---

## 7. Testing Strategy

### 7.1 Unit — `tests/ability/keywords/test_fortify.py`
| Area | Cases |
|------|-------|
| `parse_fortify_cost` | "Fortify {3}" → "{3}"; "Fortify {2}{R}" → "{2}{R}"; no Fortify clause → None; plain "Fortify" (no cost) → None |
| `has_fortify` / `from_oracle_text` | keyword present → True; "Fortify {3}" clause → True; neither → False |
| `is_fortification` | "Artifact — Fortification" → True; "Land — Mountain" → False |
| `is_land_card` | basic land → True; Fortification → True; creature → False |
| `apply()` human | valid target → attached (`attached_to`/`attachments` set); pure transform (new object, original unchanged); wrong controller → no-op; target not a land → no-op; target is self → no-op; unaffordable cost → no-op; **target is another Fortification → allowed** (both are lands) |
| `resolve_fortify_with_ai` | affordable + has land → attaches to first land; unaffordable → no-op (same object); no valid land → no-op |
| sorcery-timing | non-main-phase / non-active / stack non-empty → rejected |
| cost robustness | Fortify cost with a `{T}` component is accepted (the `/activate` machinery handles `{T}`); mana-only cost (the 2 real cards) is the common case |

### 7.2 Integration — `tests/engine/test_fortify_integration.py`
| Area | Cases |
|------|-------|
| Parser | "Fortify {3} (…)" → `ActivatedAbility` with cost "{3}" + sorcery `timing_restriction` (both real card texts) |
| Land drop | Play a Fortification as a land (main phase, stack empty, one/turn); Fortification counts toward `lands_played_this_turn`; a second land drop the same turn is rejected |
| Attach flow | Play Fortification → activate Fortify → attach to target land → verify `attached_to`/`attachments` → attach trigger fires; attach a Fortification to another Fortification (legal) |
| SBA | Attached land leaves battlefield → Fortification unattaches, **stays on battlefield**, and the host's `attachments` list is cleaned; Fortification attached to a non-land → unattaches + host `attachments` cleaned |
| Still a land | Fortification remains land-like while attached (legal target / land rules) |
| Legal actions | `fortify` action present with correct `valid_targets` when conditions met; absent when no valid land / unaffordable / wrong timing |
| API end-to-end | `POST /activate` attaches (200); instant-speed activation rejected (400 INVALID_ACTION); dry_run returns projected state without persisting |
| Regression | Full suite green |

### 7.3 Quality bars
- Pure transforms (`model_copy`) — assert original `GameState`/`Permanent` objects are unchanged after `apply()`.
- Exactly-once attach trigger (no double-fire).
- `ruff check .` clean.
- **Full suite: `2816 + N new passed`, `0 failed`; skip/xfail set byte-identical** (3 skipped `tests/api/test_etb_choices.py`; 13 xfailed across `tests/engine/test_etb_detection.py`, `test_etb_integration.py`, `test_etb_ai.py`).

---

## 8. Risks / Unknowns

| Risk | Mitigation |
|------|-----------|
| **R1 — Parser change side effects** (F1/F2): extending `ability_parser.py` could affect other cards. | The Fortify branch is gated on lines starting with "Fortify" (only 2 cards in all of MTG). `_TIMING_RE` change only *adds* a "fortify" alternative. Regression suite catches any breakage. |
| **R2 — Self-attach ambiguity** (§4.1). | Documented assumption: exclude the source. Single predicate to change if a ruling differs. |
| **R3 — Scattered land checks** (F8): a Fortification may be missed by some ad-hoc `"land" in type_line` checks. | Scope-limit: only Fortify-relevant paths use `is_land_card`. Other paths (e.g., combat "land" checks) are unaffected because a Fortification is not a creature and does not participate in those flows. Accept residual gaps as known limitations. |
| **R4 — SBA ordering** (F7): the new Fortification SBA must not interfere with the Equipment/Aura SBA blocks. | Add as a separate, self-contained loop after the Equipment block; Fortification type line ("…Fortification") does not contain "aura"/"equipment", so no overlap. |
| **R5 — "fortified land" abilities left unimplemented.** | Explicitly out of scope (§1). The attach works; the attached Fortification's own static/triggered abilities that reference the fortified land are a follow-up. Tests should not assert on those effects. |
| **R6 — AI auto-activation trigger point.** | `resolve_fortify_with_ai` is a pure, callable function the AI decision loop can invoke. Wiring it into a broader "AI plays activated abilities" feature is out of scope; the function + its tests are in scope. |

---

## 9. Definition of Done
- [ ] All acceptance criteria in the story file met.
- [ ] Both real Fortify cards (Darksteel Garrison, C.A.M.P.) parse to an `ActivatedAbility` and activate correctly end-to-end.
- [ ] Full regression suite: `2816 + N new passed`, `0 failed`, skip/xfail set byte-identical.
- [ ] `ruff check .` clean.
- [ ] No changes to Equip (7-5b) or `.opencode/pipeline/status.md`; no git commits.
