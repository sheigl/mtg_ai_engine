import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.card_data.ability_parser import (
    parse_oracle_text,
    TriggeredAbility, ActivatedAbility, KeywordAbility, SpellEffect, UnparsedAbility,
)


def test_lightning_bolt():
    """Lightning Bolt: instant → SpellEffect, no UnparsedAbility."""
    abilities = parse_oracle_text("Lightning Bolt deals 3 damage to any target.", "Instant")
    assert len(abilities) == 1
    assert isinstance(abilities[0], SpellEffect)
    assert "3 damage" in abilities[0].effect


def test_counterspell():
    """Counterspell: instant → SpellEffect."""
    abilities = parse_oracle_text("Counter target spell.", "Instant")
    assert len(abilities) == 1
    assert isinstance(abilities[0], SpellEffect)


def test_dark_ritual():
    """Dark Ritual: instant → SpellEffect."""
    abilities = parse_oracle_text("Add {B}{B}{B}.", "Instant")
    assert len(abilities) == 1
    assert isinstance(abilities[0], SpellEffect)


def test_llanowar_elves():
    """Llanowar Elves: activated mana ability."""
    abilities = parse_oracle_text("{T}: Add {G}.", "Creature — Elf Druid")
    assert len(abilities) == 1
    assert isinstance(abilities[0], ActivatedAbility)
    ab = abilities[0]
    assert "{T}" in ab.cost
    assert "{G}" in ab.effect


def test_serra_angel():
    """Serra Angel: Flying, Vigilance — both keyword abilities."""
    abilities = parse_oracle_text("Flying\nVigilance", "Creature — Angel")
    assert len(abilities) == 2
    assert all(isinstance(a, KeywordAbility) for a in abilities)
    names = {a.name for a in abilities}
    assert "flying" in names
    assert "vigilance" in names


def test_triggered_ability():
    """When this creature dies, draw a card."""
    abilities = parse_oracle_text(
        "When this creature dies, draw a card.", "Creature — Human"
    )
    assert len(abilities) == 1
    assert isinstance(abilities[0], TriggeredAbility)
    assert "dies" in abilities[0].trigger_condition.lower() or "dies" in abilities[0].raw_text.lower()


def test_whenever_trigger():
    """Whenever CARDNAME attacks, create a 1/1 token."""
    abilities = parse_oracle_text(
        "Whenever Llanowar Elves attacks, create a 1/1 green Elf creature token.",
        "Creature — Elf Druid",
    )
    assert len(abilities) == 1
    assert isinstance(abilities[0], TriggeredAbility)


def test_no_unparsed_in_test_cards():
    """All test cards must produce zero UnparsedAbility segments."""
    test_cases = [
        ("Lightning Bolt deals 3 damage to any target.", "Instant"),
        ("Counter target spell.", "Instant"),
        ("Add {B}{B}{B}.", "Instant"),
        ("{T}: Add {G}.", "Creature — Elf Druid"),
        ("Flying\nVigilance", "Creature — Angel"),
    ]
    for text, type_line in test_cases:
        abilities = parse_oracle_text(text, type_line)
        unparsed = [a for a in abilities if isinstance(a, UnparsedAbility)]
        assert not unparsed, f"UnparsedAbility found for {text!r}: {unparsed}"


# ── Fortify (CR 702.54a) ────────────────────────────────────────────────────

GARRISON_ORACLE = (
    "Fortify {3} ({3}: Attach to target land you control. "
    "Fortify only as a sorcery. This card enters unattached and stays on the "
    "battlefield if the land leaves.)"
)
CAMP_ORACLE = (
    "Fortify {2}{G} ({2}{G}: Attach to target land you control. "
    "Fortify only as a sorcery. C.A.M.P. can't be attacked. As long as C.A.M.P. "
    "is attached, it doesn't have base abilities or rules text.)"
)


def test_fortify_garrison_parses_as_activated_ability():
    """Darksteel Garrison's Fortify line is an activated ability, not a keyword."""
    abilities = parse_oracle_text(GARRISON_ORACLE, "Artifact Creature — Fortification")
    assert len(abilities) == 1
    assert isinstance(abilities[0], ActivatedAbility)
    ab = abilities[0]
    assert ab.cost == "{3}"
    assert "attach this fortification to target land you control" in ab.effect.lower()
    assert ab.timing_restriction == "(Fortify only as a sorcery.)"


def test_fortify_camp_multi_symbol_cost():
    """C.A.M.P.'s multi-symbol Fortify cost parses completely ({2}{G}, not {2})."""
    abilities = parse_oracle_text(CAMP_ORACLE, "Artifact Creature — Fortification")
    assert len(abilities) == 1
    assert isinstance(abilities[0], ActivatedAbility)
    assert abilities[0].cost == "{2}{G}"


def test_fortify_not_misparsed_as_keyword():
    """Fortify is in KEYWORDS — the Fortify branch must prevent the keyword
    fall-through from producing KeywordAbility(name='fortify {3}')."""
    abilities = parse_oracle_text(GARRISON_ORACLE, "Artifact Creature — Fortification")
    keywords = [a for a in abilities if isinstance(a, KeywordAbility)]
    assert not keywords, f"Fortify mis-parsed as keyword: {keywords}"


def test_fortify_no_cost_not_matched():
    """'Fortify only as a sorcery' (no cost) is not an activated ability."""
    abilities = parse_oracle_text("Fortify only as a sorcery.", "Artifact Creature — Fortification")
    assert not any(isinstance(a, ActivatedAbility) for a in abilities)


def test_regular_keywords_still_parse():
    """The Fortify branch must not shadow normal keyword lines."""
    abilities = parse_oracle_text("Flying\nVigilance", "Creature — Angel")
    assert all(isinstance(a, KeywordAbility) for a in abilities)


def test_regular_activated_ability_still_parses():
    """A normal activated ability is unaffected by the Fortify branch."""
    abilities = parse_oracle_text("{T}: Add {G}.", "Creature — Elf Druid")
    assert isinstance(abilities[0], ActivatedAbility)
    assert "{T}" in abilities[0].cost
