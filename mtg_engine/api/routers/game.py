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

        # Move from hand to battlefield (REQ-A02: no stack)
        player.hand[:] = [c for c in player.hand if c.id != req.card_id]
        gs, _ = put_permanent_onto_battlefield(gs, card, gs.active_player, tapped=False, from_zone="hand")
        player.lands_played_this_turn += 1
        gs = _run_sbas(gs)

    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
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
                recorder.record_cast(caster, card_name, req.targets, cast_turn, cast_phase, cast_step)
        return _ok(gs)

    card_obj = next((c for c in player_gs.hand if c.id == req.card_id), None)
    card_name = card_obj.name if card_obj else req.card_id

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
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
        recorder = _get_recorder_safe(game_id, mgr)
        if recorder:
            recorder.record_cast(caster, card_name, req.targets, cast_turn, cast_phase, cast_step)
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
    mgr = get_manager()
    gs = _get_gs(game_id)
    actions = _compute_legal_actions(gs)
    return {
        "data": {
            "priority_player": gs.priority_holder,
            "phase": gs.phase.value,
            "step": gs.step.value,
            "legal_actions": [a.model_dump() for a in actions],
            "is_paused": mgr.is_paused(game_id),
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


def _compute_legal_actions(gs: GameState) -> list[LegalAction]:
    """Compute all legal actions for the priority holder."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, ActivatedAbility
    from mtg_engine.engine.mana import can_pay_cost

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

    # Precompute available targets for "target creature" spells.
    _any_creature_on_bf = any(
        "creature" in p.card.type_line.lower() for p in gs.battlefield
    )
    _any_creature_target = _any_creature_on_bf  # simplified: any creature is a valid target

    def _has_required_targets(card: "Card") -> bool:
        """Return False if the spell requires a target that doesn't exist yet."""
        oracle = (card.oracle_text or "").lower()
        type_lower = card.type_line.lower()
        # Auras need an enchant target — check "enchant creature" in oracle or type
        if "enchantment" in type_lower and "enchant creature" in oracle:
            return _any_creature_on_bf
        # Spells with "target creature" in oracle need a creature on the battlefield
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
            # Skip if the spell requires a target that doesn't exist
            if not _has_required_targets(card):
                continue
            # Check if player can pay the mana cost
            mana_cost = card.mana_cost or ""
            if can_pay_cost(player.mana_pool, mana_cost):
                actions.append(LegalAction(
                    action_type="cast",
                    card_id=card.id,
                    card_name=card.name,
                    valid_targets=[],  # simplified: populate targets in full impl
                    mana_options=[{k: v for k, v in {"mana_cost": mana_cost}.items()}],
                    description=f"Cast {card.name}",
                ))

    # Activate abilities
    # Pre-compute: what mana symbols could still be produced by untapped mana sources?
    # Used to skip pure-mana activations that can't enable any spell in hand.
    _re = _re_spell  # reuse the re module already imported above
    _MANA_ADD_RE = _re.compile(r"add\s+\{([WUBRGC])\}", _re.IGNORECASE)

    def _mana_add_symbol(effect: str) -> str | None:
        """Return the mana symbol produced by a 'Add {X}' effect, or None."""
        m = _MANA_ADD_RE.search(effect)
        return m.group(1).upper() if m else None

    def _pool_after_add(pool: "ManaPool", symbol: str) -> "ManaPool":
        from mtg_engine.engine.mana import add_mana
        return add_mana(pool, symbol)

    def _castable_count(pool: "ManaPool") -> int:
        """Count non-land cards in hand payable with pool and legal to cast right now."""
        return sum(
            1 for card in player.hand
            if "land" not in card.type_line.lower()
            and can_pay_cost(pool, card.mana_cost or "")
            and (not _is_sorcery_speed(card) or _can_cast_at_sorcery_speed(gs, player_name))
        )

    def _total_available_pool() -> "ManaPool":
        """Current pool plus mana producible from every untapped mana source.
        Respects summoning sickness: creature tap abilities are excluded when
        the creature just entered (CR 302.6)."""
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

    _current_castable = _castable_count(player.mana_pool)
    _total_castable = _castable_count(_total_available_pool())

    for perm in gs.battlefield:
        if perm.controller != player_name:
            continue
        abilities = parse_oracle_text(perm.card.oracle_text or "", perm.card.type_line)
        activated = [a for a in abilities if isinstance(a, ActivatedAbility)]
        for idx, ab in enumerate(activated):
            # Check tap cost — CR 302.6: a creature's {T} ability can't be
            # activated while it has summoning sickness (non-creature permanents
            # such as lands are unaffected by this rule).
            is_creature = "creature" in perm.card.type_line.lower()
            if "{T}" in ab.cost and (perm.tapped or (is_creature and perm.summoning_sick)):
                continue
            mana_part = _re.sub(r"\{T\}", "", ab.cost).strip().strip(",").strip()
            if mana_part and not can_pay_cost(player.mana_pool, mana_part):
                continue
            # For pure mana abilities, only offer the tap if it makes progress toward
            # casting a spell:
            #   - If current pool already casts everything tapping everything can reach,
            #     more mana is useless.
            #   - If tapping this land enables more spells than the current pool, include.
            #   - If tapping this land alone doesn't help yet (multi-tap needed), include
            #     only when the full set of available taps would eventually reach a spell.
            produced = _mana_add_symbol(ab.effect)
            if produced is not None:
                if _current_castable >= _total_castable:
                    # Already at the maximum castable with all mana available — useless tap
                    continue
                pool_after = _pool_after_add(player.mana_pool, produced)
                if _castable_count(pool_after) <= _current_castable:
                    # This single tap doesn't unlock a new spell by itself; only include
                    # when tapping everything available would eventually reach one
                    if _total_castable == 0:
                        continue
            actions.append(LegalAction(
                action_type="activate",
                permanent_id=perm.id,
                card_name=perm.card.name,
                ability_index=idx,
                description=f"Activate {perm.card.name}: {ab.raw_text}",
            ))

    # Declare attackers (active player, declare attackers step)
    if is_active and gs.step == Step.DECLARE_ATTACKERS:
        attackers = [
            p for p in gs.battlefield
            if p.controller == player_name
            and "creature" in p.card.type_line.lower()
            and not p.tapped
            and (not p.summoning_sick or "haste" in p.card.keywords)
            and "defender" not in p.card.keywords
        ]
        if attackers:
            opponent = next((p.name for p in gs.players if p.name != player_name), "")
            attacker_names = ", ".join(p.card.name for p in attackers)
            actions.append(LegalAction(
                action_type="declare_attackers",
                valid_targets=[p.id for p in attackers],  # attacker permanent IDs
                card_name=opponent,                        # defending player
                description=f"Attack with: {attacker_names}",
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
