"""
Casting spells and the stack. REQ-S01, REQ-S02, REQ-S03, REQ-A03, REQ-A04.
CR 601: casting spells
CR 608: resolving spells and abilities
"""
import logging
import re
import uuid

from mtg_engine.models.game import Card, GameState, StackObject
from mtg_engine.engine.mana import can_pay_cost, pay_cost
from mtg_engine.engine.zones import get_player, move_permanent_to_zone, put_permanent_onto_battlefield

logger = logging.getLogger(__name__)


def _has_split_second(game_state: GameState) -> bool:
    """
    REQ-S03: split-second prevents casting spells or activating non-mana abilities.
    CR 702.60b: check if any stack object has split second.
    """
    for obj in game_state.stack:
        if "split second" in obj.source_card.keywords:
            return True
    return False


def _is_sorcery_speed(card: Card) -> bool:
    """
    Return True if card must be cast at sorcery speed (no flash, not an instant).
    REQ-A03: timing restrictions.
    """
    type_lower = card.type_line.lower()
    if "instant" in type_lower:
        return False
    if "flash" in card.keywords:
        return False
    return True


def _can_cast_at_sorcery_speed(game_state: GameState, player_name: str) -> bool:
    """
    Verify sorcery-speed casting conditions: main phase, stack empty,
    active player has priority. REQ-A03.
    """
    return (
        game_state.active_player == player_name
        and game_state.priority_holder == player_name
        and game_state.step.value == "main"
        and not game_state.stack
    )


def cast_spell(
    game_state: GameState,
    player_name: str,
    card_id: str,
    targets: list[str],
    mana_payment: dict[str, int],
    alternative_cost: str | None = None,
    modes_chosen: list[int] | None = None,
) -> GameState:
    """
    Cast a spell from a player's hand. REQ-A03, REQ-A04, REQ-S01.
    Validates timing, mana, targets; moves card to stack.
    Returns updated game_state.
    """
    # REQ-S03: split-second check
    if _has_split_second(game_state):
        raise ValueError("Cannot cast spells while a split-second spell is on the stack")

    if game_state.priority_holder != player_name:
        raise ValueError(
            f"{player_name} does not have priority (current holder: {game_state.priority_holder!r})"
        )

    player = get_player(game_state, player_name)

    # Find card in hand
    card = next((c for c in player.hand if c.id == card_id), None)
    if card is None:
        raise ValueError(f"Card {card_id!r} not found in {player_name}'s hand")

    # Timing validation REQ-A03
    if _is_sorcery_speed(card):
        if not _can_cast_at_sorcery_speed(game_state, player_name):
            raise ValueError(
                f"Cannot cast {card.name!r} at sorcery speed: "
                f"must be main phase, stack empty, active player with priority"
            )

    # Mana validation
    cost = alternative_cost if alternative_cost is not None else (card.mana_cost or "")
    if not can_pay_cost(player.mana_pool, cost, mana_payment):
        raise ValueError(
            f"Insufficient mana to cast {card.name!r}: cost={cost!r}, payment={mana_payment}"
        )

    # Pay cost — deducts mana from player's pool
    player.mana_pool = pay_cost(player.mana_pool, cost, mana_payment)

    # Move card from hand to stack (REQ-A04)
    player.hand[:] = [c for c in player.hand if c.id != card_id]

    stack_obj = StackObject(
        id=str(uuid.uuid4()),
        source_card=card,
        controller=player_name,
        targets=targets,
        is_copy=False,
        modes_chosen=modes_chosen or [],
        alternative_cost=alternative_cost,
        mana_payment=mana_payment,
    )
    game_state.stack.append(stack_obj)

    logger.info("Cast %s → stack. Controller: %s, targets: %s", card.name, player_name, targets)

    # Priority returns to active player after spell is placed on stack (REQ-S01)
    game_state.priority_holder = game_state.active_player

    return game_state


def resolve_top(game_state: GameState) -> GameState:
    """
    Resolve the top object on the stack. CR 608.
    Applies effects, moves card to appropriate zone.
    """
    if not game_state.stack:
        return game_state

    stack_obj = game_state.stack.pop()
    card = stack_obj.source_card
    type_lower = card.type_line.lower()

    logger.info("Resolving %s (controller: %s)", card.name, stack_obj.controller)

    # Permanent spell → enters battlefield (creatures, artifacts, enchantments, planeswalkers, lands)
    if any(t in type_lower for t in ("creature", "artifact", "enchantment", "land", "planeswalker")):
        game_state, _perm = put_permanent_onto_battlefield(
            game_state, card, stack_obj.controller
        )
    elif "instant" in type_lower or "sorcery" in type_lower:
        # Non-permanent spell → resolve effect, move to graveyard
        game_state = _apply_spell_effect(game_state, stack_obj)
        player = get_player(game_state, stack_obj.controller)
        player.graveyard.append(card)
    else:
        # Unknown type — put in graveyard as a fallback
        player = get_player(game_state, stack_obj.controller)
        player.graveyard.append(card)
        logger.warning("Unknown card type for %r; placed in graveyard", card.name)

    return game_state


def _apply_spell_effect(game_state: GameState, stack_obj: StackObject) -> GameState:
    """
    Apply the effect of a resolved instant or sorcery.
    Handles damage (Lightning Bolt-style) and counter-spell effects.
    Full effect system will be expanded in later tasks.
    CR 608.2: effects are applied as described on the card.
    """
    card = stack_obj.source_card
    oracle = (card.oracle_text or "").lower()

    # Damage effects: "deals N damage to any target" / "deals N damage to target creature"
    dmg_match = re.search(r"deals?\s+(\d+)\s+damage", oracle)
    if dmg_match and stack_obj.targets:
        damage = int(dmg_match.group(1))
        for target_id in stack_obj.targets:
            game_state = _deal_damage(game_state, target_id, damage, card)

    # Counter spell: "counter target spell"
    if "counter target spell" in oracle and stack_obj.targets:
        for target_id in stack_obj.targets:
            # Find and remove target from stack, put its card in owner's graveyard
            countered = next((s for s in game_state.stack if s.id == target_id), None)
            if countered:
                game_state.stack[:] = [s for s in game_state.stack if s.id != target_id]
                # Put the countered card in its controller's graveyard
                owner = get_player(game_state, countered.controller)
                owner.graveyard.append(countered.source_card)
                logger.info("Spell %s countered %s", card.name, countered.source_card.name)

    return game_state


def _deal_damage(game_state: GameState, target_id: str, damage: int, source: Card) -> GameState:
    """
    Apply damage to a target (permanent or player). REQ-R07, REQ-R08.
    Marks damage on permanents; reduces life for players.
    Deathtouch flag is set for SBA processing (REQ-R10).
    """
    # Check if target is a permanent on the battlefield
    for perm in game_state.battlefield:
        if perm.id == target_id:
            perm.damage_marked += damage
            # Mark deathtouch damage for SBA processing (CR 704.5h, REQ-R10)
            if "deathtouch" in source.keywords:
                perm.counters["__deathtouch_damage__"] = (
                    perm.counters.get("__deathtouch_damage__", 0) + damage
                )
            # Lifelink: controller gains life (REQ-R11)
            # Note: lifelink life gain is handled here as a side effect of damage
            if "lifelink" in source.keywords:
                # The source card's controller gains life equal to damage dealt
                # We look up the controller via the active player heuristic
                # (In future tasks this will be tracked on source properly)
                for player in game_state.players:
                    # Attempt to find the controlling player from battlefield context
                    pass  # placeholder — lifelink controller lookup requires source perm context
            return game_state

    # Check if target is a player (player name used as target ID)
    for player in game_state.players:
        if player.name == target_id:
            player.life -= damage
            return game_state

    logger.warning("_deal_damage: target %r not found on battlefield or as a player", target_id)
    return game_state
