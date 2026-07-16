"""Tests for banding support (CMB-03)."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.engine.combat.banding import (
    has_barding,
    get_band_attackers,
    get_band_blockers,
    validate_banding_damage_assignment,
    calculate_banding_trample_damage,
    can_block_with_barding,
)
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent, AttackerInfo,
)


def _make_perm(
    name: str = "Creature",
    keywords: list[str] | None = None,
    controller: str = "p1",
    power: str = "2",
    toughness: str = "2",
) -> Permanent:
    """Create a permanent with given properties."""
    card = Card(
        name=name,
        type_line="Creature — Human",
        keywords=keywords or [],
        power=power,
        toughness=toughness,
    )
    return Permanent(card=card, controller=controller)


def _make_game(perms: list[Permanent]) -> GameState:
    """Create a game state with given permanents."""
    return GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        battlefield=perms,
    )


def test_has_barding_true():
    """Creature with banding keyword has banding."""
    perm = _make_perm(keywords=["banding"])
    assert has_barding(perm) is True


def test_has_barding_false():
    """Creature without banding keyword does not have banding."""
    perm = _make_perm(keywords=["flying"])
    assert has_barding(perm) is False


def test_has_barding_no_keywords():
    """Creature with no keywords does not have banding."""
    perm = _make_perm(keywords=[])
    assert has_barding(perm) is False


def test_band_attackers_single_banding():
    """Single banding creature groups all attackers into one band."""
    banding = _make_perm(name="Banding Leader", keywords=["banding"], controller="p1")
    normal1 = _make_perm(name="Minion 1", controller="p1")
    normal2 = _make_perm(name="Minion 2", controller="p1")

    gs = _make_game([banding, normal1, normal2])
    bands = get_band_attackers(gs, "p1", [banding.id, normal1.id, normal2.id])

    assert len(bands) == 1
    assert set(bands[0]) == {banding.id, normal1.id, normal2.id}


def test_band_attackers_multiple_banding():
    """Multiple banding creatures form separate bands."""
    banding1 = _make_perm(name="Banding 1", keywords=["banding"], controller="p1")
    banding2 = _make_perm(name="Banding 2", keywords=["banding"], controller="p1")
    normal = _make_perm(name="Minion", controller="p1")

    gs = _make_game([banding1, banding2, normal])
    bands = get_band_attackers(gs, "p1", [banding1.id, banding2.id, normal.id])

    assert len(bands) == 2
    # First band has banding1 + normal, second band has banding2
    assert banding1.id in bands[0]
    assert normal.id in bands[0]
    assert bands[1] == [banding2.id]


def test_band_attackers_no_barding():
    """No banding creatures — single group."""
    normal1 = _make_perm(name="Minion 1", controller="p1")
    normal2 = _make_perm(name="Minion 2", controller="p1")

    gs = _make_game([normal1, normal2])
    bands = get_band_attackers(gs, "p1", [normal1.id, normal2.id])

    assert len(bands) == 1
    assert set(bands[0]) == {normal1.id, normal2.id}


def test_band_blockers_single_barding():
    """Single banding blocker groups all blockers into one band."""
    banding = _make_perm(name="Barding Blocker", keywords=["banding"], controller="p2")
    normal = _make_perm(name="Minion", controller="p2")

    gs = _make_game([banding, normal])
    attacker_info = AttackerInfo(
        permanent_id="attacker",
        defending_id="p2",
    )
    bands = get_band_blockers(gs, attacker_info, [banding.id, normal.id])

    assert len(bands) == 1
    assert set(bands[0]) == {banding.id, normal.id}


def test_banding_damage_flexible():
    """Banding allows flexible damage distribution."""
    attacker = _make_perm(name="Attacker", power="6", toughness="2")
    blocker1 = _make_perm(name="Banding A", keywords=["banding"], power="2", toughness="2")
    blocker2 = _make_perm(name="Banding B", keywords=["banding"], power="2", toughness="2")

    gs = _make_game([attacker, blocker1, blocker2])

    # In a band, any distribution is valid
    errors = validate_banding_damage_assignment(
        gs, attacker.id,
        [blocker1.id, blocker2.id],
        {blocker1.id: 1, blocker2.id: 5},
    )
    assert len(errors) == 0


def test_banding_damage_exceeds_power():
    """Banding still respects total power limit."""
    attacker = _make_perm(name="Attacker", power="3", toughness="2")
    blocker1 = _make_perm(name="Banding A", keywords=["banding"], power="2", toughness="2")
    blocker2 = _make_perm(name="Banding B", keywords=["banding"], power="2", toughness="2")

    gs = _make_game([attacker, blocker1, blocker2])

    errors = validate_banding_damage_assignment(
        gs, attacker.id,
        [blocker1.id, blocker2.id],
        {blocker1.id: 2, blocker2.id: 2},
    )
    assert len(errors) == 1
    assert "assigns 4 damage but has power 3" in errors[0]


def test_banding_trample_damage():
    """Trample with banding considers total band toughness."""
    attacker = _make_perm(
        name="Trampler", keywords=["trample"], power="6", toughness="2"
    )
    blocker1 = _make_perm(name="Banding A", keywords=["banding"], power="2", toughness="2")
    blocker2 = _make_perm(name="Banding B", keywords=["banding"], power="2", toughness="2")

    gs = _make_game([attacker, blocker1, blocker2])

    # Total toughness = 4, power = 6, so trample damage = 2
    trample = calculate_banding_trample_damage(
        gs, attacker,
        [blocker1.id, blocker2.id],
        {blocker1.id: 2, blocker2.id: 2},
    )
    assert trample == 2


def test_banding_trample_no_trample():
    """No trample damage without trample keyword."""
    attacker = _make_perm(name="Normal", power="6", toughness="2")
    blocker = _make_perm(name="Banding", keywords=["banding"], power="2", toughness="2")

    gs = _make_game([attacker, blocker])

    trample = calculate_banding_trample_damage(
        gs, attacker,
        [blocker.id],
        {blocker.id: 3},
    )
    assert trample == 0


def test_can_block_with_barding_blocker_has_barding():
    """Blocker with banding can block normally."""
    blocker = _make_perm(keywords=["banding"])
    attacker = _make_perm(keywords=[])

    gs = _make_game([blocker, attacker])
    assert can_block_with_barding(gs, blocker, attacker) is True


def test_can_block_with_barding_attacker_has_barding():
    """Blocker without banding can block attacker with banding."""
    blocker = _make_perm(keywords=[])
    attacker = _make_perm(keywords=["banding"])

    gs = _make_game([blocker, attacker])
    assert can_block_with_barding(gs, blocker, attacker) is True


def test_can_block_normal():
    """Normal creatures can block normally."""
    blocker = _make_perm(keywords=[])
    attacker = _make_perm(keywords=[])

    gs = _make_game([blocker, attacker])
    assert can_block_with_barding(gs, blocker, attacker) is True
