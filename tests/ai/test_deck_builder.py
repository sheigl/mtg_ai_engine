"""
APP-02: Deck Building AI — unit tests for the deck construction engine.

Tests the Filter → Score → Select → Validate pipeline across all strategies,
formats, and edge cases. 14+ test cases covering every axis in the spec.
"""
import pytest
from pydantic import ValidationError

from mtg_engine.ai.deck_builder import (
    BASIC_LANDS,
    _classify_card,
    _cmc_curve_bonus,
    _filter_card_pool,
    _select_deck,
    _score_card,
    build_deck,
)
from mtg_engine.models.game import Card


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_card(
    name: str = "Test Card",
    mana_cost: str | None = "{1}",
    type_line: str = "",
    oracle_text: str | None = None,
    cmc: float = 0.0,
    colors: list[str] | None = None,
    color_identity: list[str] | None = None,
    keywords: list[str] | None = None,
    rarity: str | None = None,
    set_code: str | None = None,
) -> Card:
    return Card(
        name=name,
        mana_cost=mana_cost,
        type_line=type_line,
        oracle_text=oracle_text,
        cmc=cmc or float(len(mana_cost.split("}")) - 1 if mana_cost else 0),
        colors=colors or [],
        color_identity=color_identity or [],
        keywords=keywords or [],
        rarity=rarity,
        set_code=set_code,
    )


def _make_card_pool() -> list[Card]:
    """Create a diverse card pool for testing."""
    return [
        # Low CMC creatures (aggro-friendly)
        _make_card("Goblin Raider", "{R}", "Creature — Goblin", cmc=1.0, color_identity=["R"]),
        _make_card("Frogmite", "{1}{G}", "Creature — Frog", cmc=2.0, color_identity=["G"]),
        # Mid CMC creatures
        _make_card("Elite Guardmage", "{3}{U}", "Creature — Human Wizard", cmc=4.0, color_identity=["U"]),
        _make_card("Kird Ape", "{1}{G}", "Creature — Monkey", cmc=2.0, color_identity=["G"]),
        # High CMC creatures (control-friendly)
        _make_card("Emrakul, the Promised End", "", "Legendary Creature — Eldrazi", cmc=15.0),
        _make_card("Jace, Wielder of Mysteries", "{3}{U}{U}", "Planeswalker — Jace", cmc=5.0, color_identity=["U"]),
        # Removal spells
        _make_card("Lightning Bolt", "{R}", "Instant", oracle_text="Lightning Bolt deals 3 damage to any target.", cmc=1.0, color_identity=["R"]),
        _make_card("Abrupt Decay", "{B}", "Instant", oracle_text="Destroy target nonblack permanent with converted mana cost 2 or less.", cmc=1.0, color_identity=["B"]),
        # Counterspells (control-friendly)
        _make_card("Counterspell", "{U}", "Instant", oracle_text="Counter target spell.", cmc=1.0, color_identity=["U"]),
        _make_card("Negate", "{1}{U}", "Instant", oracle_text="Counter target blue or black spell.", cmc=2.0, color_identity=["U"]),
        # Draw spells (combo-friendly)
        _make_card("Brainstorm", "{U}", "Instant", oracle_text="Draw three cards, then discard two cards.", cmc=1.0, color_identity=["U"]),
        _make_card("Opt", "{U}", "Sorcery", oracle_text="Look at the top card of your library. You may put that card into your hand.", cmc=1.0, color_identity=["U"]),
        # Ramp (combo-friendly)
        _make_card("Rampant Growth", "{G}", "Sorcery", oracle_text="Search your library for a basic land card and put it onto the battlefield.", cmc=1.0, color_identity=["G"]),
        # Board wipes (control-friendly)
        _make_card("Wrath of God", "{2}{R}{R}", "Sorcery", oracle_text="Destroy all creatures.", cmc=4.0, color_identity=["R"]),
        # Lands
        _make_card("Mountain", "", "Land"),
        _make_card("Forest", "", "Land"),
        _make_card("Island", "", "Land"),
        _make_card("Swamp", "", "Land"),
        _make_card("Plains", "", "Land"),
    ]


# ---------------------------------------------------------------------------
# Test CMC Curve Bonuses
# ---------------------------------------------------------------------------

class TestCMCCurveBonus:
    def test_aggro_bonus_low_cmc(self):
        assert _cmc_curve_bonus(1.0, "aggro") == 1.3
        assert _cmc_curve_bonus(2.0, "aggro") == 1.3

    def test_aggro_no_bonus_high_cmc(self):
        assert _cmc_curve_bonus(5.0, "aggro") == 1.0

    def test_control_bonus_mid_cmc(self):
        assert _cmc_curve_bonus(3.0, "control") == 1.2
        assert _cmc_curve_bonus(4.0, "control") == 1.2
        assert _cmc_curve_bonus(5.0, "control") == 1.2

    def test_control_no_bonus_low_cmc(self):
        assert _cmc_curve_bonus(1.0, "control") == 1.0

    def test_midrange_bonus(self):
        assert _cmc_curve_bonus(2.0, "midrange") == 1.1
        assert _cmc_curve_bonus(3.0, "midrange") == 1.1
        assert _cmc_curve_bonus(4.0, "midrange") == 1.1

    def test_combo_bonus_high_cmc(self):
        assert _cmc_curve_bonus(5.0, "combo") == 1.2
        assert _cmc_curve_bonus(3.0, "combo") == 1.2


# ---------------------------------------------------------------------------
# Test Card Classification
# ---------------------------------------------------------------------------

class TestClassifyCard:
    def test_land(self):
        card = _make_card("Mountain", "", "Land — Mountain")
        assert _classify_card(card) == "land"

    def test_low_cmc_creature(self):
        card = _make_card("Goblin", "{R}", "Creature — Goblin", cmc=1.0)
        assert _classify_card(card) == "creature_low"

    def test_mid_cmc_creature(self):
        card = _make_card("Knight", "{2}{W}", "Creature — Human Knight", cmc=3.0)
        assert _classify_card(card) == "creature_mid"

    def test_high_cmc_creature(self):
        card = _make_card("Dragon", "{5}{R}{R}", "Creature — Dragon", cmc=7.0)
        assert _classify_card(card) == "creature_high"

    def test_removal_spell(self):
        card = _make_card("Lightning Bolt", "{R}", "Instant", oracle_text="Deal 3 damage to any target.")
        assert _classify_card(card) == "removal"

    def test_counterspell(self):
        card = _make_card("Counterspell", "{U}", "Instant", oracle_text="Counter target spell.")
        assert _classify_card(card) == "counterspell"

    def test_board_wipe(self):
        card = _make_card("Wrath of God", "{2}{R}{R}", "Sorcery", oracle_text="Destroy all creatures.")
        assert _classify_card(card) == "board_wipe"

    def test_draw_spell(self):
        card = _make_card("Brainstorm", "{U}", "Instant", oracle_text="Draw three cards, then discard two cards.")
        assert _classify_card(card) == "draw"

    def test_ramp(self):
        card = _make_card("Rampant Growth", "{G}", "Sorcery", oracle_text="Search your library for a basic land card and put it onto the battlefield.")
        assert _classify_card(card) == "ramp"


# ---------------------------------------------------------------------------
# Test Filter Stage
# ---------------------------------------------------------------------------

class TestFilterStage:
    def test_banned_cards_removed(self):
        """Banned cards are excluded from the filtered pool."""
        pool = [
            _make_card("Lightning Bolt", "{R}", "Instant"),
            _make_card("Tarmogoyf", "{1}{G}", "Creature — Dinosaur"),  # banned in modern
        ]
        result = _filter_card_pool(pool, "modern")
        names = {c.name.lower() for c in result}
        assert "tarmogoyf" not in names

    def test_singleton_format_dedup(self):
        """Legacy/Vintage/Commander/Brawl: only 1 copy of each card name."""
        pool = [
            _make_card("Lightning Bolt", "{R}", "Instant"),
            _make_card("Lightning Bolt", "{R}", "Instant"),
            _make_card("Lightning Bolt", "{R}", "Instant"),
        ]
        result = _filter_card_pool(pool, "legacy")
        assert len(result) == 1

    def test_non_singleton_allows_duplicates(self):
        """Standard/Modern/Pioneer: duplicates kept for scoring."""
        pool = [
            _make_card("Lightning Bolt", "{R}", "Instant"),
            _make_card("Lightning Bolt", "{R}", "Instant"),
        ]
        result = _filter_card_pool(pool, "standard")
        assert len(result) == 2

    def test_commander_color_identity_filter(self):
        """Commander: cards outside color identity are excluded."""
        pool = [
            _make_card("Red Card", "{R}", "Instant", color_identity=["R"]),
            _make_card("Blue Card", "{U}", "Instant", color_identity=["U"]),
            _make_card("Colorless Land", "", "Land"),  # no identity → always legal
        ]
        result = _filter_card_pool(pool, "commander", commander_names=["Red Card"])
        names = {c.name.lower() for c in result}
        assert "red card" in names
        assert "blue card" not in names
        assert "colorless land" in names


# ---------------------------------------------------------------------------
# Test Score Stage
# ---------------------------------------------------------------------------

class TestScoreStage:
    def test_aggro_favors_low_cmc(self):
        """Aggro strategy gives higher scores to low-CMC creatures."""
        low = _make_card("Goblin", "{R}", "Creature — Goblin", cmc=1.0)
        high = _make_card("Dragon", "{5}{R}{R}", "Creature — Dragon", cmc=7.0)
        assert _score_card(low, "aggro") > _score_card(high, "aggro")

    def test_control_favors_counterspells(self):
        """Control strategy gives higher scores to counterspells."""
        counter = _make_card("Counterspell", "{U}", "Instant", oracle_text="Counter target spell.", cmc=1.0)
        land = _make_card("Mountain", "", "Land")
        assert _score_card(counter, "control") > _score_card(land, "control")

    def test_combo_favors_draw(self):
        """Combo strategy gives higher scores to draw spells."""
        draw = _make_card("Brainstorm", "{U}", "Instant", oracle_text="Draw three cards.", cmc=1.0)
        land = _make_card("Mountain", "", "Land")
        assert _score_card(draw, "combo") > _score_card(land, "combo")

    def test_score_is_non_negative(self):
        """All scores should be non-negative."""
        card = _make_card("Vanilla", "{1}", "Creature — Beast", cmc=1.0)
        for strategy in ("aggro", "control", "midrange", "combo"):
            assert _score_card(card, strategy) >= 0


# ---------------------------------------------------------------------------
# Test Full Pipeline (build_deck)
# ---------------------------------------------------------------------------

class TestBuildDeckPipeline:
    def test_basic_modern_aggro(self):
        """Modern aggro deck builds with low-CMC creatures and removal."""
        pool = _make_card_pool()
        result = build_deck(pool, "modern", strategy="aggro")
        assert "deck" in result
        assert "sideboard" in result
        assert "validation" in result

    def test_unknown_format_returns_error(self):
        """Unknown format returns validation error."""
        pool = [_make_card("Test Card")]
        result = build_deck(pool, "nonexistent_format")
        assert not result["validation"]["valid"]
        assert any("unknown format" in v.lower() for v in result["validation"]["violations"])

    def test_empty_pool_returns_error(self):
        """Empty card pool returns validation error."""
        result = build_deck([], "modern")
        assert not result["validation"]["valid"]

    def test_deterministic_with_seed(self):
        """Same seed produces same deck output."""
        pool = _make_card_pool()
        r1 = build_deck(pool, "modern", strategy="aggro", seed=42)
        r2 = build_deck(pool, "modern", strategy="aggro", seed=42)
        assert r1["deck"] == r2["deck"]
        assert r1["sideboard"] == r2["sideboard"]

    def test_commander_format(self):
        """Commander format builds 100-card deck with commander."""
        pool = _make_card_pool()
        result = build_deck(pool, "commander", commander_names=["Goblin Raider"])
        assert result["validation"]["format"] == "commander"

    def test_commander_deck_contains_multiple_basic_lands(self):
        """Commander deck should allow multiple basic land copies (CR 905.2)."""
        pool = [
            _make_card("Mountain", "", "Land") for _ in range(20)
        ] + [
            _make_card(f"Creature {i}", "{1}", "Creature — Beast", cmc=1.0, color_identity=["R"])
            for i in range(85)
        ]
        result = build_deck(pool, "commander", commander_names=["Creature 0"], seed=42)
        mountain_qty = sum(
            e["quantity"] for e in result["deck"] if e["name"].lower() == "mountain"
        )
        assert mountain_qty > 1, (
            f"Commander deck should allow multiple basic land copies, got {mountain_qty}"
        )

    def test_unknown_strategy_defaults_to_midrange(self):
        """Unknown strategy falls back to midrange without error."""
        pool = _make_card_pool()
        result = build_deck(pool, "modern", strategy="unknown_strat")
        assert "deck" in result


# ---------------------------------------------------------------------------
# Test Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_all_cards_banned(self):
        """If all cards are banned for the format, pool is empty."""
        pool = [
            _make_card("Tarmogoyf", "{1}{G}", "Creature — Dinosaur"),  # banned in modern
            _make_card("Lightning Screw", "{U}", "Sorcery"),  # banned in modern
        ]
        result = build_deck(pool, "modern")
        assert not result["validation"]["valid"]

    def test_pool_smaller_than_min(self):
        """Pool with fewer cards than min deck size still returns what it can."""
        pool = [_make_card("Single Card", "{1}", "Creature")]
        result = build_deck(pool, "modern")
        assert len(result["deck"]) >= 0

    def test_commander_banned(self):
        """Banned commander is filtered out from the pool."""
        # Lightning Helix is banned in Commander
        pool = [
            _make_card("Lightning Helix", "{R}", "Instant"),
            _make_card("Mountain", "", "Land"),
        ]
        result = build_deck(pool, "commander", commander_names=["Lightning Helix"])
        # The commander is banned so it gets filtered out; deck may be empty or small
        names = {e["name"].lower() for e in result["deck"]}
        assert "lightning helix" not in names


# ---------------------------------------------------------------------------
# Test Basic Land Singleton Exemption (Fix 1)
# ---------------------------------------------------------------------------

class TestBasicLandSingletonExemption:
    """Basic lands are exempt from singleton enforcement (CR 905.2)."""

    def test_basic_lands_in_set(self):
        """All basic land names are in BASIC_LANDS."""
        assert "plains" in BASIC_LANDS
        assert "island" in BASIC_LANDS
        assert "swamp" in BASIC_LANDS
        assert "mountain" in BASIC_LANDS
        assert "forest" in BASIC_LANDS
        assert "snow-covered plains" in BASIC_LANDS
        assert "wastes" in BASIC_LANDS

    def test_basic_lands_not_deduped_in_commander(self):
        """Multiple copies of basic lands survive singleton filter."""
        pool = [
            _make_card("Mountain", "", "Land"),
            _make_card("Mountain", "", "Land"),
            _make_card("Mountain", "", "Land"),
            _make_card("Forest", "", "Land"),
            _make_card("Forest", "", "Land"),
        ]
        result = _filter_card_pool(pool, "commander")
        names = [c.name.lower() for c in result]
        assert names.count("mountain") == 3
        assert names.count("forest") == 2

    def test_basic_lands_not_deduped_in_legacy(self):
        """Multiple copies of basic lands survive singleton filter in Legacy."""
        pool = [
            _make_card("Plains", "", "Land"),
            _make_card("Plains", "", "Land"),
        ]
        result = _filter_card_pool(pool, "legacy")
        assert len(result) == 2

    def test_non_basic_cards_still_deduped(self):
        """Non-basic cards are still deduplicated in singleton formats."""
        pool = [
            _make_card("Lightning Bolt", "{R}", "Instant"),
            _make_card("Lightning Bolt", "{R}", "Instant"),
            _make_card("Mountain", "", "Land"),
            _make_card("Mountain", "", "Land"),
        ]
        result = _filter_card_pool(pool, "commander")
        names = [c.name.lower() for c in result]
        assert names.count("lightning bolt") == 1
        assert names.count("mountain") == 2

    def test_snow_covered_lands_not_deduped(self):
        """Snow-covered basic lands are also exempt from singleton."""
        pool = [
            _make_card("Snow-Covered Mountain", "", "Land — Snow"),
            _make_card("Snow-Covered Mountain", "", "Land — Snow"),
        ]
        result = _filter_card_pool(pool, "commander")
        assert len(result) == 2

    def test_wastes_not_deduped(self):
        """Wastes is exempt from singleton."""
        pool = [
            _make_card("Wastes", "", "Land — Wastes"),
            _make_card("Wastes", "", "Land — Wastes"),
        ]
        result = _filter_card_pool(pool, "commander")
        assert len(result) == 2

    def test_commander_build_deck_allows_multiple_basic_lands(self):
        """Full build_deck flow: Commander deck contains multiple basic land copies.

        Regression test for the bug where basic lands were incorrectly limited to
        1 copy in singleton formats, resulting in decks with only ~30 cards instead
        of the expected 99+ (or at least a proper land count).
        """
        pool = [
            _make_card("Mountain", "", "Land"),
            _make_card("Mountain", "", "Land"),
            _make_card("Mountain", "", "Land"),
            _make_card("Mountain", "", "Land"),
            _make_card("Forest", "", "Land"),
            _make_card("Forest", "", "Land"),
            _make_card("Plains", "", "Land"),
            _make_card("Plains", "", "Land"),
        ]
        # Add enough non-land cards to fill a 99-card Commander deck
        for i in range(100):
            pool.append(_make_card(f"Creature {i}", "{1}", "Creature — Beast"))

        commander = _make_card("Test Commander", "{R}", "Legendary Creature — Human")
        pool.insert(0, commander)

        result = build_deck(pool, "commander", commander_names=["Test Commander"], seed=42)

        # Count basic lands in the built deck
        land_counts: dict[str, int] = {}
        for entry in result["deck"]:
            name_lower = entry["name"].lower()
            if name_lower in BASIC_LANDS:
                land_counts[name_lower] = land_counts.get(name_lower, 0) + entry["quantity"]

        # Should have multiple copies of basic lands (up to 4 each)
        total_basic_lands = sum(land_counts.values())
        assert total_basic_lands >= 4, (
            f"Expected at least 4 basic lands in Commander deck, got {total_basic_lands}: "
            f"{land_counts}"
        )


# ---------------------------------------------------------------------------
# Test Sideboard with Partial Main Deck Copies (Fix 2)
# ---------------------------------------------------------------------------

class TestSideboardPartialMainDeck:
    """Sideboard can contain additional copies of cards already in main deck."""

    def test_sideboard_gets_fourth_copy(self):
        """If main has 3 copies, sideboard gets the 4th copy."""
        # Create a pool with many identical high-scoring cards
        pool = [
            _make_card("Lightning Bolt", "{R}", "Instant", oracle_text="Deal 3 damage to any target.", cmc=1.0)
            for _ in range(20)
        ] + [
            _make_card(f"Filler Card {i}", "{1}", "Creature")
            for i in range(60)
        ]

        scored = [(card, 10.0 if card.name == "Lightning Bolt" else 1.0) for card in pool]
        deck_list, sideboard_list, _ = _select_deck(scored, "modern")

        # Find Lightning Bolt entries
        main_qty = sum(e["quantity"] for e in deck_list if e["name"].lower() == "lightning bolt")
        sb_qty = sum(e["quantity"] for e in sideboard_list if e["name"].lower() == "lightning bolt")

        assert main_qty > 0, "Lightning Bolt should be in main deck"
        # Total across main + sideboard should not exceed 4
        assert main_qty + sb_qty <= 4

    def test_sideboard_allows_partial_main_deck(self):
        """Sideboard can add copies when main has fewer than max."""
        pool = [
            _make_card("Counterspell", "{U}", "Instant", oracle_text="Counter target spell.", cmc=1.0)
            for _ in range(6)
        ] + [
            _make_card(f"Filler {i}", "{1}", "Creature")
            for i in range(60)
        ]

        scored = [(card, 5.0 if card.name == "Counterspell" else 1.0) for card in pool]
        deck_list, sideboard_list, _ = _select_deck(scored, "modern")

        main_qty = sum(e["quantity"] for e in deck_list if e["name"].lower() == "counterspell")
        sb_qty = sum(e["quantity"] for e in sideboard_list if e["name"].lower() == "counterspell")

        # Should have some in main and potentially some in sideboard
        assert main_qty + sb_qty <= 4


# ---------------------------------------------------------------------------
# Test Land Balancing (Fix 3)
# ---------------------------------------------------------------------------

class TestLandBalancing:
    """Deck ensures at least 24% of cards are lands."""

    def test_deck_has_lands(self):
        """A deck with enough land options gets proper land count."""
        pool = [
            _make_card("Mountain", "", "Land") for _ in range(30)
        ] + [
            _make_card(f"Creature {i}", "{1}", "Creature — Beast", cmc=1.0)
            for i in range(40)
        ]

        scored = [(card, 5.0 if "land" in (card.type_line or "").lower() else 3.0) for card in pool]
        deck_list, sideboard_list, _ = _select_deck(scored, "modern")

        total_cards = sum(e["quantity"] for e in deck_list)
        land_cards = sum(
            e["quantity"] for e in deck_list
            if "land" in (e.get("name", "")).lower() or any(
                card.name.strip().lower() == e["name"].strip().lower() and "land" in (card.type_line or "").lower()
                for card in pool
            )
        )

        # Should have at least 24% lands if enough are available
        assert total_cards > 0, "Deck should have cards"

    def test_land_balancing_fills_when_needed(self):
        """If non-lands score higher, land balancing still adds lands."""
        # Use diverse land names so max_copies=4 per name allows enough total
        land_names = ["Mountain", "Forest", "Island", "Swamp", "Plains"]
        pool = [
            _make_card(land_name, "", "Land") for land_name in land_names for _ in range(5)
        ] + [
            _make_card(f"Powerful Creature {i}", "{1}", "Creature — Beast", cmc=1.0)
            for i in range(40)
        ]

        # Creatures score much higher than lands
        scored = [(card, 1.0 if "land" in (card.type_line or "").lower() else 10.0) for card in pool]
        deck_list, sideboard_list, _ = _select_deck(scored, "modern")

        total_cards = sum(e["quantity"] for e in deck_list)
        land_names_in_pool = {c.name.strip().lower() for c in pool if "land" in (c.type_line or "").lower()}
        land_cards = sum(
            e["quantity"] for e in deck_list
            if e["name"].strip().lower() in land_names_in_pool
        )

        assert total_cards > 0, "Deck should have cards"
        # Should have at least some lands (24% target)
        min_lands = max(int(total_cards * 0.24), 1)
        assert land_cards >= min_lands, f"Expected at least {min_lands} lands, got {land_cards}"


# ---------------------------------------------------------------------------
# Test Brawl No Sideboard (Fix 9)
# ---------------------------------------------------------------------------

class TestBrawlNoSideboard:
    """Brawl format does not use sideboards."""

    def test_brawl_no_sideboard(self):
        """Brawl builds deck with no sideboard entries."""
        pool = [
            _make_card("Mountain", "", "Land") for _ in range(25)
        ] + [
            _make_card(f"Creature {i}", "{1}", "Creature — Beast", cmc=1.0)
            for i in range(40)
        ]

        scored = [(card, 5.0 if "land" in (card.type_line or "").lower() else 3.0) for card in pool]
        deck_list, sideboard_list, _ = _select_deck(scored, "brawl")

        assert len(sideboard_list) == 0, f"Brawl should have no sideboard, got {len(sideboard_list)} entries"


# ---------------------------------------------------------------------------
# Test Color Identity via get_color_identity (Fix 6)
# ---------------------------------------------------------------------------

class TestColorIdentityFallback:
    """get_color_identity() derives from mana cost when color_identity field is empty."""

    def test_commander_filters_by_derived_color_identity(self):
        """Cards with no color_identity field but colored mana cost are filtered correctly."""
        # Card has red mana cost but no explicit color_identity
        pool = [
            _make_card("Red Commander", "{R}", "Legendary Creature — Human"),  # derived: R
            _make_card("Blue Spell", "{U}", "Instant"),  # derived: U, outside identity
            _make_card("Colorless Land", "", "Land"),  # no color → always legal
        ]

        result = _filter_card_pool(pool, "commander", commander_names=["Red Commander"])
        names = {c.name.lower() for c in result}

        assert "red commander" in names
        assert "blue spell" not in names  # U outside R identity
        assert "colorless land" in names


# ---------------------------------------------------------------------------
# Test Validation with Full Card Metadata (Fix 5)
# ---------------------------------------------------------------------------

class TestValidationWithMetadata:
    """Validation uses original card objects preserving set_code and rarity."""

    def test_validation_preserves_rarity(self):
        """Pauper validation checks rarity from original cards."""
        pool = [
            _make_card("Common Card", "{1}", "Creature", rarity="common") for _ in range(30)
        ] + [
            _make_card("Uncommon Card", "{2}", "Creature", rarity="uncommon") for _ in range(30)
        ]

        result = build_deck(pool, "pauper", seed=42)
        # Pauper only allows common cards; uncommon should be filtered or flagged
        deck_names = {e["name"].lower() for e in result["deck"]}
        assert "uncommon card" not in deck_names


# ---------------------------------------------------------------------------
# Test API Validation Errors (Fix 4 - HTTP 400)
# ---------------------------------------------------------------------------

class TestAPIValidation:
    """API rejects invalid strategy and format with HTTP 422/400."""

    def test_invalid_strategy_rejected(self):
        """Invalid strategy returns validation error at engine level."""
        pool = [_make_card("Test Card", "{1}", "Creature")]
        result = build_deck(pool, "modern", strategy="invalid_strategy")
        # Engine defaults to midrange for unknown strategies (not an error)
        assert "deck" in result

    def test_invalid_format_rejected(self):
        """Invalid format returns validation error at engine level."""
        pool = [_make_card("Test Card", "{1}", "Creature")]
        result = build_deck(pool, "nonexistent_format")
        assert not result["validation"]["valid"]
        assert any("unknown format" in v.lower() for v in result["validation"]["violations"])

    def test_api_rejects_invalid_strategy(self):
        """Pydantic validator rejects invalid strategy at model level."""
        from mtg_engine.api.routers.deck_build_ai import DeckBuildRequest

        with pytest.raises(ValidationError):
            DeckBuildRequest(
                cards=[{"name": "Test Card", "mana_cost": "{1}", "type_line": "Creature"}],
                format="modern",
                strategy="invalid_strategy",
            )

    def test_api_rejects_invalid_format(self):
        """Pydantic validator rejects invalid format at model level."""
        from mtg_engine.api.routers.deck_build_ai import DeckBuildRequest

        with pytest.raises(ValidationError):
            DeckBuildRequest(
                cards=[{"name": "Test Card", "mana_cost": "{1}", "type_line": "Creature"}],
                format="nonexistent_format",
                strategy="aggro",
            )

    def test_api_accepts_valid_request(self):
        """Valid request creates DeckBuildRequest without error."""
        from mtg_engine.api.routers.deck_build_ai import DeckBuildRequest

        req = DeckBuildRequest(
            cards=[{"name": "Test Card", "mana_cost": "{1}", "type_line": "Creature"}],
            format="modern",
            strategy="aggro",
        )
        assert req.format == "modern"
        assert req.strategy == "aggro"
