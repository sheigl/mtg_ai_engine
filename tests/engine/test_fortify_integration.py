"""
Integration tests for the Fortify keyword (CR 702.54a).

End-to-end engine flows with the two real Fortify cards:
- Darksteel Garrison: "Fortify {3}"
- C.A.M.P.: "Fortify {2}{G}"

Covers: parser → apply → _apply_fortify → attach triggers → SBA, using real
engine entry points (put_permanent_onto_battlefield, apply_fortify,
check_and_apply_sbas).
"""
from mtg_engine.models.game import (
    Card, GameState, ManaPool, Phase, PlayerState, Step,
)
from mtg_engine.engine.zones import get_player, put_permanent_onto_battlefield
from mtg_engine.engine.mana import add_mana
from mtg_engine.engine.sba import check_and_apply_sbas
from mtg_engine.ability.keywords.fortify import Fortify, apply_fortify, resolve_fortify_with_ai

GARRISON_ORACLE = (
    "Fortify {3} ({3}: Attach to target land you control. "
    "Fortify only as a sorcery. This card enters unattached and stays on the "
    "battlefield if the land leaves.)"
)
CAMP_ORACLE = (
    "Fortify {2}{G} ({2}{G}: Attach to target land you control. "
    "Fortify only as a sorcery. C.A.M.P. can't be attacked. As long as C.A.M.P. "
    "is attached, it doesn't have base abilities or rules text.)"
)


def _make_game(active="p1", holder="p1",
               phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN) -> GameState:
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-fortify", seed=1,
        active_player=active, priority_holder=holder,
        phase=phase, step=step,
        players=[p1, p2],
    )


def _garrison_card() -> Card:
    return Card(name="Darksteel Garrison", type_line="Artifact Creature — Fortification",
                oracle_text=GARRISON_ORACLE)


def _camp_card() -> Card:
    return Card(name="C.A.M.P.", type_line="Artifact Creature — Fortification",
                oracle_text=CAMP_ORACLE)


def _forest_card() -> Card:
    return Card(name="Forest", type_line="Basic Land — Forest")


# Test 1: Garrison played as a land drop, then Fortified onto a Forest
def test_garrison_land_drop_then_fortify():
    """A Fortification is a land: it can be played as a land drop and later
    attached to another land (CR 301.7, CR 702.54a)."""
    gs = _make_game()
    gs = _give_mana(gs, "p1", C=3)

    gs, garrison_perm = put_permanent_onto_battlefield(gs, _garrison_card(), "p1", from_zone="hand")
    gs, forest_perm = put_permanent_onto_battlefield(gs, _forest_card(), "p1", from_zone="hand")

    assert Fortify.is_land_card(garrison_perm.card)
    gs = apply_fortify(gs, garrison_perm, forest_perm.id)

    garrison_now = next(p for p in gs.battlefield if p.id == garrison_perm.id)
    forest_now = next(p for p in gs.battlefield if p.id == forest_perm.id)
    assert garrison_now.attached_to == forest_perm.id
    assert garrison_perm.id in forest_now.attachments
    p1 = get_player(gs, "p1")
    assert p1.mana_pool.C == 0  # paid {3}


# Test 2: C.A.M.P. colored cost paid from colored pool
def test_camp_fortify_pays_colored_cost():
    gs = _make_game()
    p1 = get_player(gs, "p1")
    p1.mana_pool = add_mana(p1.mana_pool, "G")
    p1.mana_pool = add_mana(p1.mana_pool, "C")
    p1.mana_pool = add_mana(p1.mana_pool, "C")
    gs.players[0] = p1

    gs, camp_perm = put_permanent_onto_battlefield(gs, _camp_card(), "p1", from_zone="hand")
    gs, forest_perm = put_permanent_onto_battlefield(gs, _forest_card(), "p1", from_zone="hand")

    gs = apply_fortify(gs, camp_perm, forest_perm.id)

    camp_now = next(p for p in gs.battlefield if p.id == camp_perm.id)
    assert camp_now.attached_to == forest_perm.id
    p1 = get_player(gs, "p1")
    assert p1.mana_pool.G == 0
    assert p1.mana_pool.C == 0


# Test 3: Attach trigger fires exactly once
def test_attach_trigger_fires_exactly_once():
    """A Fortification with 'whenever this becomes attached' queues exactly
    one trigger per attach (Q1: exactly-once semantics)."""
    gs = _make_game()
    gs = _give_mana(gs, "p1", C=3)
    garrison = Card(
        name="Garrison Trigger", type_line="Artifact Creature — Fortification",
        oracle_text="Fortify {3}\nWhenever this becomes attached to another permanent, draw a card.",
    )
    gs, garrison_perm = put_permanent_onto_battlefield(gs, garrison, "p1", from_zone="hand")
    gs, forest_perm = put_permanent_onto_battlefield(gs, _forest_card(), "p1", from_zone="hand")

    assert len(gs.pending_triggers) == 0
    gs = apply_fortify(gs, garrison_perm, forest_perm.id)
    assert len(gs.pending_triggers) == 1
    assert gs.pending_triggers[0].controller == "p1"

    # Attaching again (second Fortify) queues exactly one more.
    gs = _give_mana(gs, "p1", C=3)
    gs = apply_fortify(gs, garrison_perm, forest_perm.id)
    assert len(gs.pending_triggers) == 2


# Test 4: No attach trigger for plain Fortification
def test_plain_fortify_queues_no_triggers():
    gs = _make_game()
    gs = _give_mana(gs, "p1", C=3)
    gs, garrison_perm = put_permanent_onto_battlefield(gs, _garrison_card(), "p1", from_zone="hand")
    gs, forest_perm = put_permanent_onto_battlefield(gs, _forest_card(), "p1", from_zone="hand")
    gs = apply_fortify(gs, garrison_perm, forest_perm.id)
    assert gs.pending_triggers == []


# Test 5: SBA cleanup after the host leaves the battlefield
def test_sba_detaches_after_host_leaves():
    """Full flow: attach, then host destroyed → SBA detaches the Fortification,
    which stays on the battlefield (CR 301.7)."""
    gs = _make_game()
    gs = _give_mana(gs, "p1", C=3)
    gs, garrison_perm = put_permanent_onto_battlefield(gs, _garrison_card(), "p1", from_zone="hand")
    gs, forest_perm = put_permanent_onto_battlefield(gs, _forest_card(), "p1", from_zone="hand")
    gs = apply_fortify(gs, garrison_perm, forest_perm.id)

    garrison_now = next(p for p in gs.battlefield if p.id == garrison_perm.id)
    assert garrison_now.attached_to == forest_perm.id

    # Destroy the Forest (simulate: remove from battlefield)
    gs.battlefield = [p for p in gs.battlefield if p.id != forest_perm.id]
    gs, events = check_and_apply_sbas(gs)

    garrison_now = next(p for p in gs.battlefield if p.id == garrison_perm.id)
    assert garrison_now.attached_to is None
    assert any(e.sba_type == "fortification_detach" for e in events)
    # Garrison stays on the battlefield
    assert len(gs.battlefield) == 1


# Test 6: AI auto-resolve picks the first valid land deterministically
def test_ai_auto_resolve_first_valid_land():
    gs = _make_game(active="p1", holder="p1")
    gs = _give_mana(gs, "p1", C=3)
    gs, garrison_perm = put_permanent_onto_battlefield(gs, _garrison_card(), "p1", from_zone="hand")
    gs, bear_perm = put_permanent_onto_battlefield(
        gs, Card(name="Bear", type_line="Creature — Beast", power="2", toughness="2"), "p1",
        from_zone="hand",
    )
    gs, forest_perm = put_permanent_onto_battlefield(gs, _forest_card(), "p1", from_zone="hand")
    gs, plains_perm = put_permanent_onto_battlefield(
        gs, Card(name="Plains", type_line="Basic Land — Plains"), "p1", from_zone="hand",
    )

    gs = resolve_fortify_with_ai(gs, garrison_perm.id)

    garrison_now = next(p for p in gs.battlefield if p.id == garrison_perm.id)
    # First land-like permanent in battlefield order (bear is not a land)
    assert garrison_now.attached_to == forest_perm.id
    p1 = get_player(gs, "p1")
    assert p1.mana_pool.C == 0


# Test 7: Fortification targeting a Fortification (a land is a land)
def test_fortify_fortification_onto_fortification():
    gs = _make_game()
    gs = _give_mana(gs, "p1", C=3)
    gs, garrison_perm = put_permanent_onto_battlefield(gs, _garrison_card(), "p1", from_zone="hand")
    gs, camp_perm = put_permanent_onto_battlefield(gs, _camp_card(), "p1", from_zone="hand")

    gs = apply_fortify(gs, garrison_perm, camp_perm.id)

    garrison_now = next(p for p in gs.battlefield if p.id == garrison_perm.id)
    camp_now = next(p for p in gs.battlefield if p.id == camp_perm.id)
    assert garrison_now.attached_to == camp_perm.id
    assert garrison_perm.id in camp_now.attachments


# Test 8: Still a land while attached (CR 301.7)
def test_attached_fortification_still_land_like():
    """An attached Fortification is still a land: another Fortification can
    target it (both are lands, CR 702.54a 'target land you control')."""
    gs = _make_game()
    gs = _give_mana(gs, "p1", C=5, G=1)
    gs, garrison_perm = put_permanent_onto_battlefield(gs, _garrison_card(), "p1", from_zone="hand")
    gs, camp_perm = put_permanent_onto_battlefield(gs, _camp_card(), "p1", from_zone="hand")
    gs, forest_perm = put_permanent_onto_battlefield(gs, _forest_card(), "p1", from_zone="hand")

    # Garrison attaches to the Forest
    gs = apply_fortify(gs, garrison_perm, forest_perm.id)
    garrison_now = next(p for p in gs.battlefield if p.id == garrison_perm.id)
    assert garrison_now.attached_to == forest_perm.id
    assert Fortify.is_land_card(garrison_now.card)  # still land-like

    # C.A.M.P. targets the attached Garrison (legal: it's a land)
    gs = apply_fortify(gs, camp_perm, garrison_perm.id)
    camp_now = next(p for p in gs.battlefield if p.id == camp_perm.id)
    assert camp_now.attached_to == garrison_perm.id
    p1 = get_player(gs, "p1")
    assert p1.mana_pool.C == 0  # paid {3} + {2}
    assert p1.mana_pool.G == 0  # paid {G}


# Test 9: Immutability — original state unchanged after apply
def test_apply_is_pure_transform():
    gs = _make_game()
    gs = _give_mana(gs, "p1", C=3)
    gs, garrison_perm = put_permanent_onto_battlefield(gs, _garrison_card(), "p1", from_zone="hand")
    gs, forest_perm = put_permanent_onto_battlefield(gs, _forest_card(), "p1", from_zone="hand")

    old_gs = gs
    gs = apply_fortify(gs, garrison_perm, forest_perm.id)

    assert gs is not old_gs
    old_garrison = next(p for p in old_gs.battlefield if p.id == garrison_perm.id)
    assert old_garrison.attached_to is None
    assert old_gs.players[0].mana_pool.C == 3


def _give_mana(gs: GameState, player_name: str, **kwargs) -> GameState:
    """Give the named player a fresh pool with the specified mana."""
    new_pool = ManaPool(**kwargs)
    new_players = [
        p.model_copy(update={"mana_pool": new_pool}) if p.name == player_name else p
        for p in gs.players
    ]
    return gs.model_copy(update={"players": new_players})
