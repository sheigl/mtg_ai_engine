"""Sunburst keyword integration tests (CR 702.103).

Tests that Sunburst applies counters when a permanent enters the battlefield
from being cast, based on colored mana symbols in its mana cost.
"""
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool


def _make_game(active: str = "p1", human: str | None = None) -> GameState:
    return GameState(
        game_id="test-sunburst",
        seed=42,
        active_player=active,
        priority_holder=active,
        players=[
            PlayerState(name="p1", life=20, mana_pool=ManaPool()),
            PlayerState(name="p2", life=20, mana_pool=ManaPool()),
        ],
        human_player_name=human,
    )


def _make_sunburst_creature(mana_cost: str = "{W}", power: str = "1", toughness: str = "1") -> Card:
    return Card(
        name="Sunburst Creature",
        type_line="Creature — Spirit",
        oracle_text="Sunburst",
        mana_cost=mana_cost,
        power=power,
        toughness=toughness,
        keywords=["sunburst"],
    )


def _make_sunburst_artifact(mana_cost: str = "{R}") -> Card:
    return Card(
        name="Sunburst Artifact",
        type_line="Artifact — Equipment",
        oracle_text="Sunburst",
        mana_cost=mana_cost,
        keywords=["sunburst"],
    )


def _make_sunburst_enchantment(mana_cost: str = "{G}") -> Card:
    return Card(
        name="Sunburst Enchantment",
        type_line="Enchantment — Aura",
        oracle_text="Sunburst\nEnchant creature",
        mana_cost=mana_cost,
        keywords=["sunburst"],
    )


# ── Colored mana counting tests ─────────────────────────────────────────────

class TestCountColoredManaSymbols:
    """count_colored_mana_symbols correctly counts colored symbols."""

    def test_single_white(self):
        from mtg_engine.ability.keywords.sunburst import SunburstKeyword
        assert SunburstKeyword.count_colored_mana_symbols("{W}") == 1

    def test_multiple_colored(self):
        from mtg_engine.ability.keywords.sunburst import SunburstKeyword
        assert SunburstKeyword.count_colored_mana_symbols("{2}{W}{U}") == 2

    def test_generic_only(self):
        from mtg_engine.ability.keywords.sunburst import SunburstKeyword
        assert SunburstKeyword.count_colored_mana_symbols("{3}") == 0

    def test_empty_cost(self):
        from mtg_engine.ability.keywords.sunburst import SunburstKeyword
        assert SunburstKeyword.count_colored_mana_symbols("") == 0

    def test_none_cost(self):
        from mtg_engine.ability.keywords.sunburst import SunburstKeyword
        assert SunburstKeyword.count_colored_mana_symbols(None) == 0

    def test_all_five_colors(self):
        from mtg_engine.ability.keywords.sunburst import SunburstKeyword
        cost = "{W}{U}{B}{R}{G}"
        assert SunburstKeyword.count_colored_mana_symbols(cost) == 5


# ── Creature sunburst tests ─────────────────────────────────────────────────

class TestSunburstCreature:
    """Creatures with sunburst get +1/+1 counters on ETB when cast."""

    def test_creature_gets_plus_one_counters(self):
        """Single colored mana → one +1/+1 counter."""
        gs = _make_game()
        card = _make_sunburst_creature(mana_cost="{W}")
        from mtg_engine.engine.zones import put_permanent_onto_battlefield

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="stack")
        # Sunburst does model_copy on battlefield — read from GS battlefield
        bf_perm = next(p for p in gs.battlefield if p.id == perm.id)
        assert bf_perm.counters.get("+1/+1", 0) == 1

    def test_creature_multiple_colored_mana(self):
        """Multiple colored mana → multiple +1/+1 counters."""
        gs = _make_game()
        card = _make_sunburst_creature(mana_cost="{2}{W}{U}{B}")
        from mtg_engine.engine.zones import put_permanent_onto_battlefield

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="stack")
        bf_perm = next(p for p in gs.battlefield if p.id == perm.id)
        assert bf_perm.counters.get("+1/+1", 0) == 3

    def test_creature_no_colored_mana(self):
        """No colored mana → no counters."""
        gs = _make_game()
        card = _make_sunburst_creature(mana_cost="{2}")
        from mtg_engine.engine.zones import put_permanent_onto_battlefield

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="stack")
        bf_perm = next(p for p in gs.battlefield if p.id == perm.id)
        assert "+1/+1" not in bf_perm.counters


# ── Non-creature sunburst tests ─────────────────────────────────────────────

class TestSunburstNonCreature:
    """Non-creatures with sunburst get charge counters on ETB when cast."""

    def test_artifact_gets_charge_counters(self):
        """Artifact gets charge counters instead of +1/+1."""
        gs = _make_game()
        card = _make_sunburst_artifact(mana_cost="{R}{G}")
        from mtg_engine.engine.zones import put_permanent_onto_battlefield

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="stack")
        bf_perm = next(p for p in gs.battlefield if p.id == perm.id)
        assert bf_perm.counters.get("charge", 0) == 2

    def test_enchantment_gets_charge_counters(self):
        """Enchantment gets charge counters instead of +1/+1."""
        gs = _make_game()
        card = _make_sunburst_enchantment(mana_cost="{U}{B}")
        from mtg_engine.engine.zones import put_permanent_onto_battlefield

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="stack")
        bf_perm = next(p for p in gs.battlefield if p.id == perm.id)
        assert bf_perm.counters.get("charge", 0) == 2


# ── No-fire conditions ──────────────────────────────────────────────────────

class TestSunburstNoFire:
    """Sunburst does NOT fire when permanent is not cast."""

    def test_no_fire_for_token(self):
        """Token with sunburst keyword doesn't get counters (tokens aren't cast)."""
        gs = _make_game()
        card = _make_sunburst_creature(mana_cost="{W}")
        from mtg_engine.engine.zones import put_permanent_onto_battlefield

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand", is_token=True)
        assert "+1/+1" not in perm.counters

    def test_no_fire_from_graveyard(self):
        """Permanent entering from graveyard doesn't trigger sunburst."""
        gs = _make_game()
        card = _make_sunburst_creature(mana_cost="{W}")
        from mtg_engine.engine.zones import put_permanent_onto_battlefield

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="graveyard")
        assert "+1/+1" not in perm.counters

    def test_no_fire_from_exile(self):
        """Permanent entering from exile doesn't trigger sunburst."""
        gs = _make_game()
        card = _make_sunburst_creature(mana_cost="{W}")
        from mtg_engine.engine.zones import put_permanent_onto_battlefield

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="exile")
        assert "+1/+1" not in perm.counters


# ── Pure transform test ─────────────────────────────────────────────────────

class TestSunburstPureTransform:
    """apply_sunburst_counters returns new GameState via model_copy."""

    def test_returns_new_game_state(self):
        from mtg_engine.ability.keywords.sunburst import SunburstKeyword
        gs = _make_game()
        card = _make_sunburst_creature(mana_cost="{W}")
        from mtg_engine.engine.zones import put_permanent_onto_battlefield

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="stack")
        old_id = id(gs)
        new_gs = SunburstKeyword.apply_sunburst_counters(gs, perm.id, "{U}")
        assert id(new_gs) != old_id

    def test_original_unchanged(self):
        """Original game state is not mutated."""
        from mtg_engine.ability.keywords.sunburst import SunburstKeyword
        gs = _make_game()
        card = _make_sunburst_creature(mana_cost="{W}")
        from mtg_engine.engine.zones import put_permanent_onto_battlefield

        gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="stack")
        original_counters = dict(perm.counters)
        SunburstKeyword.apply_sunburst_counters(gs, perm.id, "{U}")
        # Original permanent's counters unchanged (pure transform on battlefield list)
        assert perm.counters == original_counters


# ── Detection tests ─────────────────────────────────────────────────────────

class TestSunburstDetection:
    """Sunburst detection helpers work correctly."""

    def test_from_oracle_text(self):
        from mtg_engine.ability.keywords.sunburst import SunburstKeyword
        assert SunburstKeyword.from_oracle_text("Sunburst") is True
        assert SunburstKeyword.from_oracle_text("Some other ability") is False

    def test_has_sunburst_keyword_list(self):
        from mtg_engine.ability.keywords.sunburst import SunburstKeyword
        assert SunburstKeyword.has_sunburst(["sunburst"]) is True
        assert SunburstKeyword.has_sunburst(["flying", "haste"]) is False
