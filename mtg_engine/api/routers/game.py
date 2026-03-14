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
from mtg_engine.card_data.deck_loader import load_deck

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/game", tags=["game"])


# ─── Request bodies ───────────────────────────────────────────────────────────

class CreateGameRequest(BaseModel):
    player1_name: str = "player_1"
    player2_name: str = "player_2"
    deck1: list[str]   # card names
    deck2: list[str]
    seed: int | None = None


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


# ─── Game lifecycle ───────────────────────────────────────────────────────────

@router.post("")
def create_game(req: CreateGameRequest) -> dict:
    """POST /game — create a new game. REQ-G01"""
    try:
        deck1_cards = load_deck(req.deck1)
        deck2_cards = load_deck(req.deck2)
    except Exception as e:
        raise _err(str(e), "DECK_LOAD_ERROR")

    mgr = get_manager()
    gs = mgr.create_game(
        req.player1_name, req.player2_name,
        deck1_cards, deck2_cards,
        seed=req.seed,
    )
    return _ok(gs)


@router.get("/{game_id}")
def get_game(game_id: str) -> dict:
    """GET /game/{game_id} — full game state. REQ-G02"""
    return _ok(_get_gs(game_id))


@router.delete("/{game_id}")
def delete_game(game_id: str) -> dict:
    """DELETE /game/{game_id} — end game, trigger export. REQ-G03"""
    mgr = get_manager()
    try:
        gs = mgr.delete(game_id)
    except KeyError:
        raise _err("Game not found", "GAME_NOT_FOUND", 404)
    # Export hooks will be wired in Phase 6
    return {"data": {"game_id": game_id, "status": "deleted", "winner": gs.winner}}


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
    try:
        gs = pass_priority(gs, player)
        gs = _run_sbas(gs)
    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
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
        gs, _ = put_permanent_onto_battlefield(gs, card, gs.active_player, tapped=False)
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

    try:
        gs = cast_spell(
            gs,
            gs.priority_holder,
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

    try:
        from mtg_engine.card_data.ability_parser import parse_oracle_text, ActivatedAbility
        from mtg_engine.engine.mana import pay_cost, add_mana

        perm = next((p for p in gs.battlefield if p.id == req.permanent_id), None)
        if perm is None:
            raise ValueError(f"Permanent {req.permanent_id!r} not on battlefield")
        if perm.controller != gs.priority_holder:
            raise ValueError("You don't control that permanent")

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

    try:
        gs = declare_attackers(gs, req.attack_declarations)
        gs = _run_sbas(gs)
    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
    return _ok(gs)


@router.post("/{game_id}/declare-blockers")
def do_declare_blockers(game_id: str, req: DeclareBlockersRequest) -> dict:
    """POST /game/{game_id}/declare-blockers. REQ-A12"""
    mgr = get_manager()
    if req.dry_run:
        gs = mgr.snapshot(game_id)
    else:
        gs = _get_gs(game_id)

    try:
        gs = declare_blockers(gs, req.block_declarations)
        gs = _run_sbas(gs)
    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
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

    try:
        gs = assign_combat_damage(gs, req.assignments)
        gs = _run_sbas(gs)
    except ValueError as e:
        raise _err(str(e), "INVALID_ACTION")

    if not req.dry_run:
        mgr.update(game_id, gs)
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
    gs = _get_gs(game_id)
    actions = _compute_legal_actions(gs)
    return {
        "data": {
            "priority_player": gs.priority_holder,
            "phase": gs.phase.value,
            "step": gs.step.value,
            "legal_actions": [a.model_dump() for a in actions],
        }
    }


def _compute_legal_actions(gs: GameState) -> list[LegalAction]:
    """Compute all legal actions for the priority holder."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, ActivatedAbility
    from mtg_engine.engine.mana import can_pay_cost

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
    from mtg_engine.engine.stack import _is_sorcery_speed, _can_cast_at_sorcery_speed, _has_split_second
    if not _has_split_second(gs):
        for card in player.hand:
            if "land" in card.type_line.lower():
                continue
            sorcery_speed = _is_sorcery_speed(card)
            if sorcery_speed and not _can_cast_at_sorcery_speed(gs, player_name):
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
    for perm in gs.battlefield:
        if perm.controller != player_name:
            continue
        abilities = parse_oracle_text(perm.card.oracle_text or "", perm.card.type_line)
        activated = [a for a in abilities if isinstance(a, ActivatedAbility)]
        for idx, ab in enumerate(activated):
            # Check tap cost
            if "{T}" in ab.cost and perm.tapped:
                continue
            import re
            mana_part = re.sub(r"\{T\}", "", ab.cost).strip().strip(",").strip()
            if mana_part and not can_pay_cost(player.mana_pool, mana_part):
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
            actions.append(LegalAction(
                action_type="declare_attackers",
                description=f"{len(attackers)} creature(s) available to attack",
            ))

    # Put pending triggers on stack
    for trigger in gs.pending_triggers:
        if trigger.controller == player_name:
            actions.append(LegalAction(
                action_type="put_trigger",
                description=f"Put trigger on stack: {trigger.effect_description}",
            ))

    return actions
