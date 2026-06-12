"""
AI-02: AI Combat tests.

Tests the combat decision helpers in mtg_engine.ai.combat.
"""
from mtg_engine.ai.combat import (
    BlockClassification,
    can_block,
    classify_block,
    compute_power,
    compute_toughness,
    simulate_combat,
)


class TestPowerToughness:
    def test_basic_power(self):
        perm = {"card": {"power": "3", "toughness": "3"}, "power_bonus": 0,
                "toughness_bonus": 0, "counters": {}}
        assert compute_power(perm) == 3
        assert compute_toughness(perm) == 3

    def test_power_with_bonus(self):
        perm = {"card": {"power": "2", "toughness": "2"}, "power_bonus": 2,
                "toughness_bonus": 1, "counters": {}}
        assert compute_power(perm) == 4
        assert compute_toughness(perm) == 3

    def test_power_with_counters(self):
        perm = {"card": {"power": "1", "toughness": "1"}, "power_bonus": 0,
                "toughness_bonus": 0, "counters": {"+1/+1": 3}}
        assert compute_power(perm) == 4
        assert compute_toughness(perm) == 4

    def test_power_with_negative_counters(self):
        perm = {"card": {"power": "5", "toughness": "5"}, "power_bonus": 0,
                "toughness_bonus": 0, "counters": {"-1/-1": 2}}
        assert compute_power(perm) == 3
        assert compute_toughness(perm) == 3

    def test_minimum_zero(self):
        perm = {"card": {"power": "0", "toughness": "0"}, "power_bonus": -1,
                "toughness_bonus": -1, "counters": {}}
        assert compute_power(perm) == 0
        assert compute_toughness(perm) == 0


class TestCanBlock:
    def test_flying_needs_flying_or_reach(self):
        ground_attacker = {"card": {"keywords": [], "oracle_text": ""}}
        flyer = {"card": {"keywords": ["flying"], "oracle_text": ""}}
        reach = {"card": {"keywords": ["reach"], "oracle_text": ""}}
        ground = {"card": {"keywords": [], "oracle_text": ""}}

        # Ground cannot block flyer
        assert can_block(ground, flyer) is False
        # Reach can block flyer
        assert can_block(reach, flyer) is True
        # Ground can block ground
        assert can_block(ground, ground_attacker) is True

    def test_no_special_abilities(self):
        creature_a = {"card": {"keywords": [], "oracle_text": ""}}
        creature_b = {"card": {"keywords": [], "oracle_text": ""}}
        assert can_block(creature_a, creature_b) is True


class TestClassifyBlock:
    def test_safe_block(self):
        # 3/3 blocks 2/2 → SAFE
        blocker = {"card": {"power": "3", "toughness": "3"}, "power_bonus": 0,
                   "toughness_bonus": 0, "counters": {}}
        attacker = {"card": {"power": "2", "toughness": "2"}, "power_bonus": 0,
                    "toughness_bonus": 0, "counters": {}}
        assert classify_block(blocker, attacker) == BlockClassification.SAFE

    def test_trade_block(self):
        # 2/2 blocks 2/2 → TRADE
        creature = {"card": {"power": "2", "toughness": "2"}, "power_bonus": 0,
                    "toughness_bonus": 0, "counters": {}}
        assert classify_block(creature, creature) == BlockClassification.TRADE

    def test_chump_block(self):
        # 1/1 blocks 5/5 → CHUMP
        blocker = {"card": {"power": "1", "toughness": "1"}, "power_bonus": 0,
                   "toughness_bonus": 0, "counters": {}}
        attacker = {"card": {"power": "5", "toughness": "5"}, "power_bonus": 0,
                    "toughness_bonus": 0, "counters": {}}
        assert classify_block(blocker, attacker) == BlockClassification.CHUMP


class TestSimulateCombat:
    def test_no_attackers(self):
        score = simulate_combat([], [], 20)
        assert score == 0.0

    def test_lethal_attack(self):
        attacker = {"id": "g1", "name": "Grizzly Bears", "power": "2",
                    "toughness": "2", "counters": {}, "power_bonus": 0,
                    "toughness_bonus": 0,
                    "card": {"power": "2", "toughness": "2", "keywords": []}}
        score = simulate_combat([attacker], [], 2)
        assert score > 0  # lethal attack should be positive
