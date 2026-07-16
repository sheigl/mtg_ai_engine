"""Tests for mana abilities (MANA-02)."""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, project_root)

from mtg_engine.models.game import (
    GameState, Phase, Step, PlayerState, Card, Permanent, ManaPool,
)
from mtg_engine.engine.mana import (
    parse_land_mana_production,
    get_land_mana_abilities,
    resolve_land_mana_ability,
)


def _make_perm(
    name: str = "Land",
    type_line: str = "Basic Land — Forest",
    keywords: list[str] | None = None,
    oracle_text: str = "",
    controller: str = "p1",
    supertypes: list[str] | None = None,
) -> Permanent:
    card = Card(
        name=name,
        type_line=type_line,
        keywords=keywords or [],
        oracle_text=oracle_text,
        supertypes=supertypes or [],
    )
    return Permanent(card=card, controller=controller)


def _make_game(perms: list[Permanent], player_mana: ManaPool | None = None) -> GameState:
    player = PlayerState(name="p1", mana_pool=player_mana or ManaPool())
    return GameState(
        game_id="test", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[player],
        battlefield=perms,
    )


# ─── parse_land_mana_production ───────────────────────────────────────────────

def test_parse_basic_tap_for_green():
    """Parse '{T}: Add {G}'."""
    result = parse_land_mana_production("{T}: Add {G}.")
    assert len(result) == 1
    assert result[0]["symbols"] == ["G"]
    assert result[0]["tap_required"] is True
    assert result[0]["choice"] is False


def test_parse_dual_land_choice():
    """Parse '{T}: Add {W} or {U}'."""
    result = parse_land_mana_production("{T}: Add {W} or {U}.")
    assert len(result) == 1
    assert set(result[0]["symbols"]) == {"W", "U"}
    assert result[0]["tap_required"] is True
    assert result[0]["choice"] is True


def test_parse_etb_mana():
    """Parse 'When ~ enters, add {C}'."""
    result = parse_land_mana_production("When this land enters the battlefield, add {C}.")
    assert len(result) == 1
    assert result[0]["symbols"] == ["C"]
    assert result[0]["tap_required"] is False


def test_parse_no_mana_ability():
    """Non-mana text produces no results."""
    result = parse_land_mana_production("Flying.")
    assert len(result) == 0


def test_parse_empty():
    """Empty text produces no results."""
    result = parse_land_mana_production("")
    assert len(result) == 0


# ─── get_land_mana_abilities ──────────────────────────────────────────────────

def test_basic_forest():
    """Basic Forest produces {G}."""
    perm = _make_perm(type_line="Basic Land — Forest")
    abilities = get_land_mana_abilities(perm)
    assert len(abilities) == 1
    assert abilities[0]["symbols"] == ["G"]
    assert abilities[0]["tap_required"] is True


def test_basic_island():
    """Basic Island produces {U}."""
    perm = _make_perm(type_line="Basic Land — Island")
    abilities = get_land_mana_abilities(perm)
    assert len(abilities) == 1
    assert abilities[0]["symbols"] == ["U"]


def test_dual_land_oracle():
    """Dual land with oracle ability."""
    perm = _make_perm(
        name="Steam Vents",
        type_line="Land",
        oracle_text="{T}: Add {R} or {U}.",
    )
    abilities = get_land_mana_abilities(perm)
    assert len(abilities) == 1
    assert abilities[0]["choice"] is True
    assert set(abilities[0]["symbols"]) == {"R", "U"}


def test_mana_conduit():
    """Land with multiple mana abilities."""
    perm = _make_perm(
        name="Mana Conduit",
        type_line="Land",
        oracle_text="{T}: Add {R}. {T}, Sacrifice ~: Add {RRR}.",
    )
    abilities = get_land_mana_abilities(perm)
    assert len(abilities) >= 1


# ─── resolve_land_mana_ability ────────────────────────────────────────────────

def test_resolve_forest():
    """Resolve basic Forest mana ability."""
    perm = _make_perm(type_line="Basic Land — Forest", controller="p1")
    gs = _make_game([perm])
    gs = resolve_land_mana_ability(gs, perm.id)

    assert perm.tapped is True
    player = gs.players[0]
    assert player.mana_pool.G == 1


def test_resolve_dual_land_default():
    """Resolve dual land ability (default to first symbol)."""
    perm = _make_perm(
        name="Striped Riverwalk",
        type_line="Land",
        oracle_text="{T}: Add {W} or {U}.",
        controller="p1",
    )
    gs = _make_game([perm])
    gs = resolve_land_mana_ability(gs, perm.id)

    assert perm.tapped is True
    player = gs.players[0]
    assert player.mana_pool.W == 1


def test_resolve_dual_land_chosen():
    """Resolve dual land ability with chosen symbol."""
    perm = _make_perm(
        name="Striped Riverwalk",
        type_line="Land",
        oracle_text="{T}: Add {W} or {U}.",
        controller="p1",
    )
    gs = _make_game([perm])
    gs = resolve_land_mana_ability(gs, perm.id, chosen_symbol="U")

    assert perm.tapped is True
    player = gs.players[0]
    assert player.mana_pool.U == 1


def test_resolve_nonexistent_perm():
    """Resolve ability for nonexistent permanent is no-op."""
    gs = _make_game([])
    gs2 = resolve_land_mana_ability(gs, "nonexistent")
    assert gs2 is not None


def test_resolve_out_of_range_ability():
    """Resolve ability with out-of-range index is no-op."""
    perm = _make_perm(type_line="Basic Land — Forest", controller="p1")
    gs = _make_game([perm])
    gs = resolve_land_mana_ability(gs, perm.id, ability_index=99)
    player = gs.players[0]
    assert player.mana_pool.G == 0


def test_resolve_snow_land():
    """Snow land tracks snow mana."""
    perm = _make_perm(
        type_line="Snow Basic Land — Forest",
        controller="p1",
        supertypes=["Snow"],
    )
    gs = _make_game([perm])
    gs = resolve_land_mana_ability(gs, perm.id)

    player = gs.players[0]
    assert player.mana_pool.G == 1
    assert player.mana_pool.snow == 1
