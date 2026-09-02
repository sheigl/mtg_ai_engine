"""Verification test (QA): Fortification SBA when the HOST land survives but
becomes a non-land while still on the battlefield.

Covers sba.py:309-315 — the branch where ``target_perm`` still exists but is no
longer land-like, so the Fortification must detach AND the host's stale
``attachments`` reference must be cleaned (CR 301.7 / CR 704.5n).

This path is NOT exercised by test_fortify_integration.py::test_sba_detaches_after_host_leaves
(which removes the host entirely, making target_perm None and skipping the
host-attachment cleanup). Added by QA to close that gap; production code untouched.
"""
from mtg_engine.models.game import Card, GameState, ManaPool, Phase, PlayerState, Step
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.engine.sba import check_and_apply_sbas
from mtg_engine.ability.keywords.fortify import apply_fortify


def _make_game() -> GameState:
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="fortify-sba-host-nonland", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN,
        players=[p1, p2],
    )


def _garrison() -> Card:
    return Card(
        name="Darksteel Garrison", type_line="Artifact Creature — Fortification",
        oracle_text=(
            "Fortify {3} ({3}: Attach to target land you control. "
            "Fortify only as a sorcery. This card enters unattached and stays on the "
            "battlefield if the land leaves.)"
        ),
    )


def _forest() -> Card:
    return Card(name="Forest", type_line="Basic Land — Forest")


def test_host_survives_but_becomes_nonland_detaches_and_cleans_attachments():
    gs = _make_game()
    # Give p1 3 colorless to pay Fortify {3}.
    new_players = [
        p.model_copy(update={"mana_pool": ManaPool(C=3)}) if p.name == "p1" else p
        for p in gs.players
    ]
    gs = gs.model_copy(update={"players": new_players})

    gs, garrison = put_permanent_onto_battlefield(gs, _garrison(), "p1", from_zone="hand")
    gs, forest = put_permanent_onto_battlefield(gs, _forest(), "p1", from_zone="hand")
    gs = apply_fortify(gs, garrison, forest.id)

    # Sanity: attached.
    g = next(p for p in gs.battlefield if p.id == garrison.id)
    f = next(p for p in gs.battlefield if p.id == forest.id)
    assert g.attached_to == forest.id
    assert garrison.id in f.attachments

    # Simulate the host Forest becoming a non-land (e.g. some replacement effect /
    # type-changing effect) while it stays on the battlefield.
    new_bf = [
        p.model_copy(update={"card": p.card.model_copy(update={"type_line": "Creature — Beast"})})
        if p.id == forest.id else p
        for p in gs.battlefield
    ]
    gs = gs.model_copy(update={"battlefield": new_bf})

    gs, events = check_and_apply_sbas(gs)

    g2 = next(p for p in gs.battlefield if p.id == garrison.id)
    f2 = next(p for p in gs.battlefield if p.id == forest.id)
    # Fortification detaches and stays on the battlefield (not destroyed).
    assert g2.attached_to is None
    assert any(e.sba_type == "fortification_detach" for e in events)
    # Host survives, still present.
    assert f2.card.type_line == "Creature — Beast"
    # CRITICAL: host's stale attachments reference was cleaned (no dangling id).
    assert garrison.id not in f2.attachments
