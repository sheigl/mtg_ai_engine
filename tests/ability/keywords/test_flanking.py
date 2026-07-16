"""Tests for flanking keyword (CMB-04)."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.ability.keywords.flanking import (
    FlankingKeyword,
    apply_flanking_on_block,
)
from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent,
)


def _make_perm(
    name: str = "Creature",
    keywords: list[str] | None = None,
    controller: str = "p1",
    oracle_text: str = "",
    power: str = "2",
    toughness: str = "2",
) -> Permanent:
    """Create a permanent with given properties."""
    card = Card(
        name=name,
        type_line="Creature — Human",
        keywords=keywords or [],
        oracle_text=oracle_text,
        power=power,
        toughness=toughness,
    )
    return Permanent(card=card, controller=controller)


def _make_game(perms: list[Permanent]) -> GameState:
    """Create a game state with given permanents."""
    return GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_BLOCKERS,
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        battlefield=perms,
    )


def test_flanking_applies_from_keywords():
    """Flanking detects keyword in keywords list."""
    perm = _make_perm(keywords=["flanking"])
    gs = _make_game([perm])

    kw = FlankingKeyword()
    assert kw.applies(gs, perm) is True


def test_flanking_applies_from_oracle():
    """Flanking detects keyword in oracle text."""
    perm = _make_perm(keywords=[], oracle_text="Flanking")
    gs = _make_game([perm])

    kw = FlankingKeyword()
    assert kw.applies(gs, perm) is True


def test_flanking_does_not_apply():
    """Flanking returns False for non-flanking creatures."""
    perm = _make_perm(keywords=["flying"], oracle_text="Flying.")
    gs = _make_game([perm])

    kw = FlankingKeyword()
    assert kw.applies(gs, perm) is False


def test_apply_flanking_gives_minus_one():
    """Flanking gives -1/-1 to blocked creature without flanking."""
    flanker = _make_perm(name="Flanker", keywords=["flanking"], controller="p2")
    attacker = _make_perm(name="Attacker", keywords=["flying"], controller="p1",
                          power="4", toughness="4")

    gs = _make_game([flanker, attacker])
    assert attacker.power_bonus == 0
    assert attacker.toughness_bonus == 0

    kw = FlankingKeyword()
    gs = kw.apply_flanking(gs, flanker, attacker)

    assert attacker.power_bonus == -1
    assert attacker.toughness_bonus == -1
    assert attacker.power_bonus_expires == "end_of_turn"
    assert attacker.toughness_bonus_expires == "end_of_turn"


def test_apply_flanking_no_effect_if_both_have():
    """Flanking does not apply if both creatures have flanking."""
    flanker = _make_perm(name="Flanker", keywords=["flanking"], controller="p2")
    attacker = _make_perm(name="Attacker", keywords=["flanking", "flying"],
                          controller="p1", power="4", toughness="4")

    gs = _make_game([flanker, attacker])

    kw = FlankingKeyword()
    gs = kw.apply_flanking(gs, flanker, attacker)

    assert attacker.power_bonus == 0
    assert attacker.toughness_bonus == 0


def test_apply_flanking_convenience():
    """Convenience function applies flanking correctly."""
    flanker = _make_perm(name="Flanker", keywords=["flanking"], controller="p2")
    attacker = _make_perm(name="Attacker", keywords=[], controller="p1",
                          power="4", toughness="4")

    gs = _make_game([flanker, attacker])
    gs = apply_flanking_on_block(gs, attacker, flanker)

    assert attacker.power_bonus == -1
    assert attacker.toughness_bonus == -1


def test_apply_flanking_convenience_no_flanker():
    """Convenience function does nothing if blocker has no flanking."""
    flanker = _make_perm(name="Normal", keywords=[], controller="p2")
    attacker = _make_perm(name="Attacker", keywords=[], controller="p1")

    gs = _make_game([flanker, attacker])
    gs = apply_flanking_on_block(gs, attacker, flanker)

    assert attacker.power_bonus == 0
    assert attacker.toughness_bonus == 0


def test_apply_flanking_convenience_both_flanking():
    """Convenience function does nothing if both have flanking."""
    flanker = _make_perm(name="Flanker", keywords=["flanking"], controller="p2")
    attacker = _make_perm(name="Attacker", keywords=["flanking"], controller="p1")

    gs = _make_game([flanker, attacker])
    gs = apply_flanking_on_block(gs, attacker, flanker)

    assert attacker.power_bonus == 0
    assert attacker.toughness_bonus == 0


def test_from_oracle():
    """Create FlankingKeyword from oracle text."""
    kw = FlankingKeyword.from_oracle("Flanking")
    assert kw is not None

    kw2 = FlankingKeyword.from_oracle("Flying. Trample.")
    assert kw2 is None


def test_flanking_description():
    """Flanking returns proper description."""
    kw = FlankingKeyword()
    desc = kw.get_trigger_description()
    assert "-1/-1" in desc
    assert "flanking" in desc.lower()


def test_flanking_apply_with_target():
    """Flanking apply with target applies the effect."""
    flanker = _make_perm(name="Flanker", keywords=["flanking"], controller="p2")
    attacker = _make_perm(name="Attacker", keywords=[], controller="p1",
                          power="4", toughness="4")

    gs = _make_game([flanker, attacker])
    kw = FlankingKeyword()
    gs = kw.apply(gs, flanker, target=attacker)

    assert attacker.power_bonus == -1
    assert attacker.toughness_bonus == -1


def test_flanking_apply_no_target():
    """Flanking apply without target is no-op."""
    flanker = _make_perm(name="Flanker", keywords=["flanking"], controller="p2")
    gs = _make_game([flanker])

    kw = FlankingKeyword()
    result = kw.apply(gs, flanker)
    assert result is gs
