"""
Trigger detection. REQ-A08, REQ-S04.
CR 603: handling triggered abilities.
Listens for zone-change, phase-change, and damage events.
Queues triggers for APNAP ordering.
"""
import logging
import uuid

from mtg_engine.models.game import GameState, PendingTrigger, Permanent
from mtg_engine.engine.zones import register_zone_change_listener, ZoneChangeEvent

logger = logging.getLogger(__name__)


def initialize_triggers(game_state: GameState) -> None:
    """
    Register the zone-change listener for trigger detection.
    Call once when a game is created. CR 603.2.
    """
    register_zone_change_listener(_on_zone_change)


def _on_zone_change(event: ZoneChangeEvent, game_state: GameState) -> None:
    """
    Inspect zone change event and queue matching triggers from all permanents.
    CR 603.2, CR 603.6: triggered abilities fire automatically when conditions are met.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    for perm in list(game_state.battlefield):
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            if _matches_zone_change(ab, event, perm, game_state):
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="zone_change",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                )
                game_state.pending_triggers.append(trigger)
                logger.debug(
                    "Trigger queued: %r from %s (controller: %s)",
                    ab.trigger_condition, card.name, perm.controller,
                )


def _matches_zone_change(
    ability,
    event: ZoneChangeEvent,
    source_perm: Permanent,
    game_state: GameState,
) -> bool:
    """
    Check if a triggered ability's condition matches a zone-change event.
    Simplified pattern matching against common trigger conditions. CR 603.2.
    """
    cond = ability.trigger_condition.lower()
    from_z = event.get("from_zone", "")
    to_z = event.get("to_zone", "")
    event_card_id = event.get("card_id", "")

    # "when this creature dies" / "whenever a creature dies"
    # "dies" = moves from battlefield to graveyard
    if "dies" in cond or ("graveyard" in cond and from_z == "battlefield"):
        if to_z == "graveyard" and from_z == "battlefield":
            # Self-referential trigger: "when this creature dies"
            if "this" in cond or "enchanted" in cond:
                return event_card_id == source_perm.id
            return True

    # "when [this permanent] enters [the battlefield]" / "whenever a creature enters"
    if "enters" in cond and to_z == "battlefield":
        if "this" in cond or "enchanted" in cond:
            return event_card_id == source_perm.id
        return True

    # "when [this permanent] leaves the battlefield"
    if "leaves the battlefield" in cond and from_z == "battlefield":
        if "this" in cond:
            return event_card_id == source_perm.id
        return True

    return False


def check_phase_triggers(game_state: GameState) -> GameState:
    """
    Check for "at the beginning of [phase/step]" triggers. CR 603.2b.
    Called at the start of each step (after begin_step).
    REQ-A08: engine automatically detects and queues triggered abilities.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    current_step = game_state.step.value
    current_phase = game_state.phase.value

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            if _matches_phase_trigger(cond, current_step, current_phase, perm, game_state):
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="phase_change",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                )
                game_state.pending_triggers.append(trigger)
                logger.debug(
                    "Phase trigger queued: %r from %s", ab.trigger_condition, card.name
                )

    return game_state


def _matches_phase_trigger(
    cond: str,
    step: str,
    phase: str,
    source_perm: Permanent,
    game_state: GameState,
) -> bool:
    """
    Match "at the beginning of [step]" triggers. CR 603.2b.
    """
    if "beginning of your upkeep" in cond and step == "upkeep":
        return source_perm.controller == game_state.active_player
    if "beginning of each upkeep" in cond and step == "upkeep":
        return True
    if "beginning of your end step" in cond and step == "end":
        return source_perm.controller == game_state.active_player
    if "beginning of each end step" in cond and step == "end":
        return True
    if "beginning of combat" in cond and step == "beginning_of_combat":
        return True
    return False


def get_pending_triggers_for_player(
    game_state: GameState, player_name: str
) -> list[PendingTrigger]:
    """Return all pending triggers controlled by player_name. REQ-A09."""
    return [t for t in game_state.pending_triggers if t.controller == player_name]


def apnap_order_triggers(game_state: GameState) -> list[PendingTrigger]:
    """
    Return pending triggers in APNAP order. REQ-S04, CR 603.3b.
    Active player's triggers are placed on the stack first,
    then non-active player's triggers.
    """
    active_triggers = [
        t for t in game_state.pending_triggers
        if t.controller == game_state.active_player
    ]
    other_triggers = [
        t for t in game_state.pending_triggers
        if t.controller != game_state.active_player
    ]
    return active_triggers + other_triggers


def put_trigger_on_stack(
    game_state: GameState, trigger_id: str, targets: list[str]
) -> GameState:
    """
    Move a pending trigger onto the stack as a StackObject. REQ-A10.
    CR 603.3: triggered abilities go on stack next time a player receives priority.
    """
    from mtg_engine.models.game import StackObject, Card

    trigger = next(
        (t for t in game_state.pending_triggers if t.id == trigger_id), None
    )
    if trigger is None:
        raise ValueError(f"Trigger {trigger_id!r} not found in pending triggers")

    # Find source permanent on battlefield (may have left since trigger fired)
    source_perm = next(
        (p for p in game_state.battlefield if p.id == trigger.source_permanent_id), None
    )
    source_card = (
        source_perm.card
        if source_perm is not None
        else Card(
            name=trigger.source_card_name,
            type_line="",
            id=trigger.source_permanent_id,
        )
    )

    stack_obj = StackObject(
        id=str(uuid.uuid4()),
        source_card=source_card,
        controller=trigger.controller,
        targets=targets,
        effects=[trigger.effect_description],
    )
    game_state.stack.append(stack_obj)
    game_state.pending_triggers[:] = [
        t for t in game_state.pending_triggers if t.id != trigger_id
    ]

    logger.info(
        "Trigger from %s placed on stack by %s",
        trigger.source_card_name,
        trigger.controller,
    )
    return game_state
