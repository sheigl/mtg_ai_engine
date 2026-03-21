"""
Unit tests for archidekt_parser module.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from mtg_engine.card_data.archidekt_parser import (
    parse_archidekt_text,
    parse_scryfall_txt,
    _parse_line,
    _validate_parsed,
)


# ── _parse_line ───────────────────────────────────────────────────────────────

def test_parse_line_standard():
    assert _parse_line("4 Lightning Bolt") == ("Lightning Bolt", 4)


def test_parse_line_x_suffix():
    assert _parse_line("Lightning Bolt x4") == ("Lightning Bolt", 4)


def test_parse_line_x_prefix():
    assert _parse_line("4x Lightning Bolt") == ("Lightning Bolt", 4)


def test_parse_line_comment():
    assert _parse_line("// This is a comment") is None


def test_parse_line_hash_comment():
    assert _parse_line("# comment") is None


def test_parse_line_empty():
    assert _parse_line("") is None


def test_parse_line_single_no_qty():
    assert _parse_line("Forest") == ("Forest", 1)


# ── parse_archidekt_text ──────────────────────────────────────────────────────

def _make_60_forest_text():
    return "60 Forest\n"


def test_parse_text_basic():
    content = _make_60_forest_text()
    result = parse_archidekt_text(content)
    assert result["main"] == [("Forest", 60)]
    assert result["sideboard"] == []


def test_parse_text_with_sideboard():
    content = "60 Forest\nSideboard\n2 Lightning Bolt\n"
    result = parse_archidekt_text(content)
    assert result["main"] == [("Forest", 60)]
    assert result["sideboard"] == [("Lightning Bolt", 2)]


def test_parse_text_multiple_cards():
    content = "4 Lightning Bolt\n4 Mountain\n52 Forest\n"
    result = parse_archidekt_text(content)
    assert ("Lightning Bolt", 4) in result["main"]
    assert ("Mountain", 4) in result["main"]


def test_parse_text_too_few_cards():
    with pytest.raises(ValueError, match="at least 60"):
        parse_archidekt_text("4 Lightning Bolt\n")


def test_parse_text_sideboard_too_large():
    main = "60 Forest\n"
    sb = "Sideboard\n" + "1 Lightning Bolt\n" * 16
    with pytest.raises(ValueError, match="at most 15"):
        parse_archidekt_text(main + sb)


def test_parse_text_exceeds_four_copies():
    content = "5 Lightning Bolt\n55 Forest\n"
    with pytest.raises(ValueError, match="5 copies"):
        parse_archidekt_text(content)


def test_parse_text_basic_lands_unlimited():
    # 80 forests in main should be valid (basic land, no 4-copy limit)
    content = "80 Forest\n"
    result = parse_archidekt_text(content)
    assert result["main"] == [("Forest", 80)]


# ── parse_scryfall_txt ────────────────────────────────────────────────────────

def test_parse_scryfall_txt():
    content = "4 Lightning Bolt\n56 Mountain\n"
    result = parse_scryfall_txt(content)
    assert ("Lightning Bolt", 4) in result["main"]
    assert ("Mountain", 56) in result["main"]


# ── _validate_parsed ──────────────────────────────────────────────────────────

def test_validate_passes():
    main = [("Forest", 60)]
    sideboard = []
    _validate_parsed(main, sideboard)  # should not raise


def test_validate_fails_short_deck():
    with pytest.raises(ValueError):
        _validate_parsed([("Forest", 40)], [])


def test_validate_fails_large_sideboard():
    with pytest.raises(ValueError):
        _validate_parsed([("Forest", 60)], [("Mountain", 16)])
