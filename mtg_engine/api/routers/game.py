"""Game action endpoints. REQ-API01–REQ-API05."""
import copy
import logging
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mtg_engine.api.game_manager import get_manager
from mtg_engine.models.game import GameState, Phase, Step
from mtg_engine.models.actions import (
    CastRequest, ActivateRequest, PlayLandRequest,
    DeclareAttackersRequest, DeclareBlockersRequest, OrderBlockersRequest,
    AssignCombatDamageRequest, ChoiceRequest, PassRequest,
    PutTriggerRequest, SpecialActionRequest,
    MulliganRequest, ActivateLoyaltyRequest, CascadeChoiceRequest,
    LegalAction, LegalActionsResponse, ErrorResponse,
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
    deck1: list[str]   # card names
    deck2: list[str]
    seed: int | None = None
    verbose: bool = False
    debug: bool = False
    format: str = "standard"
    commander1: str | None = None
    commander2: str | None = None


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

    if req.format == "commander":
        if not req.commander1 or not req.commander2:
            raise _err("Commander format requires commander1 and commander2", "INVALID_COMMANDER")
        try:
            deck1_cards, commander1_card = load_commander_deck(req.deck1, req.commander1)
        except ValueError as e:
            msg = str(e)
            code = (
                "SINGLETON_VIOLATION" if "Singleton" in msg
                else "COLOR_IDENTITY_VIOLATION" if "Color identity" in msg
                else "INVALID_COMMANDER" if "legendary" in msg.lower() or "not found" in msg
                else "DECK_LOAD_ERROR"
            )
            raise _err(msg, code)
        try:
            deck2_cards, commander2_card = load_commander_deck(req.deck2, req.commander2)
        except ValueError as e:
            msg = str(e)
            code = (
                "SINGLETON_VIOLATION" if "Singleton" in msg
                else "COLOR_IDENTITY_VIOLATION" if "Color identity" in msg
                else "INVALID_COMMANDER" if "legendary" in msg.lower() or "not found" in msg
                else "DECK_LOAD_ERROR"
            )
            raise _err(msg, code)
        gs = mgr.create_game(
            req.player1_name, req.player2_name,
            deck1_cards, deck2_cards,
            seed=req.seed,
            verbose=req.verbose,
            debug=req.debug,
            format="commander",
            commander1_card=commander1_card,
            commander2_card=commander2_card,
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
        )
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
        tax = 2 * player_gs.commander_cast_count
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

        # Increment commander cast count
        player_gs2 = get_player(gs, caster)
        player_gs2.commander_cast_count += 1

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
                gs = move_permanent_to_zone(gs, sac_id, "graveyard")
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
    if req.from_graveyard and req.alternative_cost in {"flashback", "escape", "unearth", "disturb"}:
        _graveyard_card = next((c for c in player_gs.graveyard if c.id == req.card_id), None)
        if _graveyard_card is None:
            raise _err(f"Card {req.card_id!r} not found in graveyard", "INVALID_ACTION")
        player_gs.graveyard[:] = [c for c in player_gs.graveyard if c.id != req.card_id]
        player_gs.hand.append(_graveyard_card)

    card_obj = next((c for c in player_gs.hand if c.id == req.card_id), None)
    card_name = card_obj.name if card_obj else req.card_id
    card_mana_cost = card_obj.mana_cost or "" if card_obj else ""

    try:
        gs = cast_spell(
            gs,
            caster,
            req.card_id,
            req.targets,
            req.mana_payment,
            alternative_cost=req.alternative_cost,
            modes_chosen=req.modes_chosen,
        )
        gs = _run_sbas(gs)
    except ValueError as e:
        # Rollback graveyard move if cast fails
        if _graveyard_card is not None:
            player_gs2 = get_player(gs, caster)
            player_gs2.hand[:] = [c for c in player_gs2.hand if c.id != req.card_id]
            player_gs2.graveyard.append(_graveyard_card)
        raise _err(str(e), "INVALID_ACTION")

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

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        if recorder:
            recorder.record_cast(caster, card_name, req.targets, cast_turn, cast_phase, cast_step,
                                 mana_cost=card_mana_cost)
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
        from mtg_engine.engine.mana import pay_cost, add_mana

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

        # Apply mana ability effects immediately (REQ-A07: mana abilities bypass stack)
        import re as _re
        mana_add = _re.search(r"add\s+(\{[WUBRGC]\})", ability.effect, _re.IGNORECASE)
        if mana_add:
            sym = mana_add.group(1).strip("{}")
            player.mana_pool = add_mana(player.mana_pool, sym.upper())

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
    mgr = get_manager()
    gs = _get_gs(game_id)
    # Choice handling will be expanded with replacement effects in Phase 4+
    # For now, acknowledge the choice
    return _ok(gs)


# ─── Special action ───────────────────────────────────────────────────────────

@router.post("/{game_id}/special-action")
def special_action(game_id: str, req: SpecialActionRequest) -> dict:
    """POST /game/{game_id}/special-action. REQ-A16"""
    mgr = get_manager()
    gs = _get_gs(game_id)
    # Morph, suspend, etc. — placeholder; raises NotImplementedError for unsupported
    raise _err(
        f"Special action {req.action_type!r} not yet implemented",
        "NOT_IMPLEMENTED",
        422,
    )


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
    """
    from mtg_engine.export.store import get_export_store
    mgr = get_manager()
    gs = _get_gs(game_id)
    actions = _compute_legal_actions(gs)
    actions_data = [a.model_dump() for a in actions]
    # Record snapshot at each priority grant (needed for UUID→name resolution in game log).
    store = get_export_store(game_id)
    store.snapshots.record_snapshot(gs, actions_data)
    return {
        "data": {
            "priority_player": gs.priority_holder,
            "phase": gs.phase.value,
            "step": gs.step.value,
            "legal_actions": actions_data,
            "is_paused": mgr.is_paused(game_id),
            "is_game_over": gs.is_game_over,
            "winner": gs.winner,
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
    mgr.save(game_id, gs)
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
    from mtg_engine.engine.mana import can_pay_cost

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
            if can_pay_cost(player.mana_pool, mana_cost) or can_pay_cost(_total_available_pool(), mana_cost):
                # Build full valid_targets list so the AI client can pick the best target.
                # The AI selects via _select_best_target(); the engine enforces legality
                # at resolution time.
                spell_targets: list[str] = []
                oracle_lower = (card.oracle_text or "").lower()
                is_aura = "enchantment" in card.type_line.lower() and "enchant creature" in oracle_lower
                is_pump = bool(_re_spell.search(r"target creature gets \+\d+/\+\d+", oracle_lower))
                is_removal = bool(_re_spell.search(r"destroy target|exile target", oracle_lower))
                is_burn = bool(_re_spell.search(r"deals?\s+\d+\s+damage\s+to\s+(?:any target|target creature|target player)", oracle_lower))
                opp_names = [p.name for p in gs.players if p.name != player_name]

                if is_aura or is_pump:
                    # All creatures on battlefield — AI picks the best friendly one
                    spell_targets = [
                        p.id for p in gs.battlefield
                        if "creature" in p.card.type_line.lower()
                    ]
                elif is_removal:
                    # All opponent creatures (and opponent planeswalkers for exile)
                    spell_targets = [
                        p.id for p in gs.battlefield
                        if p.controller in opp_names
                        and (
                            "creature" in p.card.type_line.lower()
                            or "planeswalker" in p.card.type_line.lower()
                        )
                    ]
                elif is_burn:
                    # All creatures + opponent player names (for face damage)
                    spell_targets = [
                        p.id for p in gs.battlefield
                        if "creature" in p.card.type_line.lower()
                        or "planeswalker" in p.card.type_line.lower()
                    ] + opp_names
                actions.append(LegalAction(
                    action_type="cast",
                    card_id=card.id,
                    card_name=card.name,
                    valid_targets=spell_targets,
                    mana_options=[{k: v for k, v in {"mana_cost": mana_cost}.items()}],
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
            # Check tap cost — CR 302.6: a creature's {T} ability can't be
            # activated while it has summoning sickness (non-creature permanents
            # such as lands are unaffected by this rule).
            is_creature = "creature" in perm.card.type_line.lower()
            if "{T}" in ab.cost and (perm.tapped or (is_creature and perm.summoning_sick)):
                continue
            mana_part = _re.sub(r"\{T\}", "", ab.cost).strip().strip(",").strip()
            if mana_part and not can_pay_cost(player.mana_pool, mana_part):
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

    # Declare attackers (active player, declare attackers step)
    if is_active and gs.step == Step.DECLARE_ATTACKERS:
        # US6: Derive and enforce attack constraints
        from mtg_engine.engine.constraints import derive_combat_constraints
        from mtg_engine.engine.mana import can_pay_cost as _can_pay_attack
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
                    if not _can_pay_attack(player.mana_pool, con.cost):
                        can_attack = False
                        break
            if can_attack:
                attackers.append(p)

        if attackers:
            opponent = next((p.name for p in gs.players if p.name != player_name), "")
            attacker_names = ", ".join(p.card.name for p in attackers)
            actions.append(LegalAction(
                action_type="declare_attackers",
                valid_targets=[p.id for p in attackers],  # attacker permanent IDs
                card_name=opponent,                        # defending player
                description=f"Attack with: {attacker_names}",
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
        potential_blockers = [
            p for p in gs.battlefield
            if p.controller == player_name
            and "creature" in p.card.type_line.lower()
            and not p.tapped
            and p.id not in cannot_block_ids
            and p.id not in goaded_ids
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

    # Commander: cast commander from command zone
    if gs.format == "commander" and is_active and is_main and stack_empty:
        from mtg_engine.engine.mana import can_pay_cost as _can_pay
        for cmd_card in player.command_zone:
            base_cost = cmd_card.mana_cost or ""
            tax = 2 * player.commander_cast_count
            # Build taxed cost string: append {tax} generic if tax > 0
            taxed_cost = base_cost if tax == 0 else f"{{{tax}}}{base_cost}"
            if _can_pay(player.mana_pool, taxed_cost):
                tax_str = f" + {{{tax}}} tax" if tax > 0 else ""
                actions.append(LegalAction(
                    action_type="cast_commander",
                    card_id=cmd_card.id,
                    card_name=cmd_card.name,
                    mana_options=[{"mana_cost": base_cost, "commander_tax": tax}],
                    description=f"Cast {cmd_card.name} from command zone (cost: {base_cost}{tax_str})",
                ))

    return actions
