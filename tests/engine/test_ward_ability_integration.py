"""Unit tests for Ward-on-abilities (CR 702.145a) — the ``apply_ward_to_ability``
resolver in ``mtg_engine/ability/keywords/ward.py``.

Covers the pure-transform contract (Q4):

* no-op paths (no caster, no controller, self-targeting) return the SAME state
  object with the ``"proceed"`` outcome,
* a human targeter defers via ``pending_ward_payment`` tagged
  ``targeting_type="ability"`` (new state object, original untouched),
* an AI targeter auto-resolves by affordability: pays (new state, mana deducted,
  ``"proceed"``) or counters (same state object, ``"countered"``, no stack
  manipulation — inline abilities have no StackObject to remove).
"""
from mtg_engine.models.game import (
    Card,
    GameState,
    ManaPool,
    Permanent,
    PlayerState,
)
from mtg_engine.ability.keywords.ward import apply_ward_to_ability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _game(human_player: str | None = None) -> GameState:
    """Two players; ``Bot`` starts with 2 colourless mana."""
    alice = PlayerState(name="Alice", life=20, mana_pool=ManaPool())
    bot = PlayerState(name="Bot", life=20, mana_pool=ManaPool(C=2))
    return GameState(
        game_id="ward_ability_test",
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


def _ward_perm(controller: str = "Alice") -> Permanent:
    return Permanent(card=_ward_card(), controller=controller)


# ---------------------------------------------------------------------------
# No-op / guard paths (Q4 — strict same-object returns)
# ---------------------------------------------------------------------------

def test_no_caster_is_noop_same_object():
    """No identifiable targeter → same object, effect proceeds."""
    gs = _game(human_player="Alice")
    perm = _ward_perm("Alice")
    result, outcome = apply_ward_to_ability(gs, perm, caster_name=None)
    assert result is gs
    assert outcome == "proceed"
    assert result.pending_ward_payment is None


def test_empty_controller_noop_same_object():
    """A ward permanent with no controller is a strict no-op (same object)."""
    gs = _game()
    perm = Permanent(card=_ward_card(), controller="")
    result, outcome = apply_ward_to_ability(gs, perm, caster_name="Bot")
    assert result is gs
    assert outcome == "proceed"
    assert result.pending_ward_payment is None


def test_self_targeting_no_trigger_same_object():
    """CR 702.145b: self-targeting never triggers Ward — same object, the
    effect proceeds unimpeded (regardless of human/AI targeter)."""
    gs = _game(human_player="Alice")
    perm = _ward_perm("Alice")
    result, outcome = apply_ward_to_ability(gs, perm, caster_name="Alice")
    assert result is gs
    assert outcome == "proceed"
    assert result.pending_ward_payment is None

    gs2 = _game()  # AI targeter, same result
    perm2 = _ward_perm("Bot")
    result2, outcome2 = apply_ward_to_ability(gs2, perm2, caster_name="Bot")
    assert result2 is gs2
    assert outcome2 == "proceed"


# ---------------------------------------------------------------------------
# Human targeter → deferred (Q4 pure transform)
# ---------------------------------------------------------------------------

def test_human_targeter_defers_with_ability_tag():
    """A human targeter queues pending_ward_payment tagged
    targeting_type='ability' with the standard keys; new state object,
    original untouched."""
    gs = _game(human_player="Alice")
    perm = _ward_perm("Bot")  # Bot's ward, targeted by human Alice
    result, outcome = apply_ward_to_ability(gs, perm, caster_name="Alice")

    assert outcome == "deferred"
    assert id(result) != id(gs)
    pending = result.pending_ward_payment
    assert pending is not None
    assert pending["player"] == "Alice"
    assert pending["ward_cost"] == "{2}"
    assert pending["targeting_spell_id"] == ""  # inline ability — no StackObject
    assert pending["target_permanent_id"] == perm.id
    assert pending["targeting_type"] == "ability"
    # Original object untouched — no in-place mutation.
    assert gs.pending_ward_payment is None


def test_human_targeter_parses_ward_cost_from_oracle():
    """The ward cost is parsed from the permanent's oracle text."""
    gs = _game(human_player="Alice")
    perm = Permanent(
        card=Card(
            name="Costly Warden",
            type_line="Creature — Beast",
            power="2",
            toughness="2",
            keywords=["ward"],
            oracle_text="Ward {3}",
        ),
        controller="Bot",
    )
    result, outcome = apply_ward_to_ability(gs, perm, caster_name="Alice")
    assert outcome == "deferred"
    assert result.pending_ward_payment["ward_cost"] == "{3}"


# ---------------------------------------------------------------------------
# AI targeter → auto-resolve by affordability
# ---------------------------------------------------------------------------

def test_ai_pays_when_affordable():
    """AI targeter that can afford the ward cost pays it (new state, mana
    deducted) and the ability proceeds."""
    gs = _game()  # Bot C=2, affordable for Ward {2}
    perm = _ward_perm("Alice")
    result, outcome = apply_ward_to_ability(gs, perm, caster_name="Bot")

    assert outcome == "proceed"
    assert id(result) != id(gs)
    assert result.pending_ward_payment is None
    # Ward {2} deducted from Bot's pool (pure transform — new player object).
    result_bot = next(p for p in result.players if p.name == "Bot")
    assert result_bot.mana_pool.C == 0
    # Original state untouched.
    gs_bot = next(p for p in gs.players if p.name == "Bot")
    assert gs_bot.mana_pool.C == 2


def test_ai_counters_when_unaffordable():
    """AI targeter that cannot afford the ward cost: 'countered' outcome,
    state object returned unchanged (no stack manipulation — there is no
    StackObject for an inline ability), original unmutated."""
    gs = _game()
    bot = next(p for p in gs.players if p.name == "Bot")
    bot.mana_pool = ManaPool(C=0)  # cannot afford Ward {2}
    perm = _ward_perm("Alice")
    result, outcome = apply_ward_to_ability(gs, perm, caster_name="Bot")

    assert outcome == "countered"
    assert result is gs  # nothing to clear/counter — same object
    assert result.pending_ward_payment is None
    assert result.stack == []


def test_ai_pays_colored_cost():
    """A colored ward cost (Ward {R}) is paid from the AI's pool."""
    gs = _game()
    bot = next(p for p in gs.players if p.name == "Bot")
    bot.mana_pool = ManaPool(R=1)
    perm = Permanent(
        card=Card(
            name="Red Warden",
            type_line="Creature — Beast",
            power="2",
            toughness="2",
            keywords=["ward"],
            oracle_text="Ward {R}",
        ),
        controller="Alice",
    )
    result, outcome = apply_ward_to_ability(gs, perm, caster_name="Bot")
    assert outcome == "proceed"
    result_bot = next(p for p in result.players if p.name == "Bot")
    assert result_bot.mana_pool.R == 0


def test_ai_missing_player_counters():
    """A targeter with no player entry cannot pay → countered, same object."""
    gs = _game()
    perm = _ward_perm("Alice")
    result, outcome = apply_ward_to_ability(gs, perm, caster_name="Ghost")
    assert outcome == "countered"
    assert result is gs
    assert result.pending_ward_payment is None


def test_spell_path_unchanged():
    """The existing spell-oriented apply_ward / Ward.apply behavior is intact
    (regression guard for the additive change)."""
    from mtg_engine.models.game import StackObject
    from mtg_engine.ability.keywords.ward import Ward, apply_ward

    gs = _game()  # Bot C=2
    perm = _ward_perm("Alice")
    spell = StackObject(
        id="spell-1",
        source_card=Card(name="Bolt", type_line="Instant", oracle_text="Deal 3 damage to any target."),
        controller="Bot",
    )
    gs.stack.append(spell)

    result = apply_ward(gs, perm, target=spell, caster_name="Bot")
    assert result.pending_ward_payment is None
    assert next(p for p in result.players if p.name == "Bot").mana_pool.C == 0
    assert any(s.id == "spell-1" for s in result.stack)

    # Human path still queues with the legacy keys (no targeting_type needed).
    gs2 = _game(human_player="Alice")
    perm2 = _ward_perm("Bot")
    result2 = Ward().apply(gs2, perm2, target=None, caster_name="Alice")
    assert result2.pending_ward_payment is not None
    assert result2.pending_ward_payment["player"] == "Alice"
    assert result2.pending_ward_payment["ward_cost"] == "{2}"
