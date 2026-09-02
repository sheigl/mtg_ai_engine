"""Tests for TypeCycling keyword."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.ability.keywords.cycle import (
    CyclingKeyword,
    TypeCyclingKeyword,
    resolve_cycling_choice,
)
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, ManaPool,
)


def _make_game_with_card(
    type_line: str = "Creature — Elf Warrior",
    keywords: list[str] | None = None,
    library_size: int = 10,
) -> tuple[GameState, Card, PlayerState]:
    card = Card(
        name="Cycling Card",
        type_line=type_line,
        oracle_text="Type cycling {2}",
        keywords=keywords or ["typecycling"],
    )
    p1 = PlayerState(
        name="p1",
        hand=[card],
        library=[Card(name=f"Card{i}", type_line="Basic Land — Forest") for i in range(library_size)],
    )
    p2 = PlayerState(name="p2")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )
    return gs, card, p1


def test_typecycling_applies_from_keywords():
    """TypeCycling detects keyword in keywords list."""
    gs, card, _ = _make_game_with_card(keywords=["typecycling"])
    perm_card = Card(
        name="Cycling Card",
        type_line="Creature",
        oracle_text="Type cycling {2}",
        keywords=["typecycling"],
    )
    from mtg_engine.models.game import Permanent
    perm = Permanent(card=perm_card, controller="p1")
    gs.battlefield = [perm]

    kw = TypeCyclingKeyword()
    assert kw.applies(gs, perm) is True


def test_typecycling_applies_from_oracle():
    """TypeCycling detects keyword in oracle text."""
    perm_card = Card(
        name="Cycling Card",
        type_line="Creature",
        oracle_text="Type cycling {2}",
        keywords=[],
    )
    from mtg_engine.models.game import Permanent
    perm = Permanent(card=perm_card, controller="p1")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1")],
        battlefield=[perm],
    )
    kw = TypeCyclingKeyword()
    assert kw.applies(gs, perm) is True


def test_typecycling_does_not_apply():
    """TypeCycling returns False for non-cycling cards."""
    perm_card = Card(
        name="Normal Card",
        type_line="Creature",
        oracle_text="Flying.",
        keywords=["flying"],
    )
    from mtg_engine.models.game import Permanent
    perm = Permanent(card=perm_card, controller="p1")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1")],
    )
    kw = TypeCyclingKeyword()
    assert kw.applies(gs, perm) is False


def test_get_card_type_count_simple():
    """Count types for simple type line."""
    card = Card(name="Test", type_line="Creature")
    kw = TypeCyclingKeyword()
    assert kw.get_card_type_count(card) == 1


def test_get_card_type_count_with_subtype():
    """Count types with subtypes (CR 702.46b: only core card types count)."""
    card = Card(name="Test", type_line="Creature — Elf Warrior")
    kw = TypeCyclingKeyword()
    # Only "creature" is a core card type; "Elf"/"Warrior" are subtypes -> 1
    assert kw.get_card_type_count(card) == 1


def test_get_card_type_count_legendary():
    """Count types with supertype (CR 702.46b: supertypes do not count)."""
    card = Card(name="Test", type_line="Legendary Creature — Human Wizard")
    kw = TypeCyclingKeyword()
    # Only "creature" counts; "Legendary" is a supertype, others are subtypes -> 1
    assert kw.get_card_type_count(card) == 1


def test_get_draw_count():
    """Draw count equals type count (CR 702.46b)."""
    card = Card(name="Test", type_line="Creature — Elf Warrior")
    kw = TypeCyclingKeyword()
    # Only "creature" is a core card type -> draw 1
    assert kw.get_draw_count(card) == 1


def test_get_card_type_count_two_types():
    """Type-cycling draws X = number of distinct card types (CR 702.46b)."""
    card = Card(name="Test", type_line="Instant — Sorcery")
    kw = TypeCyclingKeyword()
    # "instant" + "sorcery" == 2 core card types -> draw 2
    assert kw.get_card_type_count(card) == 2
    assert kw.get_draw_count(card) == 2


def test_get_card_type_count_creates_elf_warrior():
    """Regression: 'Creature — Elf Warrior' draws exactly 1 (not 3)."""
    card = Card(name="Test", type_line="Creature — Elf Warrior")
    kw = TypeCyclingKeyword()
    assert kw.get_draw_count(card) == 1


def test_type_cycle_discards_and_draws():
    """Type cycling discards the card and draws X cards (pure transform)."""
    gs, card, p1 = _make_game_with_card(type_line="Creature — Elf Warrior")
    kw = TypeCyclingKeyword()

    assert card in p1.hand
    assert len(p1.hand) == 1
    assert len(p1.library) == 10

    # Pure transform: the original player object is untouched.
    old_gs_id = id(gs)
    gs = kw.type_cycle(gs, card, "p1")
    assert id(gs) != old_gs_id

    # Read state from the returned (new) GameState, not the stale p1.
    new_p1 = next(p for p in gs.players if p.name == "p1")
    assert card not in new_p1.hand
    assert card in new_p1.graveyard
    assert len(new_p1.hand) == 1  # Discarded 1, drew 1 (Creature — Elf Warrior -> X=1)
    assert len(new_p1.library) == 9  # 10 - 1 = 9


def test_type_cycle_minimum_one():
    """Type cycling draws at least 1 card."""
    gs, card, p1 = _make_game_with_card(type_line="Creature")
    kw = TypeCyclingKeyword()

    gs = kw.type_cycle(gs, card, "p1")
    new_p1 = next(p for p in gs.players if p.name == "p1")
    assert len(new_p1.hand) == 1  # Drew 1 card


def test_type_cycle_empty_library():
    """Type cycling handles empty library gracefully (pure transform)."""
    gs, card, p1 = _make_game_with_card(type_line="Creature — Elf", library_size=0)
    kw = TypeCyclingKeyword()

    gs = kw.type_cycle(gs, card, "p1")
    new_p1 = next(p for p in gs.players if p.name == "p1")
    assert card not in new_p1.hand
    assert card in new_p1.graveyard
    assert len(new_p1.library) == 0
    # Hand should have 0 cards since library is empty (read from returned state).
    assert len(new_p1.hand) == 0


def test_from_oracle():
    """Create TypeCyclingKeyword from oracle text."""
    kw = TypeCyclingKeyword.from_oracle("Type cycling {2}")
    assert kw is not None
    assert kw.base_cost == "{2}"


def test_from_oracle_missing():
    """from_oracle returns None when not found."""
    assert TypeCyclingKeyword.from_oracle("Flying.") is None


def test_typecycling_description():
    """TypeCycling returns proper description."""
    kw = TypeCyclingKeyword(base_cost="{2}")
    desc = kw.get_trigger_description()
    assert "{2}" in desc
    assert "types" in desc


# ─── Regular Cycling (CR 702.36) ──────────────────────────────────────────────

def _make_regular_cycle_game(
    oracle_text: str = "Cycling {1}",
    type_line: str = "Creature — Elf Warrior",
    mana: dict | None = None,
    library_size: int = 10,
    human_player: str | None = None,
) -> tuple[GameState, Card, PlayerState]:
    """Build a game whose p1 holds a *regular* cycling card.

    ``human_player`` selects the human/AI branch: when it equals "p1" apply()
    queues pending_cycling_choice (human path); any other value (or None) makes
    p1 an AI that auto-resolves.
    """
    card = Card(
        name="Cycling Card",
        type_line=type_line,
        oracle_text=oracle_text,
        keywords=["cycling"],
    )
    p1 = PlayerState(
        name="p1",
        hand=[card],
        library=[Card(name=f"Card{i}", type_line="Basic Land — Forest") for i in range(library_size)],
        mana_pool=ManaPool(**mana) if mana else ManaPool(),
    )
    p2 = PlayerState(name="p2")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2], human_player_name=human_player,
    )
    return gs, card, p1


def test_regular_cycling_detects_bare():
    """Regular CyclingKeyword detects a bare "Cycling {cost}" (CR 702.36)."""
    kw = CyclingKeyword()
    assert kw.from_oracle_text("Cycling {2}") is True
    # Colours / multi-brace costs still parse.
    assert kw.from_oracle_text("Deal 3 damage. Cycling {1}{R}") is True


def test_regular_cycling_rejects_type_cycling():
    """Negative lookbehind: "Type cycling" must NOT read as regular cycling."""
    kw = CyclingKeyword()
    assert kw.from_oracle_text("Type cycling {2}") is False


def test_regular_cycling_rejects_basicland_token():
    """A basic-land-cycling token like "Swampcycling {1}" is not regular cycling."""
    kw = CyclingKeyword()
    assert kw.from_oracle_text("Swampcycling {1}") is False


def test_regular_parse_cost():
    """parse_cost returns the cycling cost for a regular-cycling card."""
    kw = CyclingKeyword()
    assert kw.parse_cost("Cycling {2}") == "{2}"
    # Bare "Cycling" with no cost parses to None (cost defaults at resolve time).
    assert kw.parse_cost("Cycling") is None


def test_regular_from_oracle():
    """from_oracle builds a CyclingKeyword carrying the parsed cost."""
    kw = CyclingKeyword.from_oracle("Cycling {3}")
    assert kw is not None
    assert kw.cost == "{3}"
    assert CyclingKeyword.from_oracle("Flying.") is None


def test_regular_applies_from_keywords():
    """applies() is True on a Permanent carrying the regular-cycling keyword."""
    card = Card(name="Cyclist", type_line="Instant", oracle_text="Cycling {1}", keywords=["cycling"])
    from mtg_engine.models.game import Permanent
    perm = Permanent(card=card, controller="p1")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1")], battlefield=[perm],
    )
    assert CyclingKeyword().applies(gs, perm) is True


def test_regular_applies_rejects_type_cycling():
    """applies() is False on a type-cycling card (must not double-fire)."""
    card = Card(name="Type Cyclist", type_line="Instant", oracle_text="Type cycling {2}", keywords=["typecycling"])
    from mtg_engine.models.game import Permanent
    perm = Permanent(card=card, controller="p1")
    gs = GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[PlayerState(name="p1")], battlefield=[perm],
    )
    assert CyclingKeyword().applies(gs, perm) is False


def test_apply_human_queues_pending_choice():
    """Human apply() queues pending_cycling_choice and discards/draws nothing."""
    gs, card, p1 = _make_regular_cycle_game(oracle_text="Cycling {1}", human_player="p1")

    new_gs = CyclingKeyword().apply(gs, card, "p1")

    # Pure transform: a NEW object is returned.
    assert new_gs is not gs
    # Hand unchanged (nothing discarded yet).
    assert len(new_gs.players[0].hand) == 1
    # The queued choice carries the expected fields.
    pc = new_gs.pending_cycling_choice
    assert pc["player"] == "p1"
    assert pc["card_id"] == card.id
    assert pc["cost"] == "{1}"
    assert pc["draw_count"] == 1
    assert pc["resolved"] is False
    # Nothing discarded / drawn yet.
    new_p1 = next(p for p in new_gs.players if p.name == "p1")
    assert not any(c.id == card.id for c in new_p1.graveyard)
    assert len(new_p1.library) == 10


def test_apply_ai_sufficient_mana_cycles():
    """AI with affordable mana discards the card, draws 1, pays mana (pure)."""
    gs, card, p1 = _make_regular_cycle_game(
        oracle_text="Cycling {1}",
        mana={"C": 2},
        human_player="p2",  # p1 is an AI here
    )
    assert len(p1.library) == 10

    new_gs = CyclingKeyword().apply(gs, card, "p1")

    assert new_gs is not gs  # pure transform — new object
    new_p1 = next(p for p in new_gs.players if p.name == "p1")
    # Card left the hand and landed in the graveyard.
    assert all(c.id != card.id for c in new_p1.hand)
    assert any(c.id == card.id for c in new_p1.graveyard)
    # Drew exactly 1 (regular cycling draws one card).
    assert len(new_p1.library) == 9
    assert len(new_p1.hand) == 1  # discarded 1, drew 1
    # Mana was actually deducted by _pay_mana ({1} from the colorless slot).
    assert new_p1.mana_pool.C == 1


def test_apply_ai_insufficient_mana_noop():
    """AI that cannot afford the cost returns the SAME gs (pure no-op, Q4)."""
    gs, card, p1 = _make_regular_cycle_game(
        oracle_text="Cycling {2}",
        mana={"C": 0},  # empty pool
        human_player="p2",
    )

    new_gs = CyclingKeyword().apply(gs, card, "p1")

    assert new_gs is gs  # SAME object — no discard, no draw, no mana change
    new_p1 = next(p for p in new_gs.players if p.name == "p1")
    assert len(new_p1.hand) == 1
    assert not any(c.id == card.id for c in new_p1.graveyard)
    assert len(new_p1.library) == 10


def test_apply_ai_no_priority_noop():
    """Cycling outside of priority is a strict no-op returning the SAME object."""
    gs, card, p1 = _make_regular_cycle_game(oracle_text="Cycling {1}", mana={"C": 5}, human_player="p2")
    gs = gs.model_copy(update={"priority_holder": "p2"})  # p1 does not hold priority

    new_gs = CyclingKeyword().apply(gs, card, "p1")
    assert new_gs is gs


def test_apply_no_regular_cycling_noop():
    """A type-cycling card is a strict no-op for regular CyclingKeyword (Q1 guard)."""
    gs, card, p1 = _make_regular_cycle_game(oracle_text="Type cycling {2}", mana={"C": 5}, human_player="p2")
    new_gs = CyclingKeyword().apply(gs, card, "p1")
    assert new_gs is gs


def test_cycle_draw_counts_regular_vs_type():
    """Integration: regular cycling draws exactly 1; type-cycling draws #types."""
    # Regular cycling always draws exactly one card (CR 702.36).
    def _regular_library_delta(oracle_text: str, type_line: str) -> int:
        card = Card(name="Cycle Card", type_line=type_line, oracle_text=oracle_text, keywords=["cycling"])
        p1 = PlayerState(
            name="p1", mana_pool=ManaPool(C=3),
            hand=[card],
            library=[Card(name=f"Lib{i}", type_line="Land") for i in range(5)],
        )
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[p1, PlayerState(name="p2")], human_player_name="p2",  # AI
        )
        lib_before = len(gs.players[0].library)
        gs = CyclingKeyword().apply(gs, card, "p1")
        return len(gs.players[0].library) - lib_before

    assert _regular_library_delta("Cycling {1}", "Instant") == -1

    # Type-cycling draws X = number of card types (CR 702.46b), via the resolve path.
    def _type_library_delta(type_line: str) -> int:
        card = Card(name="Type Cycle", type_line=type_line, oracle_text="Type cycling {3}", keywords=["typecycling"])
        p1 = PlayerState(
            name="p1", mana_pool=ManaPool(C=3),  # afford the {3} cost so AI cycles
            hand=[card],
            library=[Card(name=f"Lib{i}", type_line="Land") for i in range(5)],
        )
        gs = GameState(
            game_id="test", seed=1,
            active_player="p1", priority_holder="p1",
            phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
            players=[p1, PlayerState(name="p2")], human_player_name="p2",  # AI
        )
        lib_before = len(gs.players[0].library)
        gs = TypeCyclingKeyword().type_cycle(gs, card, "p1")
        return len(gs.players[0].library) - lib_before

    assert _type_library_delta("Instant — Sorcery") == -2  # two core types -> draw 2
    assert _type_library_delta("Creature — Elf Warrior") == -1  # one core type -> draw 1


def test_resolve_cycling_choice_pays_discards_draws():
    """resolve_cycling_choice (human path) pays, discards and draws N cards."""
    gs, card, p1 = _make_regular_cycle_game(oracle_text="Cycling {1}", mana={"C": 3}, human_player="p1")

    gs = CyclingKeyword().apply(gs, card, "p1")          # queue the choice
    assert gs.pending_cycling_choice is not None

    gs = resolve_cycling_choice(gs, "p1")               # resolve it

    new_p1 = next(p for p in gs.players if p.name == "p1")
    assert gs.pending_cycling_choice is None            # cleared after resolution
    assert all(c.id != card.id for c in new_p1.hand)
    assert any(c.id == card.id for c in new_p1.graveyard)
    assert len(new_p1.library) == 9                     # drew one
    assert new_p1.mana_pool.C == 2                      # paid {1} from the pool
