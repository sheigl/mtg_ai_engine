"""
7-17 Integration: Fading counter-removed upkeep route (CR 702.67).

The existing ``test_020_fading.py`` drives ``begin_step`` and asserts the
COUNTER COUNT / sacrifice OUTCOME, but never asserted that a TRIGGER actually
fires through this real entry point. These tests close that gap: they place a
watcher whose oracle text references the Fading route and assert the matching
trigger lands in ``pending_triggers`` when ``begin_step`` runs the upkeep.

Real entry point under test: ``turn_manager.begin_step`` (US26 T058 Fading
upkeep — remove one fade counter, fire "counter removed" triggers, sacrifice on
the last counter which fires "is sacrificed" triggers).
"""
import uuid

from mtg_engine.models.game import (
    GameState,
    PlayerState,
    Phase,
    Step,
    Card,
    Permanent,
    ManaPool,
)
from mtg_engine.engine.turn_manager import begin_step


def _base_gs(seed: int):
    """A standard 2-player game parked at player_1's beginning-of-upkeep."""
    players = [
        PlayerState(name="p1", life=20, hand=[], mana_pool=ManaPool(),
                    library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
        PlayerState(name="p2", life=20, hand=[], mana_pool=ManaPool(),
                    library=[], graveyard=[], exile=[], command_zone=[], deck=[]),
    ]
    return GameState(
        game_id=f"test_fading_trig_{seed}",
        seed=seed,
        players=players,
        turn=1,
        phase=Phase.BEGINNING,
        step=Step.UPKEEP,
        active_player="p1",
        priority_holder="p1",
        stack=[],
        battlefield=[],
        graveyards={"p1": [], "p2": []},
        exile_zone={},
        pending_triggers=[],
        pending_choices=[],
        is_game_over=False,
        winner=None,
        format="standard",
    )


def _fading_perm(perm_id: str, fade: int, oracle_text: str = "Flying, Fading 3"):
    return Permanent(
        id=perm_id,
        card=Card(
            name="Cloud of Faeries",
            mana_cost="{U}",
            type_line="Creature - Faerie",
            oracle_text=oracle_text,
            power="1",
            toughness="1",
            colors=["U"],
        ),
        controller="p1",
        tapped=False,
        counters={"fade": fade},
        turn_entered_battlefield=1,
        summoning_sick=False,
    )


def _counter_removed_watcher():
    """A general (non self-referential) 'counter removed' watcher. Fires for any
    permanent that loses a counter, so it survives begin_step's per-permanent
    ``perm_id`` lookup regardless of which creature is the Fading subject."""
    return Permanent(
        id=str(uuid.uuid4()),
        card=Card(
            name="Resupply",
            mana_cost="{1}",
            # Must be a permanent: instants/sorceries are parsed wholesale as a
            # SpellEffect and never yield a TriggeredAbility.
            type_line="Enchantment",
            oracle_text="Whenever a counter is removed from any permanent, "
                        "draw a card.",
            power="0",
            toughness="0",
        ),
        controller="p1",
    )


def _sacrifice_watcher():
    return Permanent(
        id=str(uuid.uuid4()),
        card=Card(
            name="Zulaport Cutthroat",
            mana_cost="{B}",
            type_line="Creature - Merfolk",
            oracle_text="Whenever a creature you control is sacrificed, that "
                        "creature's controller loses 1 life and you gain 1 life.",
            power="1",
            toughness="1",
        ),
        controller="p1",
    )


def _trigger_types(gs: GameState) -> list[str]:
    return [t.trigger_type for t in gs.pending_triggers]


class TestFadingCounterRemovedTriggerRoute:
    """When Fading removes a counter (but does not sacrifice), the
    'counter removed' trigger route must fire through begin_step."""

    def test_counter_removed_trigger_fires_when_not_last(self):
        """Fading 2 -> 1 on upkeep: 'whenever a counter is removed' fires while
        the permanent survives (so no sacrifice trigger)."""
        gs = _base_gs(101)
        gs.battlefield.extend([_fading_perm("perm_fade_2", fade=2),
                               _counter_removed_watcher()])

        gs = begin_step(gs)

        perm = gs.battlefield[0]
        assert perm.counters.get("fade") == 1          # one counter removed
        assert "counter" in _trigger_types(gs), (
            f"Fading counter-removed route did not fire; got {_trigger_types(gs)}"
        )

    def test_counter_removed_trigger_does_not_fire_for_opponent(self):
        """Opponent's Fading creature is processed at ITS OWN upkeep, so p1's
        'counter removed' watcher stays silent during p1's upkeep."""
        gs = _base_gs(102)
        opp = _fading_perm("perm_opp_fade", fade=2)
        opp.controller = "p2"
        gs.battlefield.extend([_counter_removed_watcher(), opp])

        gs = begin_step(gs)

        assert "counter" not in _trigger_types(gs)


class TestFadingSacrificeTriggerRoute:
    """When Fading removes the LAST counter, the permanent is sacrificed and the
    'is sacrificed' trigger route must fire through begin_step."""

    def test_sacrifice_trigger_fires_on_last_counter(self):
        """Fading 1 -> 0 on upkeep: permanent sacrificed to graveyard AND
        'a creature you control is sacrificed' fires for a p1 watcher."""
        gs = _base_gs(103)
        gs.battlefield.extend([_sacrifice_watcher(),
                               _fading_perm("perm_fade_1", fade=1)])

        gs = begin_step(gs)

        # Permanent sacrificed (left battlefield)...
        assert all(p.id != "perm_fade_1" for p in gs.battlefield)
        # ...and the sacrifice trigger route fired through begin_step.
        assert "sacrifice" in _trigger_types(gs), (
            f"Fading sacrifice route did not fire; got {_trigger_types(gs)}"
        )

    def test_sacrifice_trigger_does_not_fire_for_opponent(self):
        """p1's 'is sacrificed' watcher stays silent when only the OPPONENT's
        Fading creature exists — it is not processed during p1's upkeep."""
        gs = _base_gs(104)
        opp = _fading_perm("perm_opp_sac", fade=1)
        opp.controller = "p2"
        gs.battlefield.extend([_sacrifice_watcher(), opp])

        gs = begin_step(gs)

        assert "sacrifice" not in _trigger_types(gs)
