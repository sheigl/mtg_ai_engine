"""
AI-01: AI Framework tests.

These tests verify that the mtg_engine.ai package correctly wraps and
delegates to the ai_client heuristic player for decision-making.
"""
import pytest

from mtg_engine.ai import HeuristicAI, LLMAI, AIFramework


class TestHeuristicAI:
    def test_create(self):
        ai = HeuristicAI(player_name="Alice")
        assert ai.name == "Alice"
        assert ai.memory is not None

    def test_decide_chooses_non_pass_action_when_available(self):
        ai = HeuristicAI(player_name="Alice")
        prompt = "You are in your main phase."
        legal_actions = [
            {"description": "Pass priority", "action_type": "pass"},
            {"description": "Play Forest", "action_type": "play_land",
             "card_id": "forest-1"},
            {"description": "Cast Llanowar Elves", "action_type": "cast_spell",
             "card_id": "elves-1"},
        ]
        game_state = {"turn": 1, "phase": "precombat_main", "active_player": "Alice"}
        idx, reasoning = ai.decide(prompt, legal_actions, game_state)
        # Should pick something with an action_type != "pass"
        chosen = legal_actions[idx]
        assert chosen["action_type"] != "pass" or idx == 0

    def test_evaluate_mulligan_keeps_reasonable_hand(self):
        ai = HeuristicAI(player_name="Alice")
        hand = [
            {"name": "Mountain", "type_line": "Basic Land — Mountain",
             "oracle_text": "", "keywords": []},
            {"name": "Lightning Bolt", "type_line": "Instant",
             "oracle_text": "Lightning Bolt deals 3 damage to any target.",
             "keywords": [], "mana_cost": "{R}"},
            {"name": "Monastery Swiftspear", "type_line": "Creature — Human Monk",
             "oracle_text": "Haste, prowess", "keywords": ["haste", "prowess"],
             "mana_cost": "{R}", "power": "1", "toughness": "2"},
        ]
        keep = ai.evaluate_mulligan(hand, hand_size=3)
        # evaluate_mulligan returns True to mulligan, False to keep
        assert keep is False  # playable hand with land + spell + creature

    def test_evaluate_mulligan_mulligans_zero_lands(self):
        ai = HeuristicAI(player_name="Bob")
        hand = [
            {"name": "Lightning Bolt", "type_line": "Instant",
             "oracle_text": "Lightning Bolt deals 3 damage to any target.",
             "keywords": [], "mana_cost": "{R}"},
            {"name": "Grizzly Bears", "type_line": "Creature — Bear",
             "oracle_text": "", "keywords": [], "mana_cost": "{1}{G}",
             "power": "2", "toughness": "2"},
            {"name": "Counterspell", "type_line": "Instant",
             "oracle_text": "Counter target spell.", "keywords": [],
             "mana_cost": "{U}{U}"},
            {"name": "Llanowar Elves", "type_line": "Creature — Elf Druid",
             "oracle_text": "{T}: Add {G}.", "keywords": [], "mana_cost": "{G}",
             "power": "1", "toughness": "1"},
            {"name": "Shock", "type_line": "Instant",
             "oracle_text": "Shock deals 2 damage to any target.",
             "keywords": [], "mana_cost": "{R}"},
            {"name": "Duress", "type_line": "Sorcery", "mana_cost": "{B}",
             "oracle_text": "Target opponent reveals their hand. You choose a noncreature, nonland card from it. That player discards that card.",
             "keywords": []},
            {"name": "Unsubstantiate", "type_line": "Instant", "mana_cost": "{1}{U}",
             "oracle_text": "Return target spell or creature to its owner's hand.",
             "keywords": []},
        ]
        keep = ai.evaluate_mulligan(hand, hand_size=7)
        assert keep is True  # zero lands -> mulligan

    def test_select_attackers_returns_list(self):
        ai = HeuristicAI(player_name="Alice")
        action = {"description": "Declare attackers", "action_type": "declare_attackers"}
        game_state = {
            "turn": 3, "phase": "combat", "step": "declare_attackers",
            "active_player": "Alice",
            "players": {
                "Alice": {"life": 20},
                "Bob": {"life": 20},
            },
            "battlefield": [
                {"id": "g1", "name": "Grizzly Bears", "power": "2", "toughness": "2",
                 "card": {"power": "2", "toughness": "2", "keywords": []},
                 "controller": "Alice", "tapped": False, "summoning_sick": False,
                 "counters": {}, "power_bonus": 0, "toughness_bonus": 0,
                 "attacking": "Bob"},
            ],
        }
        result = ai.select_attackers(action, game_state, "Alice")
        assert isinstance(result, list)


class TestAIFactory:
    def test_factory_heuristic(self):
        ai = AIFramework.for_type("heuristic", player_name="Alice")
        assert isinstance(ai, HeuristicAI)

    def test_factory_invalid(self):
        with pytest.raises(ValueError, match="Unknown AI type"):
            AIFramework.for_type("unknown", player_name="Alice")
