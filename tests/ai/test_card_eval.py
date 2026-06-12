"""
AI-03: AI Card Evaluation tests.

Tests the card evaluation helpers in mtg_engine.ai.card_eval.
"""
from mtg_engine.ai.card_eval import (
    compute_cmc,
    estimate_card_quality,
    has_keyword,
    is_board_wipe,
    is_counterspell,
    is_draw_spell,
    is_life_gain,
    is_ramp,
    is_removal_spell,
    is_token_generator,
    is_tutor,
)


def _card(name: str = "", oracle: str = "", mana: str = "",
          keywords: list | None = None, power: str = "0",
          toughness: str = "0") -> dict:
    return {
        "name": name,
        "oracle_text": oracle,
        "mana_cost": mana,
        "keywords": keywords or [],
        "type_line": "",
        "power": power,
        "toughness": toughness,
    }


class TestHasKeyword:
    def test_flying(self):
        assert has_keyword(_card(keywords=["flying"]), "flying") is True

    def test_no_keyword(self):
        assert has_keyword(_card(keywords=["haste"]), "flying") is False

    def test_keyword_in_oracle_text(self):
        card = _card(oracle="First strike, vigilance")
        assert has_keyword(card, "first strike") is True
        assert has_keyword(card, "vigilance") is True


class TestComputeCMC:
    def test_no_mana_cost(self):
        assert compute_cmc(None) == 0.0

    def test_colored_only(self):
        assert compute_cmc("{R}") == 1.0
        assert compute_cmc("{W}{U}{B}{R}{G}") == 5.0

    def test_generic_and_colored(self):
        assert compute_cmc("{2}{R}{R}") == 4.0

    def test_hybrid(self):
        assert compute_cmc("{R/W}{R/W}") == 2.0


class TestCardClassification:
    def test_removal_spell(self):
        card = _card(oracle="Destroy target creature")
        assert is_removal_spell(card) is True

    def test_not_removal(self):
        card = _card(oracle="Draw a card")
        assert is_removal_spell(card) is False

    def test_counterspell(self):
        card = _card(oracle="Counter target spell")
        assert is_counterspell(card) is True

    def test_board_wipe(self):
        card = _card(oracle="Destroy all creatures")
        assert is_board_wipe(card) is True

    def test_draw_spell(self):
        card = _card(oracle="Draw two cards")
        assert is_draw_spell(card) is True

    def test_ramp(self):
        card = _card(oracle="Search your library for a basic land card and put it onto the battlefield")
        assert is_ramp(card) is True

    def test_life_gain(self):
        card = _card(oracle="You gain 3 life")
        assert is_life_gain(card) is True

    def test_token_generator(self):
        card = _card(oracle="Create a 1/1 green Saproling creature token")
        assert is_token_generator(card) is True

    def test_tutor(self):
        card = _card(oracle="Search your library for a creature card and put it into your hand")
        assert is_tutor(card) is True


class TestEstimateCardQuality:
    def test_basic_land(self):
        card = _card(name="Forest", oracle="")
        assert 0.0 <= estimate_card_quality(card) <= 10.0

    def test_removal_spell_scores_higher(self):
        removal = _card(oracle="Destroy target creature")
        land = _card(oracle="")
        assert estimate_card_quality(removal) > estimate_card_quality(land)

    def test_board_wipe_scores_high(self):
        wipe = _card(oracle="Destroy all creatures")
        assert estimate_card_quality(wipe) >= 5.0

    def test_creature_with_keywords(self):
        creature = _card(name="Baneslayer Angel", oracle="Flying, first strike, lifelink",
                         keywords=["flying", "first strike", "lifelink"])
        vanilla = _card(oracle="")
        assert estimate_card_quality(creature) > estimate_card_quality(vanilla)
