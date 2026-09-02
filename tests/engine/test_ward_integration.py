"""Integration tests for the Ward keyword (CR 702.145).

Covers the pure-transform resolution in :meth:`Ward.apply` (human queue / AI
auto-resolve), self-targeting bypass, independence of multiple triggers, and the
real firing through stack.py's ``cast_spell`` becomes-target flow.

These tests exercise the engine directly (no HTTP layer) following the module-level
helper pattern used elsewhere in ``tests/``.
"""
from mtg_engine.models.game import (
    Card,
    GameState,
    ManaPool,
    Permanent,
    PlayerState,
    StackObject,
)
from mtg_engine.engine.stack import cast_spell
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.ability.keywords.ward import Ward


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _game(human_player: str | None = None) -> GameState:
    """Two players; ``Bot`` starts with 2 colourless mana."""
    alice = PlayerState(name="Alice", life=20, mana_pool=ManaPool())
    bot = PlayerState(name="Bot", life=20, mana_pool=ManaPool(C=2))
    return GameState(
        game_id="ward_test",
        seed=1,
        active_player="Alice",
        priority_holder="Alice",
        players=[alice, bot],
        human_player_name=human_player,
    )


def _ward_card() -> Card:
    return Card(
        name="Ward Creature",
        type_line="Creature — Goblin",
        power="1",
        toughness="1",
        mana_cost="{1}",
        keywords=["ward"],
        oracle_text="Ward {2}",
    )


def _bolt_card() -> Card:
    return Card(
        name="Bolt",
        type_line="Instant",
        mana_cost="{R}",
        oracle_text="Deal 3 damage to any target.",
    )


def _ward_perm(gs: GameState, controller: str = "Alice"):
    gs, perm = put_permanent_onto_battlefield(gs, _ward_card(), controller)
    return gs, perm


# ---------------------------------------------------------------------------
# No-op / guard paths (Q4 — strict same-object returns, no double-fire)
# ---------------------------------------------------------------------------

def test_no_caster_is_noop_same_object():
    """A trigger with no identifiable caster is a strict no-op (same object)."""
    gs = _game()
    gs, perm = _ward_perm(gs, "Alice")
    result = Ward().apply(gs, perm, caster_name=None)
    assert result is gs
    assert result.pending_ward_payment is None


def test_self_targeting_no_trigger():
    """CR 702.145b: a permanent that is its own target never triggers Ward."""
    gs = _game()
    gs, perm = _ward_perm(gs, "Alice")
    # Alice targets herself — no trigger regardless of human/AI.
    result = Ward().apply(gs, perm, caster_name="Alice")
    assert result is gs
    assert result.pending_ward_payment is None


def test_empty_controller_noop():
    """A ward permanent with no controller is a strict no-op (same object)."""
    gs = _game()
    perm = Permanent(card=_ward_card(), controller="")  # not attached to anyone
    result = Ward().apply(gs, perm, caster_name="Bot")
    assert result is gs
    assert result.pending_ward_payment is None


# ---------------------------------------------------------------------------
# Pure-transform contract (Q4)
# ---------------------------------------------------------------------------

def test_human_queue_returns_new_object():
    """A human caster queues the pay/counter choice and gets a new GameState."""
    gs = _game(human_player="Alice")
    gs, perm = _ward_perm(gs, "Bob")  # Bob's ward targeted by Alice
    result = Ward().apply(gs, perm, target=None, caster_name="Alice")
    assert id(result) != id(gs)
    pending = result.pending_ward_payment
    assert pending is not None
    assert pending["player"] == "Alice"
    assert pending["ward_cost"] == "{2}"
    assert pending["target_permanent_id"] == perm.id
    # Original object untouched — no in-place mutation.
    assert gs.pending_ward_payment is None


def test_paid_does_not_mutate_original_state():
    """Paying ward must not mutate the original GameState (pure transform)."""
    gs = _game()  # Bot has C=2, affordable for Ward {2}
    gs, perm = _ward_perm(gs, "Bob")
    spell = StackObject(id="spell-1", source_card=_bolt_card(), controller="Bot")
    gs.stack.append(spell)
    result = Ward().apply(gs, perm, target=spell, caster_name="Bot")

    # Original untouched.
    assert gs.players[1].mana_pool.C == 2
    assert gs.pending_ward_payment is None
    # Result: Bot paid and spell continues (still on stack).
    assert result.players[1].mana_pool.C == 0
    assert any(s.id == "spell-1" for s in result.stack)
    assert result.pending_ward_payment is None


# ---------------------------------------------------------------------------
# AI auto-resolve by affordability (CR 702.145b / 702.157b)
# ---------------------------------------------------------------------------

def test_ai_pays_when_affordable():
    gs = _game()  # Bot C=2, affordable for Ward {2}
    gs, perm = _ward_perm(gs, "Bob")
    spell = StackObject(id="spell-1", source_card=_bolt_card(), controller="Bot")
    gs.stack.append(spell)
    result = Ward().apply(gs, perm, target=spell, caster_name="Bot")

    assert result.pending_ward_payment is None          # resolved, not queued
    assert result.players[1].mana_pool.C == 0           # paid {2}
    assert any(s.id == "spell-1" for s in result.stack)  # spell continues


def test_ai_counters_when_unaffordable():
    gs = _game()
    bot = next(p for p in gs.players if p.name == "Bot")
    bot.mana_pool = ManaPool(C=0)                      # cannot afford Ward {2}
    gs, perm = _ward_perm(gs, "Bob")
    spell = StackObject(id="spell-b", source_card=_bolt_card(), controller="Bot")
    gs.stack.append(spell)
    original_bot = next(p for p in gs.players if p.name == "Bot")
    result = Ward().apply(gs, perm, target=spell, caster_name="Bot")

    assert result.pending_ward_payment is None          # resolved
    assert not any(s.id == "spell-b" for s in result.stack)  # countered
    # Source card to the RETURNED state's player graveyard (pure transform —
    # read from the new state, not the original shared player object).
    result_bot = next(p for p in result.players if p.name == "Bot")
    assert "Bolt" in [c.name for c in result_bot.graveyard]
    # Original state untouched — no in-place graveyard.append on the live player.
    assert "Bolt" not in [c.name for c in original_bot.graveyard]


def test_ai_pays_colored_cost():
    gs = _game()
    bot = next(p for p in gs.players if p.name == "Bot")
    bot.mana_pool = ManaPool(R=1)                       # only red, not generic
    gs, perm = _ward_perm(gs, "Bob")
    spell = StackObject(id="spell-c", source_card=_bolt_card(), controller="Bot")
    gs.stack.append(spell)

    # Ward {R} is affordable with a single red — pay it rather than counter.
    result = Ward(cost="{R}").apply(gs, perm, target=spell, caster_name="Bot")
    assert result.pending_ward_payment is None
    assert result.players[1].mana_pool.R == 0
    assert any(s.id == "spell-c" for s in result.stack)


def test_multiple_wards_fire_independently():
    """A ward creature targeted by two spells fires twice — once per event, no
    global deduplication. The first caster pays; the second cannot."""
    gs = _game()  # Bot C=2
    other = PlayerState(name="Other", life=20, mana_pool=ManaPool())
    gs.players.append(other)

    gs, perm = _ward_perm(gs, "Bob")
    spell_a = StackObject(id="spell-a", source_card=_bolt_card(), controller="Bot")
    spell_b = StackObject(id="spell-b", source_card=_bolt_card(), controller="Other")
    gs.stack.extend([spell_a, spell_b])

    # Bot can afford Ward {2} — pays; spell A continues.
    gs = Ward().apply(gs, perm, target=spell_a, caster_name="Bot")
    assert gs.players[1].mana_pool.C == 0
    assert any(s.id == "spell-a" for s in gs.stack)

    # Other has no mana — cannot pay; spell B is countered independently.
    original_other = other
    gs = Ward().apply(gs, perm, target=spell_b, caster_name="Other")
    assert not any(s.id == "spell-b" for s in gs.stack)
    # Source card to the RETURNED state's player graveyard (pure transform).
    result_other = next(p for p in gs.players if p.name == "Other")
    assert "Bolt" in [c.name for c in result_other.graveyard]
    # Original state untouched — no in-place graveyard.append on the live player.
    assert "Bolt" not in [c.name for c in original_other.graveyard]


# ---------------------------------------------------------------------------
# Real firing through stack.py's cast_spell becomes-target flow
# ---------------------------------------------------------------------------

def test_stack_cast_spell_queues_ward_for_human_caster():
    """A human casting a spell at an opponent's ward creature queues the choice."""
    gs = _game(human_player="Alice")
    gs, perm = put_permanent_onto_battlefield(gs, _ward_card(), "Bob")

    bolt = _bolt_card()
    alice = next(p for p in gs.players if p.name == "Alice")
    alice.hand.append(bolt)
    alice.mana_pool = ManaPool(R=1)                    # enough to cast Bolt {R}
    gs.priority_holder = "Alice"

    gs = cast_spell(gs, "Alice", bolt.id, targets=[perm.id], mana_payment={"R": 1})

    assert gs.pending_ward_payment is not None         # queued for human resolution
    assert gs.pending_ward_payment["player"] == "Alice"
    assert gs.pending_ward_payment["target_permanent_id"] == perm.id


def test_stack_cast_spell_ai_counters_unaffordable():
    """An AI casting a spell at an opponent's ward creature counters it when it
    cannot afford the ward cost (CR 702.157b)."""
    gs = _game()                                       # human_player_name is None -> AI
    bot = next(p for p in gs.players if p.name == "Bot")
    bot.mana_pool = ManaPool(R=1)                      # enough to cast Bolt {R}, not Ward {2}
    gs, perm = put_permanent_onto_battlefield(gs, _ward_card(), "Bob")

    bolt = _bolt_card()
    bot.hand.append(bolt)
    gs.priority_holder = "Bot"
    original_bot = next(p for p in gs.players if p.name == "Bot")

    gs = cast_spell(gs, "Bot", bolt.id, targets=[perm.id], mana_payment={"R": 1})

    assert not any(s.source_card.name == "Bolt" for s in gs.stack)  # countered at cast time
    # Source card to the RETURNED state's player graveyard (pure transform).
    result_bot = next(p for p in gs.players if p.name == "Bot")
    assert "Bolt" in [c.name for c in result_bot.graveyard]
    # Original state untouched — no in-place graveyard.append on the live player.
    assert "Bolt" not in [c.name for c in original_bot.graveyard]


def test_stack_cast_spell_ai_pays_when_affordable():
    """An AI that can afford the ward cost lets its spell continue through cast."""
    gs = _game()                                       # Bot C=2 affordable for Ward {2}, R to cast Bolt
    bot = next(p for p in gs.players if p.name == "Bot")
    bot.mana_pool = ManaPool(C=2, R=1)                 # pays Bolt {R}, then Ward {2}
    gs, perm = put_permanent_onto_battlefield(gs, _ward_card(), "Bob")

    bolt = _bolt_card()
    bot.hand.append(bolt)
    gs.priority_holder = "Bot"

    gs = cast_spell(gs, "Bot", bolt.id, targets=[perm.id], mana_payment={"R": 1})

    assert any(s.source_card.name == "Bolt" for s in gs.stack)   # spell on stack, ward paid


def test_stack_cast_spell_self_targeting_does_not_queue_ward():
    """CR 702.145b natural-context negative test: a player casting a spell at
    their OWN ward permanent never triggers Ward — the stack.py guard
    (``target_perm.controller != player_name``) keeps ``pending_ward_payment``
    as None and the spell continues uncountered."""
    gs = _game(human_player="Alice")
    gs, perm = put_permanent_onto_battlefield(gs, _ward_card(), "Alice")  # Alice's own ward

    bolt = _bolt_card()
    alice = next(p for p in gs.players if p.name == "Alice")
    alice.hand.append(bolt)
    alice.mana_pool = ManaPool(R=1)                    # enough to cast Bolt {R}
    gs.priority_holder = "Alice"

    gs = cast_spell(gs, "Alice", bolt.id, targets=[perm.id], mana_payment={"R": 1})

    assert gs.pending_ward_payment is None             # self-targeting: no Ward trigger
    assert any(s.source_card.name == "Bolt" for s in gs.stack)  # spell continues

