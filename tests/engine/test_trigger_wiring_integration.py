"""
7-2 Trigger Wiring Integration Tests (Sprint 7)

Natural-context integration tests verifying that each of the 13 trigger
categories fires through its REAL engine entry point — not by calling the
``check_*`` functions directly. Each test performs the actual game action a
player would take and asserts the corresponding trigger lands in
``game_state.pending_triggers``.

Covers (one natural-context test per trigger):

  1.  sacrifice        via ``zones._sacrifice_permanent``
  2.  life_gain_lost   via ``stack._gain_life``   (gain)
  3.  life_gain_lost   via ``stack._lose_life``   (loss)
  4.  fight            via ``stack._apply_fight``
  5.  transformed      via ``daynight.check_daynight_transition``
  6.  becomes_target   via ``stack.cast_spell``
  7.  attach           via ``stack._apply_equip``
  8.  mana_spent       via ``stack.cast_spell`` (+ 0-cost control)
  9.  draw             via ``stack._draw_cards``
  10. discard          via ``stack._discard_cards``
  11. token            via ``stack._create_tokens``
  12. counter          via ``stack._add_counters``
  13. mana_production  via ``mana.resolve_land_mana_ability``
  14. tutor            via ``stack._tutor``
"""
import uuid

import pytest

from mtg_engine.models.game import (
    GameState,
    Permanent,
    Card,
    CardFace,
    PlayerState,
    ManaPool,
    Phase,
    Step,
)
from mtg_engine.engine.zones import _sacrifice_permanent
from mtg_engine.engine.stack import (
    cast_spell,
    _gain_life,
    _lose_life,
    _apply_fight,
    _create_tokens,
    _add_counters,
    _draw_cards,
    _discard_cards,
    _tutor,
    _apply_equip,
)
from mtg_engine.engine.mana import resolve_land_mana_ability
from mtg_engine.engine.daynight import check_daynight_transition


# ─── Test helpers ────────────────────────────────────────────────────

def _make_gs(battlefield=None, players=None, **kwargs) -> GameState:
    return GameState(
        game_id="trig-wire",
        seed=42,
        turn=1,
        active_player="Alice",
        priority_holder="Alice",
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=players
        or [
            PlayerState(name="Alice", life=20),
            PlayerState(name="Bob", life=20),
        ],
        battlefield=battlefield or [],
        **kwargs,
    )


def _perm(
    name: str,
    oracle_text: str,
    controller: str = "Alice",
    type_line: str = "Creature — Human",
    **card_kwargs,
) -> Permanent:
    return Permanent(
        id=str(uuid.uuid4()),
        card=Card(name=name, type_line=type_line, oracle_text=oracle_text, **card_kwargs),
        controller=controller,
    )


def _trigger_types(gs: GameState) -> list[str]:
    return [t.trigger_type for t in gs.pending_triggers]


# ─── 1. Sacrifice ────────────────────────────────────────────────────

class TestSacrificeWiring:
    def test_sacrifice_fires_via_sacrifice_permanent(self):
        """Sacrificing a creature you control fires the 'is sacrificed' trigger."""
        gs = _make_gs()
        watcher = _perm(
            "Zulaport Cutthroat",
            "Whenever a creature you control is sacrificed, that creature's "
            "controller loses 1 life and you gain 1 life.",
        )
        victim = _perm(
            "Beast of Burden", "", controller="Alice", type_line="Creature — Beast"
        )
        gs.battlefield.extend([watcher, victim])

        gs = _sacrifice_permanent(gs, victim.id, sacrificer="Alice")

        # The victim really left the battlefield...
        assert victim.id not in [p.id for p in gs.battlefield]
        # ...and the sacrifice trigger was queued.
        assert "sacrifice" in _trigger_types(gs)

    def test_opponent_sacrifice_does_not_fire(self):
        """Negative: 'a creature you control is sacrificed' does NOT fire when an
        OPPONENT's creature is sacrificed (CR 701.19 'you control' filter)."""
        gs = _make_gs()
        watcher = _perm(
            "Zulaport Cutthroat",
            "Whenever a creature you control is sacrificed, that creature's "
            "controller loses 1 life and you gain 1 life.",
        )
        # Victim controlled by OPPONENT (Bob), sacrificed by Bob.
        victim = _perm(
            "Bob's Beast", "", controller="Bob", type_line="Creature — Beast"
        )
        gs.battlefield.extend([watcher, victim])

        gs = _sacrifice_permanent(gs, victim.id, sacrificer="Bob")

        # The victim really left the battlefield...
        assert victim.id not in [p.id for p in gs.battlefield]
        # ...but no "is sacrificed" trigger queued (wrong controller).
        assert "sacrifice" not in _trigger_types(gs)


# ─── 2/3. Life Gain / Life Lost ──────────────────────────────────────

class TestLifeGainLostWiring:
    def test_life_gain_fires_via_gain_life(self):
        """Gaining life fires the 'gain life' trigger (not the 'lose' one)."""
        gs = _make_gs()
        watcher = _perm(
            "Karametra's Blessing",
            "Whenever you gain life, put a +1/+1 counter on this creature.",
        )
        gs.battlefield.append(watcher)

        gs = _gain_life(gs, "Alice", 3)

        assert gs.players[0].life == 23  # life actually changed
        assert "life_gain_lost" in _trigger_types(gs)

    def test_life_lost_fires_via_lose_life(self):
        """Losing life fires the 'lose life' trigger (not the 'gain' one)."""
        gs = _make_gs()
        watcher = _perm(
            "Geth's Grimoire",
            "Whenever you lose life, draw a card.",
        )
        gs.battlefield.append(watcher)

        gs = _lose_life(gs, "Alice", 2)

        assert gs.players[0].life == 18  # life actually changed
        assert "life_gain_lost" in _trigger_types(gs)


# ─── 4. Fight ────────────────────────────────────────────────────────

class TestFightWiring:
    def test_fight_fires_via_apply_fight(self):
        """A creature fighting fires the 'this creature fights' trigger."""
        gs = _make_gs()
        fighter = _perm(
            "Sword of the Paruns",
            "Whenever this creature fights, put a +1/+1 counter on it.",
            type_line="Artifact Creature — Legendary",
            power="2",
            toughness="2",
        )
        opponent = _perm(
            "Opponent Beast", "", controller="Bob",
            type_line="Creature — Beast", power="2", toughness="2",
        )
        gs.battlefield.extend([fighter, opponent])

        gs = _apply_fight(gs, fighter.id, opponent.id)

        # Damage was actually dealt in both directions...
        by_id = {p.id: p for p in gs.battlefield}
        assert by_id[opponent.id].damage_marked >= 1
        assert by_id[fighter.id].damage_marked >= 1
        assert "fight" in _trigger_types(gs)


# ─── 5. Transformed ──────────────────────────────────────────────────

class TestTransformedWiring:
    def test_transformed_fires_via_daynight_transition(self):
        """A daybound DFC flipping on the day→night transition fires its trigger."""
        gs = _make_gs(is_day=True, spells_cast_last_turn=0)
        card = Card(
            name="Tovolar's Huntmaster",
            type_line="Legendary Creature — Werewolf",
            oracle_text="Daybound\nWhenever this transforms, draw a card.",
            faces=[
                CardFace(name="Tovolar's Huntmaster", type_line="Legendary Creature — Werewolf"),
                CardFace(name="Huntmaster's Nightmare", type_line="Legendary Creature — Werewolf"),
            ],
        )
        perm = Permanent(id=str(uuid.uuid4()), card=card, controller="Alice")
        gs.battlefield.append(perm)

        gs = check_daynight_transition(gs)

        assert gs.is_day is False  # transition actually happened
        assert "transformed" in _trigger_types(gs)


# ─── 6. Becomes Target ───────────────────────────────────────────────

class TestBecomesTargetWiring:
    def test_becomes_target_fires_via_cast_spell(self):
        """Casting a spell that targets a creature fires its 'becomes target' trigger."""
        gs = _make_gs()
        target_creature = _perm(
            "Shiny Impetus",
            "Whenever this creature becomes the target of a spell or ability, "
            "draw a card.",
            type_line="Creature — Human",
        )
        gs.battlefield.append(target_creature)

        spell = Card(
            name="Lightning Bolt",
            type_line="Instant",
            oracle_text="Deal 3 damage to any target.",
            mana_cost="{R}",
            cmc=1.0,
        )
        gs.players[0].hand.append(spell)
        gs.players[0].mana_pool = ManaPool(R=1)

        gs = cast_spell(
            gs, "Alice", spell.id, targets=[target_creature.id], mana_payment={"R": 1}
        )

        assert "becomes_target" in _trigger_types(gs)


# ─── 7. Attach ───────────────────────────────────────────────────────

class TestAttachWiring:
    def test_attach_fires_via_equip(self):
        """Equipping equipment fires the 'this becomes attached' trigger."""
        gs = _make_gs()
        equip_card = Card(
            name="Sword of the Gods",
            type_line="Artifact — Equipment",
            oracle_text=(
                "Equipped creature gets +2/+0\n"
                "Whenever this becomes attached to another permanent, draw a card."
            ),
        )
        equipment = Permanent(id=str(uuid.uuid4()), card=equip_card, controller="Alice")
        creature = _perm(
            "Goblin Soldier", "", controller="Alice", type_line="Creature — Goblin"
        )
        gs.battlefield.extend([equipment, creature])

        gs = _apply_equip(gs, equipment.id, creature.id)

        by_id = {p.id: p for p in gs.battlefield}
        assert by_id[equipment.id].attached_to == creature.id  # actually attached
        assert "attach" in _trigger_types(gs)


# ─── 8. Mana Spent ───────────────────────────────────────────────────

class TestManaSpentWiring:
    def test_mana_spent_fires_via_cast_spell(self):
        """Casting a spell that pays mana fires the 'spend mana' trigger."""
        gs = _make_gs()
        watcher = _perm(
            "Karametra's Aegis",
            "Whenever you spend mana, put a +1/+1 counter on this creature.",
        )
        gs.battlefield.append(watcher)

        spell = Card(
            name="Lightning Bolt",
            type_line="Instant",
            oracle_text="Deal 3 damage to any target.",
            mana_cost="{R}",
            cmc=1.0,
        )
        gs.players[0].hand.append(spell)
        gs.players[0].mana_pool = ManaPool(R=1)

        gs = cast_spell(gs, "Alice", spell.id, targets=[], mana_payment={"R": 1})

        assert gs.players[0].mana_pool.R == 0  # mana was actually paid
        assert "mana_spent" in _trigger_types(gs)

    def test_mana_spent_does_not_fire_on_zero_cost_cast(self):
        """A 0-cost spell pays no mana, so the 'spend mana' trigger must NOT fire
        (MINOR 7: the trigger is guarded by a non-empty ``mana_payment``)."""
        gs = _make_gs()
        watcher = _perm(
            "Karametra's Aegis",
            "Whenever you spend mana, put a +1/+1 counter on this creature.",
        )
        gs.battlefield.append(watcher)

        spell = Card(
            name="No Cost Zap",
            type_line="Instant",
            oracle_text="Deal 2 damage to any target.",
            mana_cost="",
            cmc=0.0,
        )
        gs.players[0].hand.append(spell)

        gs = cast_spell(gs, "Alice", spell.id, targets=[], mana_payment={})

        assert "mana_spent" not in _trigger_types(gs)


# ─── 9. Draw ─────────────────────────────────────────────────────────

class TestDrawWiring:
    def test_draw_fires_via_draw_cards(self):
        """Drawing a card fires the 'you draw a card' trigger."""
        gs = _make_gs()
        watcher = _perm(
            "Nessian Warlord",
            "Whenever you draw a card, put a +1/+1 counter on this creature.",
        )
        gs.battlefield.append(watcher)
        # Give the library several cards so drawing one does not empty it
        # (empty library = game loss, which is not what we are testing here).
        gs.players[0].library = [
            Card(name="Basic Land", type_line="Basic Land — Forest") for _ in range(3)
        ]

        gs = _draw_cards(gs, "Alice", 1)

        assert len(gs.players[0].hand) == 1  # a card was actually drawn
        assert "draw" in _trigger_types(gs)


# ─── 10. Discard ─────────────────────────────────────────────────────

class TestDiscardWiring:
    def test_discard_fires_via_discard_cards(self):
        """Discarding a card fires the 'you discard a card' trigger."""
        gs = _make_gs()
        watcher = _perm(
            "Doom Blade",
            "Whenever you discard a card, put a -1/-1 counter on this creature.",
        )
        gs.battlefield.append(watcher)
        gs.players[0].hand = [
            Card(name="Basic Land", type_line="Basic Land — Forest"),
            Card(name="Basic Land 2", type_line="Basic Land — Forest"),
        ]

        gs = _discard_cards(gs, "Alice", 1)

        assert len(gs.players[0].hand) == 1  # a card was actually discarded
        assert len(gs.players[0].graveyard) == 1
        assert "discard" in _trigger_types(gs)


# ─── 11. Token Created ───────────────────────────────────────────────

class TestTokenWiring:
    def test_token_created_fires_via_create_tokens(self):
        """Creating a creature token fires the 'you create a token' trigger."""
        gs = _make_gs()
        watcher = _perm(
            "Goblin Gang-Up",
            "Whenever you create a creature token, put a +1/+1 counter on this creature.",
        )
        gs.battlefield.append(watcher)

        gs = _create_tokens(gs, "Alice", "a", "1", "1", "Goblin")

        # A Goblin token is now on the battlefield...
        assert any(p.is_token for p in gs.battlefield)
        # ...and the token-created trigger was queued.
        assert "token" in _trigger_types(gs)


# ─── 12. Counter Placed ──────────────────────────────────────────────

class TestCounterWiring:
    def test_counter_placed_fires_via_add_counters(self):
        """Placing a +1/+1 counter on a creature you control fires the trigger."""
        gs = _make_gs()
        countered = _perm(
            "Charger", "", controller="Alice", type_line="Creature — Beast"
        )
        watcher = _perm(
            "Sun Titan",
            "Whenever a +1/+1 counter is put on a creature you control, draw a card.",
        )
        gs.battlefield.extend([countered, watcher])

        gs = _add_counters(gs, countered.id, "+1/+1", 1)

        by_id = {p.id: p for p in gs.battlefield}
        assert by_id[countered.id].counters.get("+1/+1") == 1  # counter placed
        assert "counter" in _trigger_types(gs)


# ─── 13. Mana Production ─────────────────────────────────────────────

class TestManaProductionWiring:
    def test_mana_production_fires_via_land_mana(self):
        """Tapping a land for mana fires the 'land produces mana' trigger."""
        gs = _make_gs()
        forest = _perm(
            "Forest", "{T}: Add {G}.", controller="Alice",
            type_line="Basic Land — Forest",
        )
        watcher = _perm(
            "Gaea's Cradle",
            "Whenever a land produces mana, you may pay 2 life. If you do, "
            "target creature gets -1/-1 until end of turn.",
            type_line="Creature — Elemental",
        )
        gs.battlefield.extend([forest, watcher])

        gs = resolve_land_mana_ability(gs, forest.id)

        by_id = {p.id: p for p in gs.battlefield}
        assert by_id[forest.id].tapped is True  # land actually tapped
        assert gs.players[0].mana_pool.G == 1  # mana actually produced
        assert "mana_production" in _trigger_types(gs)


# ─── 14. Tutor ───────────────────────────────────────────────────────

class TestTutorWiring:
    def test_tutor_fires_via_tutor(self):
        """Searching the library fires the 'you search your library' trigger."""
        gs = _make_gs()
        watcher = _perm(
            "Psychogenic Probe",
            "Whenever you search your library, put a -1/-1 counter on this creature.",
        )
        gs.battlefield.append(watcher)
        gs.players[0].library = [
            Card(name="Beast of Burden", type_line="Creature — Beast")
        ]

        gs = _tutor(gs, "Alice", "creature", "hand")

        assert len(gs.players[0].hand) == 1  # a card was actually put in hand
        assert "tutor" in _trigger_types(gs)


if __name__ == "__main__":  # pragma: no cover - manual run convenience
    raise SystemExit(pytest.main([__file__, "-v"]))
