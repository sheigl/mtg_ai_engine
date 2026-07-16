"""
APP-05: Draft / Sealed Simulation Engine.

Pure functions for pack generation, draft session lifecycle, pick orchestration,
bot auto-pick scoring, and sealed pool deck construction. Reuses APP-02's
build_deck() pipeline for post-draft/sealed deck building.

NOTE (MINOR 8): _draft_sessions is an in-memory dict that is NOT thread-safe.
For production deployments with concurrent requests, replace with Redis-backed
sessions or a thread-local store protected by asyncio.Lock / threading.Lock.
"""
from __future__ import annotations

import hashlib
import logging
import random
import time
import uuid
from typing import Optional

from pydantic import BaseModel, Field

from mtg_engine.ai.card_eval import (
    compute_cmc,
    estimate_card_quality,
)
from mtg_engine.models.game import Card

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rarity distribution weights for pack generation
# Standard booster: ~60% common, 25% uncommon, 10% rare, 5% mythic
# ---------------------------------------------------------------------------
RARITY_WEIGHTS: dict[str, float] = {
    "common": 60.0,
    "uncommon": 25.0,
    "rare": 10.0,
    "mythic": 5.0,
}

PACK_SIZE = 15

# ---------------------------------------------------------------------------
# Session storage limits (CRITICAL 2: LRU eviction)
# ---------------------------------------------------------------------------
MAX_DRAFT_SESSIONS = 100


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class PlayerDraftState(BaseModel):
    """Per-player state during a draft or sealed session."""
    player_name: str
    strategy: str = "midrange"
    is_human: bool = False
    drafted_cards: list[Card] = Field(default_factory=list)
    picks_per_round: dict[int, Optional[str]] = Field(default_factory=dict)


class DraftSession(BaseModel):
    """Full state of a draft session."""
    session_id: str
    players: list[PlayerDraftState]
    packs_per_player: int
    set_code: str
    format_name: str
    seed: int
    state: str = "pending"  # "pending" | "drafting" | "completed"
    current_round: int = 0
    picks_this_round: int = 0
    total_picks: int = 0
    packs: list[list[Card]] = Field(default_factory=list)
    results: Optional["DraftResults"] = None
    created_at: float = Field(default_factory=time.time)


class DraftPickInfo(BaseModel):
    """Information about the current pick in a draft."""
    round_number: int
    picks_this_round: int
    player_name: str
    available_cards: list[str]  # card names in current pack


class InternalDraftStateResponse(BaseModel):
    """Internal draft state representation (engine-side, distinct from API DraftStateResponse)."""
    session_id: str
    state: str
    round_number: int
    picks_this_round: int
    total_picks: int
    players: list[PlayerDraftState]
    current_pick_info: Optional[DraftPickInfo] = None


class DraftResults(BaseModel):
    """Final results after a draft or sealed session completes."""
    player_decks: dict[str, dict]  # player_name -> {deck: [...], sideboard: [...]}
    draft_stats: dict[str, dict]   # player_name -> {cards_per_round: {...}}


class SealedResults(BaseModel):
    """Final results for a sealed session."""
    players: list[dict]  # [{name, pool: [...], deck: [...], sideboard: [...]}]


# ---------------------------------------------------------------------------
# In-memory session store
# ---------------------------------------------------------------------------

_draft_sessions: dict[str, DraftSession] = {}


def _get_session(session_id: str) -> DraftSession:
    """Retrieve a draft session by ID. Raises ValueError if not found."""
    try:
        return _draft_sessions[session_id]
    except KeyError as exc:
        raise ValueError(f"Draft session '{session_id}' not found") from exc


def _evict_old_sessions() -> None:
    """Evict oldest sessions when we exceed MAX_DRAFT_SESSIONS.

    Priority for eviction:
    1. Completed sessions first (sorted by created_at ascending)
    2. Then pending/drafting sessions if still over limit
    """
    if len(_draft_sessions) < MAX_DRAFT_SESSIONS:
        return

    # Sort all sessions by created_at (oldest first)
    sorted_sessions = sorted(
        _draft_sessions.items(),
        key=lambda item: item[1].created_at,
    )

    # First pass: evict completed sessions
    for sid, session in sorted_sessions:
        if len(_draft_sessions) <= MAX_DRAFT_SESSIONS:
            break
        if session.state == "completed":
            del _draft_sessions[sid]
            logger.debug("APP-05: Evicted completed draft session %s", sid)

    # Second pass: evict oldest pending/drafting sessions if still over limit
    for sid, session in sorted_sessions:
        if len(_draft_sessions) <= MAX_DRAFT_SESSIONS:
            break
        if sid in _draft_sessions and session.state != "completed":
            del _draft_sessions[sid]
            logger.debug("APP-05: Evicted active draft session %s", sid)


# ---------------------------------------------------------------------------
# Pack Generation
# ---------------------------------------------------------------------------

def _generate_pack(set_code: str, rng: random.Random) -> list[Card]:
    """Generate a booster pack of 15 cards from the specified set.

    Uses ScryfallClient.search_cards() to get all cards in the set, then
    performs weighted random selection based on rarity distribution.

    Falls back to randomized pool from all cached cards if set not found.

    Raises:
        ValueError: If no cards are available in the local cache for this set
                    or any fallback source.
    """
    from mtg_engine.card_data.scryfall import ScryfallClient

    client = ScryfallClient()

    # Fetch all cards for this set (paginate through full set)
    set_cards: list[Card] = []
    page = 1
    per_page = 100
    while True:
        try:
            cards, total = client.search_cards(set_code=set_code, page=page, per_page=per_page)
            set_cards.extend(cards)
            if len(set_cards) >= total:
                break
            page += 1
        except Exception as exc:
            logger.warning("Failed to fetch set '%s' from cache: %s", set_code, exc)
            break

    # Fallback: if no cards for this set, use all cached cards
    if not set_cards:
        try:
            all_cards, _ = client.search_cards(per_page=100)
            page = 2
            while len(all_cards) > 0 and (page - 1) * per_page < _:
                more, _ = client.search_cards(page=page, per_page=per_page)
                if not more:
                    break
                all_cards.extend(more)
                page += 1
            set_cards = all_cards
        except Exception as exc:
            logger.warning("Failed to fetch any cached cards for fallback: %s", exc)

    # CRITICAL 1: Raise error instead of returning empty list
    if not set_cards:
        raise ValueError(f"No cards available for set '{set_code}' in local cache")

    # Group by rarity for weighted selection
    rarity_buckets: dict[str, list[Card]] = {"common": [], "uncommon": [], "rare": [], "mythic": []}
    for card in set_cards:
        r = (card.rarity or "").lower()
        if r == "mythical":
            r = "mythic"
        if r in rarity_buckets:
            rarity_buckets[r].append(card)
        else:
            rarity_buckets["common"].append(card)

    # If any bucket is empty, redistribute from non-empty buckets
    for key in list(rarity_buckets.keys()):
        if not rarity_buckets[key]:
            # Find a source bucket with cards
            for src_key in ("mythic", "rare", "uncommon", "common"):
                if rarity_buckets[src_key] and src_key != key:
                    # Move some cards to the empty bucket
                    n = min(len(rarity_buckets[src_key]) // 2, 5)
                    rarity_buckets[key] = rarity_buckets[src_key][:n]
                    break

    pack: list[Card] = []
    for _ in range(PACK_SIZE):
        # Choose rarity based on weights
        chosen_rarity = rng.choices(
            list(RARITY_WEIGHTS.keys()),
            weights=list(RARITY_WEIGHTS.values()),
            k=1,
        )[0]

        bucket = rarity_buckets.get(chosen_rarity, [])
        if not bucket:
            # Fallback to any non-empty bucket
            for b in ("common", "uncommon", "rare", "mythic"):
                if rarity_buckets[b]:
                    bucket = rarity_buckets[b]
                    break

        if bucket:
            pack.append(rng.choice(bucket))

    return pack


# ---------------------------------------------------------------------------
# Draft Session Lifecycle
# ---------------------------------------------------------------------------

def _start_draft_session(
    players: list[str],
    packs_per_player: int,
    set_code: str,
    format_name: str,
    strategy: str = "midrange",
    human_player_name: Optional[str] = None,
    seed: Optional[int] = None,
) -> DraftSession:
    """Create a new draft session and generate initial packs.

    Args:
        players: List of player names (2-8 recommended).
        packs_per_player: Number of rounds/packs per player (typically 3).
        set_code: Scryfall set code for pack generation.
        format_name: MTG format for post-draft deck building.
        strategy: Default strategy for bot players.
        human_player_name: Name of the human player (if any).
        seed: Random seed for reproducibility.

    Returns:
        DraftSession in "drafting" state with initial packs generated.

    Raises:
        ValueError: On invalid input, unknown format, or pack generation failure.
    """
    if len(players) < 2:
        raise ValueError("Draft requires at least 2 players")
    if packs_per_player < 1 or packs_per_player > 8:
        raise ValueError("packs_per_player must be between 1 and 8")

    # MAJOR 4: Validate format name against known formats
    from mtg_engine.engine.formats import FORMAT_VALIDATORS
    if format_name.lower().strip() not in FORMAT_VALIDATORS:
        raise ValueError(
            f"Unknown format '{format_name}'. Valid formats: {list(FORMAT_VALIDATORS.keys())}"
        )

    # Deterministic seed
    if seed is None:
        pool_hash = hashlib.sha256(
            (",".join(sorted(players)) + set_code + format_name).encode()
        ).hexdigest()
        seed = int(pool_hash[:8], 16)

    rng = random.Random(seed)

    # Create player states
    player_states: list[PlayerDraftState] = []
    for name in players:
        player_states.append(
            PlayerDraftState(
                player_name=name,
                strategy=strategy,
                is_human=(name == human_player_name),
            )
        )

    session_id = str(uuid.uuid4())

    # CRITICAL 1: Wrap pack generation in try/except to propagate errors
    initial_packs: list[list[Card]] = []
    for i in range(len(players)):
        try:
            pack = _generate_pack(set_code, rng)
        except ValueError as exc:
            raise ValueError(
                f"Failed to generate pack {i + 1}/{len(players)}: {exc}"
            ) from exc
        initial_packs.append(pack)

    session = DraftSession(
        session_id=session_id,
        players=player_states,
        packs_per_player=packs_per_player,
        set_code=set_code,
        format_name=format_name,
        seed=seed,
        state="drafting",
        current_round=1,
        picks_this_round=0,
        total_picks=0,
        packs=initial_packs,
    )

    # CRITICAL 2: Evict old sessions before adding new one
    _evict_old_sessions()
    _draft_sessions[session_id] = session
    logger.info("APP-05: Draft session %s started with %d players, %d rounds",
                session_id, len(players), packs_per_player)

    return session


def _get_current_picker(session: DraftSession) -> int | None:
    """Return the index of the player whose turn it is to pick next.

    Pick order rotates each round. In round 1, picks go left (index 0, 1, 2...).
    Each subsequent round starts from a different player.
    """
    n_players = len(session.players)
    if n_players == 0:
        return None

    # Starting index for this round rotates based on pack passing direction
    # Odd rounds pass left (packs move to higher indices), even rounds pass right
    if session.current_round % 2 == 1:
        start_index = (session.current_round - 1) % n_players
    else:
        start_index = (n_players - (session.current_round - 1)) % n_players

    picker_index = (start_index + session.picks_this_round) % n_players
    return picker_index


def _get_pack_for_picker(session: DraftSession, picker_index: int) -> list[Card]:
    """Return the pack currently in front of the given player.

    Pack passing follows standard limited rules:
    - Odd rounds pass left (packs shift toward higher indices)
    - Even rounds pass right (packs shift toward lower indices)
    """
    n_players = len(session.players)
    if session.current_round % 2 == 1:
        # Odd round: packs passed left, pack at index (picker + offset) is in front of picker
        offset = (session.current_round - 1) % n_players
        pack_index = (picker_index + offset) % n_players
    else:
        # Even round: packs passed right
        offset = (n_players - session.current_round) % n_players
        pack_index = (picker_index + offset) % n_players

    return session.packs[pack_index]


def _process_pick(
    session_id: str,
    player_name: str,
    card_name: str,
) -> tuple[DraftSession, Card]:
    """Process a pick from the current pack.

    Validates that the player is the current picker and the card is in their pack.
    Removes the card from the pack, records the pick, advances state.

    NOTE (MAJOR 4): This function intentionally mutates the session in-place rather
    than using model_copy pure transforms. Draft sessions are lightweight lifecycle
    objects stored in an in-memory dict — not GameState objects that flow through
    the engine's immutable transform pipeline. The caller is responsible for storing
    the returned session back into _draft_sessions (e.g., via _resolve_bot_picks or
    API handlers). This trade-off avoids deep-copy overhead on every pick in a tight
    draft loop with many rounds and players.

    Returns updated session and the picked card.
    Raises ValueError on validation failures.
    """
    session = _get_session(session_id)

    if session.state != "drafting":
        raise ValueError(f"Draft is not in 'drafting' state (current: {session.state})")

    # Find player index
    try:
        picker_idx = next(i for i, p in enumerate(session.players) if p.player_name == player_name)
    except StopIteration as exc:
        raise ValueError(f"Player '{player_name}' not found in draft session") from exc

    # Verify this is the current picker's turn
    current_picker = _get_current_picker(session)
    if current_picker is None or current_picker != picker_idx:
        current_name = session.players[current_picker].player_name if current_picker is not None else "none"
        raise ValueError(
            f"It is not '{player_name}''s turn to pick. Current picker: '{current_name}'"
        )

    # Get the pack in front of this player
    pack = _get_pack_for_picker(session, picker_idx)

    # CRITICAL 3: Find and validate card exists BEFORE modifying anything
    picked_card: Optional[Card] = None
    pick_index = -1
    for i, card in enumerate(pack):
        if card.name == card_name:
            picked_card = card
            pick_index = i
            break

    if picked_card is None:
        available = [c.name for c in pack]
        raise ValueError(
            f"Card '{card_name}' not found in current pack. Available: {available}"
        )

    # Now remove the validated card from the pack
    pack.pop(pick_index)

    # Record the pick
    session.players[picker_idx].drafted_cards.append(picked_card)
    session.players[picker_idx].picks_per_round[session.current_round] = card_name
    session.picks_this_round += 1
    session.total_picks += 1

    # Check if round is complete
    n_players = len(session.players)
    if session.picks_this_round >= n_players:
        # Round complete — advance to next round or finish draft
        session.picks_this_round = 0
        if session.current_round >= session.packs_per_player:
            # Draft complete — build decks
            session = _complete_draft(session)
        else:
            # Generate new packs for the next round and advance
            rng = random.Random(session.seed + session.current_round + 1)
            new_packs: list[list[Card]] = []
            for _ in range(n_players):
                pack = _generate_pack(session.set_code, rng)
                new_packs.append(pack)
            session.packs = new_packs
            session.current_round += 1

    logger.info("APP-05: %s picked '%s' (round %d, pick %d/%d)",
                player_name, card_name, session.current_round,
                session.picks_this_round + 1 if session.state == "drafting" else n_players,
                n_players)

    return session, picked_card


def _complete_draft(session: DraftSession) -> DraftSession:
    """Complete the draft and build decks for all players.

    Each player's drafted pool is passed to APP-02's build_deck() with
    'modern' format (limited format). Returns updated session with results.
    """
    from mtg_engine.ai.deck_builder import build_deck

    player_decks: dict[str, dict] = {}
    draft_stats: dict[str, dict] = {}

    for ps in session.players:
        # Build deck from drafted cards using limited format
        result = build_deck(
            card_pool=ps.drafted_cards,
            format_name="modern",  # Limited uses modern-style rules (4 of each)
            strategy=ps.strategy,
            seed=session.seed,
        )

        player_decks[ps.player_name] = {
            "deck": result["deck"],
            "sideboard": result["sideboard"],
            "validation": result.get("validation", {}),
        }

        draft_stats[ps.player_name] = {
            "cards_per_round": ps.picks_per_round,
            "total_cards": len(ps.drafted_cards),
            "strategy": ps.strategy,
        }

    session.state = "completed"
    session.results = DraftResults(
        player_decks=player_decks,
        draft_stats=draft_stats,
    )

    _draft_sessions[session.session_id] = session
    logger.info("APP-05: Draft %s completed — decks built for %d players",
                session.session_id, len(session.players))

    return session


# ---------------------------------------------------------------------------
# Bot Auto-Pick Logic
# ---------------------------------------------------------------------------

def _score_card_for_draft(card: Card, drafted_cards: list[Card], strategy: str) -> float:
    """Score a card for draft picking with synergy considerations.

    Score = base_quality * strategy_multiplier + color_synergy_bonus + cmc_curve_fit.
    """
    # Base quality from card_eval
    card_dict = {
        "name": card.name,
        "oracle_text": card.oracle_text or "",
        "mana_cost": card.mana_cost or "",
        "keywords": card.keywords or [],
        "type_line": card.type_line or "",
        "power": card.power or "0",
        "toughness": card.toughness or "0",
    }
    base_quality = estimate_card_quality(card_dict)

    # Strategy multiplier from deck_builder weights
    from mtg_engine.ai.deck_builder import _classify_card, STRATEGY_WEIGHTS, _cmc_curve_bonus

    category = _classify_card(card)
    weights = STRATEGY_WEIGHTS.get(strategy, STRATEGY_WEIGHTS["midrange"])
    strategy_mult = weights.get(category, 1.0)
    curve_bonus = _cmc_curve_bonus(compute_cmc(card.mana_cost), strategy)

    # Color synergy bonus: +0.5 per matching color in drafted cards
    card_colors = set(c.upper() for c in (card.colors or []) if c.upper() != "C")
    drafted_color_counts: dict[str, int] = {}
    for dc in drafted_cards:
        for c in (dc.colors or []):
            cu = c.upper()
            if cu != "C":
                drafted_color_counts[cu] = drafted_color_counts.get(cu, 0) + 1

    # Find dominant colors (colors with >= 2 cards drafted)
    dominant_colors = {c for c, count in drafted_color_counts.items() if count >= 2}
    color_synergy = len(card_colors & dominant_colors) * 0.5

    return base_quality * strategy_mult * curve_bonus + color_synergy


def _bot_auto_pick(session: DraftSession, player_name: str) -> tuple[DraftSession, Card]:
    """Bot auto-picks the highest-scoring card from its current pack.

    Uses deterministic scoring with session seed for reproducibility.

    Args:
        session: Direct reference to the draft session (MAJOR 3 fix).
        player_name: Name of the bot player making the pick.
    """
    # MAJOR 3: Use passed session directly instead of store lookup
    # Find player index
    try:
        picker_idx = next(i for i, p in enumerate(session.players) if p.player_name == player_name)
    except StopIteration as exc:
        raise ValueError(f"Player '{player_name}' not found") from exc

    pack = _get_pack_for_picker(session, picker_idx)
    if not pack:
        raise ValueError("No cards available in current pack")

    drafted_cards = session.players[picker_idx].drafted_cards
    strategy = session.players[picker_idx].strategy

    # Score all cards and pick the best
    scored = [(card, _score_card_for_draft(card, drafted_cards, strategy)) for card in pack]

    # Deterministic tie-breaking via seed
    rng = random.Random(session.seed + session.current_round)
    scored.sort(key=lambda x: (-x[1], x[0].name))

    best_card, best_score = scored[0]
    logger.info("APP-05: Bot '%s' auto-picked '%s' (score %.2f)",
                player_name, best_card.name, best_score)

    return _process_pick(session.session_id, player_name, best_card.name)


# ---------------------------------------------------------------------------
# Process all bot picks for the current round
# ---------------------------------------------------------------------------

def _resolve_bot_picks(session: DraftSession) -> DraftSession:
    """Resolve all remaining bot picks in the current state.

    Processes picks one at a time, resolving bot auto-picks until either:
    - A human player needs to pick (returns session with pending human pick)
    - The draft completes (returns completed session)
    """
    while session.state == "drafting":
        picker_idx = _get_current_picker(session)
        if picker_idx is None:
            break

        current_player = session.players[picker_idx]
        if current_player.is_human:
            # Human needs to pick — stop and return
            break

        # MAJOR 3: Pass session directly instead of session_id
        session, _ = _bot_auto_pick(session, current_player.player_name)
        _draft_sessions[session.session_id] = session

    return session


# ---------------------------------------------------------------------------
# Sealed Mode
# ---------------------------------------------------------------------------

def _start_sealed_session(
    players: list[str],
    set_code: str,
    format_name: str = "modern",
    strategy: str = "midrange",
    seed: Optional[int] = None,
) -> dict:
    """Start a sealed pool simulation.

    Each player gets one 15-card pack (sealed pool), then decks are built
    automatically via APP-02's build_deck().

    Returns immediate results with pools and constructed decks.
    """
    if len(players) < 1:
        raise ValueError("Sealed requires at least 1 player")

    # CRITICAL 1 fix: Validate format name against known formats (same guard as _start_draft_session)
    from mtg_engine.engine.formats import FORMAT_VALIDATORS
    if format_name.lower().strip() not in FORMAT_VALIDATORS:
        raise ValueError(
            f"Unknown format '{format_name}'. Valid formats: {list(FORMAT_VALIDATORS.keys())}"
        )

    # Deterministic seed
    if seed is None:
        pool_hash = hashlib.sha256(
            (",".join(sorted(players)) + set_code).encode()
        ).hexdigest()
        seed = int(pool_hash[:8], 16)

    rng = random.Random(seed)

    from mtg_engine.ai.deck_builder import build_deck

    player_results: list[dict] = []

    for name in players:
        # MAJOR 5: Wrap pack generation in try/except with player context
        try:
            pool = _generate_pack(set_code, rng)
        except ValueError as exc:
            raise ValueError(f"Failed to generate sealed pool for {name}: {exc}") from exc

        # Build deck from sealed pool
        result = build_deck(
            card_pool=pool,
            format_name=format_name,
            strategy=strategy,
            seed=seed,
        )

        player_results.append({
            "name": name,
            "pool": [c.name for c in pool],
            "deck": result["deck"],
            "sideboard": result["sideboard"],
            "validation": result.get("validation", {}),
        })

    logger.info("APP-05: Sealed session created for %d players from set '%s'",
                len(players), set_code)

    return {
        "players": player_results,
        "set_code": set_code,
        "format_name": format_name,
        "seed": seed,
    }


# ---------------------------------------------------------------------------
# Helper: Get current pick info for API responses
# ---------------------------------------------------------------------------

def _get_current_pick_info(session: DraftSession) -> Optional[DraftPickInfo]:
    """Build DraftPickInfo for the current state of a draft."""
    if session.state != "drafting":
        return None

    picker_idx = _get_current_picker(session)
    if picker_idx is None:
        return None

    pack = _get_pack_for_picker(session, picker_idx)
    player_name = session.players[picker_idx].player_name

    return DraftPickInfo(
        round_number=session.current_round,
        picks_this_round=session.picks_this_round + 1,
        player_name=player_name,
        available_cards=[c.name for c in pack],
    )


# ---------------------------------------------------------------------------
# Cleanup helper (for tests)
# ---------------------------------------------------------------------------

def _clear_sessions() -> None:
    """Clear all draft sessions. Used primarily in tests."""
    _draft_sessions.clear()
