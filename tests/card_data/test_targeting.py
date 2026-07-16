import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.card_data.ability_parser import parse_targets, TargetInfo


def test_target_pattern_count():
    """PAR-03: Ensure targeting patterns are defined."""
    from mtg_engine.card_data.ability_parser import _TARGET_PATTERNS
    assert len(_TARGET_PATTERNS) >= 8, f"Expected 8+ target patterns, got {len(_TARGET_PATTERNS)}"


def test_single_target_creature():
    """PAR-03: Single creature target."""
    targets = parse_targets("Deal 3 damage to target creature.")
    assert len(targets) >= 1
    assert any(t.target_type == "creature" for t in targets)


def test_single_target_player():
    """PAR-03: Single player target."""
    targets = parse_targets("Target player draws a card.")
    assert len(targets) >= 1
    assert any(t.target_type == "player" for t in targets)


def test_single_target_spell():
    """PAR-03: Single spell target."""
    targets = parse_targets("Counter target spell.")
    assert len(targets) >= 1
    assert any(t.target_type == "spell" for t in targets)


def test_single_target_permanent():
    """PAR-03: Single permanent target."""
    targets = parse_targets("Destroy target permanent.")
    assert len(targets) >= 1
    assert any(t.target_type == "permanent" for t in targets)


def test_single_target_land():
    """PAR-03: Single land target."""
    targets = parse_targets("Tap target land.")
    assert len(targets) >= 1
    assert any(t.target_type == "land" for t in targets)


def test_single_target_card():
    """PAR-03: Single card target."""
    targets = parse_targets("Exile target card.")
    assert len(targets) >= 1
    assert any(t.target_type == "card" for t in targets)


def test_single_target_any():
    """PAR-03: Any target."""
    targets = parse_targets("Deal 3 damage to any target.")
    assert len(targets) >= 1
    assert any(t.target_type == "any" for t in targets)


def test_restricted_target_creature():
    """PAR-03: Restricted creature target (e.g., 'target red creature')."""
    targets = parse_targets("Deal 3 damage to target red creature.")
    creature_targets = [t for t in targets if t.target_type == "creature"]
    assert len(creature_targets) >= 1
    assert creature_targets[0].target_restriction is not None


def test_restricted_target_player():
    """PAR-03: Restricted player target (e.g., 'target opponent')."""
    targets = parse_targets("Target opponent discards a card.")
    player_targets = [t for t in targets if t.target_type == "player"]
    assert len(player_targets) >= 1


def test_restricted_target_spell():
    """PAR-03: Restricted spell target (e.g., 'target instant spell')."""
    targets = parse_targets("Counter target instant spell.")
    spell_targets = [t for t in targets if t.target_type == "spell"]
    assert len(spell_targets) >= 1


def test_restricted_target_permanent():
    """PAR-03: Restricted permanent target (e.g., 'target artifact')."""
    targets = parse_targets("Destroy target artifact.")
    perm_targets = [t for t in targets if t.target_type == "permanent"]
    assert len(perm_targets) >= 1


def test_restricted_target_land():
    """PAR-03: Restricted land target (e.g., 'target basic land')."""
    targets = parse_targets("Tap target basic land.")
    land_targets = [t for t in targets if t.target_type == "land"]
    assert len(land_targets) >= 1


def test_restricted_target_card():
    """PAR-03: Restricted card target (e.g., 'target creature card')."""
    targets = parse_targets("Exile target creature card.")
    card_targets = [t for t in targets if t.target_type == "card"]
    assert len(card_targets) >= 1


def test_multiple_targets():
    """PAR-03: Multiple targets in same text."""
    text = "Deal 3 damage to target creature and target player."
    targets = parse_targets(text)
    assert len(targets) >= 2


def test_target_number_explicit():
    """PAR-03: Explicit target number."""
    targets = parse_targets("Deal 2 damage to target 3 creatures.")
    assert len(targets) >= 1


def test_target_optional():
    """PAR-03: Optional target ('target creature, if able')."""
    targets = parse_targets("Target creature, if able.")
    assert len(targets) >= 1
    assert any(t.is_optional for t in targets)


def test_target_battlefield():
    """PAR-03: Battlefield target."""
    targets = parse_targets("Put a +1/+1 counter on target battlefield.")
    assert len(targets) >= 1
    assert any(t.target_type == "battlefield" for t in targets)


def test_target_restriction_complex():
    """PAR-03: Complex target restriction (e.g., 'target creature you don't control')."""
    targets = parse_targets("Destroy target creature you don't control.")
    creature_targets = [t for t in targets if t.target_type == "creature"]
    assert len(creature_targets) >= 1


def test_target_restriction_color():
    """PAR-03: Color-restricted target (e.g., 'target red creature')."""
    targets = parse_targets("Deal 2 damage to target red creature.")
    creature_targets = [t for t in targets if t.target_type == "creature"]
    assert len(creature_targets) >= 1
    assert creature_targets[0].target_restriction is not None


def test_target_restriction_type():
    """PAR-03: Type-restricted target (e.g., 'target Dragon')."""
    targets = parse_targets("Target Dragon gets +1/+1.")
    creature_targets = [t for t in targets if t.target_type == "creature"]
    assert len(creature_targets) >= 1


def test_target_restriction_subtype():
    """PAR-03: Subtype-restricted target (e.g., 'target Human')."""
    targets = parse_targets("Target Human creature draws a card.")
    creature_targets = [t for t in targets if t.target_type == "creature"]
    assert len(creature_targets) >= 1


def test_target_restriction_ability():
    """PAR-03: Ability-restricted target (e.g., 'target creature with flying')."""
    targets = parse_targets("Target creature with flying gets +1/+1.")
    creature_targets = [t for t in targets if t.target_type == "creature"]
    assert len(creature_targets) >= 1


def test_target_restriction_controller():
    """PAR-03: Controller-restricted target (e.g., 'target creature you control')."""
    targets = parse_targets("Target creature you control gets +1/+1.")
    creature_targets = [t for t in targets if t.target_type == "creature"]
    assert len(creature_targets) >= 1


def test_target_restriction_opponent():
    """PAR-03: Opponent-restricted target (e.g., 'target opponent')."""
    targets = parse_targets("Target opponent discards a card.")
    player_targets = [t for t in targets if t.target_type == "player"]
    assert len(player_targets) >= 1


def test_target_restriction_any_player():
    """PAR-03: Any player target."""
    targets = parse_targets("Any target player draws a card.")
    player_targets = [t for t in targets if t.target_type == "player"]
    assert len(player_targets) >= 1


def test_target_restriction_each_player():
    """PAR-03: Each player target."""
    targets = parse_targets("Each target player draws a card.")
    player_targets = [t for t in targets if t.target_type == "player"]
    assert len(player_targets) >= 1


def test_target_restriction_each_opponent():
    """PAR-03: Each opponent target."""
    targets = parse_targets("Each target opponent discards a card.")
    player_targets = [t for t in targets if t.target_type == "player"]
    assert len(player_targets) >= 1


def test_target_restriction_each_creature():
    """PAR-03: Each creature target."""
    targets = parse_targets("Each target creature gets +1/+1.")
    creature_targets = [t for t in targets if t.target_type == "creature"]
    assert len(creature_targets) >= 1


def test_target_restriction_each_permanent():
    """PAR-03: Each permanent target."""
    targets = parse_targets("Each target permanent gets +1/+1.")
    perm_targets = [t for t in targets if t.target_type == "permanent"]
    assert len(perm_targets) >= 1


def test_target_restriction_each_land():
    """PAR-03: Each land target."""
    targets = parse_targets("Each target land becomes a 1/1 creature.")
    land_targets = [t for t in targets if t.target_type == "land"]
    assert len(land_targets) >= 1


def test_target_restriction_each_card():
    """PAR-03: Each card target."""
    targets = parse_targets("Each target card is exiled.")
    card_targets = [t for t in targets if t.target_type == "card"]
    assert len(card_targets) >= 1


def test_target_restriction_each_battlefield():
    """PAR-03: Each battlefield target."""
    targets = parse_targets("Each target battlefield gets +1/+1.")
    battlefield_targets = [t for t in targets if t.target_type == "battlefield"]
    assert len(battlefield_targets) >= 1


def test_target_restriction_each_any():
    """PAR-03: Each any target."""
    targets = parse_targets("Each target any gets +1/+1.")
    any_targets = [t for t in targets if t.target_type == "any"]
    assert len(any_targets) >= 1


def test_target_model_fields():
    """PAR-03: TargetInfo model has all required fields."""
    ti = TargetInfo(
        target_type="creature",
        target_number=1,
        target_restriction="red",
        is_optional=False,
    )
    assert ti.target_type == "creature"
    assert ti.target_number == 1
    assert ti.target_restriction == "red"
    assert ti.is_optional is False
