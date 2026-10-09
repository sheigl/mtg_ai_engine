"""Game action endpoints. REQ-API01–REQ-API05."""
import logging
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from mtg_engine.api.game_manager import get_manager
from mtg_engine.persistence.player_defaults import get_merged_player_settings_sync
from mtg_engine.models.game import GameState, Phase, Step
from mtg_engine.models.actions import (
    CastRequest, ActivateRequest, PlayLandRequest,
    DeclareAttackersRequest, DeclareBlockersRequest, OrderBlockersRequest,
    AssignCombatDamageRequest, ChoiceRequest, PassRequest,
    PutTriggerRequest, SpecialActionRequest,
    LegalAction, ForetellRequest,
)
from mtg_engine.engine.sba import check_and_apply_sbas
from mtg_engine.engine.turn_manager import pass_priority
from mtg_engine.engine.stack import cast_spell
from mtg_engine.engine.zones import get_player, put_permanent_onto_battlefield
from mtg_engine.engine.combat import (
    declare_attackers, declare_blockers, order_blockers, assign_combat_damage
)
from mtg_engine.engine.triggers import put_trigger_on_stack
from mtg_engine.card_data.deck_loader import load_deck, load_commander_deck

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/game", tags=["game"])


# ─── Response models ─────────────────────────────────────────────────────────

class GameSummary(BaseModel):
    """Lightweight projection of GameState for the game list view."""
    game_id: str
    player1_name: str
    player2_name: str
    format: str
    turn: int
    phase: str
    step: str
    is_game_over: bool
    winner: str | None = None
    active_player: str | None = None
    priority_holder: str | None = None
    has_human_player: bool = False
    human_player_name: str | None = None
    # Deck identity (033-deck-randomizer)
    player1_deck_name: str | None = None
    player2_deck_name: str | None = None
    player1_color_identity: list[str] = Field(default_factory=list)
    player2_color_identity: list[str] = Field(default_factory=list)
    # Series mode (032-game-series)
    series_id: str | None = None
    series_game_number: int = 1
    series_total: int = 1
    series_score: dict[str, int] = Field(default_factory=dict)


# ─── Request bodies ───────────────────────────────────────────────────────────

class CreateGameRequest(BaseModel):
    player1_name: str = "player_1"
    player2_name: str = "player_2"
    player1_type: str = "ai"
    player2_type: str = "ai"
    deck1: list[str]   # card names
    deck2: list[str]
    seed: int | None = None
    verbose: bool = False
    debug: bool = False
    format: str = "standard"
    commander1: str | None = None
    commander2: str | None = None
    ai_model: str = ""
    ai_base_url: str = ""
    ai_enable_thinking: bool | None = None
    observer_model: str | None = None
    observer_url: str | None = None
    observer_enabled: bool = True
    max_turns: int = 0

    @model_validator(mode="after")
    def _validate(self) -> "CreateGameRequest":
        if self.player1_type == "llm":
            self.player1_type = "ai"
        if self.player2_type == "llm":
            self.player2_type = "ai"
        valid = {"human", "ai", "heuristic"}
        if self.player1_type not in valid:
            raise ValueError(f"player1_type must be one of {valid}")
        if self.player2_type not in valid:
            raise ValueError(f"player2_type must be one of {valid}")
        return self


class VerboseToggleRequest(BaseModel):
    enabled: bool


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ok(data: Any) -> dict:
    """REQ-API02: successful response."""
    if isinstance(data, GameState):
        return {"data": data.model_dump()}
    return {"data": data}


def _err(msg: str, code: str, status: int = 422) -> HTTPException:
    """REQ-API03: error response."""
    return HTTPException(status_code=status, detail={"error": msg, "error_code": code})


def _get_gs(game_id: str) -> GameState:
    """Retrieve game state or raise 404. REQ-API04."""
    mgr = get_manager()
    try:
        return mgr.get(game_id)
    except KeyError:
        raise _err("Game not found", "GAME_NOT_FOUND", 404)


def _run_sbas(gs: GameState) -> GameState:
    """Run state-based actions and return updated state."""
    gs, _ = check_and_apply_sbas(gs)
    return gs


def _get_recorder_safe(game_id: str, mgr=None):
    """Return the recorder for a game, or None if not available."""
    try:
        return (mgr or get_manager()).get_recorder(game_id)
    except KeyError:
        return None


def _validate_targets(
    game_state: GameState,
    targets: list[str],
    source_card: Any,
    controller: str,
) -> None:
    """
    Validate that all targets are legal per CR 702.11 (hexproof), 702.18 (shroud),
    and 702.16 (protection). Raises ValueError if any target is illegal.
    """
    from mtg_engine.engine.combat import (
        _has_hexproof_or_shroud, _has_protection_from, _get_source_qualities, _has_keyword
    )

    for target_id in targets:
        # Check if target is a permanent
        target_perm = next((p for p in game_state.battlefield if p.id == target_id), None)
        if target_perm:
            # Check protection from everything first (CR 702.16) - blocks all targeting
            if any("protection from everything" in kw.lower() for kw in target_perm.card.keywords):
                raise ValueError(
                    f"{target_perm.card.name} has protection from everything — "
                    f"cannot be targeted by {source_card.name}"
                )
            
            # Check other protection qualities (CR 702.16) - before hexproof/shroud
            source_qualities = _get_source_qualities(source_card, controller, target_perm.controller)
            
            for quality in source_qualities:
                if _has_protection_from(target_perm, quality):
                    raise ValueError(
                        f"{target_perm.card.name} has protection from {quality} — "
                        f"cannot be targeted by {source_card.name}"
                    )
            
            # Hexproof: opponents cannot target (CR 702.11)
            if target_perm.controller != controller and _has_hexproof_or_shroud(target_perm):
                raise ValueError(
                    f"{target_perm.card.name} has hexproof or shroud — "
                    f"cannot be targeted by {controller}"
                )
            
            # Shroud: no player (including controller) can target (CR 702.18)
            if _has_keyword(target_perm, "shroud"):
                raise ValueError(
                    f"{target_perm.card.name} has hexproof or shroud — "
                    f"cannot be targeted by {controller}"
                )
        else:
            # Check if target is a player
            target_player = next((p for p in game_state.players if p.name == target_id), None)
            if target_player:
                # Protection from players doesn't exist in current MTG rules
                # But we should still validate hexproof/shroud if they could apply
                pass


def _record_transition_events(
    recorder,
    gs_after: GameState,
    before_turn: int,
    before_phase,
    before_step,
    before_game_over: bool,
    before_life: dict,
) -> None:
    """Record phase transitions, life changes, and game end detected by comparing states."""
    turn = gs_after.turn
    phase = gs_after.phase.value
    step = gs_after.step.value

    # Phase / turn transition
    if gs_after.turn != before_turn or gs_after.phase != before_phase or gs_after.step != before_step:
        recorder.record_phase_change(turn, phase, step, active_player=gs_after.active_player)

    # Life changes
    for p in gs_after.players:
        old_life = before_life.get(p.name, p.life)
        if p.life != old_life:
            delta = p.life - old_life
            source = "unknown"
            recorder.record_life_change(p.name, delta, source, p.life, turn, phase, step)

    # Game over
    if not before_game_over and gs_after.is_game_over:
        winner = gs_after.winner or "unknown"
        # Derive reason from player states
        reason = "unknown"
        for p in gs_after.players:
            if p.has_lost:
                if p.life <= 0:
                    reason = "life_total_zero"
                elif p.poison_counters >= 10:
                    reason = "poison_counters"
                elif not p.library:
                    reason = "decked"
                break
        recorder.record_game_end(winner, reason, turn, phase, step)


# ─── Game lifecycle ───────────────────────────────────────────────────────────

@router.get("")
def list_games() -> dict:
    """GET /game — list all active games."""
    mgr = get_manager()
    summaries = []
    for game_id, gs in mgr._games.items():
        series_info = {}
        if gs.series_id:
            try:
                sc = mgr.get_series(gs.series_id)
                series_info = {
                    "series_id": gs.series_id,
                    "series_game_number": len(sc.results) + (1 if not gs.is_game_over else 0),
                    "series_total": sc.total_games,
                    "series_score": sc.wins,
                }
            except KeyError:
                pass
        summaries.append(GameSummary(
            game_id=game_id,
            player1_name=gs.players[0].name,
            player2_name=gs.players[1].name,
            format=gs.format,
            turn=gs.turn,
            phase=gs.phase.value,
            step=gs.step.value,
            is_game_over=gs.is_game_over,
            winner=gs.winner,
            active_player=gs.active_player,
            priority_holder=gs.priority_holder,
            has_human_player=bool(gs.human_player_name),
            human_player_name=gs.human_player_name,
            player1_deck_name=gs.players[0].deck_name,
            player2_deck_name=gs.players[1].deck_name,
            player1_color_identity=gs.players[0].color_identity,
            player2_color_identity=gs.players[1].color_identity,
            **series_info,
        ).model_dump())
    return {"data": summaries}


@router.post("")
def create_game(req: CreateGameRequest) -> dict:
    """POST /game — create a new game. REQ-G01"""
    mgr = get_manager()

    # Feature 028: Fetch and merge player defaults (Feature 028)
    final_player1_type = req.player1_type
    final_player2_type = req.player2_type
    try:
        p1_request_values: dict[str, Any] = {}
        p2_request_values: dict[str, Any] = {}
        if req.player1_type in ("ai", "heuristic"):
            p1_request_values = {
                "base_url": req.ai_base_url or "",
                "model": req.ai_model or "",
                "enable_thinking": req.ai_enable_thinking,
            }
        if req.player2_type in ("ai", "heuristic"):
            p2_request_values = {
                "base_url": req.ai_base_url or "",
                "model": req.ai_model or "",
                "enable_thinking": req.ai_enable_thinking,
            }
        merged_p1 = get_merged_player_settings_sync(req.player1_type, p1_request_values if p1_request_values else None)
        merged_p2 = get_merged_player_settings_sync(req.player2_type, p2_request_values if p2_request_values else None)
        if p1_request_values:
            req.ai_base_url = merged_p1.get("base_url", req.ai_base_url) or ""
            req.ai_model = merged_p1.get("model", req.ai_model) or ""
            if req.ai_enable_thinking is None:
                req.ai_enable_thinking = merged_p1.get("enable_thinking")
        if p2_request_values:
            if not p1_request_values:
                req.ai_base_url = merged_p2.get("base_url", req.ai_base_url) or ""
                req.ai_model = merged_p2.get("model", req.ai_model) or ""
                if req.ai_enable_thinking is None:
                    req.ai_enable_thinking = merged_p2.get("enable_thinking")
            final_player1_type = merged_p1.get("player_type", req.player1_type) if "player_type" in merged_p1 else req.player1_type
            final_player2_type = merged_p2.get("player_type", req.player2_type) if "player_type" in merged_p2 else req.player2_type
    except Exception:
        pass

    if req.format == "commander":
        if not req.commander1 or not req.commander2:
            raise _err("Commander format requires commander1 and commander2", "INVALID_COMMANDER")
        # US19 (T045): Partner commander validation — validate partner pairs
        # Partners allow 2 commanders when both have Partner or matching "Partner with [Name]"
        # This is validated after loading the cards below
        deck1_list = list(req.deck1)
        if req.commander1 not in deck1_list:
            deck1_list.append(req.commander1)
        try:
            deck1_cards, commander1_card = load_commander_deck(deck1_list, req.commander1)
        except ValueError as e:
            msg = str(e)
            code = (
                "SINGLETON_VIOLATION" if "Singleton" in msg
                else "COLOR_IDENTITY_VIOLATION" if "Color identity" in msg
                else "INVALID_COMMANDER" if "legendary" in msg.lower() or "not found" in msg
                else "DECK_LOAD_ERROR"
            )
            raise _err(msg, code)
        deck2_list = list(req.deck2)
        if req.commander2 not in deck2_list:
            deck2_list.append(req.commander2)
        try:
            deck2_cards, commander2_card = load_commander_deck(deck2_list, req.commander2)
        except ValueError as e:
            msg = str(e)
            code = (
                "SINGLETON_VIOLATION" if "Singleton" in msg
                else "COLOR_IDENTITY_VIOLATION" if "Color identity" in msg
                else "INVALID_COMMANDER" if "legendary" in msg.lower() or "not found" in msg
                else "DECK_LOAD_ERROR"
            )
            raise _err(msg, code)
        # US19 (T045): Partner validation — if both commanders are different cards,
        # validate they have Partner or "Partner with [Name]" keywords
        if commander1_card.name != commander2_card.name:
            # Note: If only one is named (no partner), load_commander_deck already validates
            # Here we additionally check Partner with [Name] pairs
            import re as _re_partner
            c1_oracle = (commander1_card.oracle_text or "").lower()
            c2_oracle = (commander2_card.oracle_text or "").lower()
            c1_has_partner = "partner" in (commander1_card.keywords or []) or "partner" in c1_oracle
            c2_has_partner = "partner" in (commander2_card.keywords or []) or "partner" in c2_oracle
            # "Partner with [Name]" must reference each other
            pw_match1 = _re_partner.search(r'partner with (.+)', c1_oracle)
            pw_match2 = _re_partner.search(r'partner with (.+)', c2_oracle)
            if pw_match1 and pw_match2:
                # Both have "Partner with" — verify they reference each other
                if (commander2_card.name.lower() not in pw_match1.group(1)
                        or commander1_card.name.lower() not in pw_match2.group(1)):
                    raise _err(
                        f"Partner mismatch: {commander1_card.name!r} and {commander2_card.name!r} "
                        "do not reference each other with 'Partner with'",
                        "INVALID_COMMANDER",
                    )
            elif not (c1_has_partner and c2_has_partner):
                raise _err(
                    f"Two different commanders require both to have the Partner ability "
                    f"({commander1_card.name!r} and {commander2_card.name!r})",
                    "INVALID_COMMANDER",
                )
        gs = mgr.create_game(
            req.player1_name, req.player2_name,
            deck1_cards, deck2_cards,
            seed=req.seed,
            verbose=req.verbose,
            debug=req.debug,
            format="commander",
            commander1_card=commander1_card,
            commander2_card=commander2_card,
            player1_type=final_player1_type,
            player2_type=final_player2_type,
        )
    else:
        try:
            deck1_cards = load_deck(req.deck1)
            deck2_cards = load_deck(req.deck2)
        except Exception as e:
            raise _err(str(e), "DECK_LOAD_ERROR")
        gs = mgr.create_game(
            req.player1_name, req.player2_name,
            deck1_cards, deck2_cards,
            seed=req.seed,
            verbose=req.verbose,
            debug=req.debug,
            player1_type=final_player1_type,
            player2_type=final_player2_type,
        )
    # US16 T148: Wire zone-change triggers for death/ETB detection (CR 603.2)
    from mtg_engine.engine.triggers import initialize_triggers
    initialize_triggers(gs)
    return _ok(gs)


@router.get("/{game_id}")
def get_game(game_id: str) -> dict:
    """GET /game/{game_id} — full game state. REQ-G02"""
    return _ok(_get_gs(game_id))


def _write_to_mongodb(game_id: str, gs: GameState) -> None:
    """Write all four export documents to MongoDB. REQ-P03."""
    from mtg_engine.export.store import get_export_store, delete_export_store
    from mtg_engine.export.outcome import build_outcome
    try:
        import pymongo
        client = pymongo.MongoClient("mongodb://server.home:27017/", serverSelectionTimeoutMS=1000)
        db = client["mtg_training_data"]
        store = get_export_store(game_id)
        store.snapshots.flush()

        snapshots = store.snapshots.get_all()
        transcript = store.transcript.get_all()
        qa_pairs = store.rules_qa.get_all()
        outcome = build_outcome(gs, len(snapshots), len(transcript))

        if snapshots:
            db["snapshots"].insert_many([s.model_dump() for s in snapshots])
        if transcript:
            db["transcripts"].insert_one({"game_id": game_id, "entries": [e.model_dump() for e in transcript]})
        if qa_pairs:
            db["rules_qa"].insert_many([p.model_dump() for p in qa_pairs])
        db["outcomes"].insert_one(outcome.model_dump())

        logger.info("Exported game %s to MongoDB (%d snapshots, %d transcript entries, %d Q&A)",
                    game_id, len(snapshots), len(transcript), len(qa_pairs))
        delete_export_store(game_id)
    except Exception as e:
        logger.warning("MongoDB export failed for game %s: %s", game_id, e)
        # REQ-P04: don't fail the DELETE if export fails


@router.delete("/{game_id}")
def delete_game(game_id: str) -> dict:
    """DELETE /game/{game_id} — end game, trigger export. REQ-G03"""
    mgr = get_manager()
    try:
        gs = mgr.delete(game_id)
    except KeyError:
        raise _err("Game not found", "GAME_NOT_FOUND", 404)
    _write_to_mongodb(game_id, gs)

    # APP-06: Update player stats asynchronously after game completion
    try:
        import asyncio
        from mtg_engine.api.routers.player_stats import update_stats_for_game_completion
        from mtg_engine.persistence.mongo_client import get_main_loop
        loop = get_main_loop() or asyncio.get_event_loop()
        if loop is None or not loop.is_running():
            logger.warning("No running event loop — stats update for game %s will be skipped", game_id)
            return {"data": {"game_id": game_id, "status": "deleted", "winner": gs.winner}}
        asyncio.run_coroutine_threadsafe(update_stats_for_game_completion(game_id, gs), loop)
    except Exception:
        logger.warning("Failed to schedule stats update for game %s", game_id, exc_info=True)

    return {"data": {"game_id": game_id, "status": "deleted", "winner": gs.winner}}


# ─── Verbose logging toggle ───────────────────────────────────────────────────

@router.post("/{game_id}/verbose")
def toggle_verbose(game_id: str, req: VerboseToggleRequest) -> dict:
    """POST /game/{game_id}/verbose — enable or disable play-by-play logging."""
    mgr = get_manager()
    _get_gs(game_id)  # raise 404 if game not found
    try:
        mgr.set_verbose(game_id, req.enabled)
    except KeyError:
        raise _err("Game not found", "GAME_NOT_FOUND", 404)
    return _ok({"game_id": game_id, "verbose_enabled": req.enabled})


# ─── Priority and turn ────────────────────────────────────────────────────────

@router.post("/{game_id}/pass")
def pass_priority_endpoint(game_id: str, req: PassRequest) -> dict:
    """POST /game/{game_id}/pass — pass priority. REQ-T02"""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    player = gs.priority_holder
    # Save before-state for event detection
    before_turn = gs.turn
    before_phase = gs.phase
    before_step = gs.step
    before_game_over = gs.is_game_over
    before_life = {p.name: p.life for p in gs.players}

    try:
        gs = pass_priority(gs, player)
        gs = _run_sbas(gs)
    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        if recorder:
            _record_transition_events(
                recorder, gs,
                before_turn, before_phase, before_step,
                before_game_over, before_life,
            )
    return _ok(gs)


# ─── Land play ────────────────────────────────────────────────────────────────

@router.post("/{game_id}/play-land")
def play_land(game_id: str, req: PlayLandRequest) -> dict:
    """POST /game/{game_id}/play-land. REQ-A01, REQ-A02"""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    land_player = gs.priority_holder
    land_turn, land_phase, land_step = gs.turn, gs.phase.value, gs.step.value
    land_card_name: str = ""

    try:
        player = get_player(gs, gs.priority_holder)

        # Validate: main phase, stack empty, active player, one land per turn
        if gs.active_player != gs.priority_holder:
            raise ValueError("Only the active player can play a land")
        if gs.step != Step.MAIN:
            raise ValueError("Lands can only be played during the main phase")
        if gs.stack:
            raise ValueError("Cannot play a land while the stack is non-empty")
        if player.lands_played_this_turn >= 1:
            raise ValueError("Already played a land this turn")

        # Find the land in hand
        card = next((c for c in player.hand if c.id == req.card_id), None)
        if card is None:
            raise ValueError(f"Card {req.card_id!r} not found in hand")
        from mtg_engine.ability.keywords.fortify import Fortify
        if not Fortify.is_land_card(card):
            raise ValueError(f"{card.name} is not a land")
        land_card_name = card.name

        # Move from hand to battlefield (REQ-A02: no stack)
        player.hand[:] = [c for c in player.hand if c.id != req.card_id]
        gs, _ = put_permanent_onto_battlefield(gs, card, gs.active_player, tapped=False, from_zone="hand")
        player.lands_played_this_turn += 1
        gs = _run_sbas(gs)

    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        if recorder and land_card_name:
            recorder.record_play_land(
                land_player, land_card_name,
                land_turn, land_phase, land_step,
            )
    return _ok(gs)


# ─── Casting ─────────────────────────────────────────────────────────────────

import re as _re_mana
_MANA_SYM_RE = _re_mana.compile(r'\{([WUBRGC1-9XS])\}')
_MANA_ADD_LAND_RE = _re_mana.compile(r'add\s+\{([WUBRGC])\}', _re_mana.IGNORECASE)


def _auto_tap_and_build_payment(gs: "GameState", caster: str, mana_cost_str: str) -> tuple["GameState", dict]:
    """Tap untapped mana sources to pay mana_cost_str, return (updated_gs, payment_dict).

    Used when the human player submits a cast with no explicit mana_payment.
    Taps lands greedily (colorless-last) until the pool can satisfy the cost.
    """
    from mtg_engine.engine.mana import add_mana, can_pay_cost
    from mtg_engine.card_data.ability_parser import parse_oracle_text, ActivatedAbility

    player = get_player(gs, caster)

    # Build list of (permanent, mana_symbol) for all untapped mana sources
    sources: list[tuple[object, str]] = []
    for perm in gs.battlefield:
        if perm.controller != caster or perm.tapped:
            continue
        is_creature = "creature" in perm.card.type_line.lower()
        if is_creature and perm.summoning_sick:
            continue
        abilities = parse_oracle_text(perm.card.oracle_text or "", perm.card.type_line)
        for ab in abilities:
            if isinstance(ab, ActivatedAbility) and "{T}" in ab.cost:
                m = _MANA_ADD_LAND_RE.search(ab.effect)
                if m:
                    sources.append((perm, m.group(1).upper()))

    # Sort: colored first so we tap colored lands when needed, generic last
    sources.sort(key=lambda x: x[1] == "C")

    # Tap sources until pool can pay the cost
    for perm, sym in sources:
        if can_pay_cost(player.mana_pool, mana_cost_str):
            break
        perm.tapped = True
        player.mana_pool = add_mana(player.mana_pool, sym)

    # Build payment dict from pool + cost
    import re as _re2
    payment: dict[str, int] = {}
    pool = {
        "W": player.mana_pool.W,
        "U": player.mana_pool.U,
        "B": player.mana_pool.B,
        "R": player.mana_pool.R,
        "G": player.mana_pool.G,
        "C": player.mana_pool.C,
    }
    generic = 0
    for sym_m in _re2.findall(r'\{([^}]+)\}', mana_cost_str):
        if sym_m in ("W", "U", "B", "R", "G", "C"):
            payment[sym_m] = payment.get(sym_m, 0) + 1
            pool[sym_m] = pool.get(sym_m, 0) - 1
        elif sym_m.isdigit():
            generic += int(sym_m)
    for color in ("C", "W", "U", "B", "R", "G"):
        if generic <= 0:
            break
        avail = max(0, pool.get(color, 0))
        take = min(generic, avail)
        if take:
            payment[color] = payment.get(color, 0) + take
            pool[color] -= take
            generic -= take

    return gs, payment


@router.post("/{game_id}/cast")
def cast(game_id: str, req: CastRequest) -> dict:
    """POST /game/{game_id}/cast. REQ-A03, REQ-A04"""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    # Save caster and card name before cast_spell modifies state
    caster = gs.priority_holder
    cast_turn, cast_phase, cast_step = gs.turn, gs.phase.value, gs.step.value
    player_gs = get_player(gs, caster)

    if req.from_command_zone:
        # Commander cast: find card in command zone, validate tax, then cast
        cmd_card = next((c for c in player_gs.command_zone if c.id == req.card_id), None)
        if cmd_card is None:
            raise _err("Commander not in command zone", "INVALID_ACTION")
        card_name = cmd_card.name
        tax = 2 * player_gs.commander_cast_counts.get(cmd_card.name, 0)
        cmd_mana_cost = f"{{{tax}}}{cmd_card.mana_cost or ''}" if tax else (cmd_card.mana_cost or "")

        # Temporarily move commander into hand so cast_spell can find it
        player_gs.command_zone[:] = [c for c in player_gs.command_zone if c.id != req.card_id]
        player_gs.hand.append(cmd_card)
        try:
            gs = cast_spell(
                gs, caster, req.card_id, req.targets, req.mana_payment,
                alternative_cost=req.alternative_cost, modes_chosen=req.modes_chosen,
            )
            gs = _run_sbas(gs)
        except ValueError as e:
            # Rollback: put commander back in command zone
            player_gs2 = get_player(gs, caster)
            player_gs2.hand[:] = [c for c in player_gs2.hand if c.id != req.card_id]
            player_gs2.command_zone.append(cmd_card)
            raise _err(str(e), "INVALID_ACTION")

        # Increment commander cast count (per-card for partner support)
        player_gs2 = get_player(gs, caster)
        player_gs2.commander_cast_counts[cmd_card.name] = player_gs2.commander_cast_counts.get(cmd_card.name, 0) + 1

        if not req.dry_run:
            mgr.update(game_id, gs)
            recorder = _get_recorder_safe(game_id, mgr)
            if recorder:
                recorder.record_cast(caster, card_name, req.targets, cast_turn, cast_phase, cast_step,
                                     mana_cost=cmd_mana_cost)
        return _ok(gs)

    # Alternative cost pre-processing (US18, T057-T059, US33, T094)
    if req.alternative_cost == "phyrexian":
        # Deduct 2 life per Phyrexian symbol from the card's cost
        import re as _re
        card_for_phyrexian = next((c for c in player_gs.hand if c.id == req.card_id), None)
        if card_for_phyrexian:
            phyrexian_symbols = len(_re.findall(r'\{[WUBRG]/P\}', card_for_phyrexian.mana_cost or "", _re.IGNORECASE))
            player_gs.life -= phyrexian_symbols * 2

    if req.alternative_cost == "convoke":
        # Tap all specified creatures to pay mana
        for cid in req.targets:
            perm = next((p for p in gs.battlefield if p.id == cid), None)
            if perm and not perm.tapped:
                perm.tapped = True
    elif req.alternative_cost == "emerge":
        # Sacrifice the first target creature before casting.
        # Route through _sacrifice_permanent (not move_permanent_to_zone) so that
        # "is sacrificed" triggers fire (CR 701.19) and the zone-change event is
        # emitted for "dies" / "leaves the battlefield" triggers.
        if req.targets:
            sac_id = req.targets[0]
            from mtg_engine.engine.zones import _sacrifice_permanent
            gs = _sacrifice_permanent(gs, sac_id, sacrificer=caster)
    elif req.alternative_cost == "delve":
        # Exile specified graveyard cards to pay generic mana
        player_for_delve = get_player(gs, gs.priority_holder)
        # Use pending_delve_choice card_ids if available (from apply())
        delve_card_ids = []
        if gs.pending_delve_choice and gs.pending_delve_choice.get("card_ids"):
            delve_card_ids = gs.pending_delve_choice["card_ids"]
        if not delve_card_ids:
            delve_card_ids = req.targets
        for gid in delve_card_ids:
            delve_card = next((c for c in player_for_delve.graveyard if c.id == gid), None)
            if delve_card:
                player_for_delve.graveyard.remove(delve_card)
                player_for_delve.exile.append(delve_card)
        # Clear pending choice after resolution
        gs.pending_delve_choice = None
        req = req.model_copy(update={"targets": []})

    elif req.alternative_cost == "evoke":
        # Evoke: pay evoke cost instead of mana cost, sacrifice on ETB (CR 702.41)
        from mtg_engine.engine.evoke import parse_evoke_cost as _parse_evoke_cost
        player_for_evoke = get_player(gs, gs.priority_holder)
        oracle_text = card_obj.oracle_text or "" if card_obj else ""
        evoke_cost = _parse_evoke_cost(oracle_text)
        if evoke_cost:
            if not can_pay_cost(player_for_evoke.mana_pool, evoke_cost):
                raise _err(f"Insufficient mana for evoke {card_obj.name}", "INSUFFICIENT_MANA")
            # Pay evoke cost from mana pool (reuse existing payment logic)
            from mtg_engine.engine.mana import parse_mana_cost as _pmc_evoke
            cost_dict = _pmc_evoke(evoke_cost)
            payment = {}
            for color, amount in cost_dict.items():
                current = getattr(player_for_evoke.mana_pool, color, 0) or 0
                pay = min(amount, current)
                if pay > 0:
                    payment[color] = pay
            # Apply payment using pure transform
            new_pool = player_for_evoke.mana_pool.model_copy()
            for color, pay in payment.items():
                setattr(new_pool, color, getattr(new_pool, color, 0) - pay)
            players_new = list(gs.players)
            idx = next(i for i, p in enumerate(players_new) if p.name == player_for_evoke.name)
            players_new[idx] = players_new[idx].model_copy(update={"mana_pool": new_pool})
            gs = gs.model_copy(update={"players": players_new})
        # Set flag to trigger evoke sacrifice on ETB — handled by stack.py resolve_top()

    # Find the card in hand OR graveyard (needed for payment calculation)
    _card_for_payment = next((c for c in player_gs.hand if c.id == req.card_id), None)
    if not _card_for_payment:
        _card_for_payment = next((c for c in player_gs.graveyard if c.id == req.card_id), None)
    
    # Auto-calculate mana_payment if not provided (BUG-22 fix)
    if not req.mana_payment and _card_for_payment:
        player = get_player(gs, gs.priority_holder)
        cost_for_payment = _card_for_payment.mana_cost or ""
        if player and cost_for_payment:
            from mtg_engine.engine.mana import parse_mana_cost as _pmc
            cost_dict = _pmc(cost_for_payment)
            payment = {}
            pool = {"W": player.mana_pool.W, "U": player.mana_pool.U, "B": player.mana_pool.B, "R": player.mana_pool.R, "G": player.mana_pool.G, "C": player.mana_pool.C}
            # Pay colored first
            for color in ("W", "U", "B", "R", "G"):
                needed = cost_dict.get(color, 0)
                if needed and pool.get(color, 0) >= needed:
                    payment[color] = needed
                    pool[color] -= needed
            # Pay generic
            generic_needed = cost_dict.get("generic", 0)
            if generic_needed:
                pool_avail = sum(v for v in pool.values() if v > 0)
                if pool_avail >= generic_needed:
                    payment["C"] = min(generic_needed, pool_avail)
            # Always update req with payment (even if empty to trigger fix in stack.py)
            req = req.model_copy(update={"mana_payment": payment})

    # Graveyard cast (US11, T039): temporarily move card to hand for cast_spell
    _graveyard_card = None
    _foretold_card = None
    if req.from_graveyard and req.alternative_cost in {"flashback", "escape", "unearth", "disturb", "harmonize"}:
        _graveyard_card = next((c for c in player_gs.graveyard if c.id == req.card_id), None)
        if _graveyard_card is None:
            raise _err(f"Card {req.card_id!r} not found in graveyard", "INVALID_ACTION")
        player_gs.graveyard[:] = [c for c in player_gs.graveyard if c.id != req.card_id]
        player_gs.hand.append(_graveyard_card)
    elif req.from_graveyard and req.alternative_cost is None:
        # Aftermath (CR 702.125): cast second half from graveyard
        _graveyard_card = next((c for c in player_gs.graveyard if c.id == req.card_id), None)
        if _graveyard_card is None:
            raise _err(f"Card {req.card_id!r} not found in graveyard", "INVALID_ACTION")
        player_gs.graveyard[:] = [c for c in player_gs.graveyard if c.id != req.card_id]
        player_gs.hand.append(_graveyard_card)

    # US29: Cast from foretell exile — move card from foretold_cards to hand
    if req.alternative_cost == "foretell":
        _foretold_card = next((c for c in player_gs.foretold_cards if c.id == req.card_id), None)
        if _foretold_card is None:
            raise _err(f"Card {req.card_id!r} not found in foretold exile", "FORETELL_NOT_IN_EXILE")
        # Validate: cannot cast on the same turn the card was foretold
        foretold_on_turn = player_gs.foretold_turns.get(req.card_id)
        if foretold_on_turn is not None and foretold_on_turn == gs.turn:
            raise _err("Cannot cast a foretold card on the same turn it was foretold", "FORETELL_SAME_TURN")
        player_gs.foretold_cards[:] = [c for c in player_gs.foretold_cards if c.id != req.card_id]
        player_gs.foretold_turns.pop(req.card_id, None)
        player_gs.hand.append(_foretold_card)

    card_obj = next((c for c in player_gs.hand if c.id == req.card_id), None)
    card_name = card_obj.name if card_obj else req.card_id
    card_mana_cost = card_obj.mana_cost or "" if card_obj else ""

    # KW-43: Convoke (CR 702.43) — intercept human cast to queue pending_convoke_choice; AI auto-resolves.
    convoke_flag = False
    if (
        card_obj is not None
        and req.alternative_cost is None
        and not req.from_graveyard
    ):
        from mtg_engine.ability.keywords.convoke import Convoke
        from mtg_engine.models.game import Permanent as _ConvokePermanent
        _conv_transient = _ConvokePermanent(card=card_obj, controller=caster)
        gs = Convoke().apply(gs, _conv_transient)
        _conv_pending = gs.pending_convoke_choice
        if _conv_pending is not None and not _conv_pending.get("resolved"):
            # Human: defer cast, stash parameters
            _conv_pending.update({
                "targets": list(req.targets),
                "mana_payment": dict(req.mana_payment or {}),
                "x_value": req.x_value,
                "modes_chosen": list(req.modes_chosen or []),
                "kicker_paid": bool(req.kicker_paid),
            })
            if not req.dry_run:
                mgr.update(game_id, gs)
            return _ok(gs)
        elif _conv_pending is not None:
            # AI auto-resolved: creatures already tapped, pending contains tapped ids
            convoke_flag = True
            tapped_ids = _conv_pending.get("tapped_creature_ids", [])
            # Propagate to request for cost reduction
            req = req.model_copy(update={"convoke_creature_ids": tapped_ids})
            # Clear pending after use
            gs = gs.model_copy(update={"pending_convoke_choice": None})
        else:
            convoke_flag = False

    # US19: Apply keyword cost reductions (Convoke, Delve, Improvise, Affinity, Emerge)
    effective_cost_str = card_mana_cost
    if card_obj and (req.convoke_creature_ids or req.delve_card_ids or req.improvise_artifact_ids or req.emerge_sacrifice_id):
        from mtg_engine.engine.mana import apply_keyword_cost_reductions, format_cost_dict_to_string
        effective_cost_dict = apply_keyword_cost_reductions(
            card_mana_cost,
            req,
            gs,
            caster
        )
        effective_cost_str = format_cost_dict_to_string(effective_cost_dict)

    # Auto-tap mana sources when human player sends empty mana_payment
    mana_payment = req.mana_payment
    if not mana_payment and effective_cost_str:
        gs, mana_payment = _auto_tap_and_build_payment(gs, caster, effective_cost_str)
        player_gs = get_player(gs, caster)

    # Overload (CR 702.95) — alternative cost that replaces base cost and changes "target" to "each".
    # Intercepts human cast to queue pending_overload_choice; AI auto-resolves.
    overload_flag = False
    if (
        card_obj is not None
        and req.alternative_cost is None
        and not req.from_graveyard
    ):
        from mtg_engine.ability.keywords.overload import OverloadKeyword
        from mtg_engine.models.game import Permanent as _OLPermanent
        _ol_transient = _OLPermanent(card=card_obj, controller=caster)
        gs = OverloadKeyword().apply(gs, _ol_transient)
        _ol_pending = gs.pending_overload_choice
        if _ol_pending is not None and not _ol_pending.get("resolved"):
            # Human: defer cast, stash parameters
            _ol_pending.update({
                "targets": list(req.targets),
                "mana_payment": dict(mana_payment or {}),
                "x_value": req.x_value,
                "modes_chosen": list(req.modes_chosen or []),
                "kicker_paid": bool(req.kicker_paid),
            })
            if not req.dry_run:
                mgr.update(game_id, gs)
            return _ok(gs)
        elif _ol_pending is not None:
            # AI auto-resolved
            overload_flag = bool(_ol_pending.get("paid"))
            gs = gs.model_copy(update={"pending_overload_choice": None})
        else:
            overload_flag = False

    # T009: Validate targets before casting
    # Overloaded spells target nothing (CR 702.95b), so skip validation when overload is paid.
    if req.targets and not overload_flag:
        card_obj = next((c for c in player_gs.hand if c.id == req.card_id), None)
        if card_obj:
            _validate_targets(gs, req.targets, card_obj, caster)

    # KW-27: Buyback (CR 702.27/702.28) — a sorcery with "Buyback {cost}" cast
    # for its normal cost defers the cast until the buyback decision is made.
    # BuybackKeyword.apply() queues pending_buyback_choice for a human caster
    # (resolved=False) or auto-resolves it for an AI caster (resolved=True,
    # paid=True/False). Only normal hand casts qualify: no alternative cost,
    # no graveyard cast, no cost-reduction keywords (no buyback card combines
    # with them).
    _has_cost_reduction = bool(
        req.convoke_creature_ids or req.delve_card_ids
        or req.improvise_artifact_ids or req.emerge_sacrifice_id
    )
    buyback_flag = False
    if (
        card_obj is not None
        and req.alternative_cost is None
        and not req.from_graveyard
        and not _has_cost_reduction
    ):
        from mtg_engine.ability.keywords.buyback import BuybackKeyword
        from mtg_engine.models.game import Permanent as _BBPermanent
        _bb_transient = _BBPermanent(card=card_obj, controller=caster)
        gs = BuybackKeyword().apply(gs, _bb_transient)
        _bb_pending = gs.pending_buyback_choice
        if _bb_pending is not None and not _bb_pending.get("resolved"):
            # Human: defer the cast. Stash the cast parameters on the pending
            # choice so the buyback_pay / buyback_pass handler can re-drive the
            # exact same cast through cast_spell.
            _bb_pending.update({
                "targets": list(req.targets),
                "mana_payment": dict(mana_payment or {}),
                "x_value": req.x_value,
                "modes_chosen": list(req.modes_chosen or []),
                "kicker_paid": bool(req.kicker_paid),
            })
            if not req.dry_run:
                mgr.update(game_id, gs)
            return _ok(gs)
        elif _bb_pending is not None:
            # AI auto-resolved: clear the marker and cast with that decision.
            buyback_flag = bool(_bb_pending.get("paid"))
            gs = gs.model_copy(update={"pending_buyback_choice": None})
        else:
            buyback_flag = False

    # KW-39: Entwine (CR 702.39) — a modal spell with "Entwine {cost}" cast
    # for its normal cost defers the cast until the entwine decision is made
    # for a human caster. EntwineKeyword.apply() queues pending_entwine_choice
    # for a human caster (resolved=False) or auto-resolves it for an AI caster
    # (resolved=True, paid=True/False). Only normal hand casts qualify: no
    # alternative cost, no graveyard cast.
    entwine_flag = False
    if (
        card_obj is not None
        and req.alternative_cost is None
        and not req.from_graveyard
    ):
        from mtg_engine.ability.keywords.entwine import EntwineKeyword
        from mtg_engine.models.game import Permanent as _ENTPermanent
        _ent_transient = _ENTPermanent(card=card_obj, controller=caster)
        gs = EntwineKeyword().apply(gs, _ent_transient)
        _ent_pending = gs.pending_entwine_choice
        if _ent_pending is not None and not _ent_pending.get("resolved"):
            # Human: defer the cast. Stash the cast parameters on the pending
            # choice so the entwine_pay / entwine_pass handler can re-drive the
            # exact same cast through cast_spell.
            _ent_pending.update({
                "targets": list(req.targets),
                "mana_payment": dict(mana_payment or {}),
                "x_value": req.x_value,
                "modes_chosen": list(req.modes_chosen or []),
                "kicker_paid": bool(req.kicker_paid),
            })
            if not req.dry_run:
                mgr.update(game_id, gs)
            return _ok(gs)
        elif _ent_pending is not None:
            # AI auto-resolved: clear the marker and cast with that decision.
            entwine_flag = bool(_ent_pending.get("paid"))
            # If entwine paid, all modes are chosen; otherwise keep original modes.
            if entwine_flag:
                num_modes = _ent_pending.get("num_modes", 0)
                req = req.model_copy(update={"modes_chosen": list(range(num_modes))})
            gs = gs.model_copy(update={"pending_entwine_choice": None})
        else:
            entwine_flag = False

    try:
        gs = cast_spell(
            gs,
            caster,
            req.card_id,
            req.targets,
            mana_payment,
            alternative_cost=effective_cost_str if effective_cost_str != card_mana_cost else req.alternative_cost,
            modes_chosen=req.modes_chosen,
            x_value=req.x_value,
            kicker_paid=req.kicker_paid,
            jump_start_discard_id=req.jump_start_discard_id,
            face_index=req.face_index,
            fuse=req.fuse,
            as_face_down=req.as_face_down,
            foretell=req.foretell,
            mutate_target_id=req.mutate_target_id,
            mutate_on_top=req.mutate_on_top,
            from_graveyard=req.from_graveyard,
            overload_paid=overload_flag,
            buyback_paid=buyback_flag,
            entwine_paid=entwine_flag,
        )
        gs = _run_sbas(gs)
    except ValueError as e:
        # Rollback graveyard move if cast fails
        if _graveyard_card is not None:
            player_gs2 = get_player(gs, caster)
            player_gs2.hand[:] = [c for c in player_gs2.hand if c.id != req.card_id]
            player_gs2.graveyard.append(_graveyard_card)
        # Rollback foretold card move if cast fails
        if _foretold_card is not None:
            player_gs2 = get_player(gs, caster)
            player_gs2.hand[:] = [c for c in player_gs2.hand if c.id != req.card_id]
            player_gs2.foretold_cards.append(_foretold_card)
        raise _err(str(e), "INVALID_ACTION")

    # Ward (CR 702.145) now fires centrally in stack.py's cast_spell
    # becomes-target flow via apply_ward(), so the previous per-cast T051 block
    # below was redundant and removed to avoid double-firing pending_ward_payment.
    # The queue (human caster) / auto-resolve (AI caster) semantics live in
    # mtg_engine/ability/keywords/ward.py; the pay/counter choice handlers for a
    # queued human choice remain in this router below.

    # Post-resolution: handle graveyard keyword exile rules
    if _graveyard_card is not None:
        player_gs2 = get_player(gs, caster)
        alt = req.alternative_cost
        if alt in {"flashback", "disturb"}:
            # Flashback/disturb: card should be exiled instead of going to graveyard on resolution
            # cast_spell moves it to graveyard; remove from graveyard and exile
            player_gs2.graveyard[:] = [c for c in player_gs2.graveyard if c.id != req.card_id]
            player_gs2.exile.append(_graveyard_card)
        elif alt == "escape":
            # Escape: exile the cast card + N additional graveyard cards from req.targets
            player_gs2.graveyard[:] = [c for c in player_gs2.graveyard if c.id != req.card_id]
            player_gs2.exile.append(_graveyard_card)
            for extra_id in req.targets:
                extra_card = next((c for c in player_gs2.graveyard if c.id == extra_id), None)
                if extra_card:
                    player_gs2.graveyard.remove(extra_card)
                    player_gs2.exile.append(extra_card)
        elif alt == "unearth":
            # Unearth: exile at end of turn is handled via cleanup; for now just track it
            # The card should already have been placed on battlefield by cast_spell for creatures
            pass
        elif req.from_graveyard:
            # Aftermath (CR 702.125): card cast from graveyard is exiled instead of going to graveyard
            player_gs2.graveyard[:] = [c for c in player_gs2.graveyard if c.id != req.card_id]
            player_gs2.exile.append(_graveyard_card)

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        if recorder:
            recorder.record_cast(caster, card_name, req.targets, cast_turn, cast_phase, cast_step,
                                 mana_cost=card_mana_cost)
    return _ok(gs)


# ─── Cycling (US9) ────────────────────────────────────────────────────────────

@router.post("/{game_id}/cycle")
def cycle(game_id: str, req: CastRequest) -> dict:
    """POST /game/{game_id}/cycle. Cycle a card from hand (pay cost, discard, draw)."""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    player_name = gs.priority_holder
    player = get_player(gs, player_name)
    cycle_turn, cycle_phase, cycle_step = gs.turn, gs.phase.value, gs.step.value

    # Find the card in hand
    card = next((c for c in player.hand if c.id == req.card_id), None)
    if card is None:
        raise _err(f"Card {req.card_id!r} not found in hand", "INVALID_ACTION")

    # Extract cycling cost from oracle text. Use cycle.py as the SINGLE source of
    # truth so the live /cycle path honours the same (?<!\w)(?<!type ) guards that
    # reject "Type cycling {2}" and basic-land-cycling tokens ("Swampcycling {1}").
    from mtg_engine.ability.keywords.cycle import CyclingKeyword

    if not CyclingKeyword.from_oracle_text(card.oracle_text or ""):
        raise _err(f"{card.name} doesn't have cycling", "INVALID_ACTION")
    cycling_cost = CyclingKeyword.parse_cost(card.oracle_text or "")
    if not cycling_cost:
        raise _err(f"{card.name} has no parsable cycling cost", "INVALID_ACTION")
    from mtg_engine.engine.mana import can_pay_cost
    if not can_pay_cost(player.mana_pool, cycling_cost):
        raise _err(f"Cannot pay cycling cost {cycling_cost}", "INVALID_ACTION")

    card_name = card.name

    try:
        # Pay the cycling cost — now actually deducts mana from the pool (was a
        # documented no-op). Done via the pure helpers in cycle.py so `gs` is
        # built with model_copy and no live player list is mutated in place.
        from mtg_engine.ability.keywords.cycle import _discard_and_draw, _pay_mana

        gs = _pay_mana(gs, player_name, cycling_cost)
        gs = _discard_and_draw(gs, player_name, card, draw_count=1)

        # Wire: Discard Trigger (CR 701.18) — the cycled card is discarded.
        from mtg_engine.engine.triggers import check_discard_triggers as _check_discard
        gs = _check_discard(gs, player_name)

        # Emit cycle triggers (US9, check_cycle_triggers)
        from mtg_engine.engine.triggers import check_cycle_triggers
        gs = check_cycle_triggers(gs, card_name, card.type_line)

        gs = _run_sbas(gs)

    except (ValueError, StopIteration) as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        # TranscriptRecorder has no generic ``record_action`` method (only typed
        # record_* methods); guard so a missing method degrades to a no-op rather
        # than raising AttributeError on every real cycle.
        if recorder and hasattr(recorder, "record_action"):
            recorder.record_action(player_name, f"Cycle {card_name}", cycle_turn, cycle_phase, cycle_step)

    return _ok(gs)


# ─── Dredge (US10) ────────────────────────────────────────────────────────────

@router.post("/{game_id}/dredge")
def dredge(game_id: str, req: CastRequest) -> dict:
    """POST /game/{game_id}/dredge. Dredge a card from graveyard instead of drawing."""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    player_name = gs.active_player
    player = get_player(gs, player_name)
    dredge_turn, dredge_phase, dredge_step = gs.turn, gs.phase.value, gs.step.value

    # Validate pending dredge choice
    if not gs.pending_dredge_choice:
        raise _err("No dredge choice pending", "INVALID_ACTION")
    if gs.pending_dredge_choice.get("player") != player_name:
        raise _err("Not your dredge choice", "INVALID_ACTION")

    # Find the dredge card
    dredge_card = next((c for c in player.graveyard if c.id == req.card_id), None)
    if dredge_card is None:
        raise _err(f"Card {req.card_id!r} not found in graveyard", "INVALID_ACTION")

    # Extract dredge number from the card
    import re as _re_dredge
    dredge_match = _re_dredge.search(r'[Dd]redge (\d+)', dredge_card.oracle_text or "")
    if not dredge_match:
        raise _err(f"{dredge_card.name} doesn't have dredge", "INVALID_ACTION")

    dredge_n = int(dredge_match.group(1))
    dredge_card_name = dredge_card.name

    try:
        # Look at the top N cards of the library
        if len(player.library) < dredge_n:
            raise ValueError(f"Only {len(player.library)} cards in library (need {dredge_n} to dredge)")
        
        top_n_cards = player.library[:dredge_n]
        
        # Put the dredged card (req.card_id) into hand
        # and the rest into the graveyard
        # For now, we'll just put the top dredge_n cards into graveyard
        # except for the one being put into hand
        
        # Move dredge card from graveyard to hand
        player.graveyard[:] = [c for c in player.graveyard if c.id != req.card_id]
        player.hand.append(dredge_card)
        
        # Put top N library cards into graveyard
        cards_to_mill = player.library[:dredge_n]
        player.library = player.library[dredge_n:]
        player.graveyard.extend(cards_to_mill)
        
        # Clear the pending dredge choice
        gs.pending_dredge_choice = None
        
        gs = _run_sbas(gs)

    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        if recorder:
            recorder.record_action(player_name, f"Dredge {dredge_card_name}", dredge_turn, dredge_phase, dredge_step)

    return _ok(gs)


# ─── Proliferate (US13) ───────────────────────────────────────────────────────

class ProliferateRequest(BaseModel):
    targets: list[str] = []   # permanent IDs or player names to add one counter to
    dry_run: bool = False


@router.post("/{game_id}/proliferate")
def proliferate(game_id: str, req: ProliferateRequest) -> dict:
    """POST /game/{game_id}/proliferate. US13: add one counter of each type to chosen targets."""
    from mtg_engine.engine.proliferate import apply_proliferate
    from mtg_engine.engine.triggers import check_proliferated_triggers

    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    if not gs.pending_proliferate_choice:
        raise _err("No pending proliferate choice", "INVALID_ACTION")

    player_name = gs.pending_proliferate_choice["player"]
    eligible_ids = {e["id"] for e in gs.pending_proliferate_choice.get("eligible", [])}

    for target_id in req.targets:
        if target_id not in eligible_ids:
            raise _err(f"Target {target_id!r} is not eligible for proliferate", "INVALID_ACTION")

    # Delegate counter application to engine (pure transform)
    gs = apply_proliferate(gs, req.targets)

    # Fire "whenever you proliferate" triggers after resolution
    gs = check_proliferated_triggers(gs, player_name)

    gs = gs.model_copy(update={"pending_proliferate_choice": None})
    gs = _run_sbas(gs)

    if not req.dry_run:
        mgr.update(game_id, gs)
    return _ok(gs)


# ─── Activate ability ─────────────────────────────────────────────────────────

def _apply_activated_ability_effect(
    gs: GameState, perm: Any, ability: Any, req: ActivateRequest, player: Any
) -> GameState:
    """Apply the EFFECT portion of an activated ability (CR 605 mana / T128 regen /
    Fortify). Extracted verbatim from the /activate endpoint so the identical
    effect logic can re-run when a deferred Ward (ability) payment resolves via
    the ``ward_pay`` choice handler.

    The activation cost (tap + mana) is NOT paid here — the caller does that
    before invoking this helper. Preserves the exact existing behavior of the
    inline block (including the in-place ``player.mana_pool`` / permanent
    updates), so non-ward activations are unaffected.
    """
    import re

    from mtg_engine.engine.mana import add_mana, is_mana_ability, resolve_mana_ability

    ability_text = ability.raw_text

    # Check if this is a mana ability per CR 605 (T014, T015)
    # Mana abilities resolve immediately without going on the stack
    if is_mana_ability(ability_text, is_loyalty=False):
        # Resolve immediately - bypass stack (CR 605.3b)
        gs = resolve_mana_ability(gs, req.permanent_id, ability_text)
    else:
        # Apply non-mana ability effects
        mana_add = re.search(r"add\s+(\{[WUBRGC]\})", ability.effect, re.IGNORECASE)
        if mana_add:
            sym = mana_add.group(1).strip("{}")
            player.mana_pool = add_mana(player.mana_pool, sym.upper())
    # T128: Regeneration ability — add a regen shield to target permanent (CR 701.15a)
    regen_match = re.search(r"regenerate (target|this|~)", ability.effect, re.IGNORECASE)
    if regen_match:
        # Determine target: if "target" use req.targets[0], else use the perm itself
        if "target" in regen_match.group(1).lower() and req.targets:
            regen_target_id = req.targets[0]
        else:
            regen_target_id = perm.id
        regen_perm = next((p for p in gs.battlefield if p.id == regen_target_id), None)
        if regen_perm:
            regen_perm.regen_shields += 1
            logger.info("Regen shield added to %s (total: %d)", regen_perm.card.name, regen_perm.regen_shields)

    # Fortify (CR 702.54a): attach this Fortification to target land.
    # Cost (mana) already paid above via the shared cost machinery; the
    # timing_restriction check already enforced sorcery speed.
    fortify_match = re.search(r"attach (?:this fortification )?to target land", ability.effect, re.IGNORECASE)
    if fortify_match:
        from mtg_engine.ability.keywords.fortify import Fortify
        from mtg_engine.engine.stack import _apply_fortify
        if not req.targets:
            raise ValueError(f"{perm.card.name}: Fortify requires a target land")
        fortify_target_id = req.targets[0]
        target_perm = next((p for p in gs.battlefield if p.id == fortify_target_id), None)
        if target_perm is None:
            raise ValueError(f"Fortify target {fortify_target_id!r} not on battlefield")
        if target_perm.controller != gs.priority_holder:
            raise ValueError(f"Fortify target {target_perm.card.name} is not controlled by {gs.priority_holder}")
        if not Fortify.is_land_card(target_perm.card):
            raise ValueError(f"Fortify target {target_perm.card.name} is not a land")
        if target_perm.id == perm.id:
            raise ValueError(f"Fortify target is the source {perm.card.name}")
        gs = _apply_fortify(gs, perm.id, fortify_target_id)

    return gs


def _reapply_deferred_ability(gs: GameState, pending: dict) -> GameState:
    """Re-apply a deferred activated ability's effect after its Ward payment
    resolves via ``ward_pay`` (CR 702.145a, ability case).

    The activation cost (tap + mana) was already paid when the ability was
    activated — only the effect is re-driven here, through the same
    :func:`_apply_activated_ability_effect` helper the /activate endpoint uses
    on the proceed path. ``pending`` is the ``pending_ward_payment`` dict
    (``targeting_type="ability"``) holding the deferred activation:
    ``permanent_id``, ``ability_index``, ``targets``, ``mana_payment``.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, ActivatedAbility

    perm = next((p for p in gs.battlefield if p.id == pending.get("permanent_id", "")), None)
    if perm is None:
        logger.warning(
            "Ward re-apply: source permanent %r not on battlefield; skipping effect",
            pending.get("permanent_id"),
        )
        return gs
    abilities = parse_oracle_text(perm.card.oracle_text or "", perm.card.type_line)
    activated = [a for a in abilities if isinstance(a, ActivatedAbility)]
    ability_index = pending.get("ability_index", 0)
    if ability_index >= len(activated):
        logger.warning(
            "Ward re-apply: ability index %s out of range; skipping effect",
            ability_index,
        )
        return gs
    ability = activated[ability_index]
    req = ActivateRequest(
        permanent_id=perm.id,
        ability_index=ability_index,
        targets=list(pending.get("targets") or []),
        mana_payment=dict(pending.get("mana_payment") or {}),
    )
    player = get_player(gs, pending.get("player", gs.priority_holder))
    return _apply_activated_ability_effect(gs, perm, ability, req, player)


@router.post("/{game_id}/activate")
def activate(game_id: str, req: ActivateRequest) -> dict:
    """POST /game/{game_id}/activate. REQ-A06, REQ-A07"""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    # Save activator context before ability fires
    activator = gs.priority_holder
    act_turn, act_phase, act_step = gs.turn, gs.phase.value, gs.step.value
    perm_name_for_log = req.permanent_id  # fallback; overwritten below if perm found
    ability_text_for_log = ""

    try:
        from mtg_engine.card_data.ability_parser import parse_oracle_text, ActivatedAbility
        from mtg_engine.engine.mana import pay_cost, is_mana_ability

        perm = next((p for p in gs.battlefield if p.id == req.permanent_id), None)
        if perm is None:
            raise ValueError(f"Permanent {req.permanent_id!r} not on battlefield")
        if perm.controller != gs.priority_holder:
            raise ValueError("You don't control that permanent")
        perm_name_for_log = perm.card.name

        abilities = parse_oracle_text(perm.card.oracle_text or "", perm.card.type_line)
        activated = [a for a in abilities if isinstance(a, ActivatedAbility)]
        if req.ability_index >= len(activated):
            raise ValueError(f"Ability index {req.ability_index} out of range")

        ability = activated[req.ability_index]
        ability_text_for_log = ability.raw_text

        # T010: Validate targets for activated abilities
        if req.targets:
            _validate_targets(gs, req.targets, perm.card, gs.priority_holder)

        # US20 T162: Enforce timing_restriction on activated abilities (CR 602.1)
        if ability.timing_restriction:
            restriction = ability.timing_restriction.lower()
            is_sorcery_speed = (
                gs.active_player == gs.priority_holder
                and gs.step == Step.MAIN
                and not gs.stack
            )
            if ("sorcery" in restriction or "your main phase" in restriction) and not is_sorcery_speed:
                raise ValueError(
                    f"{perm.card.name}: ability can only be activated at sorcery speed "
                    f"({ability.timing_restriction})"
                )
            if "your turn" in restriction and gs.active_player != gs.priority_holder:
                raise ValueError(
                    f"{perm.card.name}: ability can only be activated during your turn"
                )

        # US32 T179: Enforce split second on activated abilities (CR 702.61b)
        # Mana abilities bypass the stack and are unaffected by split second.
        from mtg_engine.engine.stack import _has_split_second
        is_split_second_active = _has_split_second(gs)
        if is_split_second_active and not is_mana_ability(ability_text_for_log, is_loyalty=False):
            raise ValueError("Cannot activate non-mana abilities while a split-second spell is on the stack")

        # Pay tap cost
        player = get_player(gs, gs.priority_holder)
        if "{T}" in ability.cost:
            if perm.tapped:
                raise ValueError(f"{perm.card.name} is already tapped")
            perm.tapped = True

        # Pay mana cost (extract mana symbols from cost)
        import re
        mana_cost_part = re.sub(r"\{T\}", "", ability.cost).strip().strip(",").strip()
        if mana_cost_part:
            player.mana_pool = pay_cost(player.mana_pool, mana_cost_part, req.mana_payment)

        # Ward (CR 702.145a): an activated ability that targets an opponent's
        # ward permanent triggers Ward — the activator (the ability's
        # controller/targeter) may pay the ward cost; if they don't, the ability
        # is countered. The activation cost (tap + mana) was paid above and is
        # consumed regardless of the outcome. Mana abilities do not target, so
        # only targeting abilities reach the ward check. Self-targeting never
        # triggers Ward (CR 702.145b).
        from mtg_engine.ability.keywords.ward import (
            Ward as _WardKw,
            apply_ward_to_ability as _apply_ward_to_ability,
        )
        ward_outcome = "proceed"
        for _ward_target_id in (req.targets or []):
            _ward_target_perm = next(
                (p for p in gs.battlefield if p.id == _ward_target_id), None
            )
            if _ward_target_perm is None or _ward_target_perm.controller == gs.priority_holder:
                continue
            if not _WardKw.has_ward(_ward_target_perm.card.keywords or []):
                continue
            gs, _ward_result = _apply_ward_to_ability(
                gs, _ward_target_perm, caster_name=gs.priority_holder
            )
            if _ward_result != "proceed":
                ward_outcome = _ward_result
                break

        if ward_outcome == "deferred":
            # The human targeter must choose ward_pay / ward_counter before the
            # effect may resolve. Store the deferred activation in the pending
            # choice so ward_pay can re-drive the exact same effect logic.
            gs = gs.model_copy(
                update={
                    "pending_ward_payment": {
                        **gs.pending_ward_payment,
                        "permanent_id": perm.id,
                        "ability_index": req.ability_index,
                        "targets": list(req.targets or []),
                        "mana_payment": dict(req.mana_payment or {}),
                        "ability_text": ability.effect,
                    }
                }
            )
        elif ward_outcome == "proceed":
            # Ward did not fire (or was paid by an AI targeter) — re-fetch the
            # player in case the ward resolver replaced the player object in
            # the returned state, then apply the effect handlers.
            player = get_player(gs, gs.priority_holder)
            gs = _apply_activated_ability_effect(gs, perm, ability, req, player)
        # ward_outcome == "countered": Ward countered the ability — the effect
        # handlers are skipped and the effect does NOT apply, but the
        # activation cost (tap + mana) is consumed (CR 702.145a).

        gs = _run_sbas(gs)
    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        if recorder:
            recorder.record_activate(
                activator, perm_name_for_log, req.ability_index, req.targets,
                act_turn, act_phase, act_step,
                ability_text=ability_text_for_log,
            )
    return _ok(gs)


# ─── Triggers ─────────────────────────────────────────────────────────────────

@router.get("/{game_id}/pending-triggers")
def get_pending_triggers(game_id: str) -> dict:
    """GET /game/{game_id}/pending-triggers. REQ-A09"""
    gs = _get_gs(game_id)
    triggers = [t.model_dump() for t in gs.pending_triggers]
    return {"data": triggers}


@router.post("/{game_id}/put-trigger")
def put_trigger(game_id: str, req: PutTriggerRequest) -> dict:
    """POST /game/{game_id}/put-trigger. REQ-A10"""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    try:
        gs = put_trigger_on_stack(gs, req.trigger_id, req.targets)
        gs = _run_sbas(gs)
    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
    return _ok(gs)


@router.post("/{game_id}/decline-trigger")
def decline_trigger(game_id: str, req: PutTriggerRequest) -> dict:
    """POST /game/{game_id}/decline-trigger — discard an optional trigger without effect. US17"""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    trigger = next((t for t in gs.pending_triggers if t.id == req.trigger_id), None)
    if trigger is None:
        raise _err(f"Trigger {req.trigger_id!r} not found", "TRIGGER_NOT_FOUND")
    if not trigger.is_optional:
        raise _err(f"Trigger {req.trigger_id!r} is not optional and cannot be declined", "INVALID_ACTION")

    gs.pending_triggers[:] = [t for t in gs.pending_triggers if t.id != req.trigger_id]
    logger.info("Optional trigger %r declined by %s", trigger.source_card_name, trigger.controller)

    if not req.dry_run:
        mgr.update(game_id, gs)
    return _ok(gs)


# ─── Combat ───────────────────────────────────────────────────────────────────

@router.post("/{game_id}/declare-attackers")
def do_declare_attackers(game_id: str, req: DeclareAttackersRequest) -> dict:
    """POST /game/{game_id}/declare-attackers. REQ-A11"""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    # Build attacker name map before declaring (permanents still on battlefield)
    attacker_map = {
        decl.attacker_id: (
            next((p.card.name for p in gs.battlefield if p.id == decl.attacker_id), decl.attacker_id),
            decl.defending_id,
        )
        for decl in req.attack_declarations
    }
    attacker_player = gs.active_player
    atk_turn, atk_phase, atk_step = gs.turn, gs.phase.value, gs.step.value

    try:
        gs = declare_attackers(gs, req.attack_declarations)
        gs = _run_sbas(gs)
    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        if recorder:
            for card_name, defending_id in attacker_map.values():
                recorder.record_attack(attacker_player, card_name, defending_id, atk_turn, atk_phase, atk_step)
    return _ok(gs)


@router.post("/{game_id}/declare-blockers")
def do_declare_blockers(game_id: str, req: DeclareBlockersRequest) -> dict:
    """POST /game/{game_id}/declare-blockers. REQ-A12"""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    # Build blocker/attacker name map before declaring
    blocker_map = []
    blk_turn, blk_phase, blk_step = gs.turn, gs.phase.value, gs.step.value
    for decl in req.block_declarations:
        blocker_perm = next((p for p in gs.battlefield if p.id == decl.blocker_id), None)
        attacker_perm = next((p for p in gs.battlefield if p.id == decl.attacker_id), None)
        blocker_map.append((
            blocker_perm.controller if blocker_perm else "unknown",
            blocker_perm.card.name if blocker_perm else decl.blocker_id,
            attacker_perm.card.name if attacker_perm else decl.attacker_id,
        ))

    try:
        gs = declare_blockers(gs, req.block_declarations)
        gs = _run_sbas(gs)
        # CR 509.3: after blockers are declared, active player gets priority
        gs.priority_holder = gs.active_player
    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        if recorder:
            for blocker_controller, blocker_name, attacker_name in blocker_map:
                recorder.record_block(blocker_controller, blocker_name, attacker_name, blk_turn, blk_phase, blk_step)
    return _ok(gs)


@router.post("/{game_id}/order-blockers")
def do_order_blockers(game_id: str, req: OrderBlockersRequest) -> dict:
    """POST /game/{game_id}/order-blockers. REQ-A13"""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    try:
        for ordering in req.orderings:
            gs = order_blockers(gs, ordering.attacker_id, ordering.blocker_order)
    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
    return _ok(gs)


@router.post("/{game_id}/assign-combat-damage")
def do_assign_combat_damage(game_id: str, req: AssignCombatDamageRequest) -> dict:
    """POST /game/{game_id}/assign-combat-damage. REQ-A15"""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    before_game_over = gs.is_game_over
    before_life = {p.name: p.life for p in gs.players}
    dmg_turn, dmg_phase, dmg_step = gs.turn, gs.phase.value, gs.step.value

    try:
        gs = assign_combat_damage(gs, req.assignments)
        gs = _run_sbas(gs)
    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        if recorder:
            for p in gs.players:
                old_life = before_life.get(p.name, p.life)
                if p.life != old_life:
                    delta = p.life - old_life
                    recorder.record_life_change(p.name, delta, "combat", p.life, dmg_turn, dmg_phase, dmg_step)
            if not before_game_over and gs.is_game_over:
                winner = gs.winner or "unknown"
                reason = "unknown"
                for p in gs.players:
                    if p.has_lost:
                        if p.life <= 0:
                            reason = "life_total_zero"
                        elif p.poison_counters >= 10:
                            reason = "poison_counters"
                        break
                recorder.record_game_end(winner, reason, dmg_turn, dmg_phase, dmg_step)
    return _ok(gs)


# ─── Choice ───────────────────────────────────────────────────────────────────

@router.post("/{game_id}/choice")
def submit_choice(game_id: str, req: ChoiceRequest) -> dict:
    """POST /game/{game_id}/choice — player makes a pending choice."""
    from mtg_engine.engine.zones import move_permanent_to_zone
    mgr = get_manager()
    gs = _get_gs(game_id)
    choice_id = req.choice_id

    if choice_id == "scry_keep":
        # Keep all scried cards on top (they're already there — just clear the pending state)
        gs.pending_scry_choice = None
        mgr.update(game_id, gs)
    elif choice_id == "scry_bottom":
        # Move the scried cards from the top of the library to the bottom
        if gs.pending_scry_choice:
            player_name = gs.pending_scry_choice["player"]
            n = gs.pending_scry_choice["n"]
            from mtg_engine.engine.zones import get_player
            scry_player = get_player(gs, player_name)
            if scry_player and scry_player.library:
                cards_to_bottom = scry_player.library[:n]
                scry_player.library = scry_player.library[n:] + cards_to_bottom
            gs.pending_scry_choice = None
        mgr.update(game_id, gs)

    # Regular Scry reorder (CR 701.20) — human reorders the revealed cards in any
    # order: req.selection is an ordered list of card ids describing the desired
    # top->bottom arrangement. Pure transform via resolve_scry_choice().
    elif choice_id == "scry":
        player_name = gs.pending_scry_choice.get("player") if gs.pending_scry_choice else None
        if not player_name:
            raise _err("No scry pending for this player", "INVALID_CHOICE")
        from mtg_engine.ability.keywords.scry import resolve_scry_choice
        gs = resolve_scry_choice(gs, player_name, req.selection)
        mgr.update(game_id, gs)

    # Handling reveal-and-choose from library (e.g., Sleight of Hand)
    elif choice_id == "reveal_put_hand":
        # Player puts one of the revealed cards into hand, puts rest on bottom
        if gs.pending_scry_choice and gs.pending_scry_choice.get("effect_type") == "reveal_and_choose":
            player_name = gs.pending_scry_choice.get("player")
            from mtg_engine.engine.zones import get_player as _get_player_lib
            player = _get_player_lib(gs, player_name)
            selected_id = req.selection if isinstance(req.selection, str) else None
            scry_cards = gs.pending_scry_choice.get("cards", [])
            n = gs.pending_scry_choice.get("n", 2)
            
            if player and selected_id:
                # Find card in the revealed cards list
                for c in scry_cards:
                    if c.get("id") == selected_id:
                        # Create a Card object for it
                        
                        # Try to find in library by name (simplified)
                        lib_top = player.library[:n]
                        chosen = next((c2 for c2 in lib_top if c2.name == c.get("name")), None)
                        if chosen:
                            # Move it to hand
                            player.hand.append(chosen)
                            logger.info("Reveal choose: %s puts %s into hand", player_name, chosen.name)
                        else:
                            # Fallback: reconstruct from dict
                            reconstructed = type('Card', (), {
                                'id': c.get('id'),
                                'name': c.get('name'),
                                'type_line': c.get('type_line', ''),
                            })()
                            player.hand.append(reconstructed)
                            logger.info("Reveal choose: %s puts %s into hand (reconstructed)", player_name, reconstructed.name)
                        break
                
                # Move remaining cards to bottom (those that weren't selected)
                if player and player.library:
                    remaining_cards = player.library[:n]
                    player.library = player.library[n:] + remaining_cards
                
            gs.pending_scry_choice = None
            mgr.update(game_id, gs)
            return _ok(gs)
    
    # Handling reveal-and-choose multi (e.g., Stock Up - choose multiple cards)
    elif choice_id == "reveal_put_hand_multi":
        if gs.pending_scry_choice and gs.pending_scry_choice.get("effect_type") == "reveal_and_choose_multi":
            player_name = gs.pending_scry_choice.get("player")
            from mtg_engine.engine.zones import get_player as _get_player_multi
            player = _get_player_multi(gs, player_name)
            selected_ids = req.selection if isinstance(req.selection, list) else []
            if isinstance(req.selection, str):
                selected_ids = [req.selection]
            scry_cards = gs.pending_scry_choice.get("cards", [])
            n = gs.pending_scry_choice.get("n", 5)
            put_count = gs.pending_scry_choice.get("put_count", 2)
            
            if player and selected_ids:
                for selected_id in selected_ids[:put_count]:
                    for c in scry_cards:
                        if c.get("id") == selected_id:
                            lib_top = player.library[:n]
                            chosen = next((c2 for c2 in lib_top if c2.name == c.get("name")), None)
                            if chosen:
                                player.hand.append(chosen)
                                logger.info("Reveal choose multi: %s puts %s into hand", player_name, chosen.name)
                            break
            
            # Move remaining cards to bottom
            if player and player.library:
                remaining_cards = player.library[:n]
                player.library = player.library[n:] + remaining_cards
            
            gs.pending_scry_choice = None
            mgr.update(game_id, gs)
            return _ok(gs)

    # Morph turn face-up (CR 702.35)
    elif choice_id == "morph_turn_face_up":
        from mtg_engine.engine.morph import apply_morph_turn_face_up
        permanent_id = req.selection if isinstance(req.selection, str) else None
        if not permanent_id:
            raise _err("No permanent selected for morph turn face-up", "INVALID_CHOICE")
        gs = apply_morph_turn_face_up(gs, permanent_id, mana_payment=req.mana_payment)
        mgr.update(game_id, gs)

    # Handle Spree mode selection
    elif choice_id == "spree_select":
        if gs.pending_spree_choice:
            selected_mode = req.selection
            if isinstance(selected_mode, int) or (isinstance(selected_mode, str) and selected_mode.isdigit()):
                mode_idx = int(selected_mode) if isinstance(selected_mode, str) else selected_mode
                modes = gs.pending_spree_choice.get("modes", [])
                if 0 <= mode_idx < len(modes):
                    selected = modes[mode_idx]
                    logger.info("Spree: selected mode %d: cost=%s, effect=%s", mode_idx, selected.get("cost"), selected.get("effect"))
                    
                    player_name = gs.pending_spree_choice.get("player")
                    # Additional mana payment for Spree mode
                    from mtg_engine.engine.mana import parse_mana_cost as _pmc_spree, pay_cost as _pc_spree
                    from mtg_engine.engine.zones import get_player as _gp_spree
                    
                    spree_cost = selected.get("cost", "")
                    player = _gp_spree(gs, player_name)
                    if player and spree_cost:
                        cost_dict = _pmc_spree(spree_cost)
                        payment = {}
                        pool = {"W": player.mana_pool.W, "U": player.mana_pool.U, "B": player.mana_pool.B, "R": player.mana_pool.R, "G": player.mana_pool.G, "C": player.mana_pool.C}
                        for color in ("W", "U", "B", "R", "G"):
                            needed = cost_dict.get(color, 0)
                            if needed and pool.get(color, 0) >= needed:
                                payment[color] = needed
                                pool[color] -= needed
                        generic_needed = cost_dict.get("generic", 0)
                        if generic_needed:
                            pool_avail = sum(v for v in pool.values() if v > 0)
                            if pool_avail >= generic_needed:
                                payment["C"] = min(generic_needed, pool_avail)
                        
                        if payment:
                            player.mana_pool = _pc_spree(player.mana_pool, spree_cost, payment)
                            logger.info("Spree: paid additional %s for mode", spree_cost)
                    
                    # Store selected mode effect for resolution on the stack
                    gs.pending_spree_effects.append({
                        "effect": selected.get("effect", ""),
                        "card_id": gs.pending_spree_choice.get("card_id", ""),
                    })
                    gs.pending_spree_choice = None
                    mgr.update(game_id, gs)
                    return _ok(gs)
        
        gs.pending_spree_choice = None
        mgr.update(game_id, gs)
        return _ok(gs)
    
    elif choice_id == "surveil_keep":
        # Keep surveiled cards on top of library
        gs.pending_surveil_choice = None
        mgr.update(game_id, gs)
    elif choice_id == "surveil_graveyard":
        # Move surveiled cards from the top of library to graveyard
        if gs.pending_surveil_choice:
            player_name = gs.pending_surveil_choice["player"]
            n = gs.pending_surveil_choice["n"]
            from mtg_engine.engine.zones import get_player
            surveil_player = get_player(gs, player_name)
            if surveil_player.library:
                cards_to_gy = surveil_player.library[:n]
                surveil_player.library = surveil_player.library[n:]
                surveil_player.graveyard.extend(cards_to_gy)
            gs.pending_surveil_choice = None
            mgr.update(game_id, gs)

    elif choice_id == "ward_pay":
        # T051: Player pays ward cost — spell targeting their permanent continues
        if gs.pending_ward_payment:
            ward_cost = gs.pending_ward_payment.get("ward_cost", "")
            payer_name = gs.pending_ward_payment.get("player", gs.priority_holder)
            # NOTE: aliased import — a bare `get_player` name is function-local
            # to submit_choice (imported conditionally in the scry/surveil
            # branches), so referencing it here would raise UnboundLocalError.
            from mtg_engine.engine.zones import get_player as _gp_w
            from mtg_engine.engine.mana import can_pay_cost, pay_cost as _pc_w
            payer = _gp_w(gs, payer_name)
            # CR 702.145a: the counter is MANDATORY when the ward cost is not
            # paid. Reject an unpayable ward_pay and KEEP the pending state so
            # the player must pick ward_counter instead — otherwise the spell
            # would continue as if Ward didn't exist.
            if not (ward_cost and can_pay_cost(payer.mana_pool, ward_cost)):
                raise _err(f"Cannot pay ward {ward_cost}", "INSUFFICIENT_MANA")
            # Auto-pay from pool: explicit colored/colorless requirements first,
            # then cover any generic remainder with leftover pool mana in
            # canonical order. (pay_cost raises if the payment dict doesn't
            # fully cover the cost — a generic-only cost like "Ward {2}" must
            # be covered from the leftover pool, not left empty.)
            from mtg_engine.engine.mana import parse_mana_cost as _pmc_w
            cost_dict = _pmc_w(ward_cost)
            mana_payment = {}
            pool_avail = {
                "W": payer.mana_pool.W, "U": payer.mana_pool.U, "B": payer.mana_pool.B,
                "R": payer.mana_pool.R, "G": payer.mana_pool.G, "C": payer.mana_pool.C,
            }
            for color in ("W", "U", "B", "R", "G"):
                needed = cost_dict.get(color, 0)
                if needed > 0:
                    mana_payment[color] = needed
                    pool_avail[color] -= needed
            needed_c = cost_dict.get("C", 0)
            if needed_c > 0:
                mana_payment["C"] = needed_c
                pool_avail["C"] -= needed_c
            generic_needed = cost_dict.get("generic", 0)
            for color in ("W", "U", "B", "R", "G", "C"):
                if generic_needed <= 0:
                    break
                take = min(pool_avail[color], generic_needed)
                if take > 0:
                    mana_payment[color] = mana_payment.get(color, 0) + take
                    pool_avail[color] -= take
                    generic_needed -= take
            payer.mana_pool = _pc_w(payer.mana_pool, ward_cost, mana_payment)
            # CR 702.145a (ability case): the ward was paid, so the deferred
            # activated ability now resolves — re-drive the same effect logic
            # the /activate endpoint uses on the proceed path. The spell path
            # (no targeting_type / "spell") keeps its existing behavior: the
            # targeting spell is already on the stack and needs nothing more.
            if gs.pending_ward_payment.get("targeting_type") == "ability":
                gs = _reapply_deferred_ability(gs, gs.pending_ward_payment)
            gs.pending_ward_payment = None
            mgr.update(game_id, gs)

    elif choice_id == "ward_counter":
        # T051: Player declines to pay ward — targeting spell/ability is
        # countered (CR 702.157b)
        if gs.pending_ward_payment:
            # NOTE: aliased import — see ward_pay above for why the bare
            # function-local `get_player` name cannot be used here.
            from mtg_engine.engine.zones import get_player as _gp_wc
            if gs.pending_ward_payment.get("targeting_type") == "ability":
                # Ability case (CR 702.145a): the activated ability never went
                # on the stack and its effect was never applied (it was
                # deferred) — there is nothing to remove, just clear the
                # pending choice. The activation cost was already consumed at
                # activation time.
                gs.pending_ward_payment = None
                mgr.update(game_id, gs)
            else:
                spell_id = gs.pending_ward_payment.get("targeting_spell_id", "")
                countered = next((s for s in gs.stack if s.id == spell_id), None)
                if countered:
                    gs.stack[:] = [s for s in gs.stack if s.id != spell_id]
                    owner = _gp_wc(gs, countered.controller)
                    if not countered.is_copy:
                        owner.graveyard.append(countered.source_card)
                    logger.info("Ward: %s countered for non-payment", countered.source_card.name)
                gs.pending_ward_payment = None
                mgr.update(game_id, gs)

    elif choice_id == "echo_pay":
        # US27 (T059): Player pays echo cost — permanent is marked as paid
        if gs.pending_echo_payment:
            echo_cost = gs.pending_echo_payment.get("echo_cost", "")
            payer_name = gs.pending_echo_payment.get("player", gs.priority_holder)
            permanent_id = gs.pending_echo_payment.get("permanent_id", "")
            perm = next((p for p in gs.battlefield if p.id == permanent_id), None)
            if perm:
                perm.echo_paid = True
            gs.pending_echo_payment = None
            mgr.update(game_id, gs)

    elif choice_id == "echo_decline":
        # US27 (T059): Player declines to pay echo cost — permanent is sacrificed
        if gs.pending_echo_payment:
            permanent_id = gs.pending_echo_payment.get("permanent_id", "")
            perm = next((p for p in gs.battlefield if p.id == permanent_id), None)
            if perm:
                gs = move_permanent_to_zone(gs, perm, "graveyard")
                gs.battlefield[:] = [p for p in gs.battlefield if p.id != perm.id]
                logger.info("Echo: %s sacrificed for non-payment", perm.card.name)
            gs.pending_echo_payment = None
            mgr.update(game_id, gs)

    elif choice_id == "etb_pay":
        # 034-etb-choices: Player pays cost for ETB choice (e.g., shockland)
        from mtg_engine.engine.zones import get_player as _etb_get_player
        if gs.pending_etb_choice:
            cost = gs.pending_etb_choice.get("cost_amount", 0)
            cost_type = gs.pending_etb_choice.get("cost_type", "life")
            player_name = gs.pending_etb_choice.get("player", gs.priority_holder)
            permanent_id = gs.pending_etb_choice.get("permanent_id", "")
            
            # Apply cost payment
            player = _etb_get_player(gs, player_name)
            if cost_type == "life" and player.life >= cost:
                player.life -= cost
            
            # Mark permanent as untapped (it's already on battlefield)
            perm = next((p for p in gs.battlefield if p.id == permanent_id), None)
            if perm:
                perm.tapped = False
            
            logger.info("ETB choice: %s paid %d %s for %s to enter untapped", 
                    player_name, cost, cost_type, perm.card.name)
            
            gs.pending_etb_choice = None
            mgr.update(game_id, gs)
    
    elif choice_id == "etb_tapped":
        # 034-etb-choices: Player chooses not to pay — permanent enters tapped (already set)
        if gs.pending_etb_choice:
            permanent_id = gs.pending_etb_choice.get("permanent_id", "")
            perm = next((p for p in gs.battlefield if p.id == permanent_id), None)
            if perm:
                logger.info("ETB choice: %s entered tapped (no payment)", perm.card.name)
            
            gs.pending_etb_choice = None
            mgr.update(game_id, gs)

    elif choice_id == "tutor_pick":
        # T040: Player picks a card from library (tutor)
        if gs.pending_tutor_choice:
            destination = gs.pending_tutor_choice.get("destination", "hand")
            tutor_player_name = gs.pending_tutor_choice.get("player", gs.priority_holder)
            tutor_player = get_player(gs, tutor_player_name)
            selected_id = req.selection if isinstance(req.selection, str) else None
            card = next((c for c in tutor_player.library if c.id == selected_id), None) if selected_id else None
            if card is None and tutor_player.library:
                card = tutor_player.library[0]  # fallback: take top card
            if card:
                tutor_player.library[:] = [c for c in tutor_player.library if c.id != card.id]
                if destination == "hand":
                    tutor_player.hand.append(card)
                elif destination == "battlefield":
                    from mtg_engine.engine.zones import put_permanent_onto_battlefield
                    gs, _ = put_permanent_onto_battlefield(gs, card, tutor_player_name)
                tutor_player.library.sort(key=lambda _c: 0)  # shuffle signal; simplified
            gs.pending_tutor_choice = None
            mgr.update(game_id, gs)

    elif choice_id == "discard_pick":
        # T040: Player picks a card to discard
        if gs.pending_discard_choice:
            is_duress = gs.pending_discard_choice.get("is_duress_effect", False)
            is_optional = gs.pending_discard_choice.get("is_optional_discard", False)
            opponent_name = gs.pending_discard_choice.get("opponent")
            selected_id = req.selection if isinstance(req.selection, str) else None
            
            if is_optional:
                # Optional discard (e.g., Abandon Attachments)
                # If selected_id: discard AND draw | If no selection: don't discard, don't draw
                
                # Check for Winternight Stories conditional discard
                is_winternight = gs.pending_discard_choice.get("is_winternight_stories", False)
                
                if selected_id:
                    from mtg_engine.engine.zones import get_player as _get_player_draw
                    player_name = gs.pending_discard_choice.get("player", gs.priority_holder)
                    player = _get_player_draw(gs, player_name)
                    if player:
                        # Find and discard selected card
                        card = next((c for c in player.hand if c.id == selected_id), None)
                        if card is None and player.hand:
                            card = player.hand[0]
                        if card:
                            logger.info("Optional discard: %s discards %s", player_name, card.name)
                            player.hand[:] = [c for c in player.hand if c.id != card.id]
                            player.graveyard.append(card)
                            
                            # Winternight Stories: if discarded creature, done; if not, need another discard
                            if is_winternight:
                                is_creature = "creature" in (card.type_line or "").lower()
                                remaining = gs.pending_discard_choice.get("count", 2)
                                if is_creature or remaining <= 1:
                                    # Spell resolves (discarded creature OR already discarded 2)
                                    gs.pending_discard_choice = None
                                else:
                                    # Need to discard another card
                                    new_hand = [c.model_dump() for c in player.hand]
                                    gs.pending_discard_choice = {
                                        **gs.pending_discard_choice,
                                        "opponent_hand": new_hand,
                                        "count": remaining - 1,
                                    }
                                    logger.info("Winternight Stories: need another discard (creature=%s, remaining=%d)", is_creature, remaining - 1)
                                    mgr.update(game_id, gs)
                                    return _ok(gs)
                                draw_count = gs.pending_discard_choice.get("draw_after_discard", 1)
                            for _ in range(draw_count):
                                gs, _ = draw_card(gs, player_name)
                    else:
                        # Chose NOT to discard - don't draw any cards, spell fizzles
                        logger.info("Optional discard: chose not to discard")
                        from mtg_engine.engine.zones import get_player as _gp
                        player_name = gs.pending_discard_choice.get("player", gs.priority_holder)
                        player = _gp(gs, player_name)
                        if player:
                            player.graveyard.append(type('Card', (), {'name': gs.pending_discard_choice.get('source_card', 'Abandon Attachments')})())
                        gs.pending_discard_choice = None
                mgr.update(game_id, gs)
                return _ok(gs)
            
            if is_duress and opponent_name:
                # Duress effect: discard from opponent's hand
                from mtg_engine.engine.zones import get_player as _get_player_opponent
                opponent = _get_player_opponent(gs, opponent_name)
                if opponent:
                    selected_id = req.selection if isinstance(req.selection, str) else None
                    card = next((c for c in opponent.hand if c.id == selected_id), None) if selected_id else None
                    if card is None and opponent.hand:
                        # Fallback: discard first valid card
                        card = opponent.hand[0]
                    if card:
                        logger.info("Duress: %s discards %s", opponent_name, card.name)
                        opponent.hand[:] = [c for c in opponent.hand if c.id != card.id]
                        opponent.graveyard.append(card)
                    else:
                        logger.warning("Duress: no card found to discard")
                gs.pending_discard_choice = None
            else:
                # Original behavior: discard from caster's hand
                discard_player_name = gs.pending_discard_choice.get("player", gs.priority_holder)
                discard_player = get_player(gs, discard_player_name)
                selected_id = req.selection if isinstance(req.selection, str) else None
                card = next((c for c in discard_player.hand if c.id == selected_id), None) if selected_id else None
                if card is None and discard_player.hand:
                    card = discard_player.hand[0]
                if card:
                    discard_player.hand[:] = [c for c in discard_player.hand if c.id != card.id]
                    discard_player.graveyard.append(card)
                remaining = gs.pending_discard_choice.get("count", 1) - 1
                if remaining > 0:
                    gs.pending_discard_choice = {**gs.pending_discard_choice, "count": remaining}
                else:
                    gs.pending_discard_choice = None
            mgr.update(game_id, gs)

    elif choice_id == "dredge_skip":
        # US10: Player chooses not to dredge — just draw normally
        if gs.pending_dredge_choice:
            dredge_player_name = gs.pending_dredge_choice.get("player", gs.active_player)
            from mtg_engine.engine.zones import draw_card
            gs, _ = draw_card(gs, dredge_player_name)
            gs.pending_dredge_choice = None
            mgr.update(game_id, gs)

    # KW-19: Delve choice (CR 702.86) — resolve pending delve exile
    elif choice_id == "delve_resolve":
        if gs.pending_delve_choice:
            player_name = gs.pending_delve_choice.get("player", gs.priority_holder)
            from mtg_engine.engine.zones import get_player as _get_delve_player
            player = _get_delve_player(gs, player_name)
            if player:
                # Exile the specified cards from graveyard
                card_ids = gs.pending_delve_choice.get("card_ids", [])
                for cid in card_ids:
                    delve_card = next((c for c in player.graveyard if c.id == cid), None)
                    if delve_card:
                        player.graveyard.remove(delve_card)
                        player.exile.append(delve_card)
                        logger.info("Delve: %s exiled %s from graveyard", player_name, delve_card.name)
                # Clear pending choice
                gs.pending_delve_choice = None
            mgr.update(game_id, gs)

    elif choice_id == "commander_zone_replace":
        # CMD-01: CR 903.9 — player chooses to put commander into command zone
        if gs.pending_commander_zone_choice:
            player_name = gs.pending_commander_zone_choice.get("player", gs.priority_holder)
            card = gs.pending_commander_zone_choice.get("card")
            from mtg_engine.engine.formats.commander import move_card_to_command_zone
            if card:
                gs = move_card_to_command_zone(gs, card, player_name)
                logger.info("Commander zone choice: %s moved to command zone", card.name)
            gs.pending_commander_zone_choice = None
            mgr.update(game_id, gs)

    elif choice_id == "commander_zone_stay":
        # CMD-01: CR 903.9 — player chooses to let commander go to intended destination
        if gs.pending_commander_zone_choice:
            cmd = gs.pending_commander_zone_choice
            player_name = cmd.get("player", gs.priority_holder)
            card = cmd.get("card")
            intended = cmd.get("intended_destination", "graveyard")
            if card:
                # The card has already been removed from its source zone by the
                # initial move_permanent_to_zone / move_card_to_zone call that
                # queued this pending choice. We just need to place it in the
                # intended destination directly.
                player_obj = next(
                    (p for p in gs.players if p.name == player_name), None
                )
                if player_obj:
                    dest_list = getattr(player_obj, intended, None)
                    if dest_list is not None:
                        dest_list.append(card)
                logger.info("Commander zone choice: %s sent to %s", card.name, intended)
            gs.pending_commander_zone_choice = None
            mgr.update(game_id, gs)

    elif choice_id == "crew_confirm":
        # CR 702.147: Human resolves a pending Crew choice by tapping untapped
        # creatures it controls totalling the crew value; the vehicle becomes an
        # artifact creature until end of turn. req.selection may carry the subset
        # of creature ids to tap (otherwise all available untapped creatures are).
        if gs.pending_crew_choice:
            player_name = gs.pending_crew_choice.get("player", gs.priority_holder)
            from mtg_engine.ability.keywords.crew import resolve_crew_choice
            gs = resolve_crew_choice(gs, player_name, req.selection)
            mgr.update(game_id, gs)

    elif choice_id == "equip_confirm":
        # CR 702.5: Human resolves a pending Equip choice by attaching the
        # Equipment to one of the eligible creatures it controls (req.selection is
        # the chosen creature id; otherwise the choice is declined and cleared).
        if gs.pending_equip_choice:
            player_name = gs.pending_equip_choice.get("player", gs.priority_holder)
            from mtg_engine.ability.keywords.equip import resolve_equip_choice
            gs = resolve_equip_choice(gs, player_name, req.selection)
            mgr.update(game_id, gs)

    elif choice_id == "saddle_confirm":
        # Saddle (BLI 2025): Human resolves a pending ETB attachment by attaching the
        # saddle permanent to one of the eligible creatures it controls (req.selection
        # is the chosen creature id; otherwise the choice is cleared without attaching).
        # No sorcery-speed tap / mana cost — Saddle attaches as part of spell resolution.
        if gs.pending_saddle_choice:
            player_name = gs.pending_saddle_choice.get("player", gs.priority_holder)
            from mtg_engine.ability.keywords.saddle import resolve_saddle_choice
            gs = resolve_saddle_choice(gs, "saddle_confirm", req.selection)
            mgr.update(game_id, gs)

    elif choice_id == "cycling":
        # CR 702.36 / 702.46: Human resolves a pending Cycling / Type cycling
        # choice by paying the cost (from mana pool), discarding the card from hand
        # and drawing N cards (N=1 regular; N=card types for type-cycling). The
        # shared resolve_cycling_choice helper in cycle.py performs the pure
        # transform and clears pending_cycling_choice.
        if gs.pending_cycling_choice:
            player_name = gs.pending_cycling_choice.get("player", gs.priority_holder)
            from mtg_engine.ability.keywords.cycle import resolve_cycling_choice
            gs = resolve_cycling_choice(gs, player_name)
            mgr.update(game_id, gs)

    elif choice_id.startswith("dungeon_room_"):
        # VEN-01: Dungeon room choice — player selects a specific outcome
        if gs.pending_dungeon_room_choice:
            pending = gs.pending_dungeon_room_choice
            player_name = pending.get("player", gs.priority_holder)
            choices = pending.get("choices", [])
            selected_id = choice_id.replace("dungeon_room_", "", 1)

            # Find the matching choice
            chosen = None
            for c in choices:
                if c.get("choice_id") == selected_id:
                    chosen = c
                    break

            if chosen:
                from mtg_engine.engine.dungeon import _apply_room_effect
                outcome_ability = chosen.get("outcome_ability", "")
                gs = _apply_room_effect(gs, player_name, outcome_ability)
                logger.info("Dungeon room choice: %s selected %s for %s",
                            player_name, selected_id, outcome_ability)

            gs.pending_dungeon_room_choice = None
            mgr.update(game_id, gs)

    elif choice_id in ("buyback_pay", "buyback_pass"):
        # KW-27: Buyback (CR 702.27/702.28) — human resolves a deferred buyback
        # choice by paying (buyback_pay) or declining (buyback_pass) the
        # additional cost. The deferred cast is re-driven through cast_spell
        # with the buyback flag; cast_spell appends the buyback cost to the
        # base cost when the flag is set so the single payment flow deducts
        # both.
        if gs.pending_buyback_choice:
            pending = gs.pending_buyback_choice
            player_name = pending.get("player", gs.priority_holder)
            if gs.priority_holder != player_name:
                raise _err("Not your buyback choice", "INVALID_CHOICE")

            buyback_paid = (choice_id == "buyback_pay")
            base_cost = pending.get("base_cost") or ""
            bb_cost = pending.get("buyback_cost") or ""
            total_cost = base_cost + (bb_cost if buyback_paid else "")
            stored_payment = dict(pending.get("mana_payment") or {})

            # Tap untapped mana sources so the pool can cover the full cost
            # (base + buyback when paying), then build a payment that covers it.
            derived_payment: dict[str, int] = {}
            if total_cost:
                gs, derived_payment = _auto_tap_and_build_payment(gs, player_name, total_cost)

            # Use the stored (explicit/base) payment if it already covers the
            # full cost; otherwise fall back to the derived payment (which
            # covers base + buyback from the now-tapped pool).
            # NOTE: aliased import — ``get_player`` is also imported locally in
            # other branches of this function, which would make the bare name
            # function-local (UnboundLocalError) before those branches run.
            from mtg_engine.engine.zones import get_player as _bb_get_player
            from mtg_engine.engine.mana import can_pay_cost as _bb_can_pay
            _bb_player = _bb_get_player(gs, player_name)
            if stored_payment and _bb_can_pay(_bb_player.mana_pool, total_cost, stored_payment):
                payment = stored_payment
            else:
                payment = derived_payment
            if total_cost and not _bb_can_pay(_bb_player.mana_pool, total_cost, payment):
                raise _err(
                    f"Insufficient mana to pay the buyback cost {bb_cost}",
                    "INSUFFICIENT_MANA",
                )

            # Clear the pending choice, then re-drive the exact same cast.
            gs = gs.model_copy(update={"pending_buyback_choice": None})
            try:
                gs = cast_spell(
                    gs,
                    player_name,
                    pending.get("card_id", ""),
                    pending.get("targets") or [],
                    payment,
                    modes_chosen=pending.get("modes_chosen") or None,
                    x_value=pending.get("x_value", 0),
                    kicker_paid=bool(pending.get("kicker_paid", False)),
                    buyback_paid=buyback_paid,
                )
                gs = _run_sbas(gs)
            except ValueError as e:
                raise _err(str(e), "INVALID_ACTION")

            if not req.dry_run:
                mgr.update(game_id, gs)
                recorder = _get_recorder_safe(game_id, mgr)
                if recorder:
                    recorder.record_cast(
                        player_name,
                        pending.get("card_name", ""),
                        pending.get("targets") or [],
                        gs.turn, gs.phase.value, gs.step.value,
                        mana_cost=total_cost,
                    )

    elif choice_id in ("entwine_pay", "entwine_pass"):
        # KW-39: Entwine (CR 702.39) — human resolves a deferred entwine choice
        # by paying (entwine_pay) or declining (entwine_pass) the additional cost.
        # The deferred cast is re-driven through cast_spell with entwine_paid flag;
        # cast_spell appends the entwine cost to the base cost when the flag is set.
        if gs.pending_entwine_choice:
            pending = gs.pending_entwine_choice
            player_name = pending.get("player", gs.priority_holder)
            if gs.priority_holder != player_name:
                raise _err("Not your entwine choice", "INVALID_CHOICE")

            entwine_paid = (choice_id == "entwine_pay")
            base_cost = pending.get("base_cost") or ""
            ent_cost = pending.get("entwine_cost") or ""
            total_cost = base_cost + (ent_cost if entwine_paid else "")
            stored_payment = dict(pending.get("mana_payment") or {})

            # Tap untapped mana sources so the pool can cover the full cost
            # (base + entwine when paying), then build a payment that covers it.
            derived_payment: dict[str, int] = {}
            if total_cost:
                gs, derived_payment = _auto_tap_and_build_payment(gs, player_name, total_cost)

            from mtg_engine.engine.zones import get_player as _ent_get_player
            from mtg_engine.engine.mana import can_pay_cost as _ent_can_pay
            _ent_player = _ent_get_player(gs, player_name)
            if stored_payment and _ent_can_pay(_ent_player.mana_pool, total_cost, stored_payment):
                payment = stored_payment
            else:
                payment = derived_payment
            if total_cost and not _ent_can_pay(_ent_player.mana_pool, total_cost, payment):
                raise _err(
                    f"Insufficient mana to pay the entwine cost {ent_cost}",
                    "INSUFFICIENT_MANA",
                )

            # Determine modes chosen
            if entwine_paid:
                num_modes = pending.get("num_modes", 0)
                modes_chosen = list(range(num_modes))
            else:
                modes_chosen = pending.get("modes_chosen") or None

            # Clear pending choice, then re-drive cast
            gs = gs.model_copy(update={"pending_entwine_choice": None})
            try:
                gs = cast_spell(
                    gs,
                    player_name,
                    pending.get("card_id", ""),
                    pending.get("targets") or [],
                    payment,
                    modes_chosen=modes_chosen,
                    x_value=pending.get("x_value", 0),
                    kicker_paid=bool(pending.get("kicker_paid", False)),
                    entwine_paid=entwine_paid,
                )
                gs = _run_sbas(gs)
            except ValueError as e:
                raise _err(str(e), "INVALID_ACTION")

            if not req.dry_run:
                mgr.update(game_id, gs)
                recorder = _get_recorder_safe(game_id, mgr)
                if recorder:
                    recorder.record_cast(
                        player_name,
                        pending.get("card_name", ""),
                        pending.get("targets") or [],
                        gs.turn, gs.phase.value, gs.step.value,
                        mana_cost=total_cost,
                    )

    elif choice_id in ("overload_pay", "overload_pass"):
        # Overload (CR 702.95) — alternative cost. Human resolves deferred overload choice.
        if gs.pending_overload_choice:
            pending = gs.pending_overload_choice
            player_name = pending.get("player", gs.priority_holder)
            if gs.priority_holder != player_name:
                raise _err("Not your overload choice", "INVALID_CHOICE")

            overload_paid = (choice_id == "overload_pay")
            base_cost = pending.get("base_cost") or ""
            overload_cost = pending.get("overload_cost") or ""
            total_cost = overload_cost if overload_paid else base_cost
            stored_payment = dict(pending.get("mana_payment") or {})

            derived_payment: dict[str, int] = {}
            if total_cost:
                gs, derived_payment = _auto_tap_and_build_payment(gs, player_name, total_cost)

            from mtg_engine.engine.zones import get_player as _ol_get_player
            from mtg_engine.engine.mana import can_pay_cost as _ol_can_pay
            _ol_player = _ol_get_player(gs, player_name)
            if stored_payment and _ol_can_pay(_ol_player.mana_pool, total_cost, stored_payment):
                payment = stored_payment
            else:
                payment = derived_payment
            if total_cost and not _ol_can_pay(_ol_player.mana_pool, total_cost, payment):
                raise _err(
                    f"Insufficient mana to pay the overload cost {overload_cost}",
                    "INSUFFICIENT_MANA",
                )

            # Clear pending choice, then re-drive cast
            gs = gs.model_copy(update={"pending_overload_choice": None})
            try:
                gs = cast_spell(
                    gs,
                    player_name,
                    pending.get("card_id", ""),
                    pending.get("targets") or [],
                    payment,
                    modes_chosen=pending.get("modes_chosen") or None,
                    x_value=pending.get("x_value", 0),
                    kicker_paid=bool(pending.get("kicker_paid", False)),
                    overload_paid=overload_paid,
                )
                gs = _run_sbas(gs)
            except ValueError as e:
                raise _err(str(e), "INVALID_ACTION")

            if not req.dry_run:
                mgr.update(game_id, gs)
                recorder = _get_recorder_safe(game_id, mgr)
                if recorder:
                    recorder.record_cast(
                        player_name,
                        pending.get("card_name", ""),
                        pending.get("targets") or [],
                        gs.turn, gs.phase.value, gs.step.value,
                        mana_cost=total_cost,
                    )

    elif choice_id in ("convoke_pay", "convoke_pass"):
        # Convoke (CR 702.43) — human resolves deferred convoke choice.
        # If convoke_pay, tap selected creatures (or all eligible) to reduce cost.
        # For simplicity, we tap all eligible creatures when paying, otherwise none.
        if gs.pending_convoke_choice:
            pending = gs.pending_convoke_choice
            player_name = pending.get("player", gs.priority_holder)
            if gs.priority_holder != player_name:
                raise _err("Not your convoke choice", "INVALID_CHOICE")

            use_convoke = (choice_id == "convoke_pay")
            card_id = pending.get("card_id", "")
            card_name = pending.get("card_name", "")
            base_cost = pending.get("base_cost", "")

            # Determine which creatures to tap
            tapped_ids = []
            if use_convoke:
                # For human, we can tap all eligible creatures (or selection).
                # Use selection if provided, otherwise all eligible.
                selection = req.selection if isinstance(req.selection, list) else []
                eligible = pending.get("eligible_creatures", [])
                if selection:
                    tapped_ids = selection
                else:
                    tapped_ids = [c["id"] for c in eligible]

                # Tap creatures in game state (pure transform)
                new_battlefield = []
                for perm in gs.battlefield:
                    if perm.id in tapped_ids:
                        new_perm = perm.model_copy(update={"tapped": True})
                        new_battlefield.append(new_perm)
                    else:
                        new_battlefield.append(perm)
                gs = gs.model_copy(update={"battlefield": new_battlefield})

            # Compute effective cost after convoke reduction
            from mtg_engine.engine.mana import parse_mana_cost
            cost_dict = parse_mana_cost(base_cost)
            # Apply reduction
            if use_convoke and tapped_ids:
                # Simulate reduction: each creature reduces generic or matching color
                needed = {k: int(v) for k, v in cost_dict.items()}
                # Build mapping of creature colors
                creature_colors = {}
                for perm in gs.battlefield:
                    if perm.id in tapped_ids:
                        creature_colors[perm.id] = perm.card.colors or []
                for cid in tapped_ids:
                    colors = creature_colors.get(cid, [])
                    reduced = False
                    for color in colors:
                        if needed.get(color, 0) > 0:
                            needed[color] -= 1
                            reduced = True
                            break
                    if not reduced:
                        # Reduce generic
                        if needed.get("generic", 0) > 0:
                            needed["generic"] -= 1
                        elif needed.get("C", 0) > 0:
                            needed["C"] -= 1
                # Rebuild cost string
                cost_parts = []
                for sym, cnt in needed.items():
                    if cnt <= 0:
                        continue
                    if sym == "generic":
                        cost_parts.extend(["{" + str(cnt) + "}"] if cnt else [])
                    elif sym == "C":
                        cost_parts.extend(["{" + str(cnt) + "}"] if cnt else [])
                    else:
                        cost_parts.extend([f"{{{sym}}}"] * cnt)
                effective_cost = "".join(cost_parts)
            else:
                effective_cost = base_cost

            # Build mana payment for remaining cost
            derived_payment = {}
            if effective_cost:
                gs, derived_payment = _auto_tap_and_build_payment(gs, player_name, effective_cost)

            # Clear pending choice
            gs = gs.model_copy(update={"pending_convoke_choice": None})

            # Re-drive cast with reduced cost
            try:
                # Pass convoke creature ids via CastRequest? We'll just cast with current game state.
                # The cost reduction is already reflected in effective_cost via payment.
                # We need to pass mana_payment that covers effective cost.
                from mtg_engine.engine.zones import get_player as _cv_get_player
                from mtg_engine.engine.mana import can_pay_cost as _cv_can_pay
                _cv_player = _cv_get_player(gs, player_name)
                if effective_cost and not _cv_can_pay(_cv_player.mana_pool, effective_cost, derived_payment):
                    raise _err(f"Insufficient mana to pay convoke reduced cost", "INSUFFICIENT_MANA")
                gs = cast_spell(
                    gs,
                    player_name,
                    card_id,
                    pending.get("targets") or [],
                    derived_payment,
                    modes_chosen=pending.get("modes_chosen") or None,
                    x_value=pending.get("x_value", 0),
                    kicker_paid=bool(pending.get("kicker_paid", False)),
                )
                gs = _run_sbas(gs)
            except ValueError as e:
                raise _err(str(e), "INVALID_ACTION")

            if not req.dry_run:
                mgr.update(game_id, gs)
                recorder = _get_recorder_safe(game_id, mgr)
                if recorder:
                    recorder.record_cast(
                        player_name,
                        card_name,
                        pending.get("targets") or [],
                        gs.turn, gs.phase.value, gs.step.value,
                        mana_cost=effective_cost,
                    )

    elif choice_id in ("miracle_cast", "miracle_pass"):
        # Miracle (CR 702.93) — alternative cost triggered on first draw.
        if gs.pending_miracle_choice:
            pending = gs.pending_miracle_choice
            player_name = pending.get("player", gs.priority_holder)
            if gs.priority_holder != player_name:
                raise _err("Not your miracle choice", "INVALID_CHOICE")

            miracle_cost = pending.get("miracle_cost", "")
            card_id = pending.get("card_id", "")
            card_name = pending.get("card_name", "")

            if choice_id == "miracle_cast":
                # Cast the card for miracle cost as alternative cost
                from mtg_engine.engine.zones import get_player as _mi_get_player
                from mtg_engine.engine.mana import can_pay_cost as _mi_can_pay
                # Auto-tap and build payment for miracle cost
                gs, payment = _auto_tap_and_build_payment(gs, player_name, miracle_cost)
                _mi_player = _mi_get_player(gs, player_name)
                if miracle_cost and not _mi_can_pay(_mi_player.mana_pool, miracle_cost, payment):
                    raise _err(f"Insufficient mana to pay miracle cost {miracle_cost}", "INSUFFICIENT_MANA")
                # Clear pending before casting to avoid re-entrancy
                gs = gs.model_copy(update={"pending_miracle_choice": None})
                try:
                    gs = cast_spell(
                        gs,
                        player_name,
                        card_id,
                        targets=[],
                        mana_payment=payment,
                        alternative_cost=miracle_cost,
                    )
                    gs = _run_sbas(gs)
                except ValueError as e:
                    raise _err(str(e), "INVALID_ACTION")
                if not req.dry_run:
                    mgr.update(game_id, gs)
                    recorder = _get_recorder_safe(game_id, mgr)
                    if recorder:
                        recorder.record_cast(
                            player_name,
                            card_name,
                            [],
                            gs.turn, gs.phase.value, gs.step.value,
                            mana_cost=miracle_cost,
                        )
            else:
                # Pass: do not cast, card remains in hand
                gs = gs.model_copy(update={"pending_miracle_choice": None})
                if not req.dry_run:
                    mgr.update(game_id, gs)

    return _ok(gs)


# ─── Special action ───────────────────────────────────────────────────────────

@router.post("/{game_id}/special-action")
def special_action(game_id: str, req: SpecialActionRequest) -> dict:
    """POST /game/{game_id}/special-action. REQ-A16"""
    import re as _re_sa
    mgr = get_manager()
    gs = _get_gs(game_id)
    player_name = gs.priority_holder
    player = get_player(gs, player_name)

    if req.action_type == "special" and req.alternative_cost == "suspend":
        # T095: Suspend — exile card from hand with N time counters (CR 702.61a)
        # Time counters are tracked by encoding "suspended:N" into card.parse_status
        card = next((c for c in player.hand if c.id == req.card_id), None)
        if card is None:
            raise _err(f"Card {req.card_id!r} not in hand", "INVALID_ACTION")
        suspend_match = _re_sa.search(r'[Ss]uspend (\d+)[—–-](\{[^}]+\})', card.oracle_text or "")
        if not suspend_match:
            raise _err(f"{card.name} does not have suspend", "INVALID_ACTION")
        n_counters = int(suspend_match.group(1))
        suspend_cost = suspend_match.group(2)
        from mtg_engine.engine.mana import can_pay_cost
        if not can_pay_cost(player.mana_pool, suspend_cost):
            raise _err(f"Insufficient mana to suspend {card.name}", "INSUFFICIENT_MANA")
        # Auto-pay suspend cost from pool
        from mtg_engine.engine.mana import parse_mana_cost as _pmc, pay_cost as _pc
        cost_dict = _pmc(suspend_cost)
        mana_payment = {}
        for color in ("W", "U", "B", "R", "G", "C"):
            needed = cost_dict.get(color, 0)
            if needed > 0:
                mana_payment[color] = needed
        player.mana_pool = _pc(player.mana_pool, suspend_cost, mana_payment)
        # Move from hand to suspended_cards; encode time counter count in parse_status
        player.hand[:] = [c for c in player.hand if c.id != req.card_id]
        suspended = card.model_copy(update={"parse_status": f"suspended:{n_counters}"})
        player.suspended_cards.append(suspended)
        logger.info("%s suspended with %d time counters", card.name, n_counters)
        gs = _run_sbas(gs)

    elif req.action_type == "special" and req.alternative_cost == "foretell":
        # T096: Foretell — exile card face-down from hand for {2} (CR 702.143a)
        card = next((c for c in player.hand if c.id == req.card_id), None)
        if card is None:
            raise _err(f"Card {req.card_id!r} not in hand", "INVALID_ACTION")
        kws_lower = {k.lower() for k in (card.keywords or [])}
        oracle_lower = (card.oracle_text or "").lower()
        if "foretell" not in kws_lower and "foretell" not in oracle_lower:
            raise _err(f"{card.name} does not have foretell", "INVALID_ACTION")
        # Pay {2}
        from mtg_engine.engine.mana import can_pay_cost, pay_cost as _pc
        foretell_cost = "{2}"
        if not can_pay_cost(player.mana_pool, foretell_cost):
            raise _err("Insufficient mana for foretell ({2})", "INSUFFICIENT_MANA")
        mana_payment = {}
        available = player.mana_pool
        generic_needed = 2
        for color in ("W", "U", "B", "R", "G", "C"):
            have = getattr(available, color, 0)
            if have > 0 and generic_needed > 0:
                use = min(have, generic_needed)
                mana_payment[color] = use
                generic_needed -= use
        player.mana_pool = _pc(player.mana_pool, foretell_cost, mana_payment)
        # Move card from hand to foretold_cards exile zone
        player.hand[:] = [c for c in player.hand if c.id != req.card_id]
        player.foretold_cards.append(card)
        player.foretold_turns[card.id] = gs.turn
        logger.info("%s foretold (turn %d)", card.name, gs.turn)
        gs = _run_sbas(gs)

    else:
        raise _err(
            f"Special action {req.action_type!r}/{req.alternative_cost!r} not yet implemented",
            "NOT_IMPLEMENTED",
            422,
        )

    if not req.dry_run:
        mgr.update(game_id, gs)
    return _ok(gs)


@router.post("/{game_id}/foretell")
def foretell_card(game_id: str, req: ForetellRequest) -> dict:
    """POST /game/{game_id}/foretell — Exile a card face-down from hand for {2}. US29."""
    from mtg_engine.engine.mana import can_pay_cost
    mgr = get_manager()
    gs = _get_gs(game_id)
    player_name = gs.priority_holder
    player = get_player(gs, player_name)
    is_active = gs.active_player == player_name
    is_main = gs.phase == Phase.GAME_PLAY and gs.step in (Step.MAIN_FIRST, Step.MAIN_SECOND)

    if not is_active or not is_main:
        raise _err("Can only foretell on your turn during your main phase", "INVALID_ACTION")

    card = next((c for c in player.hand if c.id == req.card_id), None)
    if card is None:
        raise _err(f"Card {req.card_id!r} not in hand", "INVALID_ACTION")

    kws_lower = {k.lower() for k in (card.keywords or [])}
    oracle_lower = (card.oracle_text or "").lower()
    if "foretell" not in kws_lower and "foretell" not in oracle_lower:
        raise _err(f"{card.name} does not have foretell", "INVALID_ACTION")

    foretell_cost = "{2}"
    if not can_pay_cost(player.mana_pool, foretell_cost):
        raise _err("Insufficient mana for foretell ({2})", "INSUFFICIENT_MANA")

    from mtg_engine.engine.mana import pay_cost as _pc
    mana_payment = {}
    generic_needed = 2
    for color in ("W", "U", "B", "R", "G", "C"):
        have = getattr(player.mana_pool, color, 0)
        if have > 0 and generic_needed > 0:
            use = min(have, generic_needed)
            mana_payment[color] = use
            generic_needed -= use

    player.mana_pool = _pc(player.mana_pool, foretell_cost, mana_payment)
    player.hand[:] = [c for c in player.hand if c.id != req.card_id]
    player.foretold_cards.append(card)
    player.foretold_turns[card.id] = gs.turn
    logger.info("%s foretold (turn %d)", card.name, gs.turn)
    gs = _run_sbas(gs)

    mgr.update(game_id, gs)
    return _ok(gs)


# ─── Stack ────────────────────────────────────────────────────────────────────

@router.get("/{game_id}/stack")
def get_stack(game_id: str) -> dict:
    """GET /game/{game_id}/stack — current stack contents."""
    gs = _get_gs(game_id)
    return {"data": [s.model_dump() for s in gs.stack]}


# ─── Legal actions (TASK-17) ─────────────────────────────────────────────────

def _has_meaningful_actions(actions, strict: bool = False) -> bool:
    """Return True if there are actions other than pass.

    Mana abilities (activate_mana_ability) are normally filtered out since
    they're always available but rarely represent a meaningful decision on
    their own. When ``strict`` is True (e.g. priority held by a human),
    mana abilities are kept — so we don't auto-pass a human who might want
    to tap lands toward a cast.
    """
    for a in actions:
        if a.action_type == "pass":
            continue
        if not strict and a.action_type == "activate_mana_ability":
            continue
        return True
    return False


@router.get("/{game_id}/legal-actions")
def legal_actions(game_id: str) -> dict:
    """
    GET /game/{game_id}/legal-actions — compute all legal actions. REQ-S05, REQ-6.3.
    Must respond in under 200ms (REQ-P01).

    Auto-pass: if the only meaningful legal actions are "pass" (plus optional
    mana abilities), automatically submit pass and return the next state's
    legal actions. This prevents the UI/AI from being presented with an empty
    decision.
    """
    from mtg_engine.export.store import get_export_store
    from mtg_engine.engine.turn_manager import pass_priority
    mgr = get_manager()
    gs = _get_gs(game_id)

    # Auto-pass loop: if only "pass" (+ mana abilities) is available,
    # keep passing until someone has a real action or the game advances.
    max_auto_passes = 20
    for _ in range(max_auto_passes):
        is_human_priority = bool(
            gs.human_player_name and gs.priority_holder == gs.human_player_name
        )
        actions = _compute_legal_actions(gs)
        
        # If human has priority and ONLY pass action (no real choices), auto-pass immediately
        # This handles cases like untap phase where pass is the only legal action
        if is_human_priority and len(actions) == 1 and actions[0].action_type == "pass":
            logger.info("Auto-passing human in %s/%s (only pass available)", gs.phase.value, gs.step.value)
            gs = pass_priority(gs, gs.priority_holder)
            mgr.update(game_id, gs)
            continue
        
        if _has_meaningful_actions(actions, strict=False):
            break
        if gs.is_game_over:
            break
        # Only auto-pass if the stack is empty (stack items need resolution,
        # don't auto-skip those)
        if gs.stack:
            break
        gs = pass_priority(gs, gs.priority_holder)
        mgr.update(game_id, gs)
    else:
        logger.warning("Auto-pass loop exceeded %d iterations for game %s", max_auto_passes, game_id)

    actions = _compute_legal_actions(gs)
    actions_data = [a.model_dump() for a in actions]
    # Record snapshot at each priority grant (needed for UUID→name resolution in game log).
    store = get_export_store(game_id)
    snap = store.snapshots.record_snapshot(gs, actions_data)
    store.current_snapshot_id = snap.snapshot_id
    return {
        "data": {
            "priority_player": gs.priority_holder,
            "phase": gs.phase.value,
            "step": gs.step.value,
            "legal_actions": actions_data,
            "is_paused": mgr.is_paused(game_id),
            "is_game_over": gs.is_game_over,
            "winner": gs.winner,
            "snapshot_id": snap.snapshot_id,
        }
    }


@router.post("/{game_id}/pause")
def pause_game(game_id: str) -> dict:
    """Pause the game — the AI client will hold before its next decision."""
    mgr = get_manager()
    _get_gs(game_id)  # 404 if not found
    mgr.pause(game_id)
    return {"data": {"is_paused": True}}


@router.post("/{game_id}/resume")
def resume_game(game_id: str) -> dict:
    """Resume a paused game."""
    mgr = get_manager()
    _get_gs(game_id)  # 404 if not found
    mgr.resume(game_id)
    return {"data": {"is_paused": False}}


@router.post("/{game_id}/copy-spell")
def copy_spell(game_id: str, req) -> dict:
    """POST /game/{game_id}/copy-spell — Copy a spell on the stack. US7 (014)."""
    from mtg_engine.engine.stack import copy_spell_on_stack
    if not isinstance(req, dict):
        req = req.model_dump() if hasattr(req, "model_dump") else {}
    # Accept dict body directly for simplicity
    try:
        player_name = req.get("player_name", "")
        target_stack_id = req.get("target_stack_id", "")
        new_targets = req.get("new_targets", [])
    except Exception:
        raise _err("Invalid request body", "INVALID_REQUEST")
    gs = _get_gs(game_id)
    if gs.priority_holder != player_name:
        raise _err(f"{player_name} does not have priority", "PRIORITY_VIOLATION")
    if not any(o.id == target_stack_id for o in gs.stack):
        raise _err(f"Stack object {target_stack_id!r} not found", "STACK_OBJECT_NOT_FOUND")
    try:
        gs = copy_spell_on_stack(gs, target_stack_id, new_targets or None)
    except ValueError as e:
        raise _err(str(e), "COPY_SPELL_ERROR")
    mgr = get_manager()
    mgr.update(game_id, gs)
    return _ok(gs)


# ─── Mulligan endpoint (US6, T027) ───────────────────────────────────────────

@router.post("/{game_id}/mulligan")
def mulligan(game_id: str, req: dict) -> dict:
    """POST /game/{game_id}/mulligan — Mulligan decision (any variant)."""
    from mtg_engine.engine.mulligan import apply_mulligan, get_mulligan_type

    gs = _get_gs(game_id)

    player_name = req.get("player_name", "")
    keep = req.get("keep", True)

    if not gs.mulligan_phase_active:
        raise _err("Not in mulligan phase", "MULLIGAN_NOT_ACTIVE")

    player = get_player(gs, player_name)
    if player is None:
        raise _err(f"Player {player_name!r} not found", "PLAYER_NOT_FOUND")

    if player_name in gs.players_kept:
        raise _err(f"{player_name} has already committed to their hand", "ALREADY_KEPT")

    hand_size = len(player.hand)
    if not keep and hand_size <= 1:
        raise _err("Hand already at minimum size", "HAND_TOO_SMALL")

    mull_type = get_mulligan_type(gs)

    try:
        gs = apply_mulligan(gs, player_name, keep, mull_type)
    except ValueError as exc:
        raise _err(str(exc), "MULLIGAN_ERROR")

    mgr = get_manager()
    mgr.update(game_id, gs)
    return {
        "kept": keep or hand_size <= 1,
        "new_hand_size": len(player.hand),
        "hand": [c.model_dump() for c in player.hand],
    }


# ─── Activate loyalty endpoint (US4, T022) ───────────────────────────────────

@router.post("/{game_id}/activate-loyalty")
def activate_loyalty(game_id: str, req: dict) -> dict:
    """POST /game/{game_id}/activate-loyalty — Activate a planeswalker loyalty ability."""
    from mtg_engine.card_data.ability_parser import parse_loyalty_abilities
    gs = _get_gs(game_id)

    permanent_id = req.get("permanent_id", "")
    ability_index = req.get("ability_index", 0)
    targets = req.get("targets", [])

    perm = next((p for p in gs.battlefield if p.id == permanent_id), None)
    if perm is None:
        raise _err(f"Permanent {permanent_id!r} not found", "PERMANENT_NOT_FOUND")
    if "planeswalker" not in perm.card.type_line.lower():
        raise _err(f"{perm.card.name} is not a planeswalker", "NOT_PLANESWALKER")
    if perm.loyalty_activated_this_turn:
        raise _err(f"{perm.card.name} has already activated this turn", "ALREADY_ACTIVATED")

    abilities = parse_loyalty_abilities(perm.card.oracle_text or "")
    if ability_index >= len(abilities):
        raise _err(f"Ability index {ability_index} out of range", "ABILITY_INDEX_OOB")

    ability = abilities[ability_index]
    if ability.loyalty_change < 0 and perm.loyalty + ability.loyalty_change < 0:
        raise _err("Insufficient loyalty for this ability", "INSUFFICIENT_LOYALTY")

    old_loyalty = perm.loyalty
    perm.loyalty += ability.loyalty_change
    perm.loyalty_activated_this_turn = True

    mgr = get_manager()
    mgr.update(game_id, gs)
    return {
        "loyalty_change": ability.loyalty_change,
        "old_loyalty": old_loyalty,
        "new_loyalty": perm.loyalty,
        "effect_queued": True,
        "effect": ability.effect,
    }


# ─── Cascade choice endpoint (US31, T-cascade) ───────────────────────────────

@router.post("/{game_id}/cascade-choice")
def cascade_choice(game_id: str, req: dict) -> dict:
    """POST /game/{game_id}/cascade-choice — Resolve a cascade trigger."""
    gs = _get_gs(game_id)

    player_name = req.get("player_name", "")
    card_id = req.get("card_id", "")
    cast_it = req.get("cast", True)

    if gs.pending_cascade is None:
        raise _err("No cascade choice pending", "NO_CASCADE_PENDING")

    pending = gs.pending_cascade
    if pending.get("player_name") != player_name:
        raise _err(f"No cascade pending for {player_name!r}", "WRONG_PLAYER")
    if pending.get("card_id") != card_id:
        raise _err(f"Card {card_id!r} does not match offered cascade card", "WRONG_CASCADE_CARD")

    card_name = pending.get("card_name", "?")
    result = "spell_on_stack" if cast_it else "exiled"
    gs.pending_cascade = None

    mgr = get_manager()
    mgr.update(game_id, gs)
    return {
        "cast": cast_it,
        "card_name": card_name,
        "result": result,
    }


def _compute_legal_actions(gs: GameState) -> list[LegalAction]:
    """Compute all legal actions for the priority holder."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, ActivatedAbility
    from mtg_engine.engine.mana import can_pay_cost, is_mana_ability

    # Mulligan phase: mulligan actions + pass offered
    if gs.mulligan_phase_active:
        player_name = gs.priority_holder
        player = get_player(gs, player_name)
        base = [LegalAction(action_type="pass", description="Pass priority")]
        if player_name not in gs.players_kept:
            hand_size = len(player.hand)
            base += [
                LegalAction(
                    action_type="declare_mulligan",
                    description=f"Mulligan (draw {hand_size - 1})",
                ),
                LegalAction(
                    action_type="declare_mulligan",
                    description="Keep hand",
                ),
            ]
        return base

    # No priority is granted during the untap step (CR 502.4). Return only pass
    # so the AI immediately advances to upkeep rather than tapping permanents.
    if gs.step == Step.UNTAP:
        return [LegalAction(action_type="pass", description="Pass priority")]

    actions: list[LegalAction] = []
    player_name = gs.priority_holder
    player = get_player(gs, player_name)
    is_active = gs.active_player == player_name
    is_main = gs.step == Step.MAIN
    stack_empty = not gs.stack

    # CR 702.147: Crew choice pending for the priority holder — offer crew_confirm
    if gs.pending_crew_choice and gs.pending_crew_choice.get("player") == player_name:
        crew = gs.pending_crew_choice
        card_name = crew.get("card_name", "that vehicle")
        actions.append(LegalAction(
            action_type="choice",
            card_name="crew_confirm",
            description=f"Crew {card_name} (tap creatures totalling {crew.get('crew_value', 1)} power)",
            valid_targets=list(crew.get("available_creatures", [])),
        ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    # CR 702.5: Equip choice pending for the priority holder — offer equip_confirm,
    # but only under sorcery timing (CR 702.5: activate any time you could cast a
    # sorcery). The pending choice itself is only ever queued during sorcery speed
    # (see Equip.apply), so this guard keeps the gate explicit at the action layer.
    if (
        gs.pending_equip_choice
        and gs.pending_equip_choice.get("player") == player_name
        and gs.active_player == player_name
        and gs.step == Step.MAIN
        and not gs.stack
    ):
        equip = gs.pending_equip_choice
        card_name = equip.get("card_name", "that equipment")
        actions.append(LegalAction(
            action_type="choice",
            card_name="equip_confirm",
            description=f"Equip {card_name} (attach to a creature you control)",
            valid_targets=list(equip.get("available_creatures", [])),
        ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    # Saddle (BLI 2025) choice pending for the priority holder — a saddled permanent
    # entered the battlefield and is awaiting attachment to a creature it controls.
    # Unlike Equip there is NO sorcery-speed gate, no tap, and no mana cost: Saddle
    # attaches as part of spell resolution, not an activated ability. Offer the
    # saddle_confirm resolution (and pass) so the human can pick a target or decline.
    if gs.pending_saddle_choice and gs.pending_saddle_choice.get("player") == player_name:
        saddle = gs.pending_saddle_choice
        card_name = saddle.get("card_name", "that card")
        actions.append(LegalAction(
            action_type="choice",
            card_name="saddle_confirm",
            description=f"Saddle {card_name} (attach to a creature you control)",
            valid_targets=list(saddle.get("available_creatures", [])),
        ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    # CR 702.36 / 702.46: Cycling / Type cycling choice pending for the priority
    # holder — offer the "cycling" action, gated to sorcery timing (same style as
    # Equip: activate any time you could cast a sorcery). The pending choice is
    # only ever queued during that window, so this keeps the gate explicit at the
    # action layer. Cycling resolves from hand: pay cost, discard, draw N cards.
    if (
        gs.pending_cycling_choice
        and gs.pending_cycling_choice.get("player") == player_name
        and gs.active_player == player_name
        and gs.step == Step.MAIN
        and not gs.stack
    ):
        cycle = gs.pending_cycling_choice
        card_name = cycle.get("card_name", "that card")
        draw_count = int(cycle.get("draw_count", 1))
        actions.append(LegalAction(
            action_type="choice",
            card_name="cycling",
            description=f"Cycle {card_name} (pay {cycle.get('cost', '{1}')}, discard, draw {draw_count})",
        ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    # KW-27: Buyback (CR 702.27/702.28) choice pending for the priority holder —
    # a sorcery with "Buyback {cost}" is mid-cast. The player must resolve the
    # buyback decision (pay the additional cost or not) before the cast
    # completes; there is NO pass, because the cast cannot be left dangling.
    # Both outcomes complete the cast (with or without the buyback flag), so
    # only the two choices are offered — mirroring the Ward gate (no pass).
    if (
        gs.pending_buyback_choice
        and gs.pending_buyback_choice.get("player") == player_name
        and gs.active_player == player_name
        and gs.step == Step.MAIN
        and not gs.stack
    ):
        bb = gs.pending_buyback_choice
        card_name = bb.get("card_name", "that spell")
        bb_cost = bb.get("buyback_cost", "")
        actions.append(LegalAction(
            action_type="choice",
            card_name="buyback_pay",
            description=f"Pay buyback {bb_cost} ({card_name} returns to your hand)",
            valid_targets=[bb.get("card_id", "")],
        ))
        actions.append(LegalAction(
            action_type="choice",
            card_name="buyback_pass",
            description=f"Don't pay buyback {bb_cost} ({card_name} goes to the graveyard)",
            valid_targets=[bb.get("card_id", "")],
        ))
        return actions

    # KW-39: Entwine (CR 702.39) choice pending for the priority holder —
    # a modal spell with "Entwine {cost}" is mid-cast. The player must resolve
    # the entwine decision (pay to choose all modes or not) before the cast
    # completes; there is NO pass.
    if (
        gs.pending_entwine_choice
        and gs.pending_entwine_choice.get("player") == player_name
        and gs.active_player == player_name
        and gs.step == Step.MAIN
        and not gs.stack
    ):
        ent = gs.pending_entwine_choice
        card_name = ent.get("card_name", "that spell")
        ent_cost = ent.get("entwine_cost", "")
        actions.append(LegalAction(
            action_type="choice",
            card_name="entwine_pay",
            description=f"Pay entwine {ent_cost} ({card_name} — choose all modes)",
            valid_targets=[ent.get("card_id", "")],
        ))
        actions.append(LegalAction(
            action_type="choice",
            card_name="entwine_pass",
            description=f"Don't pay entwine {ent_cost} ({card_name} — choose one mode)",
            valid_targets=[ent.get("card_id", "")],
        ))
        return actions

    # Overload (CR 702.95) choice pending for the priority holder —
    # a spell with "Overload {cost}" is mid-cast. The player must resolve
    # the overload decision (pay alternative cost or not) before the cast
    # completes; there is NO pass.
    if (
        gs.pending_overload_choice
        and gs.pending_overload_choice.get("player") == player_name
        and gs.active_player == player_name
        and gs.step == Step.MAIN
        and not gs.stack
    ):
        ol = gs.pending_overload_choice
        card_name = ol.get("card_name", "that spell")
        ol_cost = ol.get("overload_cost", "")
        actions.append(LegalAction(
            action_type="choice",
            card_name="overload_pay",
            description=f"Pay overload {ol_cost} ({card_name} — target becomes each)",
            valid_targets=[ol.get("card_id", "")],
        ))
        actions.append(LegalAction(
            action_type="choice",
            card_name="overload_pass",
            description=f"Don't pay overload {ol_cost} ({card_name} — pay base cost)",
            valid_targets=[ol.get("card_id", "")],
        ))
        return actions

    # Convoke (CR 702.43) choice pending for the priority holder —
    # a spell with Convoke is mid-cast. The player must resolve convoke
    # decision (use convoke to reduce cost or not) before the cast completes;
    # there is NO pass.
    if (
        gs.pending_convoke_choice
        and gs.pending_convoke_choice.get("player") == player_name
        and gs.active_player == player_name
        and gs.step == Step.MAIN
        and not gs.stack
    ):
        conv = gs.pending_convoke_choice
        card_name = conv.get("card_name", "that spell")
        actions.append(LegalAction(
            action_type="choice",
            card_name="convoke_pay",
            description=f"Use Convoke to reduce cost of {card_name}",
            valid_targets=[conv.get("card_id", "")],
        ))
        actions.append(LegalAction(
            action_type="choice",
            card_name="convoke_pass",
            description=f"Don't use Convoke for {card_name}",
            valid_targets=[conv.get("card_id", "")],
        ))
        return actions

    # Miracle (CR 702.93) choice pending for the priority holder —
    # the card was drawn as first card this turn and has Miracle.
    # Player may cast for miracle cost or pass (card remains in hand).
    if (
        gs.pending_miracle_choice
        and gs.pending_miracle_choice.get("player") == player_name
    ):
        mi = gs.pending_miracle_choice
        card_name = mi.get("card_name", "that card")
        mi_cost = mi.get("miracle_cost", "")
        actions.append(LegalAction(
            action_type="choice",
            card_name="miracle_cast",
            description=f"Cast {card_name} for miracle cost {mi_cost}",
            valid_targets=[mi.get("card_id", "")],
        ))
        actions.append(LegalAction(
            action_type="choice",
            card_name="miracle_pass",
            description=f"Don't cast {card_name} for miracle (keep in hand)",
            valid_targets=[mi.get("card_id", "")],
        ))
        return actions

    # Early-exit: ETB choice pending (034-etb-choices)
    if gs.pending_etb_choice and gs.pending_etb_choice.get("player") == player_name:
        etb = gs.pending_etb_choice
        perm_name = etb.get("permanent_name", "that land")
        choice_type = etb.get("choice_type", "")
        
        if choice_type == "shockland":
            cost = etb.get("cost_amount", 2)
            actions.append(LegalAction(
                action_type="choice",
                card_name="etb_pay",
                description=f"Pay {cost} life → {perm_name} enters untapped",
                valid_targets=[etb.get("permanent_id", "")],
            ))
            actions.append(LegalAction(
                action_type="choice",
                card_name="etb_tapped",
                description=f"Don't pay → {perm_name} enters tapped",
                valid_targets=[etb.get("permanent_id", "")],
            ))
            if not any(a.action_type == "pass" for a in actions):
                actions.append(LegalAction(action_type="pass", description="Pass priority"))
            return actions
        
        # For other choice types, add similar logic
        # For now, default to enter tapped for checklands/fetchlands without pending
        # TODO: implement checkland/fetchland handling

    # CMD-01: Commander zone replacement (CR 903.9)
    if gs.pending_commander_zone_choice and gs.pending_commander_zone_choice.get("player") == player_name:
        cmd = gs.pending_commander_zone_choice
        card_name = cmd.get("card", {}).name if cmd.get("card") else "that commander"
        intended = cmd.get("intended_destination", "graveyard")
        actions.append(LegalAction(
            action_type="choice",
            card_name="commander_zone_replace",
            description=f"Put {card_name} into your command zone instead of {intended}",
        ))
        actions.append(LegalAction(
            action_type="choice",
            card_name="commander_zone_stay",
            description=f"Let {card_name} go to {intended}",
        ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    # Spree mode selection
    if gs.pending_spree_choice and gs.pending_spree_choice.get("player") == player_name:
        modes = gs.pending_spree_choice.get("modes", [])
        for i, mode in enumerate(modes):
            cost = mode.get("cost", "")
            effect = mode.get("effect", "")[:50]  # truncate for display
            actions.append(LegalAction(
                action_type="choice",
                description=f"+ {cost} — {effect}...",
                valid_targets=[str(i)],
                card_name="spree_select",
            ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    # KW-19: Delve choice (CR 702.86)
    if gs.pending_delve_choice and gs.pending_delve_choice.get("player") == player_name:
        actions.append(LegalAction(
            action_type="delve_resolve",
            description="Resolve Delve: exile cards from graveyard to reduce cost",
        ))
    # VEN-01: Dungeon room choice (CR 701.61)
    if gs.pending_dungeon_room_choice and gs.pending_dungeon_room_choice.get("player") == player_name:
        pending = gs.pending_dungeon_room_choice
        choices = pending.get("choices", [])
        dungeon_name = pending.get("dungeon_name", "Dungeon")
        for choice in choices:
            cid = choice.get("choice_id", "")
            desc = choice.get("description", f"Choose {cid}")
            actions.append(LegalAction(
                action_type="choice",
                card_name=f"dungeon_room_{cid}",
                description=f"[{dungeon_name}] {desc}",
            ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    # Early-exit: pending blocking choices — these block all other actions until resolved
    if gs.pending_scry_choice and gs.pending_scry_choice.get("player") == player_name:
        scry_cards = gs.pending_scry_choice.get("cards", [])
        card_ids = [c.get("id", c.get("name", "?")) if isinstance(c, dict) else c for c in scry_cards]

        # Check if this is a reveal-and-choose effect (e.g., Sleight of Hand)
        effect_type = gs.pending_scry_choice.get("effect_type", "")

        # Regular Scry reorder (CR 701.20) — the player reorders the revealed cards
        # in any order; the single legal action offers ``scry`` and the client sends
        # the desired top->bottom ordering as req.selection (a list of card ids).
        if effect_type == "scry":
            actions.append(LegalAction(
                action_type="choice",
                description=f"Scry {len(scry_cards)}: reorder library (send top->bottom order)",
                valid_targets=card_ids,
                card_name="scry",
            ))
            if not any(a.action_type == "pass" for a in actions):
                actions.append(LegalAction(action_type="pass", description="Pass priority"))
            return actions

        if effect_type == "reveal_and_choose":
            # Player chooses one card to put into hand, rest go to bottom
            actions.append(LegalAction(
                action_type="choice",
                description="Choose a card to put in your hand",
                valid_targets=card_ids,
                card_name="reveal_put_hand",
            ))
            if not any(a.action_type == "pass" for a in actions):
                actions.append(LegalAction(action_type="pass", description="Pass priority"))
            return actions
        
        if effect_type == "reveal_and_choose_multi":
            # Player chooses multiple cards to put into hand (e.g., Stock Up - choose 2)
            put_count = gs.pending_scry_choice.get("put_count", 2)
            actions.append(LegalAction(
                action_type="choice",
                description=f"Choose {put_count} cards to put in your hand",
                valid_targets=card_ids,
                card_name="reveal_put_hand_multi",
                selection=put_count,
            ))
            if not any(a.action_type == "pass" for a in actions):
                actions.append(LegalAction(action_type="pass", description="Pass priority"))
            return actions
        
        # Regular scry: keep on top or put all on bottom
        actions.append(LegalAction(
            action_type="choice",
            description=f"Scry {len(scry_cards)}: keep on top",
            valid_targets=card_ids,
            card_name="scry_keep",
        ))
        actions.append(LegalAction(
            action_type="choice",
            description=f"Scry {len(scry_cards)}: put all on bottom",
            valid_targets=card_ids,
            card_name="scry_bottom",
        ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    if gs.pending_surveil_choice and gs.pending_surveil_choice.get("player") == player_name:
        surveil_cards = gs.pending_surveil_choice.get("cards", [])
        card_ids = [c.get("id", c.get("name", "?")) if isinstance(c, dict) else c for c in surveil_cards]
        actions.append(LegalAction(
            action_type="choice",
            description=f"Surveil {len(surveil_cards)}: keep on top",
            valid_targets=card_ids,
            card_name="surveil_keep",
        ))
        actions.append(LegalAction(
            action_type="choice",
            description=f"Surveil {len(surveil_cards)}: put all in graveyard",
            valid_targets=card_ids,
            card_name="surveil_graveyard",
        ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    if gs.pending_tutor_choice and gs.pending_tutor_choice.get("player") == player_name:
        filter_type = gs.pending_tutor_choice.get("filter_type", "")
        destination = gs.pending_tutor_choice.get("destination", "hand")
        lib_card_ids = [c.id for c in player.library]
        actions.append(LegalAction(
            action_type="choice",
            card_name="tutor_pick",
            description=f"Search library for {filter_type} → {destination}",
            valid_targets=lib_card_ids,
        ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    if gs.pending_discard_choice and gs.pending_discard_choice.get("player") == player_name:
        is_duress = gs.pending_discard_choice.get("is_duress_effect", False)
        
        if is_duress:
            # Duress effect: show opponent's hand as choices
            opponent_hand = gs.pending_discard_choice.get("opponent_hand", [])
            hand_ids = [c.get("id", "") for c in opponent_hand]
            hand_names = [c.get("name", "?") for c in opponent_hand]
            card_desc = ", ".join(hand_names[:3])
            if len(hand_names) > 3:
                card_desc += f"... (+{len(hand_names)-3} more)"
            actions.append(LegalAction(
                action_type="choice",
                card_name="discard_pick",
                description=f"Pick card for opponent to discard: {card_desc}",
                valid_targets=hand_ids,
            ))
        else:
            # Normal discard: show player's own hand
            count = gs.pending_discard_choice.get("count", 1)
            hand_ids = [c.id for c in player.hand]
            actions.append(LegalAction(
                action_type="choice",
                card_name="discard_pick",
                description=f"Discard {count} card(s)",
                valid_targets=hand_ids,
            ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    if gs.pending_ward_payment and gs.pending_ward_payment.get("player") == player_name:
        # Ward is MANDATORY (CR 702.145a): the ward controller must either pay
        # or let the targeting spell be countered — "do nothing" (pass) is NOT
        # a legal outcome, unlike optional ETB/crew choices. Offering pass here
        # would let the spell resolve uncountered with pending_ward_payment
        # still dangling, bypassing Ward for free.
        ward_cost = gs.pending_ward_payment.get("ward_cost", "")
        targeting_spell_id = gs.pending_ward_payment.get("targeting_spell_id", "")
        # "ability" tag (CR 702.145a activated-ability case) vs the spell path.
        ward_target_kind = (
            "ability"
            if gs.pending_ward_payment.get("targeting_type") == "ability"
            else "spell"
        )
        actions.append(LegalAction(
            action_type="choice",
            card_name="ward_pay",
            description=f"Pay ward {ward_cost} ({ward_target_kind} targeting your permanent continues)",
            valid_targets=[targeting_spell_id],
        ))
        actions.append(LegalAction(
            action_type="choice",
            card_name="ward_counter",
            description=f"Don't pay ward {ward_cost} (targeting {ward_target_kind} is countered)",
            valid_targets=[targeting_spell_id],
        ))
        return actions

    if gs.pending_echo_payment and gs.pending_echo_payment.get("player") == player_name:
        echo_cost = gs.pending_echo_payment.get("echo_cost", "")
        permanent_id = gs.pending_echo_payment.get("permanent_id", "")
        permanent = next((p for p in gs.battlefield if p.id == permanent_id), None)
        permanent_name = permanent.card.name if permanent else "unknown"
        actions.append(LegalAction(
            action_type="choice",
            card_name="echo_pay",
            description=f"Pay echo {echo_cost} for {permanent_name}",
            valid_targets=[permanent_id],
        ))
        actions.append(LegalAction(
            action_type="choice",
            card_name="echo_decline",
            description=f"Don't pay echo {echo_cost} ({permanent_name} is sacrificed)",
            valid_targets=[permanent_id],
        ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    if gs.pending_cascade and gs.pending_cascade.get("player") == player_name:
        found_card = gs.pending_cascade.get("found_card", {})
        cascade_card_id = found_card.get("id", "") if isinstance(found_card, dict) else ""
        cascade_card_name = found_card.get("name", "?") if isinstance(found_card, dict) else "?"
        actions.append(LegalAction(
            action_type="cascade_choice",
            cascade_card_id=cascade_card_id,
            card_name=cascade_card_name,
            description=f"Cascade: cast {cascade_card_name} for free",
            valid_targets=[cascade_card_id],
        ))
        actions.append(LegalAction(
            action_type="cascade_choice",
            cascade_card_id=cascade_card_id,
            card_name=cascade_card_name,
            description=f"Cascade: exile {cascade_card_name} (skip)",
            valid_targets=[],
        ))
        if not any(a.action_type == "pass" for a in actions):
            actions.append(LegalAction(action_type="pass", description="Pass priority"))
        return actions

    if gs.pending_dredge_choice and gs.pending_dredge_choice.get("player") == player_name:
        dredgeable_cards = gs.pending_dredge_choice.get("dredgeable_cards", [])
        dredge_numbers = gs.pending_dredge_choice.get("dredge_numbers", {})
        card_ids = [c.id for c in dredgeable_cards]
        
        # Offer each dredgeable card
        for card in dredgeable_cards:
            dredge_n = dredge_numbers.get(card.id, 1)
            actions.append(LegalAction(
                action_type="dredge",
                card_id=card.id,
                card_name=card.name,
                description=f"Dredge {card.name} (look at top {dredge_n} cards, put one into hand and rest into graveyard)",
                valid_targets=[card.id],
            ))
        
        # Always offer to just draw normally instead of dredging
        actions.append(LegalAction(
            action_type="choice",
            card_name="dredge_skip",
            description="Draw normally (don't dredge)",
            valid_targets=[],
        ))
        return actions

    # US13 (T031): Proliferate pending choice
    if gs.pending_proliferate_choice and gs.pending_proliferate_choice.get("player") == player_name:
        eligible = gs.pending_proliferate_choice.get("eligible", [])
        eligible_ids = [e["id"] for e in eligible]
        actions.append(LegalAction(
            action_type="proliferate",
            description="Proliferate: choose any number of permanents/players with counters",
            valid_targets=eligible_ids,
        ))
        return actions

    # Always can pass priority
    actions.append(LegalAction(
        action_type="pass",
        description="Pass priority",
    ))

    # Play land: active player, main phase, stack empty, one land per turn.
    # Fortifications are lands (CR 301.7) even when "land" isn't in the type line.
    from mtg_engine.ability.keywords.fortify import Fortify
    if is_active and is_main and stack_empty and player.lands_played_this_turn < 1:
        for card in player.hand:
            if Fortify.is_land_card(card):
                actions.append(LegalAction(
                    action_type="play_land",
                    card_id=card.id,
                    card_name=card.name,
                    description=f"Play {card.name}",
                ))

    # Cast spells
    import re as _re_spell
    from mtg_engine.engine.stack import _is_sorcery_speed, _can_cast_at_sorcery_speed, _has_split_second

    # Pre-compute mana helpers (used by both cast section and activate section below).
    _re = _re_spell
    _MANA_ADD_RE = _re.compile(r"add\s+\{([WUBRGC])\}", _re.IGNORECASE)

    def _mana_add_symbol(effect: str) -> str | None:
        m = _MANA_ADD_RE.search(effect)
        return m.group(1).upper() if m else None

    def _pool_after_add(pool: "ManaPool", symbol: str) -> "ManaPool":
        from mtg_engine.engine.mana import add_mana
        return add_mana(pool, symbol)

    def _castable_count(pool: "ManaPool") -> int:
        return sum(
            1 for card in player.hand
            if "land" not in card.type_line.lower()
            and can_pay_cost(pool, card.mana_cost or "")
            and (not _is_sorcery_speed(card) or _can_cast_at_sorcery_speed(gs, player_name))
        )

    def _total_available_pool() -> "ManaPool":
        """Current pool plus mana producible from every untapped mana source."""
        from mtg_engine.engine.mana import add_mana
        pool = player.mana_pool.model_copy()
        for p in gs.battlefield:
            if p.controller != player_name or p.tapped:
                continue
            _p_is_creature = "creature" in p.card.type_line.lower()
            if _p_is_creature and p.summoning_sick:
                continue
            p_abs = parse_oracle_text(p.card.oracle_text or "", p.card.type_line)
            for p_ab in p_abs:
                if isinstance(p_ab, ActivatedAbility):
                    sym = _mana_add_symbol(p_ab.effect)
                    if sym:
                        pool = add_mana(pool, sym)
        return pool

    # Precompute available targets for "target creature" spells.
    _any_creature_on_bf = any(
        "creature" in p.card.type_line.lower() for p in gs.battlefield
    )

    def _has_required_targets(card: "Card") -> bool:
        """Return False if the spell requires a target that doesn't exist yet."""
        oracle = (card.oracle_text or "").lower()
        type_lower = card.type_line.lower()
        if "enchantment" in type_lower and "enchant creature" in oracle:
            return _any_creature_on_bf
        if _re_spell.search(r"\btarget creature\b", oracle):
            return _any_creature_on_bf
        return True

    def _get_spell_colors(card: "Card") -> set[str]:
        """Extract color names from the card's mana cost symbols."""
        cost = card.mana_cost or ""
        mapping = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}
        return {color for sym, color in mapping.items()
                if f"{{{sym}}}" in cost or f"{{{sym}/" in cost}

    def _get_protection_colors(perm: "Permanent") -> set[str]:
        """Parse 'protection from [color]' from oracle text."""
        oracle = (perm.card.oracle_text or "").lower()
        colors = {"white", "blue", "black", "red", "green"}
        return {c for c in colors if f"protection from {c}" in oracle}

    def _is_targetable(perm: "Permanent", targeting_player: str, spell_card: "Card") -> bool:
        """Return False if perm cannot be targeted by spell_card cast by targeting_player."""
        # US15 (Phasing, CR 702.26a): a phased-out permanent is treated as though it
        # doesn't exist — it can never be chosen as a target. Checked first so the
        # aura/pump/removal/burn spell-target comprehensions all exclude it.
        if getattr(perm, "phased_out", False):
            return False
        kws = [k.lower() for k in (perm.card.keywords or [])]
        oracle = (perm.card.oracle_text or "").lower()
        # Shroud: untargetable by anyone
        if "shroud" in kws or "shroud" in oracle:
            return False
        # Hexproof: only opponent cannot target
        if ("hexproof" in kws or "hexproof" in oracle) and targeting_player != perm.controller:
            return False
        # Protection from color
        protected = _get_protection_colors(perm)
        if protected:
            spell_colors = _get_spell_colors(spell_card)
            if spell_colors & protected:
                return False
        return True

    # Compute mana available for X spells
    def _count_colored_pips(cost: str) -> int:
        """Count non-generic, non-X mana symbols."""
        return len(_re_spell.findall(r'\{[WUBRG]\}', cost, _re_spell.IGNORECASE))

    def _total_available_mana() -> int:
        """Total mana producible from pool + untapped sources."""
        pool = _total_available_pool()
        return pool.W + pool.U + pool.B + pool.R + pool.G + pool.C

    if not _has_split_second(gs):
        for card in player.hand:
            if "land" in card.type_line.lower():
                continue
            sorcery_speed = _is_sorcery_speed(card)
            if sorcery_speed and not _can_cast_at_sorcery_speed(gs, player_name):
                continue
            if not _has_required_targets(card):
                continue
            # Show spell if payable with current pool OR after tapping available lands.
            # Mana is tapped just-in-time by the game loop when the AI commits to casting.
            mana_cost = card.mana_cost or ""
            has_x = "{X}" in mana_cost or "{x}" in mana_cost
            if can_pay_cost(player.mana_pool, mana_cost) or can_pay_cost(_total_available_pool(), mana_cost) or has_x:
                # Build full valid_targets list so the AI client can pick the best target.
                # The AI selects via _select_best_target(); the engine enforces legality
                # at resolution time.
                spell_targets: list[str] = []
                oracle_lower = (card.oracle_text or "").lower()
                is_aura = "enchantment" in card.type_line.lower() and "enchant creature" in oracle_lower
                is_pump = bool(_re_spell.search(r"target creature gets \+\d+/\+\d+", oracle_lower))
                is_removal = bool(_re_spell.search(r"destroy target|exile target", oracle_lower))
                is_burn = bool(_re_spell.search(r"deals?\s+\d+\s+damage\s+to\s+(?:any target|target creature|target player)", oracle_lower))
                is_counter = bool(_re_spell.search(r"counter target spell", oracle_lower))
                opp_names = [p.name for p in gs.players if p.name != player_name]

                if is_counter:
                    # US22 T173: exclude uncounterable stack objects from valid targets
                    spell_targets = [
                        s.id for s in gs.stack
                        if not s.uncounterable
                    ]
                elif is_aura or is_pump:
                    # Friendly + own creatures; filter by hexproof/shroud/protection
                    spell_targets = [
                        p.id for p in gs.battlefield
                        if "creature" in p.card.type_line.lower()
                        and _is_targetable(p, player_name, card)
                    ]
                elif is_removal:
                    # Opponent creatures/planeswalkers; filter by hexproof/shroud/protection
                    spell_targets = [
                        p.id for p in gs.battlefield
                        if p.controller in opp_names
                        and (
                            "creature" in p.card.type_line.lower()
                            or "planeswalker" in p.card.type_line.lower()
                        )
                        and _is_targetable(p, player_name, card)
                    ]
                elif is_burn:
                    # All creatures + opponent player names; filter permanents
                    spell_targets = [
                        p.id for p in gs.battlefield
                        if (
                            "creature" in p.card.type_line.lower()
                            or "planeswalker" in p.card.type_line.lower()
                        )
                        and _is_targetable(p, player_name, card)
                    ] + opp_names

                # X spells: generate one action per X value (1 to max_x)
                if has_x:
                    colored_pips = _count_colored_pips(mana_cost)
                    avail = _total_available_mana()
                    max_x = min(10, max(0, avail - colored_pips))
                    for x_val in range(1, max_x + 1):
                        actions.append(LegalAction(
                            action_type="cast",
                            card_id=card.id,
                            card_name=card.name,
                            valid_targets=spell_targets,
                            x_value=x_val,
                            mana_options=[{"mana_cost": mana_cost, "x_value": x_val}],
                            description=f"Cast {card.name} (X={x_val})",
                        ))
                else:
                    actions.append(LegalAction(
                        action_type="cast",
                        card_id=card.id,
                        card_name=card.name,
                        valid_targets=spell_targets,
                        mana_options=[{"mana_cost": mana_cost}],
                        description=f"Cast {card.name}",
                    ))

    # Phyrexian mana alternative cast (US33, T094)
    # When a card has {X/P} in its cost, offer a life-payment alternative
    import re as _re_phyrexian
    _PHYREXIAN_RE = _re_phyrexian.compile(r'\{[WUBRG]/P\}', _re_phyrexian.IGNORECASE)
    if _can_cast_at_sorcery_speed(gs, player_name) and not _has_split_second(gs):
        for card in player.hand:
            if "land" in card.type_line.lower():
                continue
            mana_cost = card.mana_cost or ""
            if _PHYREXIAN_RE.search(mana_cost):
                # Count how many Phyrexian symbols are in the cost (each costs 2 life)
                phyrexian_count = len(_re_phyrexian.findall(r'\{[WUBRG]/P\}', mana_cost, _re_phyrexian.IGNORECASE))
                life_cost = phyrexian_count * 2
                if player.life > life_cost:
                    # Can pay by spending life instead of colored mana
                    actions.append(LegalAction(
                        action_type="cast",
                        card_id=card.id,
                        card_name=card.name,
                        valid_targets=[],
                        alternative_cost="phyrexian",
                        mana_options=[{"mana_cost": mana_cost}],
                        description=f"Cast {card.name} (phyrexian, -{life_cost} life)",
                    ))

    # Alternative casting costs (US18, T057-T059) — convoke, delve, emerge
    if _can_cast_at_sorcery_speed(gs, player_name) and not _has_split_second(gs):
        _untapped_creatures = [
            p for p in gs.battlefield
            if p.controller == player_name
            and not p.tapped
            and "creature" in p.card.type_line.lower()
        ]
        _graveyard_count = len(player.graveyard)

        for card in player.hand:
            if "land" in card.type_line.lower():
                continue
            kws_lower = {k.lower() for k in (card.keywords or [])}
            oracle_lower = (card.oracle_text or "").lower()

            # Convoke: each creature tapped can substitute for {1} or one colored mana
            if "convoke" in kws_lower or "convoke" in oracle_lower:
                convoke_creature_ids = [p.id for p in _untapped_creatures]
                if convoke_creature_ids:
                    actions.append(LegalAction(
                        action_type="cast",
                        card_id=card.id,
                        card_name=card.name,
                        valid_targets=convoke_creature_ids,
                        alternative_cost="convoke",
                        mana_options=[{"mana_cost": card.mana_cost or ""}],
                        description=f"Cast {card.name} (convoke)",
                    ))

            # Delve: each exiled graveyard card reduces {1} from cost
            if "delve" in kws_lower or "delve" in oracle_lower:
                if _graveyard_count > 0:
                    gyard_ids = [c.id for c in player.graveyard]
                    actions.append(LegalAction(
                        action_type="cast",
                        card_id=card.id,
                        card_name=card.name,
                        valid_targets=gyard_ids,
                        alternative_cost="delve",
                        mana_options=[{"mana_cost": card.mana_cost or ""}],
                        description=f"Cast {card.name} (delve)",
                    ))

            # Evoke alternative cost (CR 702.41) — pay evoke cost instead of mana cost, sacrifice on ETB
            from mtg_engine.engine.evoke import parse_evoke_cost as _parse_evoke_cost, has_evoke as _has_evoke
            if "creature" in card.type_line.lower():
                if _has_evoke(card.oracle_text) or "evoke" in oracle_lower:
                    evoke_cost = _parse_evoke_cost(card.oracle_text or "")
                    if evoke_cost and (can_pay_cost(player.mana_pool, evoke_cost) or can_pay_cost(_total_available_pool(), evoke_cost)):
                        actions.append(LegalAction(
                            action_type="cast",
                            card_id=card.id,
                            card_name=card.name,
                            alternative_cost="evoke",
                            mana_options=[{"mana_cost": evoke_cost}],
                            description=f"Cast {card.name} (evoke {evoke_cost})",
                        ))

            # Emerge: sacrifice a creature to reduce cost by sacrificed creature's CMC
            if "emerge" in kws_lower or "emerge" in oracle_lower:
                for sac_creature in _untapped_creatures:
                    actions.append(LegalAction(
                        action_type="cast",
                        card_id=card.id,
                        card_name=card.name,
                        valid_targets=[sac_creature.id],
                        alternative_cost="emerge",
                        mana_options=[{"mana_cost": card.mana_cost or ""}],
                        description=f"Cast {card.name} (emerge, sacrifice {sac_creature.card.name})",
                    ))

            # Kicker: offer a separate cast action with kicker_paid=True
            kicker_match = _re_spell.search(r'[Kk]icker (\{[^}]+\})', card.oracle_text or "")
            if kicker_match:
                kicker_cost = kicker_match.group(1)
                base_cost = card.mana_cost or ""
                combined_cost = base_cost + kicker_cost
                if can_pay_cost(player.mana_pool, combined_cost) or can_pay_cost(_total_available_pool(), combined_cost):
                    actions.append(LegalAction(
                        action_type="cast",
                        card_id=card.id,
                        card_name=card.name,
                        valid_targets=[],
                        kicker_paid=True,
                        alternative_cost="kicker",
                        mana_options=[{"mana_cost": base_cost, "kicker_cost": kicker_cost}],
                        description=f"Cast {card.name} with kicker",
                    ))

            # Jump-start: cast from graveyard by discarding a card
            if "jump-start" in kws_lower or "jump-start" in oracle_lower:
                if player.hand:
                    discard_id = player.hand[0].id  # AI picks first card; engine just needs a valid ID
                    actions.append(LegalAction(
                        action_type="cast",
                        card_id=card.id,
                        card_name=card.name,
                        from_graveyard=True,
                        valid_targets=[discard_id],
                        alternative_cost="jump-start",
                        mana_options=[{"mana_cost": card.mana_cost or ""}],
                        description=f"Cast {card.name} (jump-start, discard a card)",
                    ))

    # Suspend: exile card with time counters from hand (sorcery speed, main phase only)
    if is_active and is_main and stack_empty and not _has_split_second(gs):
        for card in player.hand:
            if "land" in card.type_line.lower():
                continue
            suspend_match = _re_spell.search(r'[Ss]uspend (\d+)[—–-](\{[^}]+\})', card.oracle_text or "")
            if suspend_match:
                suspend_n = int(suspend_match.group(1))
                suspend_cost = suspend_match.group(2)
                if can_pay_cost(player.mana_pool, suspend_cost) or can_pay_cost(_total_available_pool(), suspend_cost):
                    actions.append(LegalAction(
                        action_type="special",
                        card_id=card.id,
                        card_name=card.name,
                        alternative_cost="suspend",
                        mana_options=[{"mana_cost": suspend_cost}],
                        description=f"Suspend {card.name} ({suspend_n} time counters)",
                    ))

    # Foretell: exile card face-down for {2} (main phase, active player)
    if is_active and is_main and stack_empty and not _has_split_second(gs):
        foretell_cost = "{2}"
        if can_pay_cost(player.mana_pool, foretell_cost) or can_pay_cost(_total_available_pool(), foretell_cost):
            for card in player.hand:
                if "land" in card.type_line.lower():
                    continue
                kws_lower = {k.lower() for k in (card.keywords or [])}
                oracle_lower = (card.oracle_text or "").lower()
                if "foretell" in kws_lower or "foretell" in oracle_lower:
                    actions.append(LegalAction(
                        action_type="special",
                        card_id=card.id,
                        card_name=card.name,
                        new_action_type="foretell",
                        mana_options=[{"mana_cost": foretell_cost}],
                        description=f"Foretell {card.name} ({foretell_cost})",
                    ))

    # Cast foretold cards from exile at discounted cost
    if not _has_split_second(gs):
        for card in player.foretold_cards:
            # Extract foretell cost: "Foretell {cost}" from oracle text
            ft_match = _re_spell.search(r'[Ff]oretell (\{[^}]+\})', card.oracle_text or "")
            foretell_alt_cost = ft_match.group(1) if ft_match else (card.mana_cost or "")
            sorcery_speed = _is_sorcery_speed(card)
            if sorcery_speed and not _can_cast_at_sorcery_speed(gs, player_name):
                continue
            if can_pay_cost(player.mana_pool, foretell_alt_cost) or can_pay_cost(_total_available_pool(), foretell_alt_cost):
                actions.append(LegalAction(
                    action_type="cast",
                    card_id=card.id,
                    card_name=card.name,
                    new_action_type="cast_foretold",
                    mana_options=[{"mana_cost": foretell_alt_cost}],
                    description=f"Cast {card.name} (foretold, {foretell_alt_cost})",
                ))

    # Morph turn face-up (CR 702.35) — instant-speed special action
    from mtg_engine.engine.morph import parse_morph_cost as _parse_morph_cost, has_morph as _has_morph
    for perm in gs.battlefield:
        if perm.controller != player_name:
            continue
        if not getattr(perm.card, 'is_face_down', False):
            continue
        # The face-down permanent stores the real card data — check for morph
        real_oracle = perm.card.oracle_text or ""
        if _has_morph(real_oracle) or "morph" in real_oracle.lower():
            morph_cost = _parse_morph_cost(real_oracle)
            if not morph_cost:
                # Fallback: standard morph cost is {3} for face-down creatures
                morph_cost = "{3}"
            if can_pay_cost(player.mana_pool, morph_cost):
                actions.append(LegalAction(
                    action_type="special",
                    card_id=perm.id,
                    card_name=perm.card.name or "Face-down creature",
                    new_action_type="turn_face_up",
                    mana_options=[{"mana_cost": morph_cost}],
                    description=f"Turn {perm.card.name} face up (pay {morph_cost})",
                ))

    # Mutate (US30) — creatures with mutate targeting non-Human creatures controlled by caster
    if is_active and is_main and stack_empty and not _has_split_second(gs):
        _MUTATE_KW = {"mutate"}
        for card in player.hand:
            if "creature" not in card.type_line.lower():
                continue
            kws_lower = {k.lower() for k in (card.keywords or [])}
            oracle_lower = (card.oracle_text or "").lower()
            if not ("mutate" in kws_lower or "mutate" in oracle_lower):
                continue
            valid_targets = []
            for perm in gs.battlefield:
                if perm.controller != player_name:
                    continue
                # US15 (Phasing, CR 702.26a): a phased-out permanent doesn't exist —
                # it can't be a mutate target.
                if getattr(perm, "phased_out", False):
                    continue
                if "creature" not in perm.card.type_line.lower():
                    continue
                if "human" in perm.card.type_line.lower():
                    continue
                valid_targets.append(perm.id)
            if not valid_targets:
                continue
            actions.append(LegalAction(
                action_type="cast",
                card_id=card.id,
                card_name=card.name,
                new_action_type="mutate",
                valid_targets=valid_targets,
                mana_options=[{"mana_cost": card.mana_cost or ""}],
                description=f"Mutate {card.name} on target non-Human creature",
            ))

    # Graveyard casting (US11, T038) — flashback, escape, unearth, disturb, harmonize
    _GRAVEYARD_CAST_KW = {"flashback", "escape", "unearth", "disturb", "harmonize"}
    if _can_cast_at_sorcery_speed(gs, player_name) and not _has_split_second(gs):
        for card in player.graveyard:
            if "land" in card.type_line.lower():
                continue
            kws_lower = {k.lower() for k in (card.keywords or [])}
            oracle_lower = (card.oracle_text or "").lower()
            detected_kw = kws_lower & _GRAVEYARD_CAST_KW
            if not detected_kw:
                for kw in _GRAVEYARD_CAST_KW:
                    if kw in oracle_lower:
                        detected_kw.add(kw)
            if not detected_kw:
                continue
            alt_cost = next(iter(detected_kw))
            mana_cost = card.mana_cost or ""
            if not (can_pay_cost(player.mana_pool, mana_cost) or can_pay_cost(_total_available_pool(), mana_cost)):
                continue
            actions.append(LegalAction(
                action_type="cast",
                card_id=card.id,
                card_name=card.name,
                from_graveyard=True,
                valid_targets=[],
                mana_options=[{"mana_cost": mana_cost}],
                description=f"Cast {card.name} ({alt_cost}) from graveyard",
            ))

    # US18: Adventure creature half cast from exile (CR 702.61)
    if _can_cast_at_sorcery_speed(gs, player_name) and not _has_split_second(gs):
        for card in player.adventure_cards:
            if card.card_layout != "adventure":
                continue
            # Creature half is face_index=0
            mana_cost = (card.faces[0].mana_cost if card.faces and len(card.faces) > 0 else card.mana_cost) or ""
            if not (can_pay_cost(player.mana_pool, mana_cost) or can_pay_cost(_total_available_pool(), mana_cost)):
                continue
            actions.append(LegalAction(
                action_type="cast",
                card_id=card.id,
                card_name=card.name,
                from_adventure_exile=True,
                valid_targets=[],
                mana_options=[{"mana_cost": mana_cost}],
                description=f"Cast {card.name} (creature half from adventure exile)",
            ))

    # Cycling (US9) — cards in hand with cycling can be cycled
    if not _has_split_second(gs):
        _CYCLING_RE = _re_spell.compile(r'[Cc]ycling (\{[^}]+\})', _re_spell.IGNORECASE)
        for card in player.hand:
            if "land" in card.type_line.lower():
                continue
            cycling_match = _CYCLING_RE.search(card.oracle_text or "")
            if not cycling_match:
                continue
            cycling_cost = cycling_match.group(1)
            if not (can_pay_cost(player.mana_pool, cycling_cost) or can_pay_cost(_total_available_pool(), cycling_cost)):
                continue
            actions.append(LegalAction(
                action_type="cycle",
                card_id=card.id,
                card_name=card.name,
                mana_options=[{"mana_cost": cycling_cost}],
                description=f"Cycle {card.name} ({cycling_cost})",
            ))

    # Activate abilities (including mana-producing ones when they unlock castable spells)
    # Precompute once: are there spells newly castable if all mana sources are tapped?
    # This correctly handles multi-land scenarios (e.g. {1}{G} with empty pool + 2 Forests).
    _new_castable_with_full_pool = (
        _castable_count(_total_available_pool()) > _castable_count(player.mana_pool)
    )
    for perm in gs.battlefield:
        if perm.controller != player_name:
            continue
        abilities = parse_oracle_text(perm.card.oracle_text or "", perm.card.type_line)
        activated = [a for a in abilities if isinstance(a, ActivatedAbility)]
        for idx, ab in enumerate(activated):
            mana_sym = _mana_add_symbol(ab.effect)
            if mana_sym is not None:
                # Only offer mana activations when tapping all available sources would
                # unlock spells not castable from the current pool.
                # auto_tap_mana handles the actual tapping when the AI commits to a cast.
                if not _new_castable_with_full_pool:
                    continue
            # US20 T163: Filter activated abilities by timing_restriction (CR 602.1)
            if ab.timing_restriction:
                restr = ab.timing_restriction.lower()
                _is_sorcery_now = (
                    gs.active_player == player_name
                    and gs.step == Step.MAIN
                    and not gs.stack
                )
                if ("sorcery" in restr or "your main phase" in restr) and not _is_sorcery_now:
                    continue
                if "your turn" in restr and gs.active_player != player_name:
                    continue
            # Check tap cost — CR 302.6: a creature's {T} ability can't be
            # activated while it has summoning sickness (non-creature permanents
            # such as lands are unaffected by this rule).
            is_creature = "creature" in perm.card.type_line.lower()
            if "{T}" in ab.cost and (perm.tapped or (is_creature and perm.summoning_sick)):
                continue
            mana_part = _re.sub(r"\{T\}", "", ab.cost).strip().strip(",").strip()
            if mana_part and not can_pay_cost(player.mana_pool, mana_part):
                continue
            # US24 T179-T180: Validate sacrifice costs — only offer if a valid target exists
            import re as _re_sac
            sac_match = _re_sac.search(r"sacrifice (a|an) ([\w ]+)", ab.cost, _re_sac.IGNORECASE)
            if sac_match:
                sac_type = sac_match.group(2).strip().lower()
                # Check if controller has a permanent matching the type to sacrifice
                has_sac_target = any(
                    p.controller == player_name
                    and p.id != perm.id  # can't sacrifice the source if not required
                    and sac_type in p.card.type_line.lower()
                    for p in gs.battlefield
                )
                if not has_sac_target:
                    # More permissive: also accept if the ability itself is the source
                    has_sac_target = any(
                        p.controller == player_name
                        and sac_type in p.card.type_line.lower()
                        for p in gs.battlefield
                    )
                if not has_sac_target:
                    continue
             # US32 T179: Tag mana abilities (CR 605.3b)
            if is_mana_ability(ab.raw_text, is_loyalty=False):
                # Include both action types for backward compatibility
                actions.append(LegalAction(
                    action_type="activate_mana_ability",
                    permanent_id=perm.id,
                    card_name=perm.card.name,
                    ability_index=idx,
                    description=f"Activate {perm.card.name}: {ab.raw_text}",
                ))
                actions.append(LegalAction(
                    action_type="activate",
                    permanent_id=perm.id,
                    card_name=perm.card.name,
                    ability_index=idx,
                    description=f"Activate {perm.card.name}: {ab.raw_text}",
                ))
            else:
                # Fortify (CR 702.54a): only offer when there is a valid target
                # land the player controls (excluding the source itself).
                from mtg_engine.ability.keywords.fortify import Fortify
                if _re.search(r"attach (?:this fortification )?to target land", ab.effect, _re.IGNORECASE):
                    fortify_targets = [
                        p.id for p in gs.battlefield
                        if p.controller == player_name
                        and p.id != perm.id
                        and Fortify.is_land_card(p.card)
                    ]
                    if not fortify_targets:
                        continue
                    actions.append(LegalAction(
                        action_type="activate",
                        permanent_id=perm.id,
                        card_name=perm.card.name,
                        ability_index=idx,
                        valid_targets=fortify_targets,
                        description=f"Fortify {perm.card.name} onto target land ({ab.cost})",
                    ))
                    continue
                actions.append(LegalAction(
                    action_type="activate",
                    permanent_id=perm.id,
                    card_name=perm.card.name,
                    ability_index=idx,
                    description=f"Activate {perm.card.name}: {ab.raw_text}",
                ))

    # Planeswalker loyalty abilities (US4, T021)
    if is_active and is_main and stack_empty:
        from mtg_engine.card_data.ability_parser import parse_loyalty_abilities
        for perm in gs.battlefield:
            if perm.controller != player_name:
                continue
            if "planeswalker" not in perm.card.type_line.lower():
                continue
            if perm.loyalty_activated_this_turn:
                continue
            loy_abilities = parse_loyalty_abilities(perm.card.oracle_text or "")
            for loy_ab in loy_abilities:
                # Filter out − abilities that would reduce loyalty below 0
                if loy_ab.loyalty_change < 0 and perm.loyalty + loy_ab.loyalty_change < 0:
                    continue
                actions.append(LegalAction(
                    action_type="activate_loyalty",
                    permanent_id=perm.id,
                    card_name=perm.card.name,
                    loyalty_ability_index=loy_ab.index,
                    description=f"Activate {perm.card.name}: {loy_ab.raw_text}",
                ))

    # Declare attackers (active player, declare attackers step, only if not yet declared)
    if is_active and gs.step == Step.DECLARE_ATTACKERS and gs.combat is None:
        # US6: Derive and enforce attack constraints
        from mtg_engine.engine.constraints import derive_combat_constraints
        from mtg_engine.engine.mana import can_pay_cost
        atk_constraints, blk_constraints = derive_combat_constraints(gs)
        gs.attack_constraints = atk_constraints
        gs.block_constraints = blk_constraints

        attackers = []
        for p in gs.battlefield:
            if not (
                p.controller == player_name
                and "creature" in p.card.type_line.lower()
                and not p.tapped
                and (not p.summoning_sick or "haste" in p.card.keywords)
                and "defender" not in p.card.keywords
                # US15 (Phasing, CR 702.26a): a phased-out permanent can't attack.
                and not getattr(p, "phased_out", False)
            ):
                continue
            # Check attack constraints
            can_attack = True
            for con in atk_constraints:
                if con.affected_id not in (p.id, "all"):
                    continue
                if con.constraint_type == "cannot_attack":
                    can_attack = False
                    break
                if con.constraint_type == "cost_to_attack" and con.cost:
                    if not can_pay_cost(player.mana_pool, con.cost):
                        can_attack = False
                        break
            if can_attack:
                attackers.append(p)

        if attackers:
            opponent = next((p.name for p in gs.players if p.name != player_name), "")
            # T120: include opponent's planeswalkers as valid defending targets (CR 506.2)
            opp_planeswalkers = [
                p for p in gs.battlefield
                if p.controller == opponent
                and "planeswalker" in p.card.type_line.lower()
            ]
            defender_ids = [opponent] + [pw.id for pw in opp_planeswalkers]
            attacker_names = ", ".join(p.card.name for p in attackers)
            pw_names = (", ".join(pw.card.name for pw in opp_planeswalkers))
            desc_suffix = f" (or {pw_names})" if opp_planeswalkers else ""
            actions.append(LegalAction(
                action_type="declare_attackers",
                valid_targets=[p.id for p in attackers],  # attacker permanent IDs
                card_name=opponent,                        # default defending player
                description=f"Attack with: {attacker_names}{desc_suffix}",
                mana_options=[{"defender_ids": defender_ids}],
            ))

    # Declare blockers (non-active/defending player, declare blockers step, only once per step)
    if (not is_active and gs.step == Step.DECLARE_BLOCKERS and gs.combat
            and gs.combat.attackers and not gs.combat.blockers_declared):
        # US6: Filter out creatures with cannot-block constraints
        cannot_block_ids = {
            con.affected_id for con in gs.block_constraints
            if con.constraint_type == "cannot_block"
        }
        # Goaded creatures can't block (CR 702.117b)
        goaded_ids = {
            p.id for p in gs.battlefield
            if any(k.startswith("goad_by_") for k in p.counters)
        }
        # CR 302.6: summoning sickness only prevents attacking and using {T} abilities,
        # NOT blocking. Tapped creatures also cannot block (CR 509.1a).
        # US21 T168: Pre-filter for evasion/protection restrictions across all attackers
        from mtg_engine.engine.combat import _LANDWALK_MAP
        attacker_perms = [
            next((p for p in gs.battlefield if p.id == a.permanent_id), None)
            for a in gs.combat.attackers
        ]
        attacker_perms = [a for a in attacker_perms if a is not None]

        def _blocker_can_block_any(blocker_perm) -> bool:
            """Check if the blocker can legally block at least one attacker."""
            for atk in attacker_perms:
                # Flying check
                if "flying" in atk.card.keywords and not (
                    "flying" in blocker_perm.card.keywords or "reach" in blocker_perm.card.keywords
                ):
                    continue
                # Shadow check
                if ("shadow" in atk.card.keywords) != ("shadow" in blocker_perm.card.keywords):
                    continue
                # Horsemanship check
                if "horsemanship" in atk.card.keywords and "horsemanship" not in blocker_perm.card.keywords:
                    continue
                # Protection (DEBT - Blocking component) check
                blocker_colors = [c.lower() for c in blocker_perm.card.colors]
                prot_blocked = False
                for kw in atk.card.keywords:
                    if kw.lower().startswith("protection from ") and kw.lower()[len("protection from "):] in blocker_colors:
                        prot_blocked = True
                        break
                if prot_blocked:
                    continue
                # Landwalk check
                landwalk_blocked = False
                for kw in atk.card.keywords:
                    land_type = _LANDWALK_MAP.get(kw.lower())
                    if land_type:
                        if any(
                            p.controller == player_name
                            and "land" in p.card.type_line.lower()
                            and land_type in p.card.type_line.lower()
                            for p in gs.battlefield
                        ):
                            landwalk_blocked = True
                            break
                if landwalk_blocked:
                    continue
                return True  # can block this attacker
            return False  # no attacker can be blocked by this creature

        potential_blockers = [
            p for p in gs.battlefield
            if p.controller == player_name
            and "creature" in p.card.type_line.lower()
            and not p.tapped
            # US15 (Phasing, CR 702.26a): a phased-out permanent can't block.
            and not getattr(p, "phased_out", False)
            and p.id not in cannot_block_ids
            and p.id not in goaded_ids
            and _blocker_can_block_any(p)
        ]
        attacker_names = ", ".join(
            next((p.card.name for p in gs.battlefield if p.id == a.permanent_id), a.permanent_id)
            for a in gs.combat.attackers
        )
        blocker_desc = (
            f"{len(potential_blockers)} creature(s) available to block"
            if potential_blockers else "no creatures available to block"
        )
        actions.append(LegalAction(
            action_type="declare_blockers",
            valid_targets=[p.id for p in potential_blockers],
            description=f"Declare blockers vs [{attacker_names}] — {blocker_desc}",
        ))

    # Assign combat damage (active player, combat damage steps).
    # Only offered once per step (damage_assigned flag prevents re-offering after execution).
    # In FIRST_STRIKE_DAMAGE, only offered when first/double strike combatants are present.
    if (
        is_active
        and gs.step in (Step.COMBAT_DAMAGE, Step.FIRST_STRIKE_DAMAGE)
        and gs.combat
        and gs.combat.attackers
        and not gs.combat.damage_assigned
    ):
        from mtg_engine.engine.combat import has_first_strike_combatants
        if gs.step == Step.FIRST_STRIKE_DAMAGE and not has_first_strike_combatants(gs):
            pass  # No first/double strike creatures — skip this step automatically
        else:
            attacker_names = ", ".join(
                next((p.card.name for p in gs.battlefield if p.id == a.permanent_id), a.permanent_id)
                for a in gs.combat.attackers
            )
            actions.append(LegalAction(
                action_type="assign_combat_damage",
                description=f"Assign combat damage from [{attacker_names}]",
            ))

    # Put pending triggers on stack
    for trigger in gs.pending_triggers:
        if trigger.controller == player_name:
            actions.append(LegalAction(
                action_type="put_trigger",
                description=f"Put trigger on stack: {trigger.effect_description}",
            ))
            # US17 T152: Optional ("you may") triggers also offer a decline action (CR 603.3)
            if trigger.is_optional:
                actions.append(LegalAction(
                    action_type="decline_trigger",
                    card_id=trigger.id,
                    description=f"Decline optional trigger: {trigger.effect_description}",
                ))

    # Commander: cast commander from command zone
    if gs.format == "commander" and is_active and is_main and stack_empty:
        from mtg_engine.engine.mana import can_pay_cost
        for cmd_card in player.command_zone:
            base_cost = cmd_card.mana_cost or ""
            tax = 2 * player.commander_cast_counts.get(cmd_card.name, 0)
            # Build taxed cost string: append {tax} generic if tax > 0
            taxed_cost = base_cost if tax == 0 else f"{{{tax}}}{base_cost}"
            if can_pay_cost(player.mana_pool, taxed_cost):
                tax_str = f" + {{{tax}}} tax" if tax > 0 else ""
                actions.append(LegalAction(
                    action_type="cast_commander",
                    card_id=cmd_card.id,
                    card_name=cmd_card.name,
                    mana_options=[{"mana_cost": base_cost, "commander_tax": tax}],
                    description=f"Cast {cmd_card.name} from command zone (cost: {base_cost}{tax_str})",
                ))

    # Always allow passing priority (CR 500.2.11)
    # Add pass as the last action - it's always available
    if not any(a.action_type == "pass" for a in actions):
        actions.append(LegalAction(action_type="pass", description="Pass priority"))

    return actions
