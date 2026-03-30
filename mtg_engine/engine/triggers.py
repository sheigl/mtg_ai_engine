"""
Trigger detection. REQ-A08, REQ-S04.
CR 603: handling triggered abilities.
Listens for zone-change, phase-change, and damage events.
Queues triggers for APNAP ordering.
"""
import logging
import uuid
import re as _re

from mtg_engine.models.game import GameState, PendingTrigger, Permanent
from mtg_engine.engine.zones import register_zone_change_listener, ZoneChangeEvent

logger = logging.getLogger(__name__)

# Trigger patterns for "whenever you cast" and "whenever a player casts"
CAST_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you cast (?:(?:a|an) )?(.*?)(?:,|\.|\?|$)", _re.IGNORECASE),
    _re.compile(r"whenever a (?:creature|artifact|instant|sorcery|enchantment|planeswalker|land) is cast", _re.IGNORECASE),
    _re.compile(r"whenever (?:(?:a|an) )?(.*?)(?:,|\.|\?|$) is cast", _re.IGNORECASE),
]

# Trigger patterns for "whenever [creature] attacks"
ATTACK_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:this|~|this creature) attacks", _re.IGNORECASE),
    _re.compile(r"whenever a (?:creature|creature with) (?:(?:that|which) )?(?:attacks|is attacking)", _re.IGNORECASE),
    _re.compile(r"whenever (?:(?:a|an) )?(.*?)(?:,|\.|\?|$) attacks", _re.IGNORECASE),
]

# Trigger patterns for "whenever [creature] blocks"
BLOCK_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:this|~|this creature) blocks", _re.IGNORECASE),
    _re.compile(r"whenever a (?:creature|creature with) (?:(?:that|which) )?(?:blocks|is blocking)", _re.IGNORECASE),
    _re.compile(r"whenever (?:(?:a|an) )?(.*?)(?:,|\.|\?|$) blocks", _re.IGNORECASE),
]


def initialize_triggers(game_state: GameState) -> None:
    """
    Register the zone-change listener for trigger detection.
    Call once when a game is created. CR 603.2.
    Guard against duplicate registration (idempotent).
    """
    from mtg_engine.engine.zones import _zone_change_listeners
    if _on_zone_change not in _zone_change_listeners:
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
                # CR 603.3: "you may" triggers are optional — detect and mark
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="zone_change",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
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
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="phase_change",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
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


def check_damage_triggers(
    game_state: GameState,
    assignments: list,
) -> GameState:
    """
    Check for "whenever this deals combat damage" triggers after damage assignment.
    CR 603.2: triggered abilities use a triggering event.
    Scans permanents for combat-damage trigger patterns and queues PendingTriggers.
    """
    import re as _re
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    # Build set of permanent IDs that dealt damage to a player this assignment
    player_names = {p.name for p in game_state.players}
    damaging_perm_ids: set[str] = set()
    for assign in assignments:
        if assign.target_id in player_names and assign.damage > 0:
            damaging_perm_ids.add(assign.source_id)

    if not damaging_perm_ids:
        return game_state

    _COMBAT_DAMAGE_TRIGGER_RE = _re.compile(
        r"whenever (?:this|~|this creature) deals? (?:combat )?damage(?: to a player)?",
        _re.IGNORECASE,
    )

    for perm in game_state.battlefield:
        if perm.id not in damaging_perm_ids:
            continue
        oracle = perm.card.oracle_text or ""
        if _COMBAT_DAMAGE_TRIGGER_RE.search(oracle):
            trigger = PendingTrigger(
                id=str(uuid.uuid4()),
                source_permanent_id=perm.id,
                controller=perm.controller,
                trigger_type="combat_damage",
                effect_description=oracle,
                source_card_name=perm.card.name,
            )
            game_state.pending_triggers.append(trigger)
            logger.debug(
                "Combat damage trigger queued from %s (controller: %s)",
                perm.card.name, perm.controller,
            )

    return game_state


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


def check_cast_triggers(
    game_state: GameState,
    caster: str,
    spell_type_line: str,
    spell_name: str,
) -> GameState:
    """
    Check for "whenever you cast" and "whenever a player casts" triggers.
    Called from cast_spell() in stack.py after placing spell on stack.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    # Check all permanents for cast triggers
    all_permanents = list(game_state.battlefield)

    for perm in all_permanents:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            
            # Check for "whenever you cast" triggers
            if "whenever you cast" in cond:
                # Check if the caster matches the trigger
                if caster in cond or "you" in cond:
                    # Check if the spell type matches
                    if spell_type_line.lower() in cond or spell_name.lower() in cond:
                        is_optional = ab.effect.lower().startswith("you may")
                        trigger = PendingTrigger(
                            id=str(uuid.uuid4()),
                            source_permanent_id=perm.id,
                            controller=perm.controller,
                            trigger_type="cast",
                            effect_description=ab.effect,
                            source_card_name=card.name,
                            is_optional=is_optional,
                        )
                        game_state.pending_triggers.append(trigger)
                        logger.debug(
                            "Cast trigger queued: %r from %s (controller: %s)",
                            ab.trigger_condition, card.name, perm.controller,
                        )
            
            # Check for "whenever a player casts" triggers
            elif "whenever a player casts" in cond:
                # This is a general trigger for any player casting any spell
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="cast",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                game_state.pending_triggers.append(trigger)
                logger.debug(
                    "Cast trigger queued: %r from %s (controller: %s)",
                    ab.trigger_condition, card.name, perm.controller,
                )

    return game_state


def check_attack_triggers(
    game_state: GameState,
    attacker_ids: list[str],
) -> GameState:
    """
    Check for "whenever [creature] attacks" triggers.
    Called from declare_attackers() in combat.py after validation.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    # Check all permanents for attack triggers
    all_permanents = list(game_state.battlefield)
    
    for perm in all_permanents:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            
            # Check for "whenever this creature attacks" triggers
            if "whenever this creature attacks" in cond or "whenever ~ attacks" in cond:
                # Check if this permanent is among the attackers
                if perm.id in attacker_ids:
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="attack",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Attack trigger queued: %r from %s (controller: %s)",
                        ab.trigger_condition, card.name, perm.controller,
                    )
            
            # Check for "whenever a creature attacks" triggers
            elif "whenever a creature attacks" in cond:
                # This is a general trigger for any creature attacking
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="attack",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                game_state.pending_triggers.append(trigger)
                logger.debug(
                    "Attack trigger queued: %r from %s (controller: %s)",
                    ab.trigger_condition, card.name, perm.controller,
                )
            
            # Check for "whenever [creature] attacks" triggers with specific creature names
            elif any(pattern.search(cond) for pattern in ATTACK_TRIGGER_PATTERNS):
                # Check if this permanent is among the attackers
                if perm.id in attacker_ids:
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="attack",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Attack trigger queued: %r from %s (controller: %s)",
                        ab.trigger_condition, card.name, perm.controller,
                    )

    # Handle exalted and battle cry triggers
    if len(attacker_ids) == 1:
        # Exalted: Find all permanents with "exalted" keyword owned by the attacking player
        attacker_id = attacker_ids[0]
        attacker_permanent = next((p for p in all_permanents if p.id == attacker_id), None)
        if attacker_permanent:
            attacker_controller = attacker_permanent.controller
            
            # Check for exalted triggers
            for perm in all_permanents:
                card = perm.card
                # Check if this permanent has "exalted" in its oracle text or keywords
                if "exalted" in (card.oracle_text or "").lower() or "exalted" in (card.keywords or []):
                    # This is an exalted permanent, create a trigger for it
                    is_optional = False  # Exalted triggers are not optional
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="attack",
                        effect_description="Exalted trigger",
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Exalted trigger queued from %s (controller: %s)",
                        card.name, perm.controller,
                    )
    
    # Handle battle cry triggers
    # For each attacker, check if it has battle cry and add triggers for other attackers
    for attacker_id in attacker_ids:
        attacker_permanent = next((p for p in all_permanents if p.id == attacker_id), None)
        if attacker_permanent:
            card = attacker_permanent.card
            # Check if this attacker has "battle cry" in its oracle text or keywords
            if "battle cry" in (card.oracle_text or "").lower() or "battle cry" in (card.keywords or []):
                # This attacker has battle cry, so create triggers for all other attackers
                for other_attacker_id in attacker_ids:
                    if other_attacker_id != attacker_id:
                        # Find the other attacker permanent
                        other_attacker_permanent = next((p for p in all_permanents if p.id == other_attacker_id), None)
                        if other_attacker_permanent:
                            # Create a trigger for the other attacker
                            is_optional = False  # Battle cry triggers are not optional
                            trigger = PendingTrigger(
                                id=str(uuid.uuid4()),
                                source_permanent_id=other_attacker_permanent.id,
                                controller=other_attacker_permanent.controller,
                                trigger_type="attack",
                                effect_description="Battle cry trigger",
                                source_card_name=other_attacker_permanent.card.name,
                                is_optional=is_optional,
                            )
                            game_state.pending_triggers.append(trigger)
                            logger.debug(
                                "Battle cry trigger queued from %s (controller: %s) for %s",
                                card.name, attacker_permanent.controller, other_attacker_permanent.card.name,
                            )

    return game_state


def check_block_triggers(
    game_state: GameState,
    blocker_ids: list[str],
) -> GameState:
    """
    Check for "whenever [creature] blocks" triggers.
    Called from declare_blockers() in combat.py after validation.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    # Check all permanents for block triggers
    all_permanents = list(game_state.battlefield)
    
    for perm in all_permanents:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            
            # Check for "whenever this creature blocks" triggers
            if "whenever this creature blocks" in cond or "whenever ~ blocks" in cond:
                # Check if this permanent is among the blockers
                if perm.id in blocker_ids:
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="block",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Block trigger queued: %r from %s (controller: %s)",
                        ab.trigger_condition, card.name, perm.controller,
                    )
            
            # Check for "whenever a creature blocks" triggers
            elif "whenever a creature blocks" in cond:
                # This is a general trigger for any creature blocking
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="block",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                game_state.pending_triggers.append(trigger)
                logger.debug(
                    "Block trigger queued: %r from %s (controller: %s)",
                    ab.trigger_condition, card.name, perm.controller,
                )
            
            # Check for "whenever [creature] blocks" triggers with specific creature names
            elif any(pattern.search(cond) for pattern in BLOCK_TRIGGER_PATTERNS):
                # Check if this permanent is among the blockers
                if perm.id in blocker_ids:
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="block",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Block trigger queued: %r from %s (controller: %s)",
                        ab.trigger_condition, card.name, perm.controller,
                    )

    return game_state


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
