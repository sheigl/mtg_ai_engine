"""Game action endpoints. REQ-API01–REQ-API05."""
import copy
import logging
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from mtg_engine.api.game_manager import get_manager
from mtg_engine.persistence.player_defaults import get_merged_player_settings_sync
from mtg_engine.models.game import GameState, Phase, Step
from mtg_engine.models.actions import (
    CastRequest, ActivateRequest, PlayLandRequest,
    DeclareAttackersRequest, DeclareBlockersRequest, OrderBlockersRequest,
    AssignCombatDamageRequest, ChoiceRequest, PassRequest,
    PutTriggerRequest, SpecialActionRequest,
    MulliganRequest, ActivateLoyaltyRequest, CascadeChoiceRequest,
    LegalAction, LegalActionsResponse, ErrorResponse,
    ForetellRequest,
)
from mtg_engine.engine.sba import check_and_apply_sbas
from mtg_engine.engine.turn_manager import pass_priority
from mtg_engine.engine.stack import cast_spell, resolve_top
from mtg_engine.engine.zones import get_player, move_card_to_zone, put_permanent_onto_battlefield
from mtg_engine.engine.combat import (
    declare_attackers, declare_blockers, order_blockers, assign_combat_damage, end_combat
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
    max_turns: int = 200

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
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=1000)
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
        if "land" not in card.type_line.lower():
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
        # Sacrifice the first target creature before casting
        if req.targets:
            sac_id = req.targets[0]
            perm_to_sac = next((p for p in gs.battlefield if p.id == sac_id), None)
            if perm_to_sac:
                from mtg_engine.engine.zones import move_permanent_to_zone
                gs = move_permanent_to_zone(gs, perm_to_sac, "graveyard")
    elif req.alternative_cost == "delve":
        # Exile specified graveyard cards to pay generic mana
        player_for_delve = get_player(gs, gs.priority_holder)
        for gid in req.targets:
            delve_card = next((c for c in player_for_delve.graveyard if c.id == gid), None)
            if delve_card:
                player_for_delve.graveyard.remove(delve_card)
                player_for_delve.exile.append(delve_card)
        req = req.model_copy(update={"targets": []})

    # Graveyard cast (US11, T039): temporarily move card to hand for cast_spell
    _graveyard_card = None
    _foretold_card = None
    if req.from_graveyard and req.alternative_cost in {"flashback", "escape", "unearth", "disturb"}:
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

    # T009: Validate targets before casting
    if req.targets:
        card_obj = next((c for c in player_gs.hand if c.id == req.card_id), None)
        if card_obj:
            _validate_targets(gs, req.targets, card_obj, caster)

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

    # T051: Ward cost check — if any target has ward, set pending_ward_payment
    # Ward triggers when a spell targeting a permanent with ward is put on the stack (CR 702.157)
    import re as _re_ward
    if req.targets and gs.stack:
        top_spell = gs.stack[-1]
        for target_id in req.targets:
            target_perm = next((p for p in gs.battlefield if p.id == target_id), None)
            if target_perm:
                ward_match = _re_ward.search(
                    r'[Ww]ard[—–-]?(\{[^}]+\}|\d+)',
                    target_perm.card.oracle_text or ""
                )
                if ward_match and target_perm.controller != caster:
                    ward_cost_raw = ward_match.group(1)
                    # Normalize numeric ward cost (e.g. "2" → "{2}")
                    ward_cost = ward_cost_raw if ward_cost_raw.startswith("{") else f"{{{ward_cost_raw}}}"
                    gs.pending_ward_payment = {
                        "player": caster,
                        "ward_cost": ward_cost,
                        "targeting_spell_id": top_spell.id,
                        "target_permanent_id": target_id,
                    }
                    logger.info("Ward triggered: %s must pay %s or spell is countered",
                                caster, ward_cost)
                    break  # only trigger ward once per spell

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

    # Extract cycling cost from oracle text
    import re as _re_cycle
    cycling_match = _re_cycle.search(r'[Cc]ycling (\{[^}]+\})', card.oracle_text or "")
    if not cycling_match:
        raise _err(f"{card.name} doesn't have cycling", "INVALID_ACTION")

    cycling_cost = cycling_match.group(1)
    from mtg_engine.engine.mana import can_pay_cost, is_mana_ability
    if not can_pay_cost(player.mana_pool, cycling_cost):
        raise _err(f"Cannot pay cycling cost {cycling_cost}", "INVALID_ACTION")

    card_name = card.name

    try:
        # Pay the cycling cost
        # Note: The AI client should provide req.mana_payment to pay the cost
        # For now, we assume the cost is paid (client validates)

        # Discard the card
        player.hand[:] = [c for c in player.hand if c.id != req.card_id]
        player.graveyard.append(card)

        # Draw a card
        if player.library:
            drawn_card = player.library.pop(0)
            player.hand.append(drawn_card)

        # Emit cycle triggers (US9, check_cycle_triggers)
        from mtg_engine.engine.triggers import check_cycle_triggers
        gs = check_cycle_triggers(gs, card_name, card.type_line)

        gs = _run_sbas(gs)

    except (ValueError, StopIteration) as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        if recorder:
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
        # Find the target — permanent or player
        perm = next((p for p in gs.battlefield if p.id == target_id), None)
        if perm:
            # Add one of each counter type the permanent already has
            for counter_type, count in list(perm.counters.items()):
                if not counter_type.startswith("__"):  # skip internal counters
                    perm.counters[counter_type] = count + 1
        else:
            # Target is a player — add one poison counter if they have any
            target_player = next((p for p in gs.players if p.name == target_id), None)
            if target_player and target_player.poison_counters > 0:
                target_player.poison_counters += 1

    gs.pending_proliferate_choice = None
    gs = _run_sbas(gs)

    if not req.dry_run:
        mgr.update(game_id, gs)
    return _ok(gs)


# ─── Activate ability ─────────────────────────────────────────────────────────

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
        from mtg_engine.engine.mana import pay_cost, add_mana, is_mana_ability, resolve_mana_ability

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

        # Check if this is a mana ability per CR 605 (T014, T015)
        # Mana abilities resolve immediately without going on the stack
        if is_mana_ability(ability_text_for_log, is_loyalty=False):
            # Resolve immediately - bypass stack (CR 605.3b)
            gs = resolve_mana_ability(gs, req.permanent_id, ability_text_for_log)
        else:
            # Apply non-mana ability effects
            import re as _re
            mana_add = _re.search(r"add\s+(\{[WUBRGC]\})", ability.effect, _re.IGNORECASE)
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
            if scry_player.library:
                cards_to_bottom = scry_player.library[:n]
                scry_player.library = scry_player.library[n:] + cards_to_bottom
            gs.pending_scry_choice = None
            mgr.update(game_id, gs)
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
            payer = get_player(gs, payer_name)
            from mtg_engine.engine.mana import can_pay_cost, pay_cost as _pc_w
            if ward_cost and can_pay_cost(payer.mana_pool, ward_cost):
                # Auto-pay from pool
                from mtg_engine.engine.mana import parse_mana_cost as _pmc_w
                cost_dict = _pmc_w(ward_cost)
                mana_payment = {}
                for color in ("W", "U", "B", "R", "G", "C"):
                    needed = cost_dict.get(color, 0)
                    if needed > 0:
                        mana_payment[color] = needed
                payer.mana_pool = _pc_w(payer.mana_pool, ward_cost, mana_payment)
            gs.pending_ward_payment = None
            mgr.update(game_id, gs)

    elif choice_id == "ward_counter":
        # T051: Player declines to pay ward — targeting spell is countered (CR 702.157b)
        if gs.pending_ward_payment:
            spell_id = gs.pending_ward_payment.get("targeting_spell_id", "")
            countered = next((s for s in gs.stack if s.id == spell_id), None)
            if countered:
                gs.stack[:] = [s for s in gs.stack if s.id != spell_id]
                owner = get_player(gs, countered.controller)
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

@router.get("/{game_id}/legal-actions")
def legal_actions(game_id: str) -> dict:
    """
    GET /game/{game_id}/legal-actions — compute all legal actions. REQ-S05, REQ-6.3.
    Must respond in under 200ms (REQ-P01).

    Auto-pass: if the only legal action is "pass", automatically submit it
    and return the next state's legal actions. This prevents the UI/AI from
    being presented with an empty decision.
    """
    from mtg_engine.export.store import get_export_store
    from mtg_engine.engine.turn_manager import pass_priority
    mgr = get_manager()
    gs = _get_gs(game_id)

    # Auto-pass loop: if only "pass" is available, keep passing until
    # someone has a real action or the game advances.
    max_auto_passes = 20
    for _ in range(max_auto_passes):
        actions = _compute_legal_actions(gs)
        if len(actions) > 1 or (actions and actions[0].action_type != "pass"):
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
    from mtg_engine.models.actions import CopySpellRequest
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
    mgr.save(game_id, gs)
    return _ok(gs)


# ─── Mulligan endpoint (US6, T027) ───────────────────────────────────────────

@router.post("/{game_id}/mulligan")
def mulligan(game_id: str, req: dict) -> dict:
    """POST /game/{game_id}/mulligan — London mulligan decision."""
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

    if keep or hand_size <= 5:
        if player_name not in gs.players_kept:
            gs.players_kept.append(player_name)
    else:
        if hand_size <= 1:
            raise _err("Hand already at minimum size", "HAND_TOO_SMALL")
        import random as _rand
        player.library = list(player.hand) + list(player.library)
        _rand.shuffle(player.library)
        new_size = hand_size - 1
        player.hand = player.library[:new_size]
        player.library = player.library[new_size:]
        gs.hands_mulliganed[player_name] = gs.hands_mulliganed.get(player_name, 0) + 1

    if all(p.name in gs.players_kept for p in gs.players):
        gs.mulligan_phase_active = False

    mgr = get_manager()
    mgr.update(game_id, gs)
    return {
        "kept": keep or hand_size <= 5,
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
    mgr.save(game_id, gs)
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
    mgr.save(game_id, gs)
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

    # Early-exit: pending blocking choices — these block all other actions until resolved
    if gs.pending_scry_choice and gs.pending_scry_choice.get("player") == player_name:
        scry_cards = gs.pending_scry_choice.get("cards", [])
        card_ids = [c.get("id", c.get("name", "?")) if isinstance(c, dict) else c for c in scry_cards]
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
        return actions

    if gs.pending_discard_choice and gs.pending_discard_choice.get("player") == player_name:
        count = gs.pending_discard_choice.get("count", 1)
        hand_ids = [c.id for c in player.hand]
        actions.append(LegalAction(
            action_type="choice",
            card_name="discard_pick",
            description=f"Discard {count} card(s)",
            valid_targets=hand_ids,
        ))
        return actions

    if gs.pending_ward_payment and gs.pending_ward_payment.get("player") == player_name:
        ward_cost = gs.pending_ward_payment.get("ward_cost", "")
        targeting_spell_id = gs.pending_ward_payment.get("targeting_spell_id", "")
        actions.append(LegalAction(
            action_type="choice",
            card_name="ward_pay",
            description=f"Pay ward {ward_cost} (spell targeting your permanent continues)",
            valid_targets=[targeting_spell_id],
        ))
        actions.append(LegalAction(
            action_type="choice",
            card_name="ward_counter",
            description=f"Don't pay ward {ward_cost} (targeting spell is countered)",
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

    # Play land: active player, main phase, stack empty, one land per turn
    if is_active and is_main and stack_empty and player.lands_played_this_turn < 1:
        for card in player.hand:
            if "land" in card.type_line.lower():
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

    # Graveyard casting (US11, T038) — flashback, escape, unearth, disturb
    _GRAVEYARD_CAST_KW = {"flashback", "escape", "unearth", "disturb"}
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

    return actions
