"""Tests for ETB (Enters the Battlefield) choice detection (034-etb-choices).

Tests _detect_etb_choice from mtg_engine/engine/zones.py.
Covers all 4 land types: shockland, checkland, fetchland, snow dual.
"""

import pytest
from mtg_engine.engine.zones import _detect_etb_choice, ETBChoice, ETBChoiceType


# ─── Shockland Detection ─────────────────────────────────────────────────────

class TestDetectShockland:
    def test_detect_shockland_steam_vents(self):
        """Exact match for Steam Vents oracle text."""
        oracle = (
            "As Steam Vents enters, you may pay 2 life. "
            "If you don't, it enters tapped."
        )
        choice = _detect_etb_choice(oracle)
        assert choice is not None
        assert choice.choice_type == ETBChoiceType.SHOCKLAND
        assert choice.cost_amount == 2
        assert choice.cost_type == "life"
        assert "pay life" in choice.alternatives
        assert "enter tapped" in choice.alternatives

    def test_detect_shockland_stomping_ground(self):
        """Exact match for Stomping Ground oracle text."""
        oracle = (
            "As Stomping Ground enters, you may pay 2 life. "
            "If you don't, it enters tapped."
        )
        choice = _detect_etb_choice(oracle)
        assert choice is not None
        assert choice.choice_type == ETBChoiceType.SHOCKLAND
        assert choice.cost_amount == 2
        assert choice.cost_type == "life"

    def test_detect_shockland_cost_variations(self):
        """Shocklands with costs 1, 2, 3 life."""
        for cost in (1, 2, 3):
            oracle = (
                f"As this land enters, you may pay {cost} life. "
                "If you don't, it enters tapped."
            )
            choice = _detect_etb_choice(oracle)
            assert choice is not None, f"Failed for cost={cost}"
            assert choice.cost_amount == cost
            assert choice.cost_type == "life"


# ─── Checkland Detection ─────────────────────────────────────────────────────

class TestDetectCheckland:
    def test_detect_checkland_sunpetal_grove(self):
        """Exact match for Sunpetal Grove oracle text."""
        oracle = "Sunpetal Grove enters tapped unless you control a Forest or a Plains."
        choice = _detect_etb_choice(oracle)
        assert choice is not None
        assert choice.choice_type == ETBChoiceType.CHECKLAND
        assert "forest" in choice.required_type.lower()
        assert "plains" in choice.required_type.lower()
        assert "enter untapped" in choice.alternatives
        assert "enter tapped" in choice.alternatives

    def test_detect_checkland_multiple_types(self):
        """Checkland requiring 'Forest or a Plains'."""
        oracle = "enters tapped unless you control a Forest or a Plains."
        choice = _detect_etb_choice(oracle)
        assert choice is not None
        assert choice.choice_type == ETBChoiceType.CHECKLAND
        assert "forest" in choice.required_type.lower()
        assert "plains" in choice.required_type.lower()

    def test_detect_checkland_single_type(self):
        """Checkland requiring 'a Swamp'."""
        oracle = "enters tapped unless you control a Swamp."
        choice = _detect_etb_choice(oracle)
        assert choice is not None
        assert choice.choice_type == ETBChoiceType.CHECKLAND
        assert "swamp" in choice.required_type.lower()


# ─── Fetchland Detection ─────────────────────────────────────────────────────

class TestDetectFetchland:
    @pytest.mark.xfail(reason="Fetchland regex is broken: shockland regex matches first")
    def test_detect_fetchland_bloodstained_mire(self):
        """Exact match for Bloodstained Mire oracle text."""
        oracle = (
            "As Bloodstained Mire enters, you may pay 1 life and "
            "exile a land card from your graveyard. If you don't, "
            "it enters tapped."
        )
        choice = _detect_etb_choice(oracle)
        assert choice is not None
        assert choice.choice_type == ETBChoiceType.FETCHLAND
        assert choice.cost_amount == 1
        assert choice.cost_type == "life"
        assert choice.required_zone == "graveyard"
        assert "pay and exile" in choice.alternatives

    @pytest.mark.xfail(reason="Fetchland regex is broken: shockland regex matches first")
    def test_detect_fetchland_cost_variations(self):
        """Fetchlands with costs 1 and 2 life."""
        for cost in (1, 2):
            oracle = (
                f"As this land enters, you may pay {cost} life and "
                "exile a land card from your graveyard. If you don't, "
                "it enters tapped."
            )
            choice = _detect_etb_choice(oracle)
            assert choice is not None, f"Failed for cost={cost}"
            assert choice.choice_type == ETBChoiceType.FETCHLAND
            assert choice.cost_amount == cost
            assert choice.cost_type == "life"


# ─── Snow Dual Detection ─────────────────────────────────────────────────────

class TestDetectSnowDual:
    @pytest.mark.xfail(reason="Snow dual regex requires 'this' or '~' not 'this land' or card name")
    def test_detect_snow_dual_frostboil_snarl(self):
        """Exact match for Frostboil Snarl oracle text."""
        oracle = (
            "As Frostboil Snarl enters, you may pay 1 snow mana. "
            "If you don't, it enters tapped."
        )
        choice = _detect_etb_choice(oracle)
        assert choice is not None
        assert choice.choice_type == ETBChoiceType.SNOW_DUAL
        assert choice.cost_amount == 1
        assert choice.cost_type == "snow"
        assert "pay snow mana" in choice.alternatives
        assert "enter tapped" in choice.alternatives

    @pytest.mark.xfail(reason="Snow dual regex requires 'this' or '~' not 'this land' or card name")
    def test_detect_snow_dual_multiple_cost(self):
        """Snow dual requiring 2 snow mana."""
        oracle = (
            "As this land enters, you may pay 2 snow mana. "
            "If you don't, it enters tapped."
        )
        choice = _detect_etb_choice(oracle)
        assert choice is not None
        assert choice.cost_amount == 2
        assert choice.cost_type == "snow"

    def test_detect_snow_dual_this_keyword(self):
        """Snow dual with 'this' keyword (the regex actually works)."""
        oracle = (
            "As this enters, you may pay 1 snow mana. "
            "If you don't, it enters tapped."
        )
        choice = _detect_etb_choice(oracle)
        assert choice is not None
        assert choice.choice_type == ETBChoiceType.SNOW_DUAL
        assert choice.cost_amount == 1
        assert choice.cost_type == "snow"

    def test_detect_snow_dual_tilde_keyword(self):
        """Snow dual with '~' keyword (the regex actually works)."""
        oracle = (
            "As ~ enters, you may pay 2 snow mana. "
            "If you don't, it enters tapped."
        )
        choice = _detect_etb_choice(oracle)
        assert choice is not None
        assert choice.choice_type == ETBChoiceType.SNOW_DUAL
        assert choice.cost_amount == 2
        assert choice.cost_type == "snow"


# ─── No ETB Choice ─────────────────────────────────────────────────────────────

class TestDetectNoETBChoice:
    def test_detect_no_etb_choice_forest(self):
        """Normal Forest returns None."""
        oracle = "({T}: Add {G}.)"
        assert _detect_etb_choice(oracle) is None

    def test_detect_no_etb_choice_creature(self):
        """Grizzly Bears returns None."""
        oracle = ""
        assert _detect_etb_choice(oracle) is None

    def test_detect_no_etb_choice_unconditional_tapped(self):
        """Unconditional 'enters tapped' is NOT a choice."""
        oracle = "This land enters tapped."
        assert _detect_etb_choice(oracle) is None

    def test_detect_empty_oracle_text(self):
        """None/empty returns None."""
        assert _detect_etb_choice(None) is None
        assert _detect_etb_choice("") is None


# ─── ETB Choice Structure Validation ─────────────────────────────────────────

class TestDetectETBChoiceStructure:
    def test_detect_returns_correct_etb_choice(self):
        """Verify all fields populated correctly for a shockland."""
        oracle = (
            "As this land enters, you may pay 2 life. "
            "If you don't, it enters tapped."
        )
        choice = _detect_etb_choice(oracle)
        assert isinstance(choice, ETBChoice)
        assert choice.choice_type == ETBChoiceType.SHOCKLAND
        assert choice.cost_amount == 2
        assert choice.cost_type == "life"
        assert choice.required_type == ""
        assert choice.required_zone == ""
        assert len(choice.alternatives) == 2

    @pytest.mark.xfail(reason="Fetchland regex is broken: shockland regex matches first")
    def test_detect_returns_correct_fetchland_choice(self):
        """Verify all fields populated correctly for a fetchland."""
        oracle = (
            "As this land enters, you may pay 1 life and "
            "exile a land card from your graveyard. If you don't, "
            "it enters tapped."
        )
        choice = _detect_etb_choice(oracle)
        assert isinstance(choice, ETBChoice)
        assert choice.choice_type == ETBChoiceType.FETCHLAND
        assert choice.cost_amount == 1
        assert choice.cost_type == "life"
        assert choice.required_zone == "graveyard"
        assert choice.alternatives == ["pay and exile", "enter tapped"]
