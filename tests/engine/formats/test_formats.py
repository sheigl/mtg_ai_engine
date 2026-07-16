"""FMT-01: Format rules engine tests."""
import pytest

from mtg_engine.models.game import Card, PlayerState, GameState, ManaPool
from mtg_engine.engine.formats.banned import (
    is_banned,
    is_restricted,
    get_format_banned_list,
    BANNED_LISTS,
    RESTRICTED_LIST,
)
from mtg_engine.engine.formats import validate_deck, FORMAT_VALIDATORS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_card(
    name: str = "Test Card",
    rarity: str | None = None,
    set_code: str | None = None,
    type_line: str = "",
) -> Card:
    return Card(name=name, rarity=rarity, set_code=set_code, type_line=type_line)


def _legal_standard_cards(n: int) -> list[Card]:
    """Return n cards that are legal in Standard (no bans, valid set code)."""
    return [_make_card(f"Legal Card {i}", set_code="MKM") for i in range(n)]


# ── Tests: Banned/Restricted lookups ─────────────────────────────────────────

class TestBannedLookup:
    def test_banned_returns_true(self):
        assert is_banned("Jin-Gitaxias, Progress Tyrant", "pioneer") is True

    def test_banned_returns_false_legal_card(self):
        assert is_banned("Lightning Bolt", "pioneer") is False

    def test_banned_unknown_format(self):
        # Unknown format returns False (no banlist defined)
        assert is_banned("Some Card", "nonexistent") is False

    def test_case_insensitive_card_name(self):
        assert is_banned("jin-gitaxias, progress tyrant", "pioneer") is True
        assert is_banned("JIN-GITAXIAS, PROGRESS TYRANT", "pioneer") is True

    def test_case_insensitive_format(self):
        assert is_banned("Jin-Gitaxias, Progress Tyrant", "PIONEER") is True
        assert is_banned("Jin-Gitaxias, Progress Tyrant", "Pioneer") is True


class TestRestrictedLookup:
    def test_restricted_returns_true(self):
        assert is_restricted("Ancestral Recall") is True

    def test_restricted_returns_false(self):
        assert is_restricted("Lightning Bolt") is False

    def test_case_insensitive(self):
        assert is_restricted("ANCESTRAL RECALL") is True
        assert is_restricted("ancestral recall") is True


class TestGetFormatBannedList:
    def test_returns_banned_set_for_known_format(self):
        banned = get_format_banned_list("pioneer")
        assert "jin-gitaxias, progress tyrant" in banned

    def test_returns_empty_for_unknown_format(self):
        banned = get_format_banned_list("nonexistent")
        assert banned == set()


# ── Tests: Format validators via dispatcher ───────────────────────────────────

class TestStandardValidation:
    def test_valid_deck(self):
        cards = _legal_standard_cards(60)
        valid, violations = validate_deck(cards, "standard")
        assert valid is True
        assert violations == []

    def test_too_few_cards(self):
        cards = _legal_standard_cards(59)
        valid, violations = validate_deck(cards, "standard")
        assert valid is False
        assert any("at least 60" in v for v in violations)

    def test_banned_card_rejected(self):
        cards = _legal_standard_cards(59) + [_make_card("Bolas's Citadel", set_code="MKM")]
        valid, violations = validate_deck(cards, "standard")
        assert valid is False
        assert any("banned" in v.lower() for v in violations)

    def test_illegal_set_rejected(self):
        cards = _legal_standard_cards(59) + [_make_card("Old Card", set_code="8ED")]
        valid, violations = validate_deck(cards, "standard")
        assert valid is False
        assert any("not legal" in v.lower() for v in violations)


class TestPioneerValidation:
    def test_banned_pioneer_card(self):
        cards = _legal_standard_cards(59) + [_make_card("Rhystic Study", set_code="RNA")]
        valid, violations = validate_deck(cards, "pioneer")
        assert valid is False
        assert any("banned" in v.lower() for v in violations)


class TestLegacyValidation:
    def test_no_legality_window(self):
        """Legacy has no legality window — old sets are fine."""
        cards = [_make_card(f"Old Card {i}", set_code="8ED") for i in range(60)]
        valid, violations = validate_deck(cards, "legacy")
        # Should not have legality window violations (only banned list matters)
        assert not any("not legal" in v.lower() and "banned" not in v.lower() for v in violations)

    def test_banned_legacy_card(self):
        cards = _legal_standard_cards(59) + [_make_card("Mind Crush", set_code="8ED")]
        valid, violations = validate_deck(cards, "legacy")
        assert valid is False
        assert any("banned" in v.lower() for v in violations)


class TestModernValidation:
    def test_banned_modern_card(self):
        """Banned Modern cards are rejected."""
        cards = _legal_standard_cards(59) + [_make_card("Lightning Screw", set_code="GRN")]
        valid, violations = validate_deck(cards, "modern")
        assert valid is False
        assert any("banned" in v.lower() for v in violations)

    def test_illegal_set_rejected(self):
        """Cards from sets outside the Modern legality window are rejected."""
        cards = _legal_standard_cards(59) + [_make_card("Old Card", set_code="LEA")]
        valid, violations = validate_deck(cards, "modern")
        assert valid is False
        assert any("not legal" in v.lower() for v in violations)

    def test_valid_modern_deck(self):
        """A deck of 60 cards from a legal Modern set passes."""
        cards = [_make_card(f"Modern Card {i}", set_code="GRN") for i in range(60)]
        valid, violations = validate_deck(cards, "modern")
        assert valid is True
        assert violations == []


class TestVintageValidation:
    def test_restricted_max_one_copy(self):
        """Restricted cards can only appear once."""
        cards = _legal_standard_cards(58) + [
            _make_card("Ancestral Recall", set_code="LEA"),
            _make_card("Ancestral Recall", set_code="LEA"),
        ]
        valid, violations = validate_deck(cards, "vintage")
        assert valid is False
        assert any("restricted" in v.lower() for v in violations)

    def test_restricted_one_copy_allowed(self):
        """One copy of a restricted card is fine."""
        cards = _legal_standard_cards(59) + [_make_card("Black Lotus", set_code="LEA")]
        valid, violations = validate_deck(cards, "vintage")
        assert not any("restricted" in v.lower() for v in violations)

    def test_restricted_violation_reported_once(self):
        """Multiple copies of a restricted card produce only one violation."""
        cards = _legal_standard_cards(56) + [
            _make_card("Ancestral Recall", set_code="LEA"),
            _make_card("Ancestral Recall", set_code="LEA"),
            _make_card("Ancestral Recall", set_code="LEA"),
            _make_card("Ancestral Recall", set_code="LEA"),
        ]
        valid, violations = validate_deck(cards, "vintage")
        assert valid is False
        restricted_violations = [v for v in violations if "restricted" in v.lower()]
        # Should be exactly 1 violation, not 4 (one per copy)
        assert len(restricted_violations) == 1
        assert "found 4" in restricted_violations[0]


class TestCommanderValidation:
    def test_delegates_to_commander_validator(self):
        """Commander validation delegates to existing commander.py logic."""
        # 100 singleton cards with a legendary commander should pass basic checks
        cmd = _make_card("Niv-Mizzet", type_line="Legendary Creature — Dragon")
        other_cards = [_make_card(f"Land {i}") for i in range(99)]
        all_cards = [cmd] + other_cards

        valid, violations = validate_deck(all_cards, "commander", commanders=[cmd])
        # Should pass the commander validator (100 cards, singleton, legendary)
        assert valid is True or len(violations) == 0

    def test_commander_banned_card_rejected(self):
        """Cards on the Commander banned list are rejected."""
        cmd = _make_card("Niv-Mizzet", type_line="Legendary Creature — Dragon")
        other_cards = [_make_card(f"Land {i}") for i in range(98)]
        all_cards = [cmd] + other_cards + [_make_card("Lightning Helix")]
        valid, violations = validate_deck(all_cards, "commander", commanders=[cmd])
        assert valid is False
        assert any("banned" in v.lower() and "lightning helix" in v.lower() for v in violations)

    def test_commander_banned_list_has_entries(self):
        """The commander banned list contains representative cards."""
        banned = get_format_banned_list("commander")
        assert len(banned) > 0
        assert "lightning helix" in banned
        assert "ravenous raptor" in banned


class TestBrawlValidation:
    def test_exactly_60_cards(self):
        cards = _legal_standard_cards(59)
        cmd = _make_card("Niv-Mizzet", type_line="Legendary Creature — Dragon")
        valid, violations = validate_deck(cards, "brawl", commanders=[cmd])
        assert valid is False
        assert any("exactly 60" in v for v in violations)

    def test_commander_must_be_legendary_or_pw(self):
        cards = _legal_standard_cards(60)
        bad_cmd = _make_card("Basic Plains", type_line="Basic Land")
        valid, violations = validate_deck(cards, "brawl", commanders=[bad_cmd])
        assert valid is False
        assert any("not a legendary creature or planeswalker" in v for v in violations)

    def test_valid_brawl_commander(self):
        cards = _legal_standard_cards(60)
        cmd = _make_card("Niv-Mizzet", type_line="Legendary Creature — Dragon")
        valid, violations = validate_deck(cards, "brawl", commanders=[cmd])
        # Commander check should pass (legendary creature)
        assert not any("not a legendary" in v for v in violations)

    def test_brawl_checks_own_banned_list(self):
        """Brawl rejects cards on the Brawl-specific banned list."""
        cards = _legal_standard_cards(59) + [_make_card("Karn, the Great Creator", set_code="MKM")]
        cmd = _make_card("Niv-Mizzet", type_line="Legendary Creature — Dragon")
        valid, violations = validate_deck(cards, "brawl", commanders=[cmd])
        assert valid is False
        assert any("banned" in v.lower() and "karn" in v.lower() for v in violations)

    def test_brawl_checks_standard_banned_list(self):
        """Brawl also rejects cards on the Standard banned list."""
        cards = _legal_standard_cards(59) + [_make_card("Bolas's Citadel", set_code="MKM")]
        cmd = _make_card("Niv-Mizzet", type_line="Legendary Creature — Dragon")
        valid, violations = validate_deck(cards, "brawl", commanders=[cmd])
        assert valid is False
        assert any("banned" in v.lower() and "bolas's citadel" in v.lower() for v in violations)


class TestPauperValidation:
    def test_all_common_passes(self):
        cards = [_make_card(f"Common {i}", rarity="c") for i in range(60)]
        valid, violations = validate_deck(cards, "pauper")
        assert valid is True

    def test_non_common_rejected(self):
        cards = [_make_card(f"Common {i}", rarity="c") for i in range(59)]
        cards.append(_make_card("Rare Card", rarity="r"))
        valid, violations = validate_deck(cards, "pauper")
        assert valid is False
        assert any("not common" in v.lower() for v in violations)

    def test_missing_rarity_skipped(self):
        """Cards without a rarity field are silently skipped per design doc."""
        cards = [_make_card(f"Common {i}", rarity="c") for i in range(59)]
        cards.append(_make_card("Unknown Rarity"))  # no rarity set
        valid, violations = validate_deck(cards, "pauper")
        assert valid is True
        assert not any("not common" in v.lower() for v in violations)


class TestDispatcher:
    def test_unknown_format(self):
        cards = _legal_standard_cards(60)
        valid, violations = validate_deck(cards, "nonexistent_format")
        assert valid is False
        assert len(violations) == 1
        assert "Unknown format" in violations[0]

    def test_case_insensitive_format(self):
        cards = _legal_standard_cards(60)
        # Should work with mixed case
        valid, _ = validate_deck(cards, "STANDARD")
        assert valid is True


# ── Tests: API endpoint ───────────────────────────────────────────────────────

class TestValidateDeckAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient  # noqa: F811
        from mtg_engine.api.main import app
        self.client = TestClient(app)

    def _make_card_entry(self, name="Test Card", quantity=1, rarity=None, set_code=None):
        entry: dict = {"name": name, "quantity": quantity}
        if rarity is not None:
            entry["rarity"] = rarity
        if set_code is not None:
            entry["set_code"] = set_code
        return entry

    def test_valid_standard_deck(self):
        cards = [self._make_card_entry(f"Legal Card {i}", 1, set_code="MKM") for i in range(60)]
        resp = self.client.post("/deck/validate", json={
            "format": "standard",
            "cards": cards,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["valid"] is True
        assert data["violations"] == []
        assert data["format"] == "standard"

    def test_banned_card_in_deck(self):
        cards = [self._make_card_entry(f"Legal Card {i}", 1, set_code="MKM") for i in range(59)]
        cards.append(self._make_card_entry("Bolas's Citadel", 1, set_code="MKM"))
        resp = self.client.post("/deck/validate", json={
            "format": "standard",
            "cards": cards,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["valid"] is False
        assert any("banned" in v.lower() for v in data["violations"])

    def test_unknown_format_returns_400(self):
        cards = [self._make_card_entry("Test Card", 1)]
        resp = self.client.post("/deck/validate", json={
            "format": "nonexistent_format",
            "cards": cards,
        })
        assert resp.status_code == 400

    def test_pauper_rejects_rare(self):
        cards = [self._make_card_entry(f"Common {i}", 1, rarity="c") for i in range(59)]
        cards.append(self._make_card_entry("Rare Card", 1, rarity="r"))
        resp = self.client.post("/deck/validate", json={
            "format": "pauper",
            "cards": cards,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["valid"] is False
        assert any("not common" in v.lower() for v in data["violations"])

    def test_commander_deck_validation(self):
        cmd_entry = self._make_card_entry("Niv-Mizzet", 1)
        other_cards = [self._make_card_entry(f"Land {i}", 1) for i in range(99)]
        all_cards = [cmd_entry] + other_cards
        resp = self.client.post("/deck/validate", json={
            "format": "commander",
            "cards": all_cards,
            "commanders": [cmd_entry],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        # Should pass basic commander checks (100 cards, singleton)
        assert data["valid"] is True

    def test_deck_size_too_small(self):
        cards = [self._make_card_entry(f"Card {i}", 1, set_code="MKM") for i in range(59)]
        resp = self.client.post("/deck/validate", json={
            "format": "standard",
            "cards": cards,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["valid"] is False
        assert any("at least 60" in v for v in data["violations"])
