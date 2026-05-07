"""
Mana system. REQ-A07, mana cost validation and payment.
Supports W, U, B, R, G, C (colorless), and generic (number).
Also supports hybrid, Phyrexian, snow, split, and energy mana symbols.
MANA-01: Enhanced mana pool with split/colored mana.
MANA-02: Full land mana ability support.
MANA-03: Mana production events.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from mtg_engine.models.game import GameState, ManaPool

logger = logging.getLogger(__name__)


# Regex to parse mana symbols from a mana cost string like "{2}{R}{U}"
_SYMBOL_RE = re.compile(r"\{([^}]+)\}")


def parse_mana_cost(mana_cost: str) -> dict[str, int]:
    """
    Parse a mana cost string into a dict of {symbol: count}.

    Examples:
      "{2}{R}"   → {"generic": 2, "R": 1}
      "{U}{U}"   → {"U": 2}
      "{W/U}"    → {"W/U": 1}  (hybrid)
      "{2/B}"    → {"2/B": 1}  (hybrid generic)
      "{B/P}"    → {"B/P": 1}  (Phyrexian)
      "{S}"      → {"S": 1}    (snow)
      "{15}"     → {"generic": 15}
    """
    cost: dict[str, int] = {}
    for m in _SYMBOL_RE.finditer(mana_cost or ""):
        sym = m.group(1)
        if sym.isdigit():
            cost["generic"] = cost.get("generic", 0) + int(sym)
        elif sym == "X":
            cost["X"] = cost.get("X", 0) + 1
        elif sym == "C":
            # {C} means specifically colorless mana required
            cost["C"] = cost.get("C", 0) + 1
        elif sym == "S":
            cost["S"] = cost.get("S", 0) + 1  # snow mana
        elif "/" in sym:
            # Hybrid or Phyrexian mana symbols
            cost[sym] = cost.get(sym, 0) + 1
        elif sym in ("W", "U", "B", "R", "G"):
            cost[sym] = cost.get(sym, 0) + 1
        else:
            # Unknown symbol (e.g., large generic numbers like {15})
            try:
                cost["generic"] = cost.get("generic", 0) + int(sym)
            except ValueError:
                cost[sym] = cost.get(sym, 0) + 1
    return cost


def pool_total(pool: ManaPool) -> int:
    """Return the total mana available in the pool."""
    return pool.W + pool.U + pool.B + pool.R + pool.G + pool.C


def can_pay_cost(
    pool: ManaPool,
    mana_cost: str,
    payment: dict[str, int] | None = None,
    player_life: int = 999,
) -> bool:
    """
    Check if the pool can pay the mana cost.
    If payment is provided, validate that specific payment dict against pool and cost.
    Otherwise perform a simplified sufficiency check.
    player_life is used for Phyrexian mana validation ({B/P} etc.).
    """
    cost = parse_mana_cost(mana_cost)
    if payment is not None:
        return _validate_payment(pool, cost, payment)
    return _can_pay_simple(pool, cost, player_life)


def _can_pay_simple(pool: ManaPool, cost: dict[str, int], player_life: int = 999) -> bool:
    """
    Sufficiency check: handles colored, colorless, generic, hybrid, and Phyrexian pips.
    CR 107.4b (hybrid), CR 702.99b (Phyrexian).
    """
    temp = {
        "W": pool.W,
        "U": pool.U,
        "B": pool.B,
        "R": pool.R,
        "G": pool.G,
        "C": pool.C,
    }
    life_used = 0

    # Handle hybrid and Phyrexian symbols first (keys containing "/")
    for sym, count in cost.items():
        if "/" not in sym:
            continue
        parts = sym.split("/")
        for _ in range(count):
            if parts[1].upper() == "P":
                # Phyrexian mana: pay the color OR pay 2 life
                color = parts[0].upper()
                if color in temp and temp[color] > 0:
                    temp[color] -= 1
                elif (player_life - life_used) >= 2:
                    life_used += 2
                else:
                    return False
            else:
                # Hybrid mana: pay either option
                opt_a = parts[0].upper()
                opt_b = parts[1].upper()
                # Numeric hybrid (e.g. "2/B"): pay 2 generic OR 1 of the color
                if opt_a.isdigit():
                    generic_cost = int(opt_a)
                    if opt_b in temp and temp[opt_b] > 0:
                        temp[opt_b] -= 1
                    elif sum(temp.values()) >= generic_cost:
                        # Deduct cheapest available mana for generic payment
                        remaining_generic = generic_cost
                        for c in ("W", "U", "B", "R", "G", "C"):
                            take = min(temp[c], remaining_generic)
                            temp[c] -= take
                            remaining_generic -= take
                            if remaining_generic == 0:
                                break
                        if remaining_generic > 0:
                            return False
                    else:
                        return False
                else:
                    # Color/color hybrid (e.g. "G/W"): pay either color
                    if opt_a in temp and temp[opt_a] > 0:
                        temp[opt_a] -= 1
                    elif opt_b in temp and temp[opt_b] > 0:
                        temp[opt_b] -= 1
                    else:
                        return False

    # Pay each required colored mana symbol
    for color in ("W", "U", "B", "R", "G"):
        needed = cost.get(color, 0)
        if temp[color] < needed:
            return False
        temp[color] -= needed

    # Pay colorless-specific cost ({C}): can only be paid with colorless mana
    needed_c = cost.get("C", 0)
    if temp["C"] < needed_c:
        return False
    temp["C"] -= needed_c

    # Pay snow mana cost {S}: any snow_by_color entry > 0 satisfies it
    s_needed = cost.get("S", 0)
    total_snow = sum(pool.snow_by_color.values())
    if total_snow < s_needed:
        return False
    # Deduct from snow_by_color (greedy: take from first available color)
    remaining_s = s_needed
    for color in pool.snow_by_color:
        if remaining_s <= 0:
            break
        take = min(pool.snow_by_color[color], remaining_s)
        temp[color] = temp.get(color, 0) - take  # deduct from temp pool too
        remaining_s -= take

    # Pay generic cost with any remaining mana
    generic = cost.get("generic", 0)
    remaining = sum(temp.values())
    return remaining >= generic


def _validate_payment(pool: ManaPool, cost: dict[str, int], payment: dict[str, int]) -> bool:
    """
    Validate an explicit payment dict against a pool and cost.
    Checks that:
    1. The payment does not exceed available mana in the pool.
    2. The payment satisfies all colored requirements.
    3. The remaining payment after colored requirements covers generic.
    """
    pool_dict = {
        "W": pool.W,
        "U": pool.U,
        "B": pool.B,
        "R": pool.R,
        "G": pool.G,
        "C": pool.C,
    }

    # Verify payment does not exceed pool amounts
    for color, amount in payment.items():
        if pool_dict.get(color, 0) < amount:
            return False

    # Verify colored requirements are satisfied by the payment
    temp_payment = dict(payment)
    for color in ("W", "U", "B", "R", "G"):
        needed = cost.get(color, 0)
        paid = temp_payment.get(color, 0)
        if paid < needed:
            return False
        temp_payment[color] = paid - needed

    # Verify colorless-specific requirement
    needed_c = cost.get("C", 0)
    if temp_payment.get("C", 0) < needed_c:
        return False
    temp_payment["C"] = temp_payment.get("C", 0) - needed_c

    # Verify {S} cost: snow mana must come from snow_by_color
    s_needed = cost.get("S", 0)
    if s_needed > 0:
        # Check that the payment for {S} uses snow mana
        s_paid = 0
        for color, amount in temp_payment.items():
            if color in pool.snow_by_color and pool.snow_by_color[color] > 0:
                s_paid += amount
        if s_paid < s_needed:
            return False

    # Verify generic requirement is covered by remaining payment
    generic = cost.get("generic", 0)
    remaining = sum(v for v in temp_payment.values() if v > 0)
    return remaining >= generic


def pay_cost(pool: ManaPool, mana_cost: str, payment: dict[str, int]) -> ManaPool:
    """
    Deduct payment from pool and return the new ManaPool.
    Raises ValueError if the payment is insufficient or invalid.
    """
    cost = parse_mana_cost(mana_cost)
    if not _validate_payment(pool, cost, payment):
        raise ValueError(
            f"Payment {payment} cannot satisfy cost {mana_cost!r} from pool {pool}"
        )
    new_pool = pool.model_copy(deep=True)
    for color, amount in payment.items():
        if color in ("W", "U", "B", "R", "G", "C"):
            current = getattr(new_pool, color, 0)
            setattr(new_pool, color, current - amount)
            # Also decrement snow tracking if this color has snow mana
            if color in new_pool.snow_by_color and new_pool.snow_by_color[color] > 0:
                new_pool.snow_by_color[color] = max(0, new_pool.snow_by_color[color] - amount)
                new_pool.snow = max(0, new_pool.snow - amount)
    # Clean up zero entries in snow_by_color
    new_pool.snow_by_color = {k: v for k, v in new_pool.snow_by_color.items() if v > 0}
    return new_pool


def add_mana(pool: ManaPool, symbol: str, amount: int = 1, is_snow: bool = False) -> ManaPool:
    """
    Add mana to pool. symbol must be one of: W, U, B, R, G, C.
    Returns a new ManaPool with the added mana.
    If is_snow=True, also tracks mana in snow and snow_by_color fields.
    """
    new_pool = pool.model_copy()
    if symbol in ("W", "U", "B", "R", "G", "C"):
        setattr(new_pool, symbol, getattr(new_pool, symbol) + amount)
        if is_snow:
            new_pool.snow += amount
            color_key = symbol if symbol != "C" else "C"
            new_pool.snow_by_color[color_key] = new_pool.snow_by_color.get(color_key, 0) + amount
    else:
        logger.warning("add_mana: unknown symbol %r", symbol)
    return new_pool


def empty_pool(pool: ManaPool) -> ManaPool:
    """Return an empty mana pool (all zeros)."""
    return ManaPool()


# ─── MANA-01: Mana Pool Enhancement ──────────────────────────────────────────

_COLOR_SYMBOLS = {"W", "U", "B", "R", "G"}
_SYMBOL_TO_NAME = {
    "W": "white", "U": "blue", "B": "black", "R": "red", "G": "green",
}
_NAME_TO_SYMBOL = {v: k for k, v in _SYMBOL_TO_NAME.items()}


def get_mana_colors(pool: ManaPool) -> set[str]:
    """
    Return the set of colors present in the mana pool.

    Returns color names like {"white", "blue"}.
    """
    colors: set[str] = set()
    for sym in _COLOR_SYMBOLS:
        if getattr(pool, sym, 0) > 0:
            colors.add(_SYMBOL_TO_NAME[sym])
    return colors


def pool_can_produce_color(pool: ManaPool, color: str) -> bool:
    """
    Check if the pool has at least one mana of the given color.

    Args:
        pool: Current mana pool.
        color: Color name ("white"/"blue"/"black"/"red"/"green")
                or symbol ("W"/"U"/"B"/"R"/"G").
    """
    sym = _NAME_TO_SYMBOL.get(color, color)
    sym = sym.upper()
    return sym in _COLOR_SYMBOLS and getattr(pool, sym, 0) > 0


def add_split_mana(pool: ManaPool, symbol_a: str, symbol_b: str, amount: int = 1) -> ManaPool:
    """
    Add split mana to a pool. Split mana ({W/U}) means the controller
    chooses which color to add. This helper adds both options to the
    pool for maximum flexibility (used internally by mana abilities
    that produce split mana).

    In practice, the controller picks one. For the engine, we add both
    and let cost payment choose.

    Args:
        pool: Current mana pool.
        symbol_a: First mana symbol (e.g., "W").
        symbol_b: Second mana symbol (e.g., "U").
        amount: Amount of each symbol to add.

    Returns:
        New ManaPool with split mana added.
    """
    result = pool.model_copy()
    if symbol_a in ("W", "U", "B", "R", "G", "C"):
        setattr(result, symbol_a, getattr(result, symbol_a, 0) + amount)
    if symbol_b in ("W", "U", "B", "R", "G", "C"):
        setattr(result, symbol_b, getattr(result, symbol_b, 0) + amount)
    return result


# ─── MANA-02: Mana Abilities (Land) ──────────────────────────────────────────

def parse_land_mana_production(oracle_text: str) -> list[dict[str, Any]]:
    """
    Parse mana production abilities from oracle text.

    Returns list of dicts with keys:
      - symbols: list of mana symbols produced (e.g., ["W", "U"])
      - tap_required: whether {T} is in the cost
      - sacrifice_required: whether "sacrifice" is in the cost
      - conditional: condition text if any (e.g., "if you control an Island")
      - choice: True if the ability offers a choice (e.g., "add {W} or {U}")

    Examples:
      "{T}: Add {G}" → [{"symbols": ["G"], "tap_required": True, "choice": False}]
      "{T}: Add {W} or {U}" → [{"symbols": ["W", "U"], "tap_required": True, "choice": True}]
      "When ~ enters, add {C}" → [{"symbols": ["C"], "tap_required": False, "choice": False}]
    """
    import re as _re

    results: list[dict[str, Any]] = []
    if not oracle_text:
        return results

    # Split oracle text into individual ability lines (split on newlines and periods followed by space)
    ability_lines = re.split(r"\n|(?<=[.!])\s+", oracle_text)

    for line in ability_lines:
        line = line.strip()
        if not line:
            continue

        tap_required = "{t}" in line.lower() or "{tap}" in line.lower()
        sacrifice_required = "sacrifice" in line.lower()

        # Check for conditional ("if ...")
        cond_match = _re.search(r"\bif\s+(.+?)(?:\.|$)", line, _re.IGNORECASE)
        conditional = cond_match.group(1).strip() if cond_match else None

        # Find "add {X}" patterns
        add_matches = list(_re.finditer(r"\badd\s+(\{[^}]+\})", line, _re.IGNORECASE))
        if not add_matches:
            continue

        symbols: list[str] = []
        choice = False

        # Check for "or" choice between mana symbols
        or_match = _re.search(
            r"\badd\s+\{([^}]+)\}\s+or\s+\{([^}]+)\}",
            line,
            _re.IGNORECASE,
        )
        if or_match:
            symbols = [or_match.group(1).strip("{}").upper(), or_match.group(2).strip("{}").upper()]
            choice = True
        else:
            for m in add_matches:
                sym = m.group(1).strip("{}").upper()
                symbols.append(sym)

        results.append({
            "symbols": symbols,
            "tap_required": tap_required,
            "sacrifice_required": sacrifice_required,
            "conditional": conditional,
            "choice": choice,
        })

    return results


def get_land_mana_abilities(permanent) -> list[dict[str, Any]]:
    """
    Get all mana abilities a land permanent can produce.

    Combines basic land defaults with parsed oracle text.

    Args:
        permanent: The land permanent on the battlefield.

    Returns:
        List of mana ability dicts.
    """
    card = permanent.card
    type_line = (card.type_line or "").lower()

    # Basic lands produce their default color
    basic_map = {
        "plains": ["W"],
        "island": ["U"],
        "swamp": ["B"],
        "mountain": ["R"],
        "forest": ["G"],
    }

    results: list[dict[str, Any]] = []

    for land_type, symbols in basic_map.items():
        if land_type in type_line:
            results.append({
                "symbols": symbols,
                "tap_required": True,
                "sacrifice_required": False,
                "conditional": None,
                "choice": False,
            })

    # Parse additional abilities from oracle text
    oracle_abilities = parse_land_mana_production(card.oracle_text or "")
    results.extend(oracle_abilities)

    return results


def resolve_land_mana_ability(
    game_state: GameState,
    permanent_id: str,
    ability_index: int = 0,
    chosen_symbol: str | None = None,
) -> GameState:
    """
    Resolve a land's mana ability: tap the land and add mana to the controller's pool.

    Args:
        game_state: Current game state.
        permanent_id: ID of the land permanent.
        ability_index: Index into the list of mana abilities (for lands with multiple).
        chosen_symbol: For choice abilities, which symbol to produce.

    Returns:
        Updated game state with mana added to pool.
    """
    permanent = next(
        (p for p in game_state.battlefield if p.id == permanent_id),
        None,
    )
    if permanent is None:
        logger.warning("Permanent %r not found for land mana ability", permanent_id)
        return game_state

    abilities = get_land_mana_abilities(permanent)
    if ability_index >= len(abilities):
        logger.warning("Ability index %d out of range for %s", ability_index, permanent.card.name)
        return game_state

    ability = abilities[ability_index]
    symbols = ability["symbols"]

    # Tap the land
    permanent.tapped = True

    # Determine which symbol to add
    if ability["choice"] and chosen_symbol and chosen_symbol in symbols:
        produce_symbol = chosen_symbol
    elif len(symbols) == 1:
        produce_symbol = symbols[0]
    elif len(symbols) > 1:
        produce_symbol = symbols[0]  # Default to first
    else:
        return game_state

    # Add mana to controller's pool
    controller_name = permanent.controller
    player = next(
        (p for p in game_state.players if p.name == controller_name),
        None,
    )
    if player is None:
        logger.warning("Player %r not found for land mana ability", controller_name)
        return game_state

    is_snow = any("snow" in s.lower() for s in (permanent.card.supertypes or []))
    sym_upper = produce_symbol.upper()
    if sym_upper in ("W", "U", "B", "R", "G", "C"):
        player.mana_pool = add_mana(player.mana_pool, sym_upper, 1, is_snow=is_snow)
        logger.debug(
            "Land mana: %s added {%s} to %s's pool",
            permanent.card.name, sym_upper, controller_name,
        )

    return game_state


def apply_keyword_cost_reductions(
    base_cost: str,
    cast_request,
    game_state,
    player_name: str,
) -> dict[str, int]:
    """
    Apply keyword cost modifiers (Convoke, Delve, Improvise, Affinity, Emerge)
    to the base mana cost and return the effective cost dict.
    
    Args:
        base_cost: Card's original mana cost string (e.g., "{2}{R}")
        cast_request: CastRequest with creature/artifact/card IDs for cost reduction
        game_state: GameState for permanents and card data lookup
        player_name: Player casting the spell
    
    Returns:
        Effective cost dict {symbol: count} after applying reductions
    """
    import re
    from mtg_engine.engine.zones import get_player
    
    # Start with base cost
    cost = parse_mana_cost(base_cost)
    generic_reduction = 0
    
    # CR 702.50: Convoke — tap creatures to reduce cost by {1} per creature tapped
    if cast_request.convoke_creature_ids:
        generic_reduction += len(cast_request.convoke_creature_ids)
    
    # CR 702.65: Delve — exile cards from graveyard to reduce generic cost by {1} per card
    if cast_request.delve_card_ids:
        generic_reduction += len(cast_request.delve_card_ids)
    
    # CR 702.113: Improvise — tap artifacts to reduce generic cost by {1} per artifact
    if cast_request.improvise_artifact_ids:
        generic_reduction += len(cast_request.improvise_artifact_ids)
    
    # CR 702.142: Affinity — reduce cost by {1} for each permanent on battlefield of the type
    # (Check oracle_text for affinity pattern "affinity for [type]")
    from mtg_engine.models.game import Card  # Import here to avoid circular imports
    
    card = next((c for p in game_state.players for c in p.hand if c.id == cast_request.card_id), None)
    if card:
        affinity_match = re.search(r"affinity for (.*?)(?:\.|$)", card.oracle_text or "", re.IGNORECASE)
        if affinity_match:
            affinity_type = affinity_match.group(1).strip()
            # Count matching permanents on battlefield
            for perm in game_state.battlefield:
                if perm.controller == player_name and affinity_type.lower() in perm.card.type_line.lower():
                    generic_reduction += 1
    
    # CR 702.38: Emerge — sacrifice a creature to reduce cost by that creature's mana value
    if cast_request.emerge_sacrifice_id:
        emerge_perm = next(
            (p for p in game_state.battlefield if p.id == cast_request.emerge_sacrifice_id),
            None
        )
        if emerge_perm:
            # Mana value = total generic + colored pips in mana cost
            emerge_card_cost = parse_mana_cost(emerge_perm.card.mana_cost or "{0}")
            mana_value = emerge_card_cost.get("generic", 0)
            for sym, count in emerge_card_cost.items():
                if sym not in ("generic", "X"):
                    mana_value += count if isinstance(count, int) else 0
            generic_reduction += mana_value
    
    # Apply the reduction to generic cost
    cost["generic"] = max(0, cost.get("generic", 0) - generic_reduction)
    
    return cost


def add_generic_to_cost(cost: dict[str, int], amount: int) -> dict[str, int]:
    """
    Add generic mana to a cost dict.
    
    Args:
        cost: Cost dict {symbol: count}
        amount: Number of generic mana to add
    
    Returns:
        Updated cost dict
    """
    new_cost = dict(cost)
    new_cost["generic"] = new_cost.get("generic", 0) + amount
    return new_cost


def format_cost_dict_to_string(cost: dict[str, int]) -> str:
    """
    Convert a cost dict back to a mana cost string.
    
    Args:
        cost: Cost dict {symbol: count} (e.g., {"generic": 2, "R": 1})
    
    Returns:
        Mana cost string (e.g., "{2}{R}")
    """
    result = []
    
    # Format generic mana first
    if cost.get("generic", 0) > 0:
        result.append(f"{{{cost['generic']}}}")
    
    # Format X value if present
    if cost.get("X", 0) > 0:
        for _ in range(cost["X"]):
            result.append("{X}")
    
    # Format colored and special mana symbols
    for symbol in ("W", "U", "B", "R", "G", "C", "S"):
        count = cost.get(symbol, 0)
        for _ in range(count):
            result.append(f"{{{symbol}}}")
    
    # Format hybrid and Phyrexian symbols
    for symbol, count in sorted(cost.items()):
        if "/" in symbol:
            for _ in range(count):
                result.append(f"{{{symbol}}}")
    
    return "".join(result)


# ─── Mana Ability Detection (CR 605) ──────────────────────────────────────────

def is_mana_ability(oracle_text: str, is_loyalty: bool = False) -> bool:
    """
    Determine if an ability is a mana ability per CR 605.
    
    A mana ability must meet ALL of the following criteria (CR 605.1a):
    1. It doesn't require a target (no "target" keyword in text)
    2. It could add mana to a player's mana pool when it resolves
    3. It's not a loyalty ability
    
    CR 605.1b: Triggered mana abilities also don't require targets, 
    but this function primarily checks activated abilities.
    
    Examples of mana abilities:
      - "{T}: Add {G}" (Forest)
      - "{T}: Add {G} or {U}" (dual land)
      - "{1}, {T}: Add {C}" (man land)
    
    Examples of non-mana abilities:
      - "{T}: Draw a card" (has effect other than mana)
      - "{1}: Add {G}, target creature gets +2/+2" (has target)
      - "+1: Draw a card" (loyalty ability)
      - "{T}: Scry 1, add {G}" (has non-mana effect)
    
    Note: The ability is a mana ability even if it can't produce mana
    in the current game state (CR 605.2).
    """
    # Rule: Not a loyalty ability
    if is_loyalty:
        return False
    
    text = oracle_text or ""
    text_lower = text.lower()
    
    # Rule: Must not have "target" in text (CR 605.5a)
    # Check for "target" keyword as a standalone word
    if re.search(r'\btarget\b', text_lower):
        return False
    
    # Extract the effect part (after the first ":") to avoid matching activation costs
    if ":" in text:
        effect = text.split(":", 1)[1]
        effect_lower = effect.lower()
    else:
        effect = text
        effect_lower = text_lower
    
    # Rule: Must be capable of adding mana
    # Look for mana production patterns in the effect part:
    # - "add {color}" where color is W, U, B, R, G, or C
    # - "add {X}{Y}" pattern (hybrid mana)
    # - "add [number] mana"
    # - "add {C}" (colorless mana)
    
    # Pattern 1: "add {X}" where X is a mana symbol (use case-insensitive flag)
    if re.search(r'\badd\s+\{[wubrg]/[wubrg]\}', effect_lower):
        return True
    if re.search(r'\badd\s+\{[wubrgcs]\}', effect_lower):
        return True
    if re.search(r'\badd\s+\{[0-9]/[wubrgcs]\}', effect_lower):
        return True
    if re.search(r'\badd\s+\{[wubrgcs]/[0-9]\}', effect_lower):
        return True
    
    # Pattern 3: "add {N} mana" or "add N mana"
    if re.search(r'\badd\s+[0-9]+\s+mana\b', effect_lower):
        return True
    
    # Pattern 4: "add one mana"
    if re.search(r'\badd\s+one\s+mana\b', effect_lower):
        return True
    
    # Pattern 5: "add {X} mana"
    if re.search(r'\badd\s+\{x\}\s+mana\b', effect_lower):
        return True
    if re.search(r'\badd\s+mana\b', effect_lower):
        return True
    
    # Pattern 6: "produce {color} mana"
    if re.search(r'\bproduce\s+\{[wubrg]\}\s+mana\b', effect_lower):
        return True
    
    return False


def resolve_mana_ability(game_state: GameState, permanent_id: str, ability_text: str) -> GameState:
    """
    Resolve a mana ability immediately (bypassing the stack per CR 605.3b).
    
    This function extracts mana production from the ability text and adds it
    to the active player's mana pool. The ability resolves immediately without
    going on the stack.
    
    Args:
        game_state: Current game state
        permanent_id: ID of the permanent with the ability
        ability_text: The full text of the ability being resolved
    
    Returns:
        Updated game state with mana added to pool
    """
    import logging
    import re
    
    logger = logging.getLogger(__name__)
    
    # Extract the effect part (after the first ":") to avoid matching activation costs
    if ":" in ability_text:
        effect = ability_text.split(":", 1)[1]
        effect_lower = effect.lower()
    else:
        effect = ability_text
        effect_lower = ability_text.lower()
    
    # Find the permanent
    permanent = next((p for p in game_state.battlefield if p.id == permanent_id), None)
    if permanent is None:
        logger.warning("Permanent %r not found for mana ability resolution", permanent_id)
        return game_state
    
    # Determine controller (who gets the mana)
    controller_name = permanent.controller
    player = next((p for p in game_state.players if p.name == controller_name), None)
    if player is None:
        logger.warning("Player %r not found for mana ability resolution", controller_name)
        return game_state
    
    # Parse mana production from ability text
    mana_added = []
    
    # Pattern: "add {X} or {Y}" - choice (check before single pattern)
    choice_match = re.search(r'\badd\s+(\{[wubrgcs]\})\s+or\s+(\{[wubrgcs]\})', effect_lower)
    if choice_match:
        # For deterministic behavior, choose first option
        symbol = choice_match.group(1).strip('{}').upper()
        if symbol in ('W', 'U', 'B', 'R', 'G', 'C'):
            mana_added.append(symbol)
    
    # Pattern: "add {X}" - single mana symbol (use finditer for multiple occurrences)
    if not choice_match:
        for match in re.finditer(r'\badd\s+(\{[wubrgcs]\})', effect_lower):
            symbol = match.group(1).strip('{}').upper()
            if symbol in ('W', 'U', 'B', 'R', 'G', 'C'):
                mana_added.append(symbol)
    
    # Pattern: "add {N} mana" - generic mana (convert to colorless)
    generic_match = re.search(r'\badd\s+(\d+)\s+mana\b', effect_lower)
    if generic_match:
        amount = int(generic_match.group(1))
        mana_added.extend(['C'] * amount)
    
    # Pattern: "add one mana" - single mana
    if re.search(r'\badd\s+one\s+mana\b', effect_lower):
        # Default to colorless for "add one mana"
        mana_added.append('C')
    
    # Pattern: "add {X} mana" - X variable
    x_match = re.search(r'\badd\s+\{x\}\s+mana\b', effect_lower)
    if x_match:
        # For {X} without value, default to one colorless
        mana_added.append('C')
    
    # Pattern: "produce {X} mana"
    for match in re.finditer(r'\bproduce\s+(\{[wubrgcs]\})\s+mana\b', effect_lower):
        symbol = match.group(1).strip('{}').upper()
        if symbol in ('W', 'U', 'B', 'R', 'G', 'C'):
            mana_added.append(symbol)
    
    # Add mana to player's pool
    # US23: Check if this is a snow permanent (has "Snow" supertype)
    is_snow = "Snow" in permanent.card.supertypes
    for symbol in mana_added:
        player.mana_pool = add_mana(player.mana_pool, symbol, 1, is_snow=is_snow)
        logger.debug("Mana ability resolved: %s added %s to %s's mana pool (is_snow=%s)", 
                     permanent.card.name, symbol, controller_name, is_snow)
    
    return game_state
