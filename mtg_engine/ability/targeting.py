import re
from typing import Optional
from pydantic import BaseModel, Field

# Color name to single-letter code mapping
COLOR_NAME_TO_CODE = {
    "white": "W",
    "blue": "U",
    "black": "B",
    "red": "R",
    "green": "G",
}


class TargetSpec(BaseModel):
    """Parsed target specification from oracle text."""
    is_targeted: bool = False
    count_min: int = 1
    count_max: int = 1
    target_types: list[str] = Field(default_factory=list)  # ["creature", "player", "planeswalker"]
    color_restrictions: list[str] = Field(default_factory=list)  # ["black", "red"]
    subtype_restrictions: list[str] = Field(default_factory=list)  # ["Goblin", "Wall"]
    controller_restrictions: list[str] = Field(default_factory=list)  # ["you control", "opponent controls"]
    raw_text: str = ""


def parse_target_spec(oracle_text: str) -> TargetSpec:
    """Parse target specification from oracle text.

    Handles patterns like:
    - "target creature"
    - "up to 2 target creatures"
    - "target player or planeswalker"
    - "target black creature"
    - "up to 1 target artifact an opponent controls"
    """
    result = TargetSpec(raw_text=oracle_text)
    if not oracle_text:
        return result

    # Check for "up to N targets" pattern
    up_to_match = re.search(r"up\s+to\s+(\d+)\s+targets?", oracle_text.lower())
    if up_to_match:
        result.count_min = 1
        result.count_max = int(up_to_match.group(1))
        result.is_targeted = True
    else:
        # Check for "N targets" pattern (e.g., "2 targets")
        count_match = re.search(r"(\d+)\s+targets?", oracle_text.lower())
        if count_match:
            result.count_min = int(count_match.group(1))
            result.count_max = int(count_match.group(1))
            result.is_targeted = True
        else:
            # Check if "target" appears at all (implies 1 target)
            if re.search(r"\btarget\b", oracle_text.lower()):
                result.is_targeted = True
                result.count_min = 1
                result.count_max = 1
            else:
                return result

    # Extract target types (creature, player, planeswalker, permanent, artifact, enchantment, etc.)
    target_types = []
    type_keywords = [
        "creature", "player", "planeswalker", "permanent", "artifact",
        "enchantment", "land", "battle"
    ]
    for keyword in type_keywords:
        if re.search(rf"\b{keyword}\b", oracle_text.lower()):
            target_types.append(keyword)

    result.target_types = target_types

    # Extract color restrictions
    colors = ["white", "blue", "black", "red", "green"]
    for color in colors:
        if re.search(rf"\b{color}\b", oracle_text.lower()):
            result.color_restrictions.append(color)

    # Extract subtype restrictions (words after target types, before next keyword)
    # This is a simplified extraction - looks for common creature types
    subtype_keywords = [
        "goblin", "elf", "dragon", "angel", "demon", "zombie", "soldier",
        "wizard", "knight", "beast", "snake", "bird", "cat", "horror",
        "wall", "shaman", "warrior", "cleric", "gnome", "rat", "thief",
        "scout", "spirit", " Elemental", "fortification", "vehicle",
        "equipment", "aura", "saga", "class", "case", "rune"
    ]
    for subtype in subtype_keywords:
        if re.search(rf"\b{subtype}\b", oracle_text.lower()):
            result.subtype_restrictions.append(subtype)

    # Extract controller restrictions
    if re.search(r"you\s+control", oracle_text.lower()):
        result.controller_restrictions.append("you_control")
    if re.search(r"opponent\s+controls", oracle_text.lower()):
        result.controller_restrictions.append("opponent_controls")

    return result


def validate_target_type(target_id: str, game_state, target_spec: TargetSpec) -> bool:
    """Validate that a target matches the required type specification.

    Args:
        target_id: The ID of the target (permanent ID or player name)
        game_state: Current game state
        target_spec: Parsed target specification

    Returns:
        True if target is valid, False otherwise
    """
    if not target_spec.is_targeted:
        return True

    # Check if target is a permanent
    target_perm = next((p for p in game_state.battlefield if p.id == target_id), None)
    if target_perm:
        return _validate_permanent_target(target_perm, target_spec)

    # Check if target is a player
    target_player = next((p for p in game_state.players if p.name == target_id), None)
    if target_player:
        return _validate_player_target(target_player, target_spec)

    # Check if target is on the stack (for spells/abilities targeting stack objects)
    target_stack = next((s for s in game_state.stack if s.id == target_id), None)
    if target_stack:
        return _validate_stack_target(target_stack, target_spec)

    # Target not found - invalid
    return False


def _validate_permanent_target(perm, target_spec: TargetSpec) -> bool:
    """Validate a permanent target against the specification."""
    type_line = perm.card.type_line.lower()

    # Check target types
    if target_spec.target_types:
        # Must match at least one of the specified types
        type_match = False
        for ttype in target_spec.target_types:
            if ttype in type_line:
                type_match = True
                break

        # Special case: "permanent" matches any permanent type
        if "permanent" not in target_spec.target_types and not type_match:
            return False

    # Check color restrictions
    if target_spec.color_restrictions:
        card_colors = [c.upper() for c in (perm.card.colors or [])]
        # Map color names to codes (e.g., "black" -> "B")
        req_color_codes = []
        for req_color in target_spec.color_restrictions:
            code = COLOR_NAME_TO_CODE.get(req_color.lower())
            if code:
                req_color_codes.append(code)
        
        # Check if the card has at least one of the required colors
        has_required_color = False
        for req_code in req_color_codes:
            if req_code in card_colors:
                has_required_color = True
                break
        if not has_required_color:
            return False

    # Check subtype restrictions
    if target_spec.subtype_restrictions:
        has_subtype = False
        for subtype in target_spec.subtype_restrictions:
            if subtype.lower() in type_line:
                has_subtype = True
                break
        if not has_subtype:
            return False

    # Check controller restrictions
    if "you_control" in target_spec.controller_restrictions:
        from mtg_engine.engine.stack import _has_split_second
        # In context, we'd need to know who the controller of the spell is
        # For now, assume the spell's controller is checking
        # This would be passed in as a parameter in real usage
        pass

    if "opponent_controls" in target_spec.controller_restrictions:
        # Would need to check if target is controlled by an opponent
        pass

    return True


def _validate_player_target(player, target_spec: TargetSpec) -> bool:
    """Validate a player target against the specification."""
    # Players can be targeted unless there are specific restrictions
    # For now, all player targets are valid
    return True


def _validate_stack_target(stack_obj, target_spec: TargetSpec) -> bool:
    """Validate a stack object (spell/ability) target against the specification."""
    type_line = stack_obj.source_card.type_line.lower()

    # Check target types
    if target_spec.target_types:
        type_match = False
        for ttype in target_spec.target_types:
            if ttype in type_line:
                type_match = True
                break

        if "permanent" not in target_spec.target_types and not type_match:
            return False

    return True


def validate_target_count(num_targets: int, target_spec: TargetSpec) -> bool:
    """Validate that the number of targets is within the allowed range.

    Args:
        num_targets: Number of targets selected
        target_spec: Parsed target specification

    Returns:
        True if count is valid, False otherwise
    """
    if not target_spec.is_targeted:
        return True

    return target_spec.count_min <= num_targets <= target_spec.count_max


def get_valid_targets(game_state, target_spec: TargetSpec) -> list[str]:
    """Get all valid targets for a spell/ability with the given target specification.

    Args:
        game_state: Current game state
        target_spec: Parsed target specification

    Returns:
        List of valid target IDs (permanents or players)
    """
    valid_targets = []

    # Check permanents
    for perm in game_state.battlefield:
        if validate_target_type(perm.id, game_state, target_spec):
            valid_targets.append(perm.id)

    # Check players - only include if player is a valid target type
    if "player" in target_spec.target_types:
        for player in game_state.players:
            if validate_target_type(player.name, game_state, target_spec):
                valid_targets.append(player.name)

    return valid_targets
