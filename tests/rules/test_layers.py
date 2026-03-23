import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import time
from mtg_engine.models.game import GameState, Phase, Step, PlayerState, Card, Permanent
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.engine.layers import apply_continuous_effects, get_effective_power_toughness


def _make_game() -> GameState:
    p1 = PlayerState(name="p1")
    p2 = PlayerState(name="p2")
    return GameState(game_id="t", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2])


def test_counter_modifies_power_toughness():
    gs = _make_game()
    card = Card(name="Bear", type_line="Creature — Bear", power="2", toughness="2")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    perm.counters["+1/+1"] = 2
    p, t = get_effective_power_toughness(perm)
    assert p == 4 and t == 4


def test_humility_sets_all_creatures_to_1_1():
    """Humility: all creatures become 1/1 and lose abilities. Layer 6 then 7b."""
    gs = _make_game()
    humility = Card(
        name="Humility",
        type_line="Enchantment",
        oracle_text="All creatures lose all abilities and are 1/1.",
    )
    bear = Card(name="Bear", type_line="Creature — Bear", power="4", toughness="4")
    gs, h_perm = put_permanent_onto_battlefield(gs, humility, "p1")
    # Give Humility an earlier timestamp
    h_perm.timestamp = 1.0
    gs, b_perm = put_permanent_onto_battlefield(gs, bear, "p2")
    b_perm.timestamp = 2.0

    gs = apply_continuous_effects(gs)

    # Bear should be 1/1
    bear_perm = next(p for p in gs.battlefield if p.card.name == "Bear")
    assert bear_perm.card.power == "1", f"expected power 1, got {bear_perm.card.power}"
    assert bear_perm.card.toughness == "1", f"expected toughness 1, got {bear_perm.card.toughness}"


def test_pt_boost_with_humility():
    """
    Giant Growth (+3/+3 until EOT) then Humility:
    Humility in layer 7b sets to 1/1, overriding the boost which is in layer 7c.
    Net result: layer 7b sets to 1/1, then layer 7c adds +1/+1 counter = 2/2.
    This tests that layer ordering matters.
    """
    gs = _make_game()
    humility = Card(
        name="Humility",
        type_line="Enchantment",
        oracle_text="All creatures lose all abilities and are 1/1.",
    )
    bear = Card(name="Bear", type_line="Creature — Bear", power="2", toughness="2")
    gs, h_perm = put_permanent_onto_battlefield(gs, humility, "p1")
    h_perm.timestamp = 1.0
    gs, b_perm = put_permanent_onto_battlefield(gs, bear, "p2")
    b_perm.timestamp = 2.0
    # Simulate a +1/+1 counter (layer 7c)
    b_perm.counters["+1/+1"] = 1

    gs = apply_continuous_effects(gs)

    # Layer 7b: Humility sets to 1/1
    # Layer 7c: +1/+1 counter adds 1/1 → result is 2/2
    bear_perm = next(p for p in gs.battlefield if p.card.name == "Bear")
    p_val = int(bear_perm.card.power)
    t_val = int(bear_perm.card.toughness)
    assert p_val == 2 and t_val == 2, f"Expected 2/2, got {p_val}/{t_val}"


# ─── US5: Layer 1–5 coverage ──────────────────────────────────────────────────

def test_layer1_copy_acquires_source_stats():
    """US5 Layer 1: permanent with copy_of_permanent_id copies source card's P/T and keywords."""
    gs = _make_game()
    source_card = Card(
        name="Dragon", type_line="Creature — Dragon",
        power="5", toughness="5", keywords=["flying", "trample"],
    )
    copy_card = Card(
        name="Clone", type_line="Creature — Shapeshifter",
        power="0", toughness="0",
    )
    gs, src_perm = put_permanent_onto_battlefield(gs, source_card, "p1")
    gs, copy_perm = put_permanent_onto_battlefield(gs, copy_card, "p1")
    copy_perm.copy_of_permanent_id = src_perm.id

    gs = apply_continuous_effects(gs)

    copy_result = next(p for p in gs.battlefield if p.card.name in ("Clone", "Dragon")
                       and p.id == copy_perm.id)
    assert copy_result.card.power == "5"
    assert copy_result.card.toughness == "5"
    assert "flying" in copy_result.card.keywords


def test_layer2_control_change_aura():
    """US5 Layer 2: control-change aura changes permanent's controller."""
    gs = _make_game()
    control_aura = Card(
        name="Control Magic",
        type_line="Enchantment — Aura",
        oracle_text="Enchant creature. You control enchanted creature.",
    )
    target_card = Card(name="Creature", type_line="Creature — Beast", power="3", toughness="3")
    gs, aura_perm = put_permanent_onto_battlefield(gs, control_aura, "p1")
    gs, target_perm = put_permanent_onto_battlefield(gs, target_card, "p2")
    aura_perm.attached_to = target_perm.id

    gs = apply_continuous_effects(gs)

    updated = next(p for p in gs.battlefield if p.id == target_perm.id)
    assert updated.controller == "p1"  # p1 now controls it via Control Magic


def test_layer4_type_addition():
    """US5 Layer 4: 'is an artifact in addition' effect adds Artifact to type_line."""
    gs = _make_game()
    enchantment = Card(
        name="Type-Changer",
        type_line="Enchantment",
        oracle_text="Each creature is an artifact in addition to its other types.",
    )
    creature = Card(name="Bear", type_line="Creature — Bear", power="2", toughness="2")
    gs, _ = put_permanent_onto_battlefield(gs, enchantment, "p1")
    gs, bear_perm = put_permanent_onto_battlefield(gs, creature, "p1")

    gs = apply_continuous_effects(gs)

    updated = next(p for p in gs.battlefield if p.id == bear_perm.id)
    assert "artifact" in updated.card.type_line.lower()


def test_layer5_all_colors():
    """US5 Layer 5: 'is all colors' effect sets permanent's colors to WUBRG."""
    gs = _make_game()
    enchantment = Card(
        name="Color Blast",
        type_line="Enchantment",
        oracle_text="Each creature is all colors.",
    )
    creature = Card(name="Bear", type_line="Creature — Bear", power="2", toughness="2", colors=["G"])
    gs, _ = put_permanent_onto_battlefield(gs, enchantment, "p1")
    gs, bear_perm = put_permanent_onto_battlefield(gs, creature, "p1")

    gs = apply_continuous_effects(gs)

    updated = next(p for p in gs.battlefield if p.id == bear_perm.id)
    assert set(updated.card.colors) == {"W", "U", "B", "R", "G"}
