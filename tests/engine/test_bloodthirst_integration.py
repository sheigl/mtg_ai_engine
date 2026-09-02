"""
Integration tests for Bloodthirst keyword (CR 702.22).

CR 702.22: "Bloodthirst N" means "If an opponent was dealt damage this turn,
this permanent enters the battlefield with N +1/+1 counters on it."

Covers:
- Unit tests of the keyword module helpers (has/parse/from_oracle)
- Direct apply() behavior (counters, guards, pure transform)
- ETB wiring via put_permanent_onto_battlefield
- Damage-source independence (combat and spell damage both count, CR 702.22b)
"""
from mtg_engine.models.game import (
    Card,
    GameState,
    ManaPool,
    Permanent,
    Phase,
    PlayerState,
    Step,
)
from mtg_engine.engine.zones import get_player, put_permanent_onto_battlefield
from mtg_engine.ability.keywords.bloodthirst import BloodthirstKeyword
from mtg_engine.engine.combat import declare_attackers, assign_combat_damage
from mtg_engine.models.actions import AttackDeclaration


def _make_game(player_names=("p1", "p2")) -> GameState:
    """Create a minimal 2-player test game state."""
    p1 = PlayerState(name=player_names[0], life=20, mana_pool=ManaPool())
    p2 = PlayerState(name=player_names[1], life=20, mana_pool=ManaPool())
    return GameState(
        game_id="bloodthirst_test",
        seed=1,
        active_player=player_names[0],
        priority_holder=player_names[0],
        phase=Phase.PRECOMBAT_MAIN,
        step=Step.MAIN,
        players=[p1, p2],
        human_player_name=player_names[0],
    )


def _bloodthirst_card(name: str = "Raging Rhinoceros", amount: int = 2) -> Card:
    """Create a creature card with Bloodthirst N."""
    return Card(
        name=name,
        type_line="Creature — Beast",
        power="2",
        toughness="2",
        mana_cost="{1}{G}",
        oracle_text=f"Bloodthirst {amount}",
        keywords=["bloodthirst"],
    )


def _plain_card(name: str = "Plain Beast") -> Card:
    """Create a creature card without bloodthirst."""
    return Card(
        name=name,
        type_line="Creature",
        power="1",
        toughness="1",
        oracle_text="Trample",
    )


def _perm(card: Card, controller: str = "p1", perm_id: str = "perm-bt-1") -> Permanent:
    """Create a permanent with an explicit ID for battlefield lookup."""
    return Permanent(card=card, controller=controller).model_copy(update={"id": perm_id})


def _perm_on_bf(gs: GameState, perm_id: str) -> Permanent:
    """Look up a permanent on the battlefield by ID."""
    return next(p for p in gs.battlefield if p.id == perm_id)


# ── 1. Unit tests of the keyword module ───────────────────────────────────────

class TestBloodthirstUnit:
    def test_has_bloodthirst_true(self):
        assert BloodthirstKeyword.has_bloodthirst(["bloodthirst"]) is True

    def test_has_bloodthirst_false(self):
        assert BloodthirstKeyword.has_bloodthirst(["trample", "haste"]) is False

    def test_parse_bloodthirst_amount(self):
        assert BloodthirstKeyword.parse_bloodthirst_amount("Bloodthirst 2") == 2
        assert BloodthirstKeyword.parse_bloodthirst_amount("Bloodthirst 5\nHaste") == 5

    def test_parse_no_bloodthirst(self):
        assert BloodthirstKeyword.parse_bloodthirst_amount("Trample") is None
        assert BloodthirstKeyword.parse_bloodthirst_amount("") is None
        # "Bloodthirst" without a number is not a valid "Bloodthirst N"
        assert BloodthirstKeyword.parse_bloodthirst_amount("Bloodthirst") is None

    def test_from_oracle(self):
        kw = BloodthirstKeyword.from_oracle("Bloodthirst 2")
        assert kw is not None
        assert kw.amount == 2

    def test_from_oracle_no_match(self):
        assert BloodthirstKeyword.from_oracle("Trample") is None
        assert BloodthirstKeyword.from_oracle("") is None


# ── 2. Direct apply() behavior ────────────────────────────────────────────────

class TestBloodthirstApply:
    def test_apply_adds_counters_when_opponent_damaged(self):
        gs = _make_game()
        gs = gs.model_copy(update={"damage_dealt_this_turn": {"p2": 3}})
        gs = gs.model_copy(update={"battlefield": [_perm(_bloodthirst_card(amount=1))]})
        bt = BloodthirstKeyword(amount=1)
        gs = bt.apply(gs, _perm_on_bf(gs, "perm-bt-1"))
        assert _perm_on_bf(gs, "perm-bt-1").counters.get("+1/+1", 0) == 1

    def test_apply_no_counters_when_no_damage(self):
        gs = _make_game()
        gs = gs.model_copy(update={"battlefield": [_perm(_bloodthirst_card(amount=1))]})
        bt = BloodthirstKeyword(amount=1)
        gs = bt.apply(gs, _perm_on_bf(gs, "perm-bt-1"))
        assert _perm_on_bf(gs, "perm-bt-1").counters.get("+1/+1", 0) == 0

    def test_apply_returns_same_object_when_no_bloodthirst(self):
        gs = _make_game()
        gs = gs.model_copy(update={"damage_dealt_this_turn": {"p2": 3}})
        gs = gs.model_copy(update={"battlefield": [_perm(_plain_card())]})
        bt = BloodthirstKeyword(amount=1)
        result = bt.apply(gs, _perm_on_bf(gs, "perm-bt-1"))
        # No bloodthirst → same object returned (no-op guard)
        assert result is gs

    def test_apply_amount_parsed_from_oracle(self):
        gs = _make_game()
        gs = gs.model_copy(update={"damage_dealt_this_turn": {"p2": 1}})
        # amount=0 default → parses "Bloodthirst 2" from oracle text
        gs = gs.model_copy(update={"battlefield": [_perm(_bloodthirst_card(amount=2))]})
        bt = BloodthirstKeyword(amount=0)
        gs = bt.apply(gs, _perm_on_bf(gs, "perm-bt-1"))
        assert _perm_on_bf(gs, "perm-bt-1").counters.get("+1/+1", 0) == 2

    def test_apply_pure_transform(self):
        gs = _make_game()
        gs = gs.model_copy(update={"damage_dealt_this_turn": {"p2": 4}})
        gs = gs.model_copy(update={"battlefield": [_perm(_bloodthirst_card(amount=2))]})
        original = gs
        bt = BloodthirstKeyword(amount=2)
        gs_after = bt.apply(gs, _perm_on_bf(gs, "perm-bt-1"))
        # New object returned, original unmutated
        assert gs_after is not original
        assert _perm_on_bf(original, "perm-bt-1").counters.get("+1/+1", 0) == 0
        assert _perm_on_bf(gs_after, "perm-bt-1").counters.get("+1/+1", 0) == 2


# ── 3. ETB integration via put_permanent_onto_battlefield ─────────────────────

class TestBloodthirstETB:
    def test_bloodthirst_etb_with_damage(self):
        gs = _make_game()
        gs = gs.model_copy(update={"damage_dealt_this_turn": {"p2": 3}})
        card = _bloodthirst_card(amount=2)
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        assert perm.counters.get("+1/+1", 0) == 2
        assert any(p.id == perm.id for p in gs.battlefield)

    def test_bloodthirst_etb_no_damage(self):
        gs = _make_game()
        # No damage dealt this turn
        gs = gs.model_copy(update={"damage_dealt_this_turn": {}})
        card = _bloodthirst_card(amount=2)
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        assert perm.counters.get("+1/+1", 0) == 0

    def test_bloodthirst_etb_ai_player(self):
        gs = _make_game()
        # p2 (AI) controls the creature; p1 (opponent) was dealt damage
        gs = gs.model_copy(update={"damage_dealt_this_turn": {"p1": 2}})
        card = _bloodthirst_card(amount=3)
        gs, perm = put_permanent_onto_battlefield(gs, card, "p2")
        assert perm.counters.get("+1/+1", 0) == 3

    def test_bloodthirst_etb_damage_to_controller_no_counters(self):
        gs = _make_game()
        # Damage to the controller (p1) should NOT trigger p1's creature
        gs = gs.model_copy(update={"damage_dealt_this_turn": {"p1": 5}})
        card = _bloodthirst_card(amount=2)
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        assert perm.counters.get("+1/+1", 0) == 0

    def test_bloodthirst_etb_multiple_opponents_any_damage_triggers(self):
        # Three-player game
        alice = PlayerState(name="Alice", life=20)
        bob = PlayerState(name="Bob", life=20)
        carol = PlayerState(name="Carol", life=20)
        gs = GameState(
            game_id="bloodthirst_multi",
            seed=1,
            active_player="Alice",
            priority_holder="Alice",
            players=[alice, bob, carol],
        )
        # Damage to Carol (opponent of Alice) → triggers
        gs = gs.model_copy(update={"damage_dealt_this_turn": {"Carol": 2}})
        card = _bloodthirst_card(amount=1)
        gs, perm = put_permanent_onto_battlefield(gs, card, "Alice")
        assert perm.counters.get("+1/+1", 0) == 1

    def test_bloodthirst_etb_no_keyword_no_counters(self):
        gs = _make_game()
        gs = gs.model_copy(update={"damage_dealt_this_turn": {"p2": 10}})
        card = _plain_card()
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        assert perm.counters.get("+1/+1", 0) == 0


# ── 4. Damage-source independence (CR 702.22b) ────────────────────────────────

class TestBloodthirstDamageTracking:
    def _make_combat_game(self) -> GameState:
        """Game state ready for a real combat flow."""
        p1 = PlayerState(name="p1", life=20, library=[])
        p2 = PlayerState(name="p2", life=20, library=[])
        return GameState(
            game_id="bloodthirst_combat",
            seed=1,
            active_player="p1",
            priority_holder="p1",
            phase=Phase.COMBAT,
            step=Step.DECLARE_ATTACKERS,
            players=[p1, p2],
        )

    def test_combat_damage_triggers_bloodthirst(self):
        """Combat damage to a player records damage_dealt_this_turn."""
        gs = self._make_combat_game()
        attacker_card = Card(
            name="Bear",
            type_line="Creature — Bear",
            power="2",
            toughness="2",
        )
        gs, attacker = put_permanent_onto_battlefield(gs, attacker_card, "p1")
        attacker.summoning_sick = False

        # Full real combat flow: declare attackers → combat damage step → assign
        gs = declare_attackers(
            gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")]
        )
        gs.step = Step.COMBAT_DAMAGE
        gs = assign_combat_damage(gs)

        # p2 (opponent of p1) should be recorded as damaged this turn
        assert gs.damage_dealt_this_turn.get("p2", 0) == 2
        # p2 life reduced by 2
        assert get_player(gs, "p2").life == 18

        # Now a bloodthirst creature for p1 should get counters
        card = _bloodthirst_card(amount=1)
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        assert perm.counters.get("+1/+1", 0) == 1

    def test_spell_damage_triggers_bloodthirst(self):
        """Non-combat (spell/ability) damage also records damage_dealt_this_turn."""
        gs = _make_game()
        # Simulate a spell dealing 3 damage to p2 (as stack.py _deal_damage does)
        damage_dict = dict(gs.damage_dealt_this_turn)
        damage_dict["p2"] = damage_dict.get("p2", 0) + 3
        gs = gs.model_copy(update={"damage_dealt_this_turn": damage_dict})

        # A bloodthirst creature for p1 should get counters from spell damage
        card = _bloodthirst_card(amount=2)
        gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
        assert perm.counters.get("+1/+1", 0) == 2
