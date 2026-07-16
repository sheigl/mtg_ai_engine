"""
APP-02: Deck Building AI — stateless deck construction engine.

Filter → Score → Select → Validate pipeline that takes a card pool, format,
and strategy description, then produces a legal, optimized MTG deck.
"""
import hashlib
import logging
import random
from typing import Optional

from mtg_engine.ai.card_eval import (
    compute_cmc,
    estimate_card_quality,
    is_board_wipe,
    is_counterspell,
    is_draw_spell,
    is_ramp,
    is_removal_spell,
)
from mtg_engine.engine.formats.banned import get_format_banned_list, is_banned, is_restricted
from mtg_engine.models.game import Card

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Basic lands exempt from singleton enforcement (CR 905.2)
# ---------------------------------------------------------------------------

BASIC_LANDS: set[str] = {
    "plains", "island", "swamp", "mountain", "forest",
    "snow-covered plains", "snow-covered island",
    "snow-covered swamp", "snow-covered mountain",
    "snow-covered forest", "wastes",
}


# ---------------------------------------------------------------------------
# Strategy weights: category → multiplier per strategy
# ---------------------------------------------------------------------------

STRATEGY_WEIGHTS: dict[str, dict[str, float]] = {
    "aggro": {
        "creature_low": 1.5,   # CMC 0-2
        "creature_mid": 1.0,   # CMC 3-4
        "creature_high": 0.5,  # CMC 5+
        "removal": 1.0,
        "counterspell": 0.7,
        "draw": 1.0,
        "ramp": 1.2,
        "board_wipe": 0.5,
        "land": 1.0,
        "other": 1.0,
    },
    "control": {
        "creature_low": 0.7,
        "creature_mid": 1.0,
        "creature_high": 1.2,
        "removal": 1.5,
        "counterspell": 1.5,
        "draw": 1.3,
        "ramp": 1.0,
        "board_wipe": 1.4,
        "land": 1.0,
        "other": 1.0,
    },
    "midrange": {
        "creature_low": 1.0,
        "creature_mid": 1.2,
        "creature_high": 1.0,
        "removal": 1.1,
        "counterspell": 1.0,
        "draw": 1.2,
        "ramp": 1.1,
        "board_wipe": 1.0,
        "land": 1.0,
        "other": 1.0,
    },
    "combo": {
        "creature_low": 1.3,
        "creature_mid": 1.0,
        "creature_high": 1.4,
        "removal": 0.8,
        "counterspell": 1.2,
        "draw": 1.5,
        "ramp": 1.3,
        "board_wipe": 0.6,
        "land": 1.0,
        "other": 1.0,
    },
}


# ---------------------------------------------------------------------------
# CMC curve bonuses per strategy
# ---------------------------------------------------------------------------

def _cmc_curve_bonus(cmc: float, strategy: str) -> float:
    """Return the CMC curve bonus multiplier for a given strategy."""
    if strategy == "aggro":
        return 1.3 if cmc <= 2 else 1.0
    elif strategy == "control":
        return 1.2 if 3 <= cmc <= 5 else 1.0
    elif strategy == "midrange":
        return 1.1 if 2 <= cmc <= 4 else 1.0
    elif strategy == "combo":
        return 1.2 if cmc >= 3 else 1.0
    return 1.0


# ---------------------------------------------------------------------------
# Card category classification
# ---------------------------------------------------------------------------

def _classify_card(card: Card | dict) -> str:
    """Classify a card into a scoring category based on type and oracle text."""
    if isinstance(card, dict):
        type_line = (card.get("type_line") or "").lower()
    else:
        type_line = (card.type_line or "").lower()

    # Land first — lands are always "land" regardless of other properties
    if "land" in type_line:
        return "land"

    is_creature = "creature" in type_line

    if not is_creature:
        # Non-creature classification based on oracle text
        card_dict = _card_to_dict(card)
        if is_removal_spell(card_dict):
            return "removal"
        if is_counterspell(card_dict):
            return "counterspell"
        if is_board_wipe(card_dict):
            return "board_wipe"
        if is_draw_spell(card_dict):
            return "draw"
        if is_ramp(card_dict):
            return "ramp"
        return "other"

    # Creature classification based on CMC
    cmc = _get_cmc(card)
    if cmc <= 2:
        return "creature_low"
    elif cmc <= 4:
        return "creature_mid"
    else:
        return "creature_high"


def _card_to_dict(card: Card | dict) -> dict:
    """Convert a Card model or dict to the format expected by card_eval helpers."""
    if isinstance(card, dict):
        return card
    return {
        "name": card.name,
        "oracle_text": card.oracle_text or "",
        "mana_cost": card.mana_cost or "",
        "keywords": card.keywords or [],
        "type_line": card.type_line or "",
        "power": card.power or "0",
        "toughness": card.toughness or "0",
    }


def _get_cmc(card: Card | dict) -> float:
    """Get the CMC of a card, computing from mana_cost if needed."""
    if isinstance(card, Card):
        if card.cmc > 0:
            return card.cmc
        return compute_cmc(card.mana_cost)
    # dict format
    cmc = card.get("cmc")
    if cmc and float(cmc) > 0:
        return float(cmc)
    return compute_cmc(card.get("mana_cost"))


# ---------------------------------------------------------------------------
# Filter stage
# ---------------------------------------------------------------------------

def _filter_card_pool(
    cards: list[Card],
    format_name: str,
    commander_names: Optional[list[str]] = None,
) -> list[Card]:
    """
    Stage 1 — Filter.

    Remove banned cards, enforce singleton for Legacy/Vintage/Commander/Brawl,
    apply legality window filtering, and handle Commander color identity.
    Returns a deduplicated list of legal cards (each unique name appears once).
    """
    fmt = format_name.lower().strip()
    is_singleton_format = fmt in ("legacy", "vintage", "commander", "brawl")

    # Determine commander color identity for filtering
    from mtg_engine.engine.formats.commander import get_color_identity

    commander_color_identity: set[str] = set()
    if commander_names and fmt == "commander":
        for card in cards:
            if card.name in commander_names:
                cid = set(c.upper() for c in get_color_identity(card))
                commander_color_identity.update(cid)

    # Collect banned names once
    banned_set = {name.lower() for name in _get_banned_list(fmt)}

    seen_names: dict[str, Card] = {}  # lowercase name -> first legal card (singleton only)
    result: list[Card] = []           # non-singleton formats keep all copies

    for card in cards:
        name_lower = card.name.strip().lower()

        # Skip banned cards
        if name_lower in banned_set:
            continue

        # Pauper: only common cards are legal (CR 109.5)
        if fmt == "pauper" and (card.rarity or "").lower() != "common":
            continue

        # For singleton formats, only keep the first occurrence of each name
        # Basic lands are exempt from singleton (CR 905.2)
        if is_singleton_format and name_lower not in BASIC_LANDS and name_lower in seen_names:
            continue

        # Commander color identity filter
        if commander_color_identity:
            card_cid = set(c.upper() for c in get_color_identity(card))
            # Cards with no color identity are always legal; cards must be within identity
            if card_cid and not card_cid.issubset(commander_color_identity):
                continue

        if is_singleton_format:
            if name_lower in BASIC_LANDS:
                # Basic lands exempt from singleton dedup (CR 905.2)
                result.append(card)
            else:
                seen_names[name_lower] = card
        else:
            result.append(card)

    return result + list(seen_names.values()) if is_singleton_format else result


def _get_banned_list(fmt: str) -> set[str]:
    """Get banned names for a format, using the existing banned module."""
    return get_format_banned_list(fmt)


# ---------------------------------------------------------------------------
# Score stage
# ---------------------------------------------------------------------------

def _score_card(card: Card | dict, strategy: str) -> float:
    """
    Stage 2 — Score.

    Composite score = baseline_quality × strategy_multiplier × cmc_curve_bonus.
    Returns a non-negative float.
    """
    card_dict = _card_to_dict(card)
    baseline = estimate_card_quality(card_dict)
    category = _classify_card(card)
    cmc = _get_cmc(card)

    weights = STRATEGY_WEIGHTS.get(strategy, STRATEGY_WEIGHTS["midrange"])
    strategy_mult = weights.get(category, 1.0)
    curve_bonus = _cmc_curve_bonus(cmc, strategy)

    return baseline * strategy_mult * curve_bonus


# ---------------------------------------------------------------------------
# Select stage
# ---------------------------------------------------------------------------

def _select_deck(
    scored_cards: list[tuple[Card | dict, float]],
    format_name: str,
    commander_names: Optional[list[str]] = None,
    rng: random.Random | None = None,
) -> tuple[list[dict], list[dict], dict[str, Card]]:
    """
    Stage 3 — Select.

    Sort by composite score descending, greedily pick top N respecting format
    constraints. Commander(s) locked first if provided. Sideboard fills from
    remaining cards up to 15.

    Returns (deck_entries, sideboard_entries, deck_card_map) where each entry is
    {"name": str, "quantity": int} and deck_card_map maps lowercase name → original Card.
    """
    fmt = format_name.lower().strip()
    rng = rng or random.Random(42)

    # Determine deck size minimums
    if fmt == "commander" or fmt == "brawl":
        deck_min = 100 if fmt == "commander" else 60
    else:
        deck_min = 60

    is_singleton_format = fmt in ("legacy", "vintage", "commander", "brawl")

    # Separate commanders from the pool if provided
    commander_set: set[str] = set()
    if commander_names and (fmt == "commander" or fmt == "brawl"):
        for name in commander_names:
            commander_set.add(name.strip().lower())

    # Lock commanders first
    deck_entries: dict[str, int] = {}  # lowercase name -> quantity
    remaining: list[tuple[Card | dict, float]] = []

    for card, score in scored_cards:
        name_lower = card["name"].strip().lower() if isinstance(card, dict) else card.name.strip().lower()
        if name_lower in commander_set:
            deck_entries[name_lower] = 1
        else:
            remaining.append((card, score))

    # Sort remaining by score descending (stable sort preserves original order for ties)
    remaining.sort(key=lambda x: (-x[1], x[0]["name"] if isinstance(x[0], dict) else x[0].name))

    # Greedily fill deck to minimum size
    current_deck_count = sum(deck_entries.values())

    # Count available land copies in the pool for reservation
    _land_name_counts: dict[str, int] = {}
    for card, _ in remaining:
        tl = (card["type_line"] if isinstance(card, dict) else (card.type_line or "")).lower()
        if "land" not in tl:
            continue
        cn = (card["name"] if isinstance(card, dict) else card.name).strip().lower()
        _land_name_counts[cn] = _land_name_counts.get(cn, 0) + 1

    available_land_copies = 0
    for cn, count in _land_name_counts.items():
        if is_singleton_format and cn not in BASIC_LANDS:
            # Singleton format: 1 copy per non-basic land name
            available_land_copies += 1
        elif cn in BASIC_LANDS:
            # Basic lands always allow up to 4 copies (CR 905.2)
            available_land_copies += min(count, 4)
        else:
            # Non-singleton format: up to 4 per name
            available_land_copies += min(count, 4)

    # Reserve slots for land balancing: target ~24% lands
    land_reserve = min(max(int(deck_min * 0.24), 1), available_land_copies)
    greedy_target = deck_min - land_reserve

    for card, score in remaining:
        if current_deck_count >= deck_min:
            break

        name_lower = card["name"].strip().lower() if isinstance(card, dict) else card.name.strip().lower()
        tl = (card["type_line"] if isinstance(card, dict) else (card.type_line or "")).lower()
        is_land = "land" in tl

        # Determine max copies for this card in the format
        # Basic lands exempt from singleton constraint (CR 905.2)
        if name_lower in BASIC_LANDS:
            max_copies = 4
        elif is_singleton_format:
            max_copies = 1
        else:
            max_copies = 4

        already_in_deck = deck_entries.get(name_lower, 0)
        can_add = max_copies - already_in_deck

        if can_add <= 0:
            continue

        # For non-land cards in greedy phase, stop at greedy_target to reserve space for lands
        if not is_land and current_deck_count >= greedy_target:
            continue

        add_count = min(can_add, deck_min - current_deck_count)

        if add_count > 0:
            deck_entries[name_lower] = already_in_deck + add_count
            current_deck_count += add_count

    # Land balancing: ensure at least 24% of the deck are lands
    land_names_in_deck: set[str] = set()
    for card, _ in scored_cards:
        cn = (card["name"] if isinstance(card, dict) else card.name).strip().lower()
        tl = (card["type_line"] if isinstance(card, dict) else (card.type_line or "")).lower()
        if "land" in tl and cn in deck_entries:
            land_names_in_deck.add(cn)

    # Count total land copies in deck
    land_copies = sum(deck_entries.get(n, 0) for n in land_names_in_deck)
    land_target = max(int(current_deck_count * 0.24), 1)

    if land_copies < land_target:
        needed_lands = land_target - land_copies
        # Find remaining lands not yet in deck (sorted by score descending)
        available_lands = [
            (card, score) for card, score in remaining
            if "land" in (card["type_line"] if isinstance(card, dict) else (card.type_line or "")).lower()
        ]
        # already sorted by score from earlier sort
        for card, score in available_lands:
            if needed_lands <= 0:
                break
            name_lower = card["name"].strip().lower() if isinstance(card, dict) else card.name.strip().lower()

            # Basic lands exempt from singleton constraint (CR 905.2)
            if name_lower in BASIC_LANDS:
                max_copies = 4
            elif is_singleton_format:
                max_copies = 1
            else:
                max_copies = 4

            already_in_deck = deck_entries.get(name_lower, 0)
            can_add = min(max_copies - already_in_deck, needed_lands)

            if can_add > 0:
                deck_entries[name_lower] = already_in_deck + can_add
                current_deck_count += can_add
                land_copies += can_add
                needed_lands -= can_add

    # Build sideboard from remaining cards (non-Commander/Brawl formats only)
    sideboard_entries: dict[str, int] = {}
    sb_target = 15 if fmt not in ("commander", "brawl") else 0
    sb_count = 0

    for card, score in remaining:
        if sb_count >= sb_target:
            break

        name_lower = card["name"].strip().lower() if isinstance(card, dict) else card.name.strip().lower()

        # Skip cards already in main deck at max copies
        already_in_deck = deck_entries.get(name_lower, 0)
        if is_singleton_format and already_in_deck >= 1:
            continue
        if not is_singleton_format and already_in_deck >= 4:
            continue

        # For singleton formats sideboard can also only have 1 copy total
        max_total = 1 if is_singleton_format else 4  # main+sideboard combined cap
        sb_add = min(max_total - already_in_deck, sb_target - sb_count)

        if sb_add > 0 and (already_in_deck + sideboard_entries.get(name_lower, 0)) < max_total:
            sideboard_entries[name_lower] = sb_add
            sb_count += sb_add

    # Convert to list format with original names
    def _to_list(entries: dict[str, int], scored_cards_map: Optional[dict[str, str]] = None) -> list[dict]:
        """Convert entries dict to list of {name, quantity} dicts."""
        result = []
        for name_lower, qty in sorted(entries.items()):
            # Find original case name from scored cards
            orig_name = name_lower
            for card, _ in scored_cards_map or []:
                cn = card["name"] if isinstance(card, dict) else card.name
                if cn.strip().lower() == name_lower:
                    orig_name = cn
                    break
            result.append({"name": orig_name, "quantity": qty})
        return result

    deck_list = _to_list(deck_entries, scored_cards)
    sideboard_list = _to_list(sideboard_entries, scored_cards)

    # Build card map: lowercase name → original Card object for validation
    deck_card_map: dict[str, Card] = {}
    for card, _ in scored_cards:
        if isinstance(card, Card):
            cn = card.name.strip().lower()
            if cn in deck_entries and cn not in deck_card_map:
                deck_card_map[cn] = card

    return deck_list, sideboard_list, deck_card_map


# ---------------------------------------------------------------------------
# Validate stage
# ---------------------------------------------------------------------------

def _validate_constructed_deck(
    deck_entries: list[dict],
    format_name: str,
    commander_names: Optional[list[str]] = None,
    card_map: Optional[dict[str, Card]] = None,
) -> tuple[bool, list[str]]:
    """
    Stage 4 — Validate.

    Run FMT-01's validate_deck() on the constructed deck entries.
    Uses original Card objects from card_map if available (preserves set_code, rarity, etc.).
    Returns (is_valid, violations).
    """
    from mtg_engine.engine.formats import validate_deck as fmt_validate

    # Expand entries into Card list for validation using original card objects
    cards: list[Card] = []
    cm = card_map or {}
    for entry in deck_entries:
        name = entry["name"]
        qty = entry.get("quantity", 1)
        key = name.strip().lower()
        if key in cm:
            # Use original Card with full metadata (set_code, rarity, etc.)
            cards.extend([cm[key]] * qty)
        else:
            # Fallback to bare Card if not found in map
            for _ in range(qty):
                cards.append(Card(name=name))

    # Build commander Card list from card_map if available
    commanders: Optional[list[Card]] = None
    if commander_names:
        commanders = []
        for n in commander_names:
            key = n.strip().lower()
            if key in cm:
                commanders.append(cm[key])
            else:
                commanders.append(Card(name=n))

    return fmt_validate(cards, format_name, commanders)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_deck(
    card_pool: list[Card],
    format_name: str,
    strategy: str = "midrange",
    commander_names: Optional[list[str]] = None,
    seed: Optional[int] = None,
) -> dict:
    """
    Build a legal, optimized deck from a card pool.

    Pipeline: Filter → Score → Select → Validate.

    Args:
        card_pool: List of Card objects to choose from.
        format_name: MTG format (e.g., "modern", "legacy", "commander").
        strategy: One of "aggro", "control", "midrange", "combo".
        commander_names: Optional list of commander names for Commander/Brawl.
        seed: Optional random seed for deterministic results.

    Returns:
        Dict with keys: deck, sideboard, validation.
    """
    fmt = format_name.lower().strip()
    strat = strategy.lower().strip() if strategy else "midrange"

    # Validate inputs
    from mtg_engine.engine.formats import FORMAT_VALIDATORS
    if fmt not in FORMAT_VALIDATORS:
        return {
            "deck": [],
            "sideboard": [],
            "validation": {"valid": False, "violations": [f"Unknown format: {format_name}"], "format": format_name},
        }

    if strat not in STRATEGY_WEIGHTS:
        logger.warning("Unknown strategy '%s', defaulting to midrange", strat)
        strat = "midrange"

    # Deterministic seed
    if seed is None:
        pool_hash = hashlib.sha256(
            (fmt + strat + ",".join(sorted(c.name for c in card_pool))).encode()
        ).hexdigest()
        seed = int(pool_hash[:8], 16)
    rng = random.Random(seed)

    # Stage 1: Filter
    legal_cards = _filter_card_pool(card_pool, fmt, commander_names)
    logger.info("APP-02: Filtered %d cards from pool of %d for format '%s'", len(legal_cards), len(card_pool), fmt)

    if not legal_cards:
        return {
            "deck": [],
            "sideboard": [],
            "validation": {"valid": False, "violations": ["No legal cards in the card pool"], "format": format_name},
        }

    # Stage 2: Score
    scored = [(card, _score_card(card, strat)) for card in legal_cards]

    # Shuffle ties deterministically (cards with same score get randomized order)
    # Group by score bucket and shuffle within each bucket
    from itertools import groupby
    scored.sort(key=lambda x: -x[1])
    shuffled_scored: list[tuple[Card, float]] = []
    for _, group in groupby(scored, key=lambda x: x[1]):
        bucket = list(group)
        rng.shuffle(bucket)
        shuffled_scored.extend(bucket)

    # Stage 3: Select
    deck_entries, sideboard_entries, deck_card_map = _select_deck(
        shuffled_scored, fmt, commander_names, rng=rng
    )

    logger.info("APP-02: Selected %d main deck cards and %d sideboard cards",
                len(deck_entries), len(sideboard_entries))

    # Stage 4: Validate (pass original card references for full metadata)
    is_valid, violations = _validate_constructed_deck(
        deck_entries, fmt, commander_names, card_map=deck_card_map
    )

    return {
        "deck": deck_entries,
        "sideboard": sideboard_entries,
        "validation": {
            "valid": is_valid,
            "violations": violations,
            "format": format_name,
        },
    }
