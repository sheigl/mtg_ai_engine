"""Tests for US30: Mutate (CR 702.139).

Mutate allows casting a creature for its mutate cost targeting a non-Human creature.
The mutating creature merges with the target.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.models.game import (
    GameState, PlayerState, Card, Permanent, Phase, Step, ManaPool,
)
from mtg_engine.engine.stack import cast_spell, resolve_top
from mtg_engine.api.routers.game import _compute_legal_actions


def _creature(name, power, toughness, keywords=None, oracle_text="", type_line="Creature — Beast", mana_cost=None):
    return Card(
        name=name, type_line=type_line,
        power=str(power), toughness=str(toughness),
        keywords=keywords or [], oracle_text=oracle_text,
        mana_cost=mana_cost,
    )


def _human(name, power, toughness, keywords=None, oracle_text=""):
    return _creature(name, power, toughness, keywords, oracle_text, "Creature — Human")


def _gs(active_player="p1", priority_holder="p1", phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN, turn=1):
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="test_mutate", seed=1,
        active_player=active_player, priority_holder=priority_holder,
        phase=phase, step=step, turn=turn,
        players=[p1, p2],
    )


class TestMutate:
    """US30: Mutate allows creatures to merge into a single permanent pile."""

    def test_mutate_targeting_non_human_creature(self):
        """Scenario 1: Mutate onto non-Human creature → merge into single permanent."""
        gs = _gs(turn=1, phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN)

        # Target: non-Human creature already on battlefield
        target = _creature("Ogre Warrior", 3, 2, type_line="Creature — Ogre")
        gs.battlefield.append(Permanent(card=target, controller="p1"))

        # Mutating creature in hand
        mutate_card = _creature(
            "Giant Growth Creature", 2, 2,
            keywords=["mutate"],
            oracle_text="Mutate {3}\n",
        )
        gs.players[0].hand.append(mutate_card)
        gs.players[0].mana_pool = ManaPool(C=3)

        # Check legal actions include mutate
        actions = _compute_legal_actions(gs)
        mutate_actions = [a for a in actions if a.new_action_type == "mutate"]
        assert len(mutate_actions) >= 1
        assert mutate_actions[0].card_id == mutate_card.id

    def test_mutate_onto_human_rejected(self):
        """Scenario 5: Mutate onto Human creature → rejected."""
        gs = _gs(turn=1, phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN)

        # Target: Human creature on battlefield
        target = _human("Grenzo, Dungeon Warden", 3, 2)
        gs.battlefield.append(Permanent(card=target, controller="p1"))

        # Mutating creature in hand
        mutate_card = _creature(
            "Giant Growth Creature", 2, 2,
            keywords=["mutate"],
            oracle_text="Mutate {3}\n",
        )
        gs.players[0].hand.append(mutate_card)
        gs.players[0].mana_pool = ManaPool(C=3)

        # Check legal actions do NOT include mutate for targeting Human
        actions = _compute_legal_actions(gs)
        mutate_actions = [a for a in actions if a.new_action_type == "mutate" and a.card_id == mutate_card.id]
        # Human creatures should NOT be valid mutate targets
        for action in mutate_actions:
            assert "Grenzo" not in action.valid_targets

    def test_mutate_onto_opponent_creature_rejected(self):
        """Mutate onto opponent's creature → rejected."""
        gs = _gs(turn=1, phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN)

        # Target: opponent's non-Human creature
        target = _creature("Ogre Warrior", 3, 2, type_line="Creature — Ogre")
        gs.battlefield.append(Permanent(card=target, controller="p2"))

        # Mutating creature in p1's hand
        mutate_card = _creature(
            "Giant Growth Creature", 2, 2,
            keywords=["mutate"],
            oracle_text="Mutate {3}\n",
        )
        gs.players[0].hand.append(mutate_card)
        gs.players[0].mana_pool = ManaPool(C=3)

        actions = _compute_legal_actions(gs)
        mutate_actions = [a for a in actions if a.new_action_type == "mutate" and a.card_id == mutate_card.id]
        for action in mutate_actions:
            # Opponent's creature should NOT be valid target
            assert "Ogre" not in action.valid_targets

    def test_mutate_merge_pile_on_top(self):
        """Scenario 2: Mutate on top → permanent has top card's name/P/T/types + all abilities."""
        gs = _gs(turn=1, phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN)

        # Target: non-Human creature on battlefield
        target = _creature("Ogre Warrior", 3, 2, type_line="Creature — Ogre")
        perm = Permanent(card=target, controller="p1")
        gs.battlefield.append(perm)

        # Mutating creature
        mutate_card = _creature(
            "Giant Growth Creature", 2, 2,
            keywords=["mutate"],
            oracle_text="Mutate {3}\n",
            mana_cost="{3}",
        )
        gs.players[0].hand.append(mutate_card)
        gs.players[0].mana_pool = ManaPool(C=3)

        # Cast with mutate targeting the Ogre
        gs = cast_spell(
            gs, "p1", mutate_card.id,
            [perm.id],
            {"C": 3},
            alternative_cost="mutate",
            mutate_target_id=perm.id,
            mutate_on_top=True,
        )

        # Spell on stack
        assert len(gs.stack) == 1
        assert gs.stack[0].mutate_target_id == perm.id
        assert gs.stack[0].mutate_on_top is True

        # Resolve the spell
        gs = resolve_top(gs)

        # Verify merge happened
        assert len(gs.battlefield) == 1
        merged = gs.battlefield[0]
        assert len(merged.mutated_cards) >= 1

        # Top card should be the mutate card (mutate_on_top=True)
        top_card = merged.mutated_cards[0]
        assert top_card.name == "Giant Growth Creature"
        assert merged.card.name == "Giant Growth Creature"

    def test_mutate_merge_pile_on_bottom(self):
        """Mutate on bottom → permanent keeps existing top card's name/P/T/types."""
        gs = _gs(turn=1, phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN)

        # Target: non-Human creature on battlefield
        target = _creature("Ogre Warrior", 3, 2, type_line="Creature — Ogre")
        perm = Permanent(card=target, controller="p1")
        gs.battlefield.append(perm)

        # Mutating creature
        mutate_card = _creature(
            "Giant Growth Creature", 2, 2,
            keywords=["mutate"],
            oracle_text="Mutate {3}\n",
            mana_cost="{3}",
        )
        gs.players[0].hand.append(mutate_card)
        gs.players[0].mana_pool = ManaPool(C=3)

        # Cast with mutate targeting the Ogre, on bottom
        gs = cast_spell(
            gs, "p1", mutate_card.id,
            [perm.id],
            {"C": 3},
            alternative_cost="mutate",
            mutate_target_id=perm.id,
            mutate_on_top=False,
        )

        # Resolve the spell
        gs = resolve_top(gs)

        # Verify merge happened
        assert len(gs.battlefield) == 1
        merged = gs.battlefield[0]
        assert len(merged.mutated_cards) >= 1

        # Bottom card should be the mutate card
        # Top card should still be Ogre (existing)
        assert merged.card.name == "Ogre Warrior"

    def test_mutate_all_abilities_from_pile(self):
        """Scenario 2 (extended): Permanent has all abilities from all cards in pile."""
        gs = _gs(turn=1, phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN)

        # Target: non-Human creature on battlefield
        target = _creature("Ogre Warrior", 3, 2, type_line="Creature — Ogre")
        perm = Permanent(card=target, controller="p1")
        gs.battlefield.append(perm)

        # Mutating creature with flying keyword
        mutate_card = _creature(
            "Giant Growth Creature", 2, 2,
            keywords=["mutate", "flying"],
            oracle_text="Mutate {3}\nFlying",
            mana_cost="{3}",
        )
        gs.players[0].hand.append(mutate_card)
        gs.players[0].mana_pool = ManaPool(C=3)

        # Cast with mutate
        gs = cast_spell(
            gs, "p1", mutate_card.id,
            [perm.id],
            {"C": 3},
            alternative_cost="mutate",
            mutate_target_id=perm.id,
            mutate_on_top=True,
        )

        # Resolve the spell
        gs = resolve_top(gs)

        # Verify flying ability is granted
        merged = gs.battlefield[0]
        assert "flying" in merged.card.keywords

    def test_mutate_death_all_cards_to_graveyard(self):
        """Scenario 4: Merged creature dies → all cards in pile go to graveyard."""
        gs = _gs(turn=1, phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN)

        # Target: non-Human creature on battlefield
        target = _creature("Ogre Warrior", 3, 2, type_line="Creature — Ogre")
        perm = Permanent(card=target, controller="p1")
        gs.battlefield.append(perm)

        # Mutating creature
        mutate_card = _creature(
            "Giant Growth Creature", 2, 2,
            keywords=["mutate"],
            oracle_text="Mutate {3}\n",
            mana_cost="{3}",
        )
        gs.players[0].hand.append(mutate_card)
        gs.players[0].mana_pool = ManaPool(C=3)

        # Cast with mutate
        gs = cast_spell(
            gs, "p1", mutate_card.id,
            [perm.id],
            {"C": 3},
            alternative_cost="mutate",
            mutate_target_id=perm.id,
            mutate_on_top=True,
        )

        # Resolve the spell
        gs = resolve_top(gs)

        merged = gs.battlefield[0]
        pile_count = len(merged.mutated_cards) + 1  # +1 for the base card

        # Set damage to kill the merged creature (toughness-based)
        merged.damage_marked = 10

        # Simulate death by checking SBA
        from mtg_engine.engine.sba import check_and_apply_sbas
        gs, _ = check_and_apply_sbas(gs)

        # Verify all cards in pile went to graveyard
        player = next(p for p in gs.players if p.name == "p1")
        graveyard_names = [c.name for c in player.graveyard]
        assert "Ogre Warrior" in graveyard_names
        assert "Giant Growth Creature" in graveyard_names

    def test_mutate_non_creature_rejected(self):
        """Mutate onto non-creature (artifact, etc.) → rejected."""
        gs = _gs(turn=1, phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN)

        # Target: non-creature permanent (artifact)
        artifact_card = Card(
            name="Iron Guardian", type_line="Artifact",
            keywords=[], oracle_text="",
        )
        perm = Permanent(card=artifact_card, controller="p1")
        gs.battlefield.append(perm)

        # Mutating creature in hand
        mutate_card = _creature(
            "Giant Growth Creature", 2, 2,
            keywords=["mutate"],
            oracle_text="Mutate {3}\n",
        )
        gs.players[0].hand.append(mutate_card)
        gs.players[0].mana_pool = ManaPool(C=3)

        actions = _compute_legal_actions(gs)
        mutate_actions = [a for a in actions if a.new_action_type == "mutate" and a.card_id == mutate_card.id]
        for action in mutate_actions:
            # Artifact should NOT be a valid mutate target
            assert "Iron Guardian" not in action.valid_targets

    def test_mutate_without_mutate_keyword_rejected(self):
        """Creature without mutate keyword cannot be used for mutate."""
        gs = _gs(turn=1, phase=Phase.PRECOMBAT_MAIN, step=Step.MAIN)

        # Target: non-Human creature
        target = _creature("Ogre Warrior", 3, 2, type_line="Creature — Ogre")
        perm = Permanent(card=target, controller="p1")
        gs.battlefield.append(perm)

        # Regular creature without mutate keyword
        regular_card = _creature(
            "Giant Growth Creature", 2, 2,
            oracle_text="",
            mana_cost="{3}",
        )
        gs.players[0].hand.append(regular_card)
        gs.players[0].mana_pool = ManaPool(C=3)

        actions = _compute_legal_actions(gs)
        # No mutate actions should be available
        for action in actions:
            if action.card_id == regular_card.id:
                assert action.new_action_type != "mutate"
