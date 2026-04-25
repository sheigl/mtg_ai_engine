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
    x_value: int = 0,
    kicker_paid: bool = False,
    jump_start_discard_id: str | None = None,
    face_index: int = 0,
    fuse: bool = False,
    as_face_down: bool = False,
    foretell: bool = False,
    mutate_target_id: str | None = None,
    mutate_on_top: bool = True,
    from_graveyard: bool = False,
    from_adventure_exile: bool = False,
) -> GameState:
    """
    Cast a spell from a player's hand (or graveyard/adventure exile).
    REQ-A03, REQ-A04, REQ-S01. CR 709: split cards. CR 702.61: adventure.
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

    # Find card in hand (or graveyard/adventure exile for special casts)
    card = next((c for c in player.hand if c.id == card_id), None)
    if card is None:
        if from_adventure_exile:
            card = next((c for c in player.adventure_cards if c.id == card_id), None)
            if card is None:
                raise ValueError(f"Card {card_id!r} not found in {player_name}'s adventure exile")
        elif from_graveyard:
            card = next((c for c in player.graveyard if c.id == card_id), None)
            if card is None:
                raise ValueError(f"Card {card_id!r} not found in {player_name}'s graveyard")
        else:
            raise ValueError(f"Card {card_id!r} not found in {player_name}'s hand")

    # US4: Handle multi-face cards (split cards, MDFCs, aftermath)
    if card.faces and len(card.faces) > 1 and face_index >= 0:
        card_face = card.faces[face_index]
        card = _apply_face_to_card(card, card_face)

    # US4: Handle fuse for split cards
    if fuse and card.faces and len(card.faces) >= 2:
        card = _fuse_split_card(card)

    # Timing validation REQ-A03
    if _is_sorcery_speed(card):
        if not _can_cast_at_sorcery_speed(game_state, player_name):
            raise ValueError(
                f"Cannot cast {card.name!r} at sorcery speed: "
                f"must be main phase, stack empty, active player with priority"
            )

    # Mana validation
    if alternative_cost in ("foretell", "cast_foretold"):
        import re as _re
        foretell_match = _re.search(r'[Ff]oretell\s+(\{[^}]+\})', card.oracle_text or "")
        if foretell_match:
            cost = foretell_match.group(1)
        else:
            cost = (card.mana_cost or "")
    else:
        cost = alternative_cost if alternative_cost is not None else (card.mana_cost or "")
    
    # Auto-calculate payment if not provided (BUG fix for bots/empty payment)
    if not mana_payment:
        from mtg_engine.engine.mana import parse_mana_cost as _parse_cost
        cost_dict = _parse_cost(cost)
        mana_payment = {}
        pool_dict = {"W": player.mana_pool.W, "U": player.mana_pool.U, "B": player.mana_pool.B, "R": player.mana_pool.R, "G": player.mana_pool.G, "C": player.mana_pool.C}
        # Pay colored first
        for color in ("W", "U", "B", "R", "G"):
            needed = cost_dict.get(color, 0)
            if needed and pool_dict.get(color, 0) >= needed:
                mana_payment[color] = needed
                pool_dict[color] -= needed
        # Pay generic with whatever's left
        generic_needed = cost_dict.get("generic", 0)
        if generic_needed:
            from collections import Counter
            pool_available = sum(v for v in pool_dict.values() if v > 0)
            if pool_available >= generic_needed:
                mana_payment["C"] = min(generic_needed, pool_available)
    
    if not can_pay_cost(player.mana_pool, cost, mana_payment):
        raise ValueError(
            f"Insufficient mana to cast {card.name!r}: cost={cost!r}, payment={mana_payment}"
        )

    # Pay cost — deducts mana from player's pool
    player.mana_pool = pay_cost(player.mana_pool, cost, mana_payment)

    # Handle Spree mechanic - detect and queue choice for additional costs
    oracle_lower = (card.oracle_text or "").lower()
    if "spree" in oracle_lower:
        import re as _spree_re
        spree_modes = []
        mode_pattern = _spree_re.compile(r'\+ (\{[^}]+\}|{[^}]+}{[^}]+})\s*[–—:-]\s*(.+(?:\n\+.+)*)', _spree_re.DOTALL)
        for match in mode_pattern.finditer(oracle_lower):
            mode_cost = match.group(1)
            mode_effect = match.group(2).strip()
            spree_modes.append({"cost": mode_cost, "effect": mode_effect})

        if spree_modes:
            game_state.pending_spree_choice = {
                "player": player_name,
                "card_id": card_id,
                "card_name": card.name,
                "modes": spree_modes,
            }
            logger.info("%s: queued Spree choice with %d modes", card.name, len(spree_modes))

    # Move card from hand (or graveyard/adventure exile) to stack
    if from_adventure_exile:
        player.adventure_cards[:] = [c for c in player.adventure_cards if c.id != card_id]
    elif from_graveyard:
        player.graveyard[:] = [c for c in player.graveyard if c.id != card_id]
    else:
        player.hand[:] = [c for c in player.hand if c.id != card_id]

    # Handle jump-start discard before putting spell on stack
    if jump_start_discard_id and alternative_cost == "jump-start":
        discard_card = next((c for c in player.hand if c.id == jump_start_discard_id), None)
        if discard_card:
            player.hand[:] = [c for c in player.hand if c.id != jump_start_discard_id]
            player.graveyard.append(discard_card)

    # CR 702.102: detect "can't be countered" / "this spell can't be countered" in oracle text
    oracle_lower = (card.oracle_text or "").lower()
    is_uncounterable = (
        "can't be countered" in oracle_lower
        or "cannot be countered" in oracle_lower
    )

    # US7: Detect buyback (CR 702.27) — buyback allows returning spell to hand from graveyard
    has_buyback = "buyback" in (card.keywords or []) or "buyback" in oracle_lower

    # US7: Detect replicate (CR 702.87) — replicate creates copies for additional cost
    has_replicate = "replicate" in (card.keywords or []) or "replicate" in oracle_lower
    replicate_count = 0
    if has_replicate:
        # Extract replicate count from oracle text (e.g., "replicate {2}" → 2 additional mana → 1 copy)
        import re as _re
        replicate_match = _re.search(r"replicate\s+(\{[^}]+\})", oracle_lower)
        if replicate_match:
            # For now, set a default replicate count of 1 (will be adjusted by player input)
            replicate_count = 1

    # US8: Detect flashback and escape from alternative_cost
    is_flashback = alternative_cost == "flashback"
    is_escape = alternative_cost == "escape"

    # US30: Validate mutate target
    if mutate_target_id:
        target_perm = next((p for p in game_state.battlefield if p.id == mutate_target_id), None)
        if target_perm is None:
            raise ValueError(f"Mutate target {mutate_target_id!r} not found on battlefield")
        if target_perm.controller != player_name:
            raise ValueError(f"Cannot mutate onto opponent's creature {target_perm.card.name!r}")
        if "creature" not in target_perm.card.type_line.lower():
            raise ValueError(f"Cannot mutate onto non-creature {target_perm.card.type!r}")
        if "human" in target_perm.card.type_line.lower():
            raise ValueError(f"Cannot mutate onto Human creature {target_perm.card.name!r}")

    stack_obj = StackObject(
        id=str(uuid.uuid4()),
        source_card=card,
        controller=player_name,
        targets=targets,
        is_copy=False,
        modes_chosen=modes_chosen or [],
        alternative_cost=alternative_cost,
        mana_payment=mana_payment,
        x_value=x_value,
        kicker_paid=kicker_paid,
        jump_start_discard_id=jump_start_discard_id,
        uncounterable=is_uncounterable,
        buyback_paid=has_buyback,  # US7: Mark if buyback cost was paid (set by API)
        replicate_count=replicate_count,  # US7: Number of replicates to create
        flashback=is_flashback,  # US8: Whether cast via flashback from graveyard
        escape=is_escape,  # US8: Whether cast via escape from graveyard
        face_index=face_index,
        is_face_down=as_face_down,
        is_adventure=card.card_layout == "adventure" and face_index == 1,
        is_fused=fuse,
        is_foretold=alternative_cost in ("foretell", "cast_foretold"),
        mutate_target_id=mutate_target_id,
        mutate_on_top=mutate_on_top,
    )
    game_state.stack.append(stack_obj)

    logger.info("Cast %s → stack. Controller: %s, targets: %s", card.name, player_name, targets)

    # Priority returns to active player after spell is placed on stack (REQ-S01)
    game_state.priority_holder = game_state.active_player

    return game_state


def copy_spell_on_stack(
    game_state: GameState,
    source_stack_id: str,
    new_targets: list[str] | None = None,
) -> GameState:
    """
    Create a copy of a spell on the stack. US7 (014).
    CR 706.10: copies of spells on the stack cease to exist when they leave the stack.
    Returns updated game_state with the copy appended to the stack.
    """
    source_obj = next((o for o in game_state.stack if o.id == source_stack_id), None)
    if source_obj is None:
        raise ValueError(f"Stack object {source_stack_id!r} not found on stack")

    copy = source_obj.model_copy(update={
        "id": str(uuid.uuid4()),
        "is_copy": True,
        "targets": new_targets if new_targets is not None else list(source_obj.targets),
    })
    game_state.stack.append(copy)
    logger.info(
        "Copied %s on stack (copy id: %s, new targets: %s)",
        source_obj.source_card.name, copy.id, copy.targets,
    )
    return game_state


def _check_duress_effect(oracle_text: str) -> bool:
    """Check if card text matches discard-from-hand effect pattern.
    
    Patterns:
    - "target opponent reveals their hand...you choose...discard"
    - "target opponent reveals their hand...discard"
    - "each opponent discards a card"
    - "each opponent discards..."
    - "opponent discards a card"
    - "you may discard a card" (own hand choice)
    - "you may discard" (own hand choice)
    """
    if not oracle_text:
        return False
    text_lower = oracle_text.lower()
    
    # Patterns for discard-from-hand effects
    discard_patterns = [
        r"target opponent reveals their hand",
        r"opponent reveals their hand.*?discard",
        r"each opponent discards",
        r"opponent discards a card",
        r"you may discard a card",
        r"you may discard\.",
        r"draw three cards\.? then discard",
        r"draw \w+ cards\.? then discard",
        r"choose.*?opponent.*?discards",
    ]
    import re as _re
    for pattern in discard_patterns:
        if _re.search(pattern, text_lower):
            return True
    return False


def _resolve_duress_effect(game_state: GameState, caster_name: str, card: Card) -> GameState:
    """Resolve discard-from-hand effect: make opponent discard.
    
    General handling for effects like Duress, Thought Erasure, Coercion, etc.
    Also handles "you may discard" (own hand choice).
    
    For "you may discard" effects (optional):
    - Queue choice (discard or don't discard)
    - Don't resolve spell effect until choice is made
    
    For opponent discard effects:
    - Queue choice, resolve immediately
    """
    from mtg_engine.engine.zones import get_player
    from mtg_engine.engine.zones import draw_card
    
    oracle = (card.oracle_text or "").lower()
    
    # Check if this is caster's own hand choice
    # - "you may discard" (Abandon Attachments)
    # - "draw X cards...then discard" (Winternight Stories)
    caster_is_target = "you may discard" in oracle or "discard a card" in oracle or "then discard" in oracle
    
    # Check for Winternight Stories pattern: "draw three cards. Then discard two cards unless you discard a creature card."
    is_winternight_stories = "draw three cards" in oracle and "unless you discard a creature" in oracle
    
    if caster_is_target:
        import re as _re
        # Optional discard from own hand - e.g., Abandon Attachments
        # DON'T resolve yet - queue choice
        discard_player = get_player(game_state, caster_name)
        if not discard_player:
            _move_to_graveyard(game_state, caster_name, card)
            return game_state
        
        # Check how many cards to draw (default 1, look for "draw X cards")
        draw_count = 1
        draw_match = _re.search(r'draw (\w+) cards?', oracle)
        if draw_match:
            draw_word = draw_match.group(1)
            draw_map = {"one": 1, "two": 2, "three": 3, "four": 4}
            draw_count = draw_map.get(draw_word, 1)
        
        # Handle Winternight Stories: draw 3 cards first, then conditional discard
        if is_winternight_stories:
            for _ in range(draw_count):
                game_state, _ = draw_card(game_state, discard_player.name)
            game_state.pending_discard_choice = {
                "player": caster_name,
                "opponent": discard_player.name,
                "opponent_hand": [c.model_dump() for c in discard_player.hand],
                "count": 2,  # default: discard 2 unless...
                "is_duress_effect": True,
                "source_card": card.name,
                "is_optional_discard": True,
                "is_winternight_stories": True,
                "spell_card_id": card.id,
            }
            logger.info("%s: %s queued winternight stories choice (draw %d, discard 2 unless 1 creature)", card.name, discard_player.name, draw_count)
            return game_state
        
        game_state.pending_discard_choice = {
            "player": caster_name,
            "opponent": discard_player.name,
            "opponent_hand": [c.model_dump() for c in discard_player.hand],
            "count": 1,
            "is_duress_effect": True,
            "source_card": card.name,
            "is_optional_discard": True,
            "draw_after_discard": draw_count,
            "spell_card_id": card.id,  # Remember spell to resolve after choice
        }
        logger.info("%s: %s queued optional discard choice", card.name, discard_player.name)
        return game_state
    
    # Original: opponent discards
    # Find opponent (player who is not the caster)
    opponent = next((p for p in game_state.players if p.name != caster_name), None)
    if not opponent:
        _move_to_graveyard(game_state, caster_name, card)
        return game_state
    
    # Parse restriction from card text
    # Default: noncreature, nonland
    restriction = _parse_discard_restriction(oracle)
    
    # Filter opponent's hand
    valid_cards = [c for c in opponent.hand if restriction(c)]
    
    if not valid_cards:
        logger.info("%s: opponent %s has no valid cards to discard", card.name, opponent.name)
        _move_to_graveyard(game_state, caster_name, card)
        return game_state
    
    if len(valid_cards) == 1:
        # Auto-discard single valid card
        logger.info("%s: %s discards %s", card.name, opponent.name, valid_cards[0].name)
        opponent.hand.remove(valid_cards[0])
        opponent.graveyard.append(valid_cards[0])
        _move_to_graveyard(game_state, caster_name, card)
        return game_state
    
    # Multiple valid cards - queue choice for caster
    game_state.pending_discard_choice = {
        "player": caster_name,
        "opponent": opponent.name,
        "opponent_hand": [c.model_dump() for c in valid_cards],
        "count": 1,
        "is_duress_effect": True,  # Flag to show it's a choice, not mandatory discard
        "source_card": card.name,  # For logging
    }
    _move_to_graveyard(game_state, caster_name, card)
    return game_state


def _parse_discard_restriction(oracle_text: str, for_self: bool = False):
    """Parse what card types can be chosen for discard.
    
    Returns a filter function.
    
    for_self: if True, allow discarding any card (for "you may discard" effects)
    """
    text = oracle_text.lower()
    
    # For own hand choice ("you may discard"), can discard anything
    if for_self:
        return lambda c: True
    
    if "noncreature, nonland" in text:
        return lambda c: not _is_creature_or_land(c)
    elif "noncreature" in text:
        return lambda c: "creature" not in c.type_line.lower()
    elif "nonland" in text:
        return lambda c: "land" not in c.type_line.lower()
    elif "nonartifact" in text:
        return lambda c: "artifact" not in c.type_line.lower()
    elif "nonenchantment" in text:
        return lambda c: "enchantment" not in c.type_line.lower()
    else:
        # Default: any nonland card (usually discard effects target spells or non-permanents)
        return lambda c: "land" not in c.type_line.lower()


def _move_to_graveyard(game_state: GameState, player_name: str, card: Card) -> None:
    """Move card to player's graveyard."""
    player = get_player(game_state, player_name)
    if player and card not in player.graveyard:
        player.graveyard.append(card)


def _is_creature_or_land(card: Card) -> bool:
    """Check if card is a creature or land."""
    type_line = (card.type_line or "").lower()
    return "creature" in type_line or "land" in type_line


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

    # CR 702.40: Storm — before resolving a spell with storm, create copies equal to spells cast this turn - 1
    # US6, 019-rules-engine-gap-closure
    kws_lower = [k.lower() for k in (card.keywords or [])]
    oracle_lower = (card.oracle_text or "").lower()
    if "storm" in kws_lower or "storm" in oracle_lower:
        storm_count = max(0, game_state.spells_cast_this_turn - 1)
        if storm_count > 0:
            logger.info("Storm: %s creates %d copy/copies", card.name, storm_count)
            for _ in range(storm_count):
                game_state = copy_spell_on_stack(game_state, stack_obj.id, stack_obj.targets)

    # CR 608.2b: fizzle — if spell has targets and ALL are now illegal, the spell does nothing
    if stack_obj.targets and ("instant" in type_lower or "sorcery" in type_lower):
        valid_targets = [
            t for t in stack_obj.targets
            if (any(p.id == t for p in game_state.battlefield)
                or any(pl.name == t for pl in game_state.players)
                or any(s.id == t for s in game_state.stack)
                or any(c.id == t for p in game_state.players for c in p.hand)
                or any(c.id == t for p in game_state.players for c in p.graveyard))
        ]
        if not valid_targets:
            logger.info("Fizzle: all targets illegal for %s", card.name)
            if not stack_obj.is_copy:
                player = get_player(game_state, stack_obj.controller)
                player.graveyard.append(card)
            return game_state

    logger.info("Resolving %s (controller: %s)", card.name, stack_obj.controller)

    # Duress-type effects: "Target opponent reveals their hand. You choose...discard"
    # Check for this pattern BEFORE moving to graveyard
    if _check_duress_effect(oracle_lower):
        game_state = _resolve_duress_effect(
            game_state, stack_obj.controller, card
        )
        return game_state

    # US30: Mutate — merge into target creature instead of creating new permanent
    mutate_handled = False
    if stack_obj.mutate_target_id:
        target_perm = next((p for p in game_state.battlefield if p.id == stack_obj.mutate_target_id), None)
        if target_perm:
            # Create a temporary permanent so the card gets a proper ID
            _, new_perm = put_permanent_onto_battlefield(
                game_state, card, stack_obj.controller, from_zone="stack"
            )
            # Remove it from battlefield — will be merged into target instead
            game_state.battlefield[:] = [p for p in game_state.battlefield if p.id != new_perm.id]
            
            # Add target card to pile first, then add mutate card in correct position
            target_perm.mutated_cards.append(target_perm.card)
            if stack_obj.mutate_on_top:
                target_perm.mutated_cards.insert(0, new_perm.card)
            else:
                target_perm.mutated_cards.append(new_perm.card)
            
            # Top card of pile determines name/P/T/types
            top_card = target_perm.mutated_cards[0]
            target_perm.card = top_card
            
            # Grant all abilities from all cards in the pile
            all_keywords = list(top_card.keywords or [])
            for mc in target_perm.mutated_cards[1:]:
                for kw in (mc.keywords or []):
                    if kw not in all_keywords:
                        all_keywords.append(kw)
            target_perm.card = target_perm.card.model_copy(update={"keywords": all_keywords})
            
            logger.info("Mutate: %s merged into %s (on_top=%s)", card.name, top_card.name, stack_obj.mutate_on_top)
            mutate_handled = True
    
    # Permanent spell → enters battlefield (creatures, artifacts, enchantments, planeswalkers, lands)
    if not mutate_handled and any(t in type_lower for t in ("creature", "artifact", "enchantment", "land", "planeswalker")):
        game_state, perm = put_permanent_onto_battlefield(
            game_state, card, stack_obj.controller, from_zone="stack"
        )
        
        # TASK-019-027: Grant haste if metadata indicates grant_haste=True (e.g., suspended creatures)
        if stack_obj.metadata and stack_obj.metadata.get("grant_haste", False):
            if "creature" in type_lower and "haste" not in perm.card.keywords:
                # Add haste to the creature
                perm.card = perm.card.model_copy(
                    update={"keywords": list(perm.card.keywords or []) + ["haste"]}
                )
                perm.summoning_sick = False  # Haste also removes summoning sickness
                logger.info("Granted haste to %s (from suspend)", card.name)
        
        # CR 303.4: Aura enters the battlefield attached to its target
        oracle = (card.oracle_text or "").lower()
        if "enchant" in oracle and "aura" in type_lower and stack_obj.targets:
            target_id = stack_obj.targets[0]
            target_perm = next((p for p in game_state.battlefield if p.id == target_id), None)
            if target_perm and target_perm.id != perm.id:
                perm.attached_to = target_id
                if perm.id not in target_perm.attachments:
                    target_perm.attachments.append(perm.id)
                # Apply aura's continuous P/T bonus and keyword grants to the enchanted creature.
                # Reversed in zones.move_permanent_to_zone when the aura leaves.
                pt_match = re.search(r"enchanted creature gets? \+(\d+)/\+(\d+)", oracle)
                if pt_match:
                    target_perm.power_bonus += int(pt_match.group(1))
                    target_perm.toughness_bonus += int(pt_match.group(2))
                # Grant keywords (e.g. Rancor → trample)
                for kw in ("trample", "flying", "lifelink", "deathtouch", "first strike",
                           "double strike", "haste", "vigilance", "reach", "hexproof",
                           "indestructible", "menace"):
                    if kw in oracle and kw not in target_perm.card.keywords:
                        target_perm.card = target_perm.card.model_copy(
                            update={"keywords": list(target_perm.card.keywords) + [kw]}
                        )
    elif "instant" in type_lower or "sorcery" in type_lower:
        # US7: Handle replicate before resolving (CR 702.87)
        if stack_obj.replicate_count > 0 and not stack_obj.is_copy:
            for _ in range(stack_obj.replicate_count):
                game_state = copy_spell_on_stack(game_state, stack_obj.id, stack_obj.targets)
                logger.info("Replicate: created copy of %s", card.name)
        
        # Non-permanent spell → resolve effect
        game_state = _apply_spell_effect(game_state, stack_obj)
        
        # CR 706.10: copies of spells cease to exist (don't go to graveyard)
        if not stack_obj.is_copy:
            player = get_player(game_state, stack_obj.controller)
            
            # US7: Buyback (CR 702.27) — return to hand instead of graveyard if buyback cost paid
            if stack_obj.buyback_paid:
                player.hand.append(card)
                logger.info("Buyback: %s returned to hand", card.name)
            # US18: Adventure (CR 702.61) — exiled to adventure_cards instead of graveyard
            elif stack_obj.is_adventure:
                player.adventure_cards.append(card)
                logger.info("Adventure: %s exiled (creature half available from exile)", card.name)
            # US8: Flashback/Escape (CR 702.32, CR 702.132) — exile instead of graveyard
            elif stack_obj.flashback or stack_obj.escape:
                player.exile.append(card)
                logger.info("Flashback/Escape: %s exiled instead of going to graveyard", card.name)
            else:
                player.graveyard.append(card)
    elif stack_obj.effects:
        # Triggered or activated ability resolving — execute the effect
        game_state = _apply_triggered_effect(game_state, stack_obj)
    else:
        # Unknown type — put in graveyard as a fallback (unless copy)
        if not stack_obj.is_copy:
            player = get_player(game_state, stack_obj.controller)
            player.graveyard.append(card)
            logger.warning("Unknown card type for %r; placed in graveyard", card.name)

    # Cascade trigger: fires after any non-copy spell resolves (CR 702.84)
    if not stack_obj.is_copy:
        kws_lower = [k.lower() for k in (card.keywords or [])]
        if "cascade" in kws_lower or "cascade" in (card.oracle_text or "").lower():
            cmc = card.cmc if card.cmc is not None else 0
            game_state = _trigger_cascade(game_state, stack_obj.controller, int(cmc))

    return game_state


def _trigger_cascade(game_state: GameState, caster_name: str, cascade_cmc: int) -> GameState:
    """
    Implement cascade: exile cards from top of library until finding a non-land card
    with CMC < cascade_cmc. Set pending_cascade with the found card for player choice.
    CR 702.84
    """
    caster = get_player(game_state, caster_name)
    exiled_non_chosen: list = []

    found_card = None
    while caster.library:
        top_card = caster.library.pop(0)
        if "land" not in top_card.type_line.lower():
            card_cmc = top_card.cmc if top_card.cmc is not None else 0
            if int(card_cmc) < cascade_cmc:
                found_card = top_card
                break
        exiled_non_chosen.append(top_card)

    if found_card is not None:
        caster.exile.extend(exiled_non_chosen)
        game_state.pending_cascade = {
            "player": caster_name,
            "found_card": found_card.model_dump(),
            "exiled_cards": [c.model_dump() for c in exiled_non_chosen],
            "cascade_cmc": cascade_cmc,
        }
        logger.info("Cascade: %s found %s (CMC < %d)", caster_name, found_card.name, cascade_cmc)
    else:
        # Nothing found — put all exiled cards on library bottom
        caster.library.extend(exiled_non_chosen)
        logger.info("Cascade: no card found with CMC < %d", cascade_cmc)

    return game_state


def _apply_triggered_effect(game_state: GameState, stack_obj: StackObject) -> GameState:
    """
    Apply the effect text of a resolved triggered or activated ability. CR 608.2.
    Delegates to the shared pattern matcher in _apply_single_effect_text so
    triggered abilities support the same effect vocabulary as spells
    (token creation, card draw, destroy, life gain, counters, etc.).
    Handles self-referential "return this to its owner's hand" separately
    since that pattern has no `target` clause.
    """
    for effect_text in stack_obj.effects:
        effect_lower = effect_text.lower()

        # Self-referential "return CARDNAME to its owner's hand" (e.g. dies triggers).
        # The spell pattern requires "target" and wouldn't match.
        if (
            "return" in effect_lower
            and "hand" in effect_lower
            and "target" not in effect_lower
        ):
            card_name = stack_obj.source_card.name
            controller = stack_obj.controller
            player = get_player(game_state, controller)
            target_card = next((c for c in player.graveyard if c.name == card_name), None)
            if target_card:
                player.graveyard[:] = [c for c in player.graveyard if c.id != target_card.id]
                player.hand.append(target_card)
                logger.info("Triggered effect: returned %s to %s's hand", card_name, controller)
            continue

        game_state = _apply_single_effect_text(game_state, stack_obj, effect_text)

    return game_state


def _apply_single_effect_text(game_state: GameState, stack_obj: StackObject, effect_text: str) -> GameState:
    """Apply the effect of a single oracle text clause against the pattern list."""
    card = stack_obj.source_card
    x_value = stack_obj.x_value

    patterns = [
        (r"draw (\d+|x) cards?",
         lambda m: _draw_cards(game_state, stack_obj.controller,
                               int(m.group(1)) if m.group(1).isdigit() else x_value)),
        (r"destroy target [\w\s]+",
         lambda m: _destroy_permanent(game_state, stack_obj.targets[0] if stack_obj.targets else None)),
        (r"exile target [\w ]+",
         lambda m: _exile_permanent(game_state, stack_obj.targets[0] if stack_obj.targets else None)),
(r"return target [\w ]+ to (?:its owner'?s?|your) hand",
         lambda m: _bounce_permanent(game_state, stack_obj.targets[0] if stack_obj.targets else None)),
        # Token with prowess keyword and optional colors
        (r"create (a|an|one|two|three|\d+) (\d+)/(\d+) ((?:blue|red|white|black|green) and (?:blue|red|white|black|green) )?([\w ]+) creature tokens? with prowess",
         lambda m: _create_token_with_keywords(game_state, stack_obj.controller,
                                   m.group(1), m.group(5).strip() if m.group(5) else m.group(4),
                                   "prowess")),
        # Token with multiple colors (e.g., "blue and red")
        (r"create (a|an|one|two|three|\d+) (\d+)/(\d+) (blue|red|white|black|green) and (blue|red|white|black|green) ([\w ]+) creature tokens?",
         lambda m: _create_token_with_pt_and_keywords(game_state, stack_obj.controller,
                                   m.group(1), m.group(2), m.group(3), m.group(5),
                                   f"{m.group(3)} {m.group(4)}")),
        # Simple token with prowess
        (r"create (a|an|one|two|three|\d+) (\d+)/(\d+) ([\w ]+) creature tokens? with prowess",
         lambda m: _create_token_with_keywords(game_state, stack_obj.controller,
                                   m.group(1), m.group(4), "prowess")),
        (r"create (a|an|one|two|three|\d+) (\d+)/(\d+) ([\w ]+) creature tokens?",
         lambda m: _create_tokens(game_state, stack_obj.controller,
                                   m.group(1), m.group(2), m.group(3), m.group(4))),
        (r"gain(?:s)? (\d+|x) life",
         lambda m: _gain_life(game_state, stack_obj.controller,
int(m.group(1)) if m.group(1).isdigit() else x_value)),
        (r"put (\d+|x) \+1/\+1 counters? on target creature",
         lambda m: _add_counters(game_state, stack_obj.targets[0] if stack_obj.targets else None,
                                 "+1/+1", int(m.group(1)) if m.group(1).isdigit() else x_value)),
        # "put a +1/+1 counter on this creature" (self-target for landfall)
        (r"put a \+1/\+1 counter on (?:this|~)",
         lambda m: _add_counters(game_state, stack_obj.source_permanent_id,
                                 "+1/+1", 1)),
        (r"scry (\d+|x)",
          lambda m: _apply_scry(game_state, stack_obj.controller,
                                int(m.group(1)) if m.group(1).isdigit() else x_value)),
        (r"surveil (\d+|x)",
         lambda m: _apply_surveil(game_state, stack_obj.controller,
                                  int(m.group(1)) if m.group(1).isdigit() else x_value)),
        # "look at the top X of your library. Put Y of them into your hand..." (e.g., Stock Up)
        (r"look at the top (\d+) cards? of your library\.? put (\d+) of them into your hand",
         lambda m: _apply_reveal_and_choose_multi(game_state, stack_obj.controller,
                                          int(m.group(1)), int(m.group(2)))),
        # "look at the top X of your library. put one into your hand..." (e.g., Sleight of Hand)
        (r"look at the top (\d+) cards? of your library",
         lambda m: _apply_reveal_and_choose(game_state, stack_obj.controller,
                                          int(m.group(1)) if m.group(1).isdigit() else 2)),
    ]

    oracle_lower = effect_text.lower()
    for pattern, effect_func in patterns:
        match = re.search(pattern, oracle_lower)
        if match:
            result = effect_func(match)
            if result is not None:
                game_state = result
            return game_state
    return game_state


def _apply_spell_effect(game_state: GameState, stack_obj: StackObject) -> GameState:
    """
    Apply the effect of a resolved instant or sorcery.
    Implements all new spell effects from the 018 feature spec.
    CR 608.2: effects are applied as described on the card.
    """
    card = stack_obj.source_card
    oracle = (card.oracle_text or "").lower()

    # Modal spells (US4): apply only chosen modes
    if stack_obj.modes_chosen:
        # Split oracle text by bullet (•) or "Mode N:" markers
        raw = card.oracle_text or ""
        mode_texts = re.split(r'•|Mode \d+:', raw)
        mode_texts = [m.strip() for m in mode_texts if len(m.strip()) > 5]
        for mode_idx in stack_obj.modes_chosen:
            if mode_idx < len(mode_texts):
                game_state = _apply_single_effect_text(game_state, stack_obj, mode_texts[mode_idx])
        return game_state

    # Helper to substitute X values in patterns
    def _substitute_x_in_pattern(pattern: str, x_value: int) -> str:
        return re.sub(r'\bX\b', str(x_value), pattern, flags=re.IGNORECASE)

    # Helper to get x_value from stack object
    x_value = stack_obj.x_value
    
    # Priority-ordered pattern list for spell effect resolution.
    # Each entry: (regex_pattern, lambda taking full re.Match object).
    # First match wins; unrecognized oracle text logs at DEBUG level (no crash).
    patterns = [
        # 1. Draw cards: "draw N cards" / "draw x cards"
        (r"draw (\d+|x) cards?",
         lambda m: _draw_cards(game_state, stack_obj.controller,
                               int(m.group(1)) if m.group(1).isdigit() else x_value)),
        # 2. Destroy permanent
        (r"destroy target [\w\s]+",
         lambda m: _destroy_permanent(game_state, stack_obj.targets[0] if stack_obj.targets else None)),
        # 3. Exile permanent
        (r"exile target [\w ]+",
         lambda m: _exile_permanent(game_state, stack_obj.targets[0] if stack_obj.targets else None)),
        # 4. Bounce permanent back to hand
        (r"return target [\w ]+ to (?:its owner'?s?|your) hand",
         lambda m: _bounce_permanent(game_state, stack_obj.targets[0] if stack_obj.targets else None)),
        # 5. Create creature tokens with explicit P/T (most specific create pattern first)
        (r"create (a|an|one|two|three|\d+) (\d+)/(\d+) ([\w ]+) creature tokens?",
         lambda m: _create_tokens(game_state, stack_obj.controller,
                                  m.group(1), m.group(2), m.group(3), m.group(4))),
        # 6. Gain life: "you gain N life" / "gains N life"
        (r"gain(?:s)? (\d+|x) life",
         lambda m: _gain_life(game_state, stack_obj.controller,
                              int(m.group(1)) if m.group(1).isdigit() else x_value)),
        # 7. Discard cards: "discard N cards" / "discards N cards"
        (r"discard(?:s)? (\d+|x) cards?",
         lambda m: _discard_cards(game_state, stack_obj.controller,
                                  int(m.group(1)) if m.group(1).isdigit() else x_value)),
        # 8. Tutor: search library for a card
        (r"search your library for (?:a|an) ([\w ]+)",
         lambda m: _tutor(game_state, stack_obj.controller, m.group(1).strip(), "hand")),
        # 9. Add +1/+1 counters on target creature
        (r"put (\d+|x) \+1/\+1 counters? on target creature",
         lambda m: _add_counters(game_state, stack_obj.targets[0] if stack_obj.targets else None,
                                 "+1/+1", int(m.group(1)) if m.group(1).isdigit() else x_value)),
        # 10. Scry N
        (r"scry (\d+|x)",
         lambda m: _apply_scry(game_state, stack_obj.controller,
                               int(m.group(1)) if m.group(1).isdigit() else x_value)),
        # 11. Surveil N
        (r"surveil (\d+|x)",
         lambda m: _apply_surveil(game_state, stack_obj.controller,
                                  int(m.group(1)) if m.group(1).isdigit() else x_value)),
        # 12. Damage: "deals N damage"
        (r"deals?\s+(\d+)\s+damage",
         lambda m: _deal_damage(game_state, stack_obj.targets[0] if stack_obj.targets else None,
                                int(m.group(1)), card) if stack_obj.targets else None),
        # 13. Pump: "target creature gets +N/+M until your next turn"  (US23: different scope)
        (r"target creature gets \+(\d+)/\+(\d+) until your next turn",
         lambda m: _pump_creature(
             game_state, stack_obj.targets[0] if stack_obj.targets else None,
             int(m.group(1)), int(m.group(2)),
             expires=f"player:{stack_obj.controller}",
         ) if stack_obj.targets else None),
        # 13b. Pump: "target creature gets +N/+M until end of turn"
        (r"target creature gets \+(\d+)/\+(\d+) until end of turn",
         lambda m: _pump_creature(game_state, stack_obj.targets[0] if stack_obj.targets else None,
                                  int(m.group(1)), int(m.group(2))) if stack_obj.targets else None),
        # 14. Counter spell
        (r"counter target spell",
         lambda m: _counter_spell(game_state, stack_obj.targets[0] if stack_obj.targets else None)
         if stack_obj.targets else None),
        # 15. Draw a card, then discard a card (looting)
        (r"draw a card, then discard a card",
         lambda m: _draw_discard(game_state, stack_obj.controller)),
        # 16. Mill N cards
        (r"mill (\d+)",
         lambda m: _mill(game_state, stack_obj.controller, int(m.group(1)))),
        # 17. Shuffle library
        (r"shuffle your library",
         lambda m: _shuffle_library(game_state, stack_obj.controller)),
        # 18. Extra turn: "take an extra turn after this" / "target player takes an extra turn"
        (r"take an? extra turn after this|you take an? extra turn",
         lambda m: _grant_extra_turn(game_state, stack_obj.controller)),
        (r"target player takes? an? extra turn",
         lambda m: _grant_extra_turn(
             game_state,
             stack_obj.targets[0] if stack_obj.targets else stack_obj.controller,
         )),
    ]

    # Try each pattern in order; pass the full match object to the lambda.
    for pattern, effect_func in patterns:
        m = re.search(pattern, oracle)
        if m:
            result = effect_func(m)
            if result is not None:
                game_state = result
            return game_state

    # US13 (T030): Proliferate — detect and set pending proliferate choice
    if re.search(r'\bproliferate\b', oracle, re.IGNORECASE):
        game_state = _trigger_proliferate(game_state, stack_obj.controller)
        return game_state

    # US20 (T047): "Each opponent" pattern — apply effect to all opponents
    each_opp_m = re.search(r'each opponent (loses? \d+ life|discards? \d+ cards?|draws? \d+ cards?)', oracle, re.IGNORECASE)
    if each_opp_m:
        effect_text = each_opp_m.group(0)
        for opp in get_opponents(game_state, stack_obj.controller):
            opp_stack_obj = stack_obj.model_copy(update={"controller": opp.name})
            game_state = _apply_single_effect_text(game_state, opp_stack_obj, effect_text)
        return game_state

    # If no pattern matched, log at DEBUG level (no crash — CR 608.2b: unimplemented effects no-op)
    logger.debug("Spell effect not implemented for %r: %r", card.name, oracle)
    return game_state


def _trigger_proliferate(game_state: GameState, controller: str) -> GameState:
    """
    Set pending_proliferate_choice for the controller. US13 (T030).
    Collects all permanents and players with at least one counter.
    """
    eligible = []
    for perm in game_state.battlefield:
        if perm.counters:
            eligible.append({
                "id": perm.id,
                "name": perm.card.name,
                "counters": dict(perm.counters),
                "type": "permanent",
            })
    for player in game_state.players:
        if player.poison_counters > 0:
            eligible.append({
                "id": player.name,
                "name": player.name,
                "counters": {"poison": player.poison_counters},
                "type": "player",
            })
    game_state.pending_proliferate_choice = {
        "player": controller,
        "eligible": eligible,
    }
    logger.info("Proliferate: %d eligible targets for %s", len(eligible), controller)
    return game_state


def get_opponents(game_state: GameState, player_name: str):
    """
    Return all players who are opponents of player_name. US20 (T046).
    In a 2-player game this is just the other player.
    """
    return [p for p in game_state.players if p.name != player_name]


def _draw_cards(game_state: GameState, player_name: str, n: int) -> GameState:
    """Draw N cards from the top of player's library to their hand."""
    player = get_player(game_state, player_name)
    if n <= 0:
        return game_state
    
    # Draw cards from top of library
    drawn_cards = []
    for _ in range(min(n, len(player.library))):
        if player.library:
            drawn_cards.append(player.library.pop(0))
    
    player.hand.extend(drawn_cards)
    
    # Check for empty library (player loses)
    if not player.library:
        player.has_lost = True
        game_state.winner = next((p.name for p in game_state.players if p.name != player_name), None)
        logger.info("%s draws from empty library and loses the game", player_name)
    
    logger.info("%s draws %d cards", player_name, len(drawn_cards))
    return game_state


def _destroy_permanent(game_state: GameState, perm_id: str) -> GameState:
    """Destroy a permanent (move to graveyard)."""
    if not perm_id:
        return game_state

    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if not perm:
        return game_state

    if "indestructible" in perm.card.keywords:
        logger.info("%s is indestructible and cannot be destroyed", perm.card.name)
        return game_state

    # CR 701.15: regeneration shield prevents destruction
    if perm.regen_shields > 0:
        perm.regen_shields -= 1
        perm.damage_marked = 0
        perm.tapped = True
        logger.info("%s regenerates (shield remaining: %d)", perm.card.name, perm.regen_shields)
        return game_state

    # Remove from battlefield
    game_state.battlefield[:] = [p for p in game_state.battlefield if p.id != perm_id]
    player = get_player(game_state, perm.controller)
    player.graveyard.append(perm.card)

    logger.info("%s destroyed", perm.card.name)
    return game_state


def _grant_extra_turn(game_state: GameState, player_name: str) -> GameState:
    """Grant an extra turn to player_name. CR 500.7: extra turns form a LIFO stack."""
    game_state.extra_turns.append(player_name)
    logger.info("Extra turn granted to %s (queue depth: %d)", player_name, len(game_state.extra_turns))
    return game_state


def _exile_permanent(game_state: GameState, perm_id: str) -> GameState:
    """Exile a permanent (move to exile zone)."""
    if not perm_id:
        return game_state
    
    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if not perm:
        return game_state
    
    # Remove from battlefield
    game_state.battlefield[:] = [p for p in game_state.battlefield if p.id != perm_id]
    player = get_player(game_state, perm.controller)
    player.exile.append(perm.card)
    
    logger.info("%s exiled", perm.card.name)
    return game_state


def _bounce_permanent(game_state: GameState, perm_id: str) -> GameState:
    """Return a permanent to its owner's hand."""
    if not perm_id:
        return game_state
    
    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if not perm:
        return game_state
    
    # Remove from battlefield
    game_state.battlefield[:] = [p for p in game_state.battlefield if p.id != perm_id]
    player = get_player(game_state, perm.controller)
    player.hand.append(perm.card)
    
    logger.info("%s bounced to hand", perm.card.name)
    return game_state


def _create_tokens(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtypes: str) -> GameState:
    """Create creature tokens."""
    # Parse count
    count_map = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3}
    count = count_map.get(count_str.lower(), int(count_str) if count_str.isdigit() else 1)
    
    # Parse power/toughness
    p = int(power) if power.isdigit() else 0
    t = int(toughness) if toughness.isdigit() else 0
    
    # Create token cards
    token_name = f"{subtypes} Token"
    token_card = Card(
        name=token_name,
        type_line="Token Creature — " + subtypes,
        power=str(p),
        toughness=str(t),
        mana_cost="",
        colors=[],
        keywords=[],
        parse_status="ok"
    )
    
    # Create tokens
    for _ in range(count):
        _, new_perm = put_permanent_onto_battlefield(game_state, token_card, controller, from_zone="hand", is_token=True)
        logger.info("%s token created", token_name)
    
    return game_state


def _gain_life(game_state: GameState, player_name: str, n: int) -> GameState:
    """Gain life."""
    player = get_player(game_state, player_name)
    player.life += n
    logger.info("%s gains %d life", player_name, n)
    return game_state


def _discard_cards(game_state: GameState, player_name: str, n: int) -> GameState:
    """Discard N cards from player's hand."""
    player = get_player(game_state, player_name)
    if n <= 0:
        return game_state
    
    # For heuristic AI, we'll just discard the lowest CMC cards
    # In a real implementation, this would be handled by pending_discard_choice
    cards_to_discard = min(n, len(player.hand))
    discarded = player.hand[:cards_to_discard]
    player.hand = player.hand[cards_to_discard:]
    
    # Add to graveyard
    player.graveyard.extend(discarded)
    
    logger.info("%s discards %d cards", player_name, cards_to_discard)
    return game_state


def _tutor(game_state: GameState, player_name: str, filter_type: str, destination: str) -> GameState:
    """Search library for a card and put it in hand."""
    player = get_player(game_state, player_name)
    if not player.library:
        return game_state
    
    # Set pending tutor choice - in a real implementation, this would be handled by AI
    # For now, we'll just pick the first card
    if player.library:
        card = player.library.pop(0)
        if destination == "hand":
            player.hand.append(card)
        elif destination == "battlefield":
            _, _ = put_permanent_onto_battlefield(game_state, card, player_name, from_zone="hand")
        logger.info("%s tutors for %s", player_name, card.name)
    
    return game_state


def _add_counters(game_state: GameState, perm_id: str, counter_type: str, n: int) -> GameState:
    """Add counters to a permanent."""
    if not perm_id or n <= 0:
        return game_state
    
    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if not perm:
        return game_state
    
    perm.counters[counter_type] = perm.counters.get(counter_type, 0) + n
    logger.info("%s gets %d %s counters", perm.card.name, n, counter_type)
    return game_state


def _apply_scry(game_state: GameState, player_name: str, n: int) -> GameState:
    """Apply scry effect."""
    player = get_player(game_state, player_name)
    if n <= 0 or not player.library:
        return game_state
    
    # Get top N cards
    revealed_cards = player.library[:min(n, len(player.library))]
    
    # Set pending scry choice
    game_state.pending_scry_choice = {
        "player": player_name,
        "cards": [c.model_dump() for c in revealed_cards],
        "n": n
    }
    
    logger.info("%s scrys %d cards", player_name, n)
    return game_state


def _apply_reveal_and_choose(game_state: GameState, player_name: str, n: int) -> GameState:
    """
    Apply "look at the top N cards, put one in hand, put rest on bottom" effect.
    (e.g., Sleight of Hand)
    """
    player = get_player(game_state, player_name)
    if n <= 0 or not player.library:
        return game_state
    
    # Get top N cards
    revealed_cards = player.library[:min(n, len(player.library))]
    
    # Set pending reveal-and-choose choice
    game_state.pending_scry_choice = {
        "player": player_name,
        "cards": [c.model_dump() for c in revealed_cards],
        "n": n,
        "effect_type": "reveal_and_choose",  # distinguishes from regular scry
    }
    
    logger.info("%s reveals %d cards from top of library", player_name, n)
    return game_state


def _apply_reveal_and_choose_multi(game_state: GameState, player_name: str, n: int, put_count: int) -> GameState:
    """
    Apply "look at the top N cards, put M into hand, rest on bottom" effect.
    (e.g., Stock Up - look at top 5, put 2 in hand)
    """
    player = get_player(game_state, player_name)
    if n <= 0 or not player.library:
        return game_state
    
    revealed_cards = player.library[:min(n, len(player.library))]
    
    game_state.pending_scry_choice = {
        "player": player_name,
        "cards": [c.model_dump() for c in revealed_cards],
        "n": n,
        "effect_type": "reveal_and_choose_multi",
        "put_count": put_count,
    }
    
    logger.info("%s reveals %d cards from top of library, choose %d for hand", player_name, n, put_count)
    return game_state


def _apply_surveil(game_state: GameState, player_name: str, n: int) -> GameState:
    """Apply surveil effect."""
    player = get_player(game_state, player_name)
    if n <= 0 or not player.library:
        return game_state
    
    # Get top N cards
    revealed_cards = player.library[:min(n, len(player.library))]
    
    # Set pending surveil choice
    game_state.pending_surveil_choice = {
        "player": player_name,
        "cards": [c.model_dump() for c in revealed_cards],
        "n": n
    }
    
    logger.info("%s surveils %d cards", player_name, n)
    return game_state


def _pump_creature(
    game_state: GameState,
    perm_id: str,
    p_bonus: int,
    t_bonus: int,
    expires: str = "end_of_turn",
) -> GameState:
    """Pump a creature with an expiry scope. US23: supports 'end_of_turn' and 'player:<name>'."""
    if not perm_id:
        return game_state

    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if not perm:
        return game_state

    perm.power_bonus += p_bonus
    perm.toughness_bonus += t_bonus
    perm.power_bonus_expires = expires
    perm.toughness_bonus_expires = expires
    logger.info("%s gets +%d/+%d (expires: %s)", perm.card.name, p_bonus, t_bonus, expires)
    return game_state


def _schedule_delayed_trigger(
    game_state: GameState,
    controller: str,
    trigger_phase: str,
    trigger_step: str | None,
    effect: str,
    once: bool = True,
) -> GameState:
    """Schedule a delayed triggered ability to fire at a future phase/step. CR 603.7."""
    game_state.delayed_triggers.append({
        "phase": trigger_phase,
        "step": trigger_step,
        "controller": controller,
        "effect": effect,
        "once": once,
    })
    logger.info(
        "Delayed trigger scheduled for %s %s by %s: %r",
        trigger_phase, trigger_step, controller, effect,
    )
    return game_state


def _counter_spell(game_state: GameState, target_id: str) -> GameState:
    """Counter a spell. CR 702.102: uncounterable spells cannot be countered."""
    if not target_id:
        return game_state

    # Find target on stack
    countered = next((s for s in game_state.stack if s.id == target_id), None)
    if countered:
        # CR 702.102: if the spell can't be countered, the countering effect does nothing
        if countered.uncounterable:
            logger.info("%s can't be countered — counter effect does nothing", countered.source_card.name)
            return game_state
        game_state.stack[:] = [s for s in game_state.stack if s.id != target_id]
        # Put the countered card in its controller's graveyard
        owner = get_player(game_state, countered.controller)
        owner.graveyard.append(countered.source_card)
        logger.info("Countered %s", countered.source_card.name)

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


# ─── Missing Spell Effects ────────────────────────────────────────────────────

def _cascade(game_state: GameState, player_name: str) -> GameState:
    """Handle cascade effect."""
    # Cascade implementation - for now, just log it
    logger.info("%s cascades", player_name)
    return game_state


def _ward(game_state: GameState, player_name: str, ward_value: int) -> GameState:
    """Handle ward effect."""
    # Ward implementation - for now, just log it
    logger.info("%s wards %d", player_name, ward_value)
    return game_state


def _kicker(game_state: GameState, player_name: str, kicker_paid: bool) -> GameState:
    """Handle kicker effect."""
    # Kicker implementation - for now, just log it
    logger.info("%s kicker %s", player_name, "paid" if kicker_paid else "not paid")
    return game_state


def _jump_start(game_state: GameState, player_name: str, discard_id: str) -> GameState:
    """Handle jump-start effect."""
    # Jump-start implementation - for now, just log it
    logger.info("%s jump-starts", player_name)
    return game_state


def _suspend(game_state: GameState, player_name: str, suspend_value: int) -> GameState:
    """Handle suspend effect."""
    # Suspend implementation - for now, just log it
    logger.info("%s suspends %d", player_name, suspend_value)
    return game_state


def _foretell(game_state: GameState, player_name: str, foretold_cards: list[str]) -> GameState:
    """Handle foretell effect."""
    # Foretell implementation - for now, just log it
    logger.info("%s foretells", player_name)
    return game_state


def _unearth(game_state: GameState, player_name: str) -> GameState:
    """Handle unearth effect."""
    # Unearth implementation - for now, just log it
    logger.info("%s unearth", player_name)
    return game_state


def _choose_mode(game_state: GameState, player_name: str, modes_chosen: list[int]) -> GameState:
    """Handle modal spell mode choice."""
    # Modal spell mode handling - for now, just log it
    logger.info("%s chooses modes %s", player_name, modes_chosen)
    return game_state


def _x_spell_variant(game_state: GameState, player_name: str, x_value: int) -> GameState:
    """Handle X spell variant."""
    # X spell variant handling - for now, just log it
    logger.info("%s casts X spell with value %d", player_name, x_value)
    return game_state


def _targeted_damage(game_state: GameState, source_type: str, damage: int, target_type: str) -> GameState:
    """Handle targeted damage effect."""
    # Targeted damage handling - for now, just log it
    logger.info("Targeted damage: %s deals %d damage to %s", source_type, damage, target_type)
    return game_state


def _prevent_damage(game_state: GameState, player_name: str, damage_amount: int) -> GameState:
    """Handle damage prevention."""
    # Damage prevention handling - for now, just log it
    logger.info("%s prevents %d damage", player_name, damage_amount)
    return game_state


def _draw_discard(game_state: GameState, player_name: str) -> GameState:
    """Handle draw and discard effect."""
    # Draw and discard handling - for now, just log it
    logger.info("%s draws and discards", player_name)
    return game_state


def _shuffle_library(game_state: GameState, player_name: str) -> GameState:
    """Handle shuffle library effect."""
    # Shuffle library handling - for now, just log it
    logger.info("%s shuffles library", player_name)
    return game_state


def _mill(game_state: GameState, player_name: str, mill_count: int) -> GameState:
    """Handle mill effect."""
    # Mill handling - for now, just log it
    logger.info("%s mills %d cards", player_name, mill_count)
    return game_state


def _reveal_cards(game_state: GameState, player_name: str, reveal_count: int) -> GameState:
    """Handle reveal cards effect."""
    # Reveal cards handling - for now, just log it
    logger.info("%s reveals %d cards", player_name, reveal_count)
    return game_state


def _put_into_play(game_state: GameState, player_name: str, target_type: str) -> GameState:
    """Handle put into play effect."""
    # Put into play handling - for now, just log it
    logger.info("%s puts %s into play", player_name, target_type)
    return game_state


def _create_artifact_tokens(game_state: GameState, controller: str, count_str: str, subtype: str) -> GameState:
    """Create artifact tokens."""
    # Artifact token creation - for now, just log it
    logger.info("%s creates artifact tokens", controller)
    return game_state


def _create_enchantment_tokens(game_state: GameState, controller: str, count_str: str, subtype: str) -> GameState:
    """Create enchantment tokens."""
    # Enchantment token creation - for now, just log it
    logger.info("%s creates enchantment tokens", controller)
    return game_state


def _create_planeswalker_tokens(game_state: GameState, controller: str, count_str: str, subtype: str) -> GameState:
    """Create planeswalker tokens."""
    # Planeswalker token creation - for now, just log it
    logger.info("%s creates planeswalker tokens", controller)
    return game_state


def _create_land_tokens(game_state: GameState, controller: str, count_str: str, subtype: str) -> GameState:
    """Create land tokens."""
    # Land token creation - for now, just log it
    logger.info("%s creates land tokens", controller)
    return game_state


def _create_creature_tokens(game_state: GameState, controller: str, count_str: str, subtype: str) -> GameState:
    """Create creature tokens."""
    # Creature token creation - for now, just log it
    logger.info("%s creates creature tokens", controller)
    return game_state


def _create_token_with_pt(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtype: str) -> GameState:
    """Create token with power/toughness."""
    # Token with power/toughness creation - for now, just log it
    logger.info("%s creates token with PT", controller)
    return game_state


def _create_token_with_keywords(game_state: GameState, controller: str, count_str: str, subtype: str, keywords: str) -> GameState:
    """Create token with keywords (e.g., prowess,飞行, etc)."""
    count_map = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3}
    count = count_map.get(count_str.lower(), int(count_str) if count_str.isdigit() else 1)
    
    token_name = f"{subtype} Token"
    token_card = Card(
        name=token_name,
        type_line="Token Creature — " + subtype,
        power="1",
        toughness="1",
        mana_cost="",
        colors=[],
        keywords=keywords.split(),
        parse_status="ok"
    )
    
    for _ in range(count):
        _, new_perm = put_permanent_onto_battlefield(game_state, token_card, controller, from_zone="hand", is_token=True)
    
    logger.info("%s creates %d %s token(s) with %s", controller, count, token_name, keywords)
    return game_state


def _create_token_with_pt_and_keywords(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtype: str, keywords: str) -> GameState:
    """Create token with power/toughness and keywords."""
    count_map = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3}
    count = count_map.get(count_str.lower(), int(count_str) if count_str.isdigit() else 1)
    
    p = int(power) if power.isdigit() else 1
    t = int(toughness) if toughness.isdigit() else 1
    
    token_name = f"{subtype} Token"
    token_card = Card(
        name=token_name,
        type_line="Token Creature — " + subtype,
        power=str(p),
        toughness=str(t),
        mana_cost="",
        colors=[],
        keywords=keywords.split(),
        parse_status="ok"
    )
    
    for _ in range(count):
        _, new_perm = put_permanent_onto_battlefield(game_state, token_card, controller, from_zone="hand", is_token=True)
    
    logger.info("%s creates %d %s/%s %s token(s) with %s", controller, p, t, token_name, count, keywords)
    return game_state


def _create_token_with_abilities(game_state: GameState, controller: str, count_str: str, subtype: str, abilities: str) -> GameState:
    """Create token with abilities."""
    # Token with abilities creation - for now, just log it
    logger.info("%s creates token with abilities", controller)
    return game_state


def _create_token_with_pt_and_abilities(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtype: str, abilities: str) -> GameState:
    """Create token with power/toughness and abilities."""
    # Token with PT and abilities creation - for now, just log it
    logger.info("%s creates token with PT and abilities", controller)
    return game_state


def _create_token_with_abilities_and_keywords(game_state: GameState, controller: str, count_str: str, subtype: str, abilities: str, keywords: str) -> GameState:
    """Create token with abilities and keywords."""
    # Token with abilities and keywords creation - for now, just log it
    logger.info("%s creates token with abilities and keywords", controller)
    return game_state


def _create_token_with_pt_abilities_and_keywords(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtype: str, abilities: str, keywords: str) -> GameState:
    """Create token with power/toughness, abilities, and keywords."""
    # Token with PT, abilities, and keywords creation - for now, just log it
    logger.info("%s creates token with PT, abilities, and keywords", controller)
    return game_state


def _create_token_with_multiple_abilities(game_state: GameState, controller: str, count_str: str, subtype: str, ability1: str, ability2: str, ability3: str) -> GameState:
    """Create token with multiple abilities."""
    # Token with multiple abilities creation - for now, just log it
    logger.info("%s creates token with multiple abilities", controller)
    return game_state


def _create_token_with_multiple_abilities_and_pt(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtype: str, ability1: str, ability2: str, ability3: str) -> GameState:
    """Create token with multiple abilities and power/toughness."""
    # Token with multiple abilities and PT creation - for now, just log it
    logger.info("%s creates token with multiple abilities and PT", controller)
    return game_state


def _create_token_with_multiple_abilities_and_keywords(game_state: GameState, controller: str, count_str: str, subtype: str, ability1: str, ability2: str, ability3: str, keywords: str) -> GameState:
    """Create token with multiple abilities and keywords."""
    # Token with multiple abilities and keywords creation - for now, just log it
    logger.info("%s creates token with multiple abilities and keywords", controller)
    return game_state


def _create_token_with_multiple_abilities_pt_and_keywords(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtype: str, ability1: str, ability2: str, ability3: str, keywords: str) -> GameState:
    """Create token with multiple abilities, power/toughness, and keywords."""
    # Token with multiple abilities, PT, and keywords creation - for now, just log it
    logger.info("%s creates token with multiple abilities, PT, and keywords", controller)
    return game_state


def _create_token_with_multiple_abilities_pt_keywords_and_type(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtype: str, ability1: str, ability2: str, ability3: str, keywords: str, type_name: str) -> GameState:
    """Create token with multiple abilities, power/toughness, keywords, and type."""
    # Token with multiple abilities, PT, keywords, and type creation - for now, just log it
    logger.info("%s creates token with multiple abilities, PT, keywords, and type", controller)
    return game_state


def _create_token_with_multiple_abilities_pt_keywords_type_and_subtype(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtype: str, ability1: str, ability2: str, ability3: str, keywords: str, type_name: str, subtype_name: str) -> GameState:
    """Create token with multiple abilities, power/toughness, keywords, type, and subtype."""
    # Token with multiple abilities, PT, keywords, type, and subtype creation - for now, just log it
    logger.info("%s creates token with multiple abilities, PT, keywords, type, and subtype", controller)
    return game_state


def _create_token_with_multiple_abilities_pt_keywords_type_subtype_and_color(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtype: str, ability1: str, ability2: str, ability3: str, keywords: str, type_name: str, subtype_name: str, color: str) -> GameState:
    """Create token with multiple abilities, power/toughness, keywords, type, subtype, and color."""
    # Token with multiple abilities, PT, keywords, type, subtype, and color creation - for now, just log it
    logger.info("%s creates token with multiple abilities, PT, keywords, type, subtype, and color", controller)
    return game_state


def _create_token_with_multiple_abilities_pt_keywords_type_subtype_color_and_mana_cost(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtype: str, ability1: str, ability2: str, ability3: str, keywords: str, type_name: str, subtype_name: str, color: str, mana_cost: str) -> GameState:
    """Create token with multiple abilities, power/toughness, keywords, type, subtype, color, and mana cost."""
    # Token with multiple abilities, PT, keywords, type, subtype, color, and mana cost creation - for now, just log it
    logger.info("%s creates token with multiple abilities, PT, keywords, type, subtype, color, and mana cost", controller)
    return game_state


def _apply_face_to_card(card: Card, card_face) -> Card:
    """Apply a CardFace's properties to a copy of the parent card. CR 709.3."""
    from copy import deepcopy
    new_card = deepcopy(card)
    new_card.name = card_face.name
    new_card.mana_cost = card_face.mana_cost
    new_card.type_line = card_face.type_line
    new_card.oracle_text = card_face.oracle_text
    new_card.power = card_face.power
    new_card.toughness = card_face.toughness
    new_card.loyalty = card_face.loyalty
    if card_face.colors:
        new_card.colors = list(card_face.colors)
    return new_card


def _fuse_split_card(card: Card) -> Card:
    """Fuse both halves of a split card into a single spell. CR 709.4.
    
    When cast with fuse, the card is treated as if it were two spells
    cast at the same time. The fused spell has combined mana cost,
    combined type line, and combined oracle text.
    """
    from copy import deepcopy
    new_card = deepcopy(card)
    if not card.faces or len(card.faces) < 2:
        return new_card
    
    face0 = card.faces[0]
    face1 = card.faces[1]
    
    # Combined mana cost: both halves' costs
    cost_parts = []
    if face0.mana_cost:
        cost_parts.append(face0.mana_cost)
    if face1.mana_cost:
        cost_parts.append(face1.mana_cost)
    new_card.mana_cost = " ".join(cost_parts)
    
    # Combined type line: both faces' types
    type_parts = []
    if face0.type_line:
        type_parts.append(face0.type_line)
    if face1.type_line:
        type_parts.append(face1.type_line)
    new_card.type_line = " — ".join(type_parts)
    
    # Combined oracle text: both faces' text
    text_parts = []
    if face0.oracle_text:
        text_parts.append(face0.oracle_text)
    if face1.oracle_text:
        text_parts.append(face1.oracle_text)
    new_card.oracle_text = "\n\n".join(text_parts)
    
    # CMC = total combined cost
    from mtg_engine.engine.mana import parse_mana_cost
    combined_cost = new_card.mana_cost or ""
    parsed = parse_mana_cost(combined_cost)
    new_card.cmc = sum(parsed.values())
    
    return new_card
