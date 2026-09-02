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
from mtg_engine.engine.zones import get_player, put_permanent_onto_battlefield

logger = logging.getLogger(__name__)


def _split_modal_texts(oracle_text: str) -> list[str]:
    """Split modal spell oracle text into individual mode texts.

    Uses the same logic as the modal resolution block: split on bullet (•) or
    "Mode N:" markers, then filter out short fragments.
    """
    raw = oracle_text or ""
    mode_texts = re.split(r'•|Mode \d+:', raw)
    return [m.strip() for m in mode_texts if len(m.strip()) > 5]


def _update_player_life(game_state: GameState, player_name: str, new_life: int) -> GameState:
    """Pure transform: update a player's life total. Returns new GameState."""
    players = []
    for p in game_state.players:
        if p.name == player_name:
            players.append(p.model_copy(update={"life": new_life}))
        else:
            players.append(p)
    return game_state.model_copy(update={"players": players})


def _update_player_hand(game_state: GameState, player_name: str, new_hand: list[Card]) -> GameState:
    """Pure transform: update a player's hand. Returns new GameState."""
    players = []
    for p in game_state.players:
        if p.name == player_name:
            players.append(p.model_copy(update={"hand": new_hand}))
        else:
            players.append(p)
    return game_state.model_copy(update={"players": players})


def _update_player_graveyard(game_state: GameState, player_name: str, new_graveyard: list[Card]) -> GameState:
    """Pure transform: update a player's graveyard. Returns new GameState."""
    players = []
    for p in game_state.players:
        if p.name == player_name:
            players.append(p.model_copy(update={"graveyard": new_graveyard}))
        else:
            players.append(p)
    return game_state.model_copy(update={"players": players})


def _update_player_library(game_state: GameState, player_name: str, new_library: list[Card]) -> GameState:
    """Pure transform: update a player's library. Returns new GameState."""
    players = []
    for p in game_state.players:
        if p.name == player_name:
            players.append(p.model_copy(update={"library": new_library}))
        else:
            players.append(p)
    return game_state.model_copy(update={"players": players})


def _update_player_mana_pool(game_state: GameState, player_name: str, new_pool) -> GameState:
    """Pure transform: update a player's mana pool. Returns new GameState."""
    players = []
    for p in game_state.players:
        if p.name == player_name:
            players.append(p.model_copy(update={"mana_pool": new_pool}))
        else:
            players.append(p)
    return game_state.model_copy(update={"players": players})


def _update_battlefield(game_state: GameState, new_battlefield: list) -> GameState:
    """Pure transform: replace battlefield. Returns new GameState."""
    return game_state.model_copy(update={"battlefield": new_battlefield})


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
    overload_paid: bool = False,
    from_suspended: bool = False,
    buyback_paid: bool = False,
    entwine_paid: bool = False,
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

    # KW-... Overload (CR 702.95) — overload is an ALTERNATIVE cost that replaces the base cost.
    # When overload_paid is True, replace cost with the parsed overload cost.
    if overload_paid and not from_graveyard:
        from mtg_engine.ability.keywords.overload import OverloadKeyword
        _parsed_overload = OverloadKeyword.parse_overload_cost_static(card.oracle_text or "")
        if _parsed_overload:
            cost = _parsed_overload
            # Rebuild mana_payment if it doesn't cover the new cost
            if not can_pay_cost(player.mana_pool, cost, mana_payment):
                from mtg_engine.engine.mana import parse_mana_cost as _parse_overload_cost
                _ol_cost = _parse_overload_cost(cost)
                _ol_pool = {c: getattr(player.mana_pool, c, 0) for c in ("W", "U", "B", "R", "G", "C")}
                _ol_pay: dict[str, int] = {}
                for _c in ("W", "U", "B", "R", "G"):
                    _need = _ol_cost.get(_c, 0)
                    if _need:
                        _ol_pay[_c] = min(_need, _ol_pool[_c])
                        _ol_pool[_c] -= _ol_pay[_c]
                if _ol_cost.get("C"):
                    _ol_pay["C"] = min(_ol_cost["C"], _ol_pool["C"])
                    _ol_pool["C"] -= _ol_pay["C"]
                _generic = _ol_cost.get("generic", 0)
                for _c in ("C", "W", "U", "B", "R", "G"):
                    if _generic <= 0:
                        break
                    _take = min(_generic, _ol_pool[_c])
                    if _take:
                        _ol_pay[_c] = _ol_pay.get(_c, 0) + _take
                        _ol_pool[_c] -= _take
                        _generic -= _take
                mana_payment = _ol_pay

    # KW-27: Buyback (CR 702.27) — the buyback cost is an ADDITIONAL cost on
    # top of the base cost, paid as the spell is cast. When the ``buyback_paid``
    # flag is set (human choice handler / AI auto-resolution), append the
    # parsed buyback cost to ``cost`` so the single payment flow below
    # validates and deducts base + buyback together. Only applies to normal
    # hand casts — not alternative-cost casts (flashback/escape/foretell/...)
    # or graveyard casts.
    buyback_extra_cost = ""
    if buyback_paid and not from_graveyard:
        from mtg_engine.ability.keywords.buyback import BuybackKeyword
        _parsed_bb = BuybackKeyword.parse_buyback_cost(card.oracle_text or "")
        if _parsed_bb:
            buyback_extra_cost = _parsed_bb
            cost = cost + _parsed_bb
            # The provided payment was typically derived for the BASE cost only
            # (endpoint auto-derivation / explicit client payment). If it does
            # not cover base + buyback, rebuild it from the player's pool so
            # the single payment flow below deducts both (same pattern as the
            # empty-payment auto-derivation above).
            if not can_pay_cost(player.mana_pool, cost, mana_payment):
                from mtg_engine.engine.mana import parse_mana_cost as _parse_bb_cost
                _bb_cost = _parse_bb_cost(cost)
                _bb_pool = {c: getattr(player.mana_pool, c, 0) for c in ("W", "U", "B", "R", "G", "C")}
                _bb_pay: dict[str, int] = {}
                for _c in ("W", "U", "B", "R", "G"):
                    _need = _bb_cost.get(_c, 0)
                    if _need:
                        _bb_pay[_c] = min(_need, _bb_pool[_c])
                        _bb_pool[_c] -= _bb_pay[_c]
                if _bb_cost.get("C"):
                    _bb_pay["C"] = min(_bb_cost["C"], _bb_pool["C"])
                    _bb_pool["C"] -= _bb_pay["C"]
                _generic = _bb_cost.get("generic", 0)
                for _c in ("C", "W", "U", "B", "R", "G"):
                    if _generic <= 0:
                        break
                    _take = min(_generic, _bb_pool[_c])
                    if _take:
                        _bb_pay[_c] = _bb_pay.get(_c, 0) + _take
                        _bb_pool[_c] -= _take
                        _generic -= _take
                mana_payment = _bb_pay

    # KW-39: Entwine (CR 702.39) — the entwine cost is an ADDITIONAL cost on top of
    # the base cost, paid as the spell is cast. When the ``entwine_paid`` flag is
    # set (human choice handler / AI auto-resolution), append the parsed entwine
    # cost to ``cost`` so the single payment flow below validates and deducts
    # base + entwine together. Only applies to normal hand casts — not
    # alternative-cost casts or graveyard casts.
    if entwine_paid and not from_graveyard:
        from mtg_engine.ability.keywords.entwine import EntwineKeyword
        _parsed_ent = EntwineKeyword.parse_entwine_cost(card.oracle_text or "")
        if _parsed_ent:
            cost = cost + _parsed_ent
            if not can_pay_cost(player.mana_pool, cost, mana_payment):
                from mtg_engine.engine.mana import parse_mana_cost as _parse_ent_cost
                _ent_cost = _parse_ent_cost(cost)
                _ent_pool = {c: getattr(player.mana_pool, c, 0) for c in ("W", "U", "B", "R", "G", "C")}
                _ent_pay: dict[str, int] = {}
                for _c in ("W", "U", "B", "R", "G"):
                    _need = _ent_cost.get(_c, 0)
                    if _need:
                        _ent_pay[_c] = min(_need, _ent_pool[_c])
                        _ent_pool[_c] -= _ent_pay[_c]
                if _ent_cost.get("C"):
                    _ent_pay["C"] = min(_ent_cost["C"], _ent_pool["C"])
                    _ent_pool["C"] -= _ent_pay["C"]
                _generic = _ent_cost.get("generic", 0)
                for _c in ("C", "W", "U", "B", "R", "G"):
                    if _generic <= 0:
                        break
                    _take = min(_generic, _ent_pool[_c])
                    if _take:
                        _ent_pay[_c] = _ent_pay.get(_c, 0) + _take
                        _ent_pool[_c] -= _take
                        _generic -= _take
                mana_payment = _ent_pay

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
            pool_available = sum(v for v in pool_dict.values() if v > 0)
            if pool_available >= generic_needed:
                mana_payment["C"] = min(generic_needed, pool_available)
    
    if not can_pay_cost(player.mana_pool, cost, mana_payment):
        raise ValueError(
            f"Insufficient mana to cast {card.name!r}: cost={cost!r}, payment={mana_payment}"
        )

    # Pay cost — deducts mana from player's pool (pure transform)
    new_mana_pool = pay_cost(player.mana_pool, cost, mana_payment)
    game_state = _update_player_mana_pool(game_state, player_name, new_mana_pool)

    # Wire: Mana Spent Trigger (CR 118.9) — fire only if mana was actually paid.
    # An empty mana_payment dict means the spell was cast for free (0-cost or a
    # free alternative cost), so no mana was "spent" and the trigger must not fire.
    if mana_payment:
        from mtg_engine.engine.triggers import check_mana_spent_triggers as _check_mana_spent
        game_state = _check_mana_spent(game_state, player_name)

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

    # Move card from source zone to stack
    if from_adventure_exile:
        player.adventure_cards[:] = [c for c in player.adventure_cards if c.id != card_id]
    elif from_graveyard:
        player.graveyard[:] = [c for c in player.graveyard if c.id != card_id]
    elif from_suspended:
        # SA-04 Suspend: move from suspended_cards zone, not hand
        player.suspended_cards[:] = [c for c in player.suspended_cards if c.id != card_id]
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
    # SA-04: Detect evoke from alternative_cost
    is_evoke = alternative_cost == "evoke"

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
        buyback_paid=buyback_paid and bool(buyback_extra_cost),  # KW-27: True only if the buyback cost was actually paid AND parsed (CR 702.27)
        replicate_count=replicate_count,  # US7: Number of replicates to create
        flashback=is_flashback,  # US8: Whether cast via flashback from graveyard
        escape=is_escape,  # US8: Whether cast via escape from graveyard
        metadata={"is_evoke": is_evoke},  # SA-04: Evoke flag for ETB sacrifice
        face_index=face_index,
        is_face_down=as_face_down,
        is_adventure=card.card_layout == "adventure" and face_index == 1,
        is_fused=fuse,
        is_foretold=alternative_cost in ("foretell", "cast_foretold"),
        mutate_target_id=mutate_target_id,
        mutate_on_top=mutate_on_top,
        overload_paid=overload_paid,  # SPL-02: Overload (CR 702.76)
    )
    game_state.stack.append(stack_obj)

    # Wire: Becomes Target Trigger (CR 109.3) — fire for each permanent target
    if targets:
        from mtg_engine.engine.triggers import check_becomes_target_triggers as _check_becomes_target
        for t in targets:
            # Only fire for targets that are permanent IDs on battlefield
            target_perm = next((p for p in game_state.battlefield if p.id == t), None)
            if target_perm is not None:
                game_state = _check_becomes_target(game_state, t)
                # Ward (CR 702.145): an opponent targeting a permanent with ward
                # triggers it — the caster pays the ward cost or the spell is
                # countered. Fires once per targeted permanent; self-targeting is
                # ignored inside apply_ward(). Uses the keyword list (not oracle
                # text) for precise detection, avoiding substrings like "award".
                from mtg_engine.ability.keywords.ward import (
                    Ward as _Ward,
                    apply_ward as _apply_ward,
                )
                if _Ward.has_ward(target_perm.card.keywords or []) and target_perm.controller != player_name:
                    game_state = _apply_ward(
                        game_state,
                        target_perm,
                        target=stack_obj,
                        caster_name=player_name,
                    )

    logger.info("Cast %s → stack. Controller: %s, targets: %s", card.name, player_name, targets)

    # Priority returns to active player after spell is placed on stack (REQ-S01)
    game_state.priority_holder = game_state.active_player

    # DNG-01: Track spell cast for Storm, day/night, etc.
    game_state.spells_cast_this_turn += 1
    game_state.spells_cast_this_turn_by_player[player_name] = \
        game_state.spells_cast_this_turn_by_player.get(player_name, 0) + 1

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

                # Wire: Attach Trigger (CR 702.5) — fire when aura attaches
                from mtg_engine.engine.triggers import check_attach_triggers as _check_attach
                game_state = _check_attach(game_state, perm.id)
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
        
        # SA-04: Evoke (CR 702.41) — queue mandatory sacrifice if cast via evoke cost
        if stack_obj.metadata and stack_obj.metadata.get("is_evoke", False):
            from mtg_engine.engine.evoke import queue_evoke_sacrifice as _queue_evoke
            game_state = _queue_evoke(
                game_state, perm.id, stack_obj.controller, card.name
            )

    elif "instant" in type_lower or "sorcery" in type_lower:
        # SPL-02: Overload (CR 702.76) — if overload was paid, get all valid targets
        if stack_obj.overload_paid and "overload" in oracle_lower:
            from mtg_engine.ability.keywords.overload import get_overload_targets
            all_targets = get_overload_targets(card.oracle_text or "", game_state)
            if all_targets:
                logger.info("Overload: %s affecting %d targets", card.name, len(all_targets))
                # Update targets to include all valid targets for overload
                stack_obj.targets = all_targets
        
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

    Keyword-triggered abilities (afterlife, undying, persist) are dispatched
    at the top based on stack_obj.trigger_type for explicit handling via keyword modules.
    """
    # ── Keyword-trigger dispatch ─────────────────────────────────────────────
    trigger_type = getattr(stack_obj, "trigger_type", None)
    if trigger_type == "afterlife":
        from mtg_engine.ability.keywords.afterlife import resolve_trigger as _resolve_afterlife
        return _resolve_afterlife(game_state, stack_obj)
    if trigger_type == "undying":
        from mtg_engine.ability.keywords.undying import resolve_trigger as _resolve_undying
        return _resolve_undying(game_state, stack_obj)
    if trigger_type == "persist":
        from mtg_engine.ability.keywords.persist import resolve_trigger as _resolve_persist
        return _resolve_persist(game_state, stack_obj)

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


def _word_to_int(word: str) -> int:
    """Convert word numbers to integers."""
    mapping = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
    }
    return mapping.get(word.lower(), 1)


def _apply_single_effect_text(game_state: GameState, stack_obj: StackObject, effect_text: str) -> GameState:
    """Apply the effect of a single oracle text clause against the pattern list."""
    card = stack_obj.source_card
    x_value = stack_obj.x_value

    # Determine target player for effects that use "target player"
    # Default to controller, but use stack_obj.targets[0] if it's a player name
    target_player = stack_obj.controller
    if stack_obj.targets and isinstance(stack_obj.targets[0], str):
        # Check if target is a player name
        for p in game_state.players:
            if p.name == stack_obj.targets[0]:
                target_player = stack_obj.targets[0]
                break

    patterns = [
        # ── Spree-specific patterns (BUG-26) ───────────────────────────────
        # "Search your library for a card, then shuffle and put that card on top."
        (r"search your library for a card.*?put (?:that )?card on top",
         lambda m: _tutor_to_top(game_state, stack_obj.controller)),
        # "Target player draws N cards and loses X life" (combined effect)
        (r"(?:target player |)draws? (\d+|x|one|two|three|four|five|six|seven|eight|nine|ten) cards?.*?loses? (\d+|x|one|two|three|four|five|six|seven|eight|nine|ten) life",
         lambda m: _apply_combined_draw_lose_life(
             game_state, target_player,
             int(m.group(1)) if m.group(1).isdigit() else (x_value if m.group(1).lower() == 'x' else _word_to_int(m.group(1))),
             int(m.group(2)) if m.group(2).isdigit() else (x_value if m.group(2).lower() == 'x' else _word_to_int(m.group(2))))),
        # ── Regular tutor-to-hand (non-Spree) ─────────────────────────────
        (r"search your library for a card.*?put (?:it|that card) into your hand",
         lambda m: _tutor(game_state, stack_obj.controller, "any", "hand")),
        # ──────────────────────────────────────────────────────────────────────
        (r"draw (\d+|x|one|two|three|four|five|six|seven|eight|nine|ten) cards?",
         lambda m: _draw_cards(game_state, stack_obj.controller,
                                                                 int(m.group(1)) if m.group(1).isdigit() else (x_value if m.group(1).lower() == 'x' else _word_to_int(m.group(1))))),

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
        # ── VEN-01: Venture into the dungeon (CR 701.61) ───────────────────
        (r"\bventure\s+into\s+(?:the\s+)?dungeon\b",
          lambda m: _apply_venture(game_state, stack_obj.controller)),
        # ── CR 701.6: Fight ────────────────────────────────────────────────
        (r"(?:(?:this|target) creature )?fights target creature",
         lambda m: _apply_fight(
             game_state,
             stack_obj.source_permanent_id if stack_obj.source_permanent_id else (stack_obj.targets[0] if len(stack_obj.targets) >= 1 else None),
             stack_obj.targets[-1] if stack_obj.targets else None)),
        # ── CR 702.5: Equip/Attach ────────────────────────────────────────
        (r"equip target creature",
          lambda m: _apply_equip(game_state, stack_obj.source_permanent_id,
                                 stack_obj.targets[0] if stack_obj.targets else None)),
        # ── CR 701.32: Investigate ─────────────────────────────────────────
        # Standalone "Investigate." instruction (e.g. "At the beginning of your
        # upkeep, investigate."). On this triggered-ability path no other
        # pattern consumes "investigate". On the spell path (_apply_spell_effect)
        # the create-token pattern precedes it, but that function strips
        # parenthetical reminder text first (CR 201.8), so the create-token
        # phrasing inside the canonical [[Investigate]] reminder cannot shadow
        # this match.
        (r"\binvestigate\b",
          lambda m: _investigate(game_state, stack_obj.controller)),
    ]

    oracle_lower = effect_text.lower()
    for pattern, effect_func in patterns:
        match = re.search(pattern, oracle_lower)
        if match:
            result = effect_func(match)
            if result is not None:
                game_state = result
            return game_state

    # US13 (T030): Proliferate — detect and set pending proliferate choice
    if re.search(r'\bproliferate\b', oracle_lower):
        from mtg_engine.engine.proliferate import setup_pending_proliferate, _resolve_proliferate_with_ai

        # Determine if controller is human or AI
        is_human = any(
            p.name == stack_obj.controller and
            getattr(game_state, 'human_player_name', None) == p.name
            for p in game_state.players
        )

        if is_human:
            game_state = setup_pending_proliferate(game_state, stack_obj.controller)
        else:
            game_state = _resolve_proliferate_with_ai(game_state, stack_obj.controller)

    return game_state


def _apply_spell_effect(game_state: GameState, stack_obj: StackObject) -> GameState:
    """
    Apply the effect of a resolved instant or sorcery.
    Implements all new spell effects from the 018 feature spec.
    CR 608.2: effects are applied as described on the card.
    """
    card = stack_obj.source_card
    # CR 201.8: parenthetical text is reminder text, not rules text. Strip it
    # before pattern matching so a reminder sentence cannot shadow a real
    # effect pattern. Concrete example: the canonical [[Investigate]] (M19)
    # reminder contains "create a 1/1 red Goblin creature token with
    # 'investigate.'", which would otherwise match the create-token pattern
    # below (listed earlier) and skip the library interaction and the
    # investigated trigger entirely. Stripping here makes ALL patterns in this
    # function immune to reminder-text shadowing.
    oracle = re.sub(r"\([^)]*\)", "", card.oracle_text or "").lower()
    # CR 702.95 Overload: replace "target" with "each" in effect text
    if getattr(stack_obj, "overload_paid", False):
        oracle = re.sub(r"\btarget\b", "each", oracle)

    # Spree mechanic (036-spree): apply selected mode effects
    # Spree cards have mode lines in their oracle text; the modes ARE the effect,
    # so after applying them we skip the main pattern matching to avoid duplicates.
    applied_spree = False
    if game_state.pending_spree_effects:
        remaining = []
        for spree_effect in game_state.pending_spree_effects:
            if spree_effect.get("card_id") == card.id:
                game_state = _apply_single_effect_text(game_state, stack_obj, spree_effect["effect"])
                logger.info("Spree: applied mode effect for %s", card.name)
                applied_spree = True
            else:
                remaining.append(spree_effect)
        game_state.pending_spree_effects = remaining

    if applied_spree:
        return game_state

    # Modal spells (US4): apply only chosen modes
    if stack_obj.modes_chosen:
        mode_texts = _split_modal_texts(card.oracle_text or "")
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
                                 int(m.group(1)), card, stack_obj.controller) if stack_obj.targets else None),
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
        # ── VEN-01: Venture into the dungeon (CR 701.61) ───────────────────
        (r"\bventure\s+into\s+(?:the\s+)?dungeon\b",
          lambda m: _apply_venture(game_state, stack_obj.controller)),
        # ── CR 701.6: Fight ────────────────────────────────────────────────
        (r"(?:(?:this|target) creature )?fights target creature",
          lambda m: _apply_fight(
              game_state,
              stack_obj.source_permanent_id if stack_obj.source_permanent_id else (stack_obj.targets[0] if len(stack_obj.targets) >= 1 else None),
              stack_obj.targets[-1] if stack_obj.targets else None)),
        # ── CR 701.32: Investigate ─────────────────────────────────────────
        # Standalone "Investigate." instruction in a spell's main effect.
        # Mirrors the pattern in _apply_single_effect_text so the action works
        # for both triggered abilities and main spell resolution.
        (r"\binvestigate\b",
          lambda m: _investigate(game_state, stack_obj.controller)),
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
        from mtg_engine.engine.proliferate import setup_pending_proliferate, _resolve_proliferate_with_ai

        # Determine if controller is human or AI
        is_human = any(
            p.name == stack_obj.controller and
            getattr(game_state, 'human_player_name', None) == p.name
            for p in game_state.players
        )

        if is_human:
            game_state = setup_pending_proliferate(game_state, stack_obj.controller)
        else:
            game_state = _resolve_proliferate_with_ai(game_state, stack_obj.controller)
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


def get_opponents(game_state: GameState, player_name: str):
    """
    Return all players who are opponents of player_name. US20 (T046).
    In a 2-player game this is just the other player.
    """
    return [p for p in game_state.players if p.name != player_name]


def _draw_cards(game_state: GameState, player_name: str, n: int) -> GameState:
    """Draw N cards from the top of player's library to their hand. Pure transform."""
    player = get_player(game_state, player_name)
    if n <= 0:
        return game_state

    # Draw cards from top of library — pure (no mutation)
    num_to_draw = min(n, len(player.library))
    drawn_cards = list(player.library[:num_to_draw])
    new_library = list(player.library[num_to_draw:])
    new_hand = list(player.hand) + drawn_cards

    # Check for empty library (player loses) — pure transform
    has_lost = False
    winner_name = None
    if not new_library:
        has_lost = True
        winner_name = next((p.name for p in game_state.players if p.name != player_name), None)
        logger.info("%s draws from empty library and loses the game", player_name)

    new_players = []
    for p in game_state.players:
        if p.name == player_name:
            updates = {"library": new_library, "hand": new_hand}
            if has_lost:
                updates["has_lost"] = True
            new_players.append(p.model_copy(update=updates))
        else:
            new_players.append(p)

    update_dict = {"players": new_players}
    if winner_name and not game_state.is_game_over:
        update_dict["winner"] = winner_name
    game_state = game_state.model_copy(update=update_dict)

    logger.info("%s draws %d cards", player_name, len(drawn_cards))

    # Wire: Draw Trigger (CR 701.16)
    from mtg_engine.engine.triggers import check_draw_triggers as _check_draw
    game_state = _check_draw(game_state, player_name)
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

    # Wire: Token Created Trigger (CR 110.5/110.6). Fire once PER token created —
    # a "whenever a token enters the battlefield" watcher must see each token as a
    # separate event, not one trigger for the whole batch (CR 110.6).
    from mtg_engine.engine.triggers import check_token_triggers as _check_token

    # Create tokens
    for _ in range(count):
        _, new_perm = put_permanent_onto_battlefield(game_state, token_card, controller, from_zone="hand", is_token=True)
        logger.info("%s token created", token_name)
        game_state = _check_token(game_state, controller)

    return game_state


def _investigate(game_state: GameState, player_name: str) -> GameState:
    """Perform the investigate action (CR 701.32, MODERN rules).

    Look at the top card of the library:
      - If it's a land: reveal it and keep it revealed. This engine represents
        "kept revealed" by moving the card to the player's hand (simplest
        correct representation; documented decision).
      - Otherwise: put it on the bottom of the library (auto-bottom; a human
        "may put on bottom" pending choice is out of scope for this story).
    Then create a 1/1 red Goblin creature token with "investigate".
    Finally, fire "whenever you investigate" triggers (CR 701.32).
    """
    player = get_player(game_state, player_name)

    if player.library:
        top = player.library[0]
        if "land" in (top.type_line or "").lower():
            # CR 701.32: land — reveal and keep revealed (moved to hand here).
            new_library = list(player.library[1:])
            new_hand = list(player.hand) + [top]
            game_state = _update_player_library(game_state, player_name, new_library)
            game_state = _update_player_hand(game_state, player_name, new_hand)
            logger.info("%s investigates and reveals %s (land, kept revealed)", player_name, top.name)
        else:
            # CR 701.32: non-land — put on the bottom of the library.
            new_library = list(player.library[1:]) + [top]
            game_state = _update_player_library(game_state, player_name, new_library)
            logger.info("%s investigates and puts %s on the bottom of the library", player_name, top.name)

    # Create the 1/1 red Goblin "investigate" token (CR 701.32). put_permanent_onto_battlefield
    # does NOT itself fire token-created triggers, so _create_token_with_pt_and_keywords calls
    # check_token_triggers AFTER each put — so both "token created" and "investigated" fire on
    # investigate (correct).
    game_state = _create_token_with_pt_and_keywords(
        game_state, player_name, "a", "1", "1", "Goblin", "investigate", colors=["R"]
    )

    # Fire "whenever you investigate" triggers (CR 701.32). Pure transform —
    # capture the returned state (Q4).
    from mtg_engine.engine.triggers import check_investigated_triggers as _check_investigated
    game_state = _check_investigated(game_state, player_name)

    return game_state


def _gain_life(game_state: GameState, player_name: str, n: int) -> GameState:
    """Gain N life. Pure transform."""
    player = get_player(game_state, player_name)
    old = player.life
    new_life = old + n
    game_state = _update_player_life(game_state, player_name, new_life)
    _emit_life_changed(game_state, player_name, old, new_life, n, "spell")
    logger.info("%s gains %d life", player_name, n)

    # Wire: Life Gain/Lost Trigger (CR 701.12/701.13)
    from mtg_engine.engine.triggers import check_life_gain_lost_triggers as _check_life
    game_state = _check_life(game_state, player_name, n)
    return game_state


def _lose_life(game_state: GameState, player_name: str, n: int) -> GameState:
    """Lose N life (for spell effects like 'lose X life'). Pure transform."""
    player = get_player(game_state, player_name)
    old = player.life
    new_life = old - n
    game_state = _update_player_life(game_state, player_name, new_life)
    _emit_life_changed(game_state, player_name, old, new_life, -n, "spell")
    logger.info("%s loses %d life", player_name, n)

    # Wire: Life Gain/Lost Trigger (CR 701.12/701.13) — negative for loss
    from mtg_engine.engine.triggers import check_life_gain_lost_triggers as _check_life
    game_state = _check_life(game_state, player_name, -n)
    return game_state


def _discard_cards(game_state: GameState, player_name: str, n: int) -> GameState:
    """Discard N cards from player's hand. Pure transform."""
    player = get_player(game_state, player_name)
    if n <= 0:
        return game_state

    # For heuristic AI, we'll just discard the lowest CMC cards
    # In a real implementation, this would be handled by pending_discard_choice
    cards_to_discard = min(n, len(player.hand))
    discarded = list(player.hand[:cards_to_discard])
    new_hand = list(player.hand[cards_to_discard:])
    new_graveyard = list(player.graveyard) + discarded

    game_state = _update_player_hand(game_state, player_name, new_hand)
    game_state = _update_player_graveyard(game_state, player_name, new_graveyard)

    logger.info("%s discards %d cards", player_name, cards_to_discard)

    # Wire: Discard Trigger (CR 701.18)
    from mtg_engine.engine.triggers import check_discard_triggers as _check_discard
    game_state = _check_discard(game_state, player_name)
    return game_state


def _tutor(game_state: GameState, player_name: str, filter_type: str, destination: str) -> GameState:
    """Search library for a card and put it in hand. Pure-ish transform."""
    player = get_player(game_state, player_name)
    if not player.library:
        return game_state

    # Set pending tutor choice - in a real implementation, this would be handled by AI
    # For now, we'll just pick the first card
    if player.library:
        card = player.library.pop(0)
        new_library = list(player.library)
        if destination == "hand":
            new_hand = list(player.hand) + [card]
            game_state = _update_player_hand(game_state, player_name, new_hand)
        elif destination == "battlefield":
            _, _ = put_permanent_onto_battlefield(game_state, card, player_name, from_zone="hand")
        else:
            # Default: return to library
            pass
        game_state = _update_player_library(game_state, player_name, new_library)
        logger.info("%s tutors for %s", player_name, card.name)

    # Wire: Tutor/Search Library Trigger (CR 400.8/400.9)
    from mtg_engine.engine.triggers import check_tutor_triggers as _check_tutor
    game_state = _check_tutor(game_state, player_name)
    return game_state


def _tutor_to_top(game_state: GameState, player_name: str) -> GameState:
    """Search library for a card and put it on top of library.

    For Spree effects like "Search your library for a card, then shuffle and put that card on top."
    Pure-ish transform.
    """
    player = get_player(game_state, player_name)
    if not player.library:
        return game_state

    # For heuristic AI, pick the first card from library
    # In a real implementation, this would be handled by pending_tutor_choice
    if player.library:
        card = player.library.pop(0)
        new_library = [card] + list(player.library)
        game_state = _update_player_library(game_state, player_name, new_library)
        logger.info("%s tutors for %s and puts it on top of library", player_name, card.name)

    # Wire: Tutor/Search Library Trigger (CR 400.8/400.9)
    from mtg_engine.engine.triggers import check_tutor_triggers as _check_tutor
    game_state = _check_tutor(game_state, player_name)
    return game_state


def _apply_venture(game_state: GameState, player_name: str) -> GameState:
    """Apply 'Venture into the dungeon' effect (VEN-01, CR 701.61).

    Called from stack resolution when a card effect or room ability contains
    "venture into the dungeon". Chains through the dungeon engine's venture()
    function which handles starting new dungeons, advancing rooms, and firing
    room abilities.
    """
    from mtg_engine.engine.dungeon import venture as _venture

    # Guard against infinite recursion: if player has completed all rooms
    # in current dungeon, venture() starts a fresh one automatically.
    game_state = _venture(game_state, player_name)
    logger.info("Venture into the dungeon resolved for %s", player_name)
    return game_state


def _apply_fight(game_state: GameState, attacker_id: str, defender_id: str) -> GameState:
    """Apply 'target creature fights target creature' effect (CR 701.6).

    Each creature deals damage equal to its power to the other.
    Pure transform where possible.
    """
    if not attacker_id or not defender_id:
        return game_state

    attacker = next((p for p in game_state.battlefield if p.id == attacker_id), None)
    defender = next((p for p in game_state.battlefield if p.id == defender_id), None)
    if not attacker or not defender:
        logger.debug("Fight: one or both creatures not found (%s, %s)", attacker_id, defender_id)
        return game_state

    # Get power values (default to 0 if not parseable)
    try:
        atk_power = int(attacker.card.power) if attacker.card.power else 0
    except (ValueError, TypeError):
        atk_power = 0
    try:
        def_power = int(defender.card.power) if defender.card.power else 0
    except (ValueError, TypeError):
        def_power = 0

    # Deal damage from attacker to defender and vice versa
    new_battlefield = []
    for perm in game_state.battlefield:
        if perm.id == defender_id:
            # Attacker deals power damage to defender
            new_damage = getattr(perm, "damage_marked", 0) + atk_power
            new_perm = perm.model_copy(update={"damage_marked": new_damage})
            logger.info("Fight: %s deals %d damage to %s", attacker.card.name, atk_power, defender.card.name)
            new_battlefield.append(new_perm)
        elif perm.id == attacker_id:
            # Defender deals power damage to attacker
            new_damage = getattr(perm, "damage_marked", 0) + def_power
            new_perm = perm.model_copy(update={"damage_marked": new_damage})
            logger.info("Fight: %s deals %d damage to %s", defender.card.name, def_power, attacker.card.name)
            new_battlefield.append(new_perm)
        else:
            new_battlefield.append(perm)

    game_state = _update_battlefield(game_state, new_battlefield)

    # Wire: Fight Trigger (CR 701.6)
    from mtg_engine.engine.triggers import check_fight_triggers as _check_fight
    game_state = _check_fight(game_state, [attacker_id, defender_id])
    return game_state


def _apply_equip(game_state: GameState, equipment_id: str, creature_id: str) -> GameState:
    """Apply 'equip target creature' effect (CR 702.5).

    Attaches the equipment to the target creature and fires attach triggers.
    Pure transform where possible.
    """
    if not equipment_id or not creature_id:
        return game_state

    equipment = next((p for p in game_state.battlefield if p.id == equipment_id), None)
    creature = next((p for p in game_state.battlefield if p.id == creature_id), None)
    if not equipment or not creature:
        logger.debug("Equip: one or both permanents not found (%s, %s)", equipment_id, creature_id)
        return game_state

    # Update battlefield with new attachment (pure transform)
    new_battlefield = []
    for perm in game_state.battlefield:
        if perm.id == equipment_id:
            new_perm = perm.model_copy(update={"attached_to": creature_id})
            new_battlefield.append(new_perm)
        elif perm.id == creature_id:
            attachments = list(perm.attachments)
            if equipment_id not in attachments:
                attachments.append(equipment_id)
            new_perm = perm.model_copy(update={"attachments": attachments})
            new_battlefield.append(new_perm)
        else:
            new_battlefield.append(perm)

    game_state = _update_battlefield(game_state, new_battlefield)
    logger.info("Equip: %s attached to %s", equipment.card.name, creature.card.name)

    # Wire: Attach Trigger (CR 702.5)
    from mtg_engine.engine.triggers import check_attach_triggers as _check_attach
    game_state = _check_attach(game_state, equipment_id)
    return game_state


def _apply_fortify(game_state: GameState, fortification_id: str, land_id: str) -> GameState:
    """Apply 'attach this Fortification to target land' effect (CR 702.54a).

    Attaches the Fortification to the target land and fires attach triggers.
    No-op (same object) if either permanent is missing. Mirrors
    ``_apply_equip`` as a pure transform.
    """
    if not fortification_id or not land_id:
        return game_state

    fortification = next((p for p in game_state.battlefield if p.id == fortification_id), None)
    land = next((p for p in game_state.battlefield if p.id == land_id), None)
    if not fortification or not land:
        logger.debug("Fortify: one or both permanents not found (%s, %s)", fortification_id, land_id)
        return game_state

    # Update battlefield with new attachment (pure transform)
    new_battlefield = []
    for perm in game_state.battlefield:
        if perm.id == fortification_id:
            new_perm = perm.model_copy(update={"attached_to": land_id})
            new_battlefield.append(new_perm)
        elif perm.id == land_id:
            attachments = list(perm.attachments)
            if fortification_id not in attachments:
                attachments.append(fortification_id)
            new_perm = perm.model_copy(update={"attachments": attachments})
            new_battlefield.append(new_perm)
        else:
            new_battlefield.append(perm)

    game_state = _update_battlefield(game_state, new_battlefield)
    logger.info("Fortify: %s attached to %s", fortification.card.name, land.card.name)

    # Wire: Attach Trigger (CR 702.5)
    from mtg_engine.engine.triggers import check_attach_triggers as _check_attach
    game_state = _check_attach(game_state, fortification_id)
    return game_state


def _apply_combined_draw_lose_life(game_state: GameState, player_name: str, draw_count: int, life_loss: int) -> GameState:
    """Apply combined 'draw N cards and lose X life' effect (Spree mode).
    
    Example: "Target player draws three cards and loses 3 life."
    """
    game_state = _draw_cards(game_state, player_name, draw_count)
    game_state = _lose_life(game_state, player_name, life_loss)
    logger.info("%s draws %d cards and loses %d life (Spree combined effect)", player_name, draw_count, life_loss)
    return game_state


def _add_counters(game_state: GameState, perm_id: str, counter_type: str, n: int) -> GameState:
    """Add counters to a permanent. Pure transform."""
    if not perm_id or n <= 0:
        return game_state

    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if not perm:
        return game_state

    new_counters = dict(perm.counters)
    new_counters[counter_type] = new_counters.get(counter_type, 0) + n
    new_perm = perm.model_copy(update={"counters": new_counters})

    new_battlefield = [new_perm if p.id == perm_id else p for p in game_state.battlefield]
    game_state = _update_battlefield(game_state, new_battlefield)

    logger.info("%s gets %d %s counters", perm.card.name, n, counter_type)

    # Wire: Counter Placed Trigger (CR 122.1)
    from mtg_engine.engine.triggers import check_counter_triggers as _check_counter
    game_state = _check_counter(game_state, perm_id, perm.controller)
    return game_state


def _place_counter_on_permanent(game_state: GameState, perm_id: str, counter_type: str, amount: int) -> GameState:
    """Centralized helper to place counters on a permanent. Pure transform.

    Finds the permanent on battlefield, places the counter via model_copy,
    and fires counter triggers.
    """
    if not perm_id or amount <= 0:
        return game_state

    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if not perm:
        return game_state

    new_counters = dict(perm.counters)
    new_counters[counter_type] = new_counters.get(counter_type, 0) + amount
    new_perm = perm.model_copy(update={"counters": new_counters})

    new_battlefield = [new_perm if p.id == perm_id else p for p in game_state.battlefield]
    game_state = _update_battlefield(game_state, new_battlefield)

    logger.info("%s gets %d %s counters", perm.card.name, amount, counter_type)

    # Wire: Counter Placed Trigger (CR 122.1)
    from mtg_engine.engine.triggers import check_counter_triggers as _check_counter
    game_state = _check_counter(game_state, perm_id, perm.controller)
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
        # CR 701.5: fire "countered" triggers BEFORE the spell leaves the stack so
        # self-referential triggers ("whenever this is countered") can still read the
        # source card. Pure transform — capture the returned state (Q3, Q4).
        from mtg_engine.engine.triggers import check_countered_triggers as _check_countered
        game_state = _check_countered(game_state, countered)
        game_state.stack[:] = [s for s in game_state.stack if s.id != target_id]
        # Put the countered card in its controller's graveyard
        owner = get_player(game_state, countered.controller)
        owner.graveyard.append(countered.source_card)
        logger.info("Countered %s", countered.source_card.name)

    return game_state


def _deal_damage(game_state: GameState, target_id: str, damage: int, source: Card, controller_name: str) -> GameState:
    """
    Apply damage to a target (permanent or player). REQ-R07, REQ-R08.
    Marks damage on permanents; reduces life for players.
    Deathtouch flag is set for SBA processing (REQ-R10).
    Lifelink and infect are handled via keyword module pure transforms.

    controller_name: the player who controls the source of damage (for lifelink/infect).
    """
    from mtg_engine.ability.keywords.deathtouch import apply_deathtouch_damage_from_card
    from mtg_engine.ability.keywords.infect import apply_infect_from_card
    from mtg_engine.ability.keywords.lifelink import apply_lifelink_from_card

    source_keywords = source.keywords or []

    # Emit damage event (must happen before state transforms for transcript)
    _emit_damage_dealt(game_state, source.id, controller_name,
                       target_id, damage, is_combat=False)

    # Check if target is a permanent on the battlefield
    for perm in game_state.battlefield:
        if perm.id == target_id:
            # Mark damage on creature via model_copy (pure transform)
            new_perm = perm.model_copy(
                update={"damage_marked": perm.damage_marked + damage}
            )
            game_state = game_state.model_copy(
                update={
                    "battlefield": [
                        new_perm if p.id == target_id else p
                        for p in game_state.battlefield
                    ]
                }
            )

            # Deathtouch tracking (pure transform, no-op if no deathtouch)
            game_state = apply_deathtouch_damage_from_card(
                game_state, source_keywords, target_id, damage
            )

            # Infect: -1/-1 counters on creatures (pure transform, no-op if no infect)
            game_state = apply_infect_from_card(
                game_state, source_keywords, controller_name,
                target_perm_id=target_id, target_player_name=None,
                damage_amount=damage,
            )

            # Lifelink: controller gains life (pure transform, no-op if no lifelink)
            game_state = apply_lifelink_from_card(
                game_state, source_keywords, controller_name, damage
            )

            return game_state

    # Check if target is a player (player name used as target ID)
    for player in game_state.players:
        if player.name == target_id:
            old_life = player.life
            new_life = old_life - damage

            _emit_life_changed(game_state, player.name, old_life, new_life,
                               -damage, reason="spell_damage")

            # Apply life reduction via model_copy (pure transform)
            new_player = player.model_copy(update={"life": new_life})
            game_state = game_state.model_copy(
                update={
                    "players": [
                        new_player if p.name == target_id else p
                        for p in game_state.players
                    ]
                }
            )

            # Infect: poison counters on players (pure transform, no-op if no infect)
            game_state = apply_infect_from_card(
                game_state, source_keywords, controller_name,
                target_perm_id=None, target_player_name=target_id,
                damage_amount=damage,
            )

            # Lifelink: controller gains life (pure transform, no-op if no lifelink)
            game_state = apply_lifelink_from_card(
                game_state, source_keywords, controller_name, damage
            )

            # Bloodthirst tracking: record damage dealt to player this turn
            damage_dict = dict(game_state.damage_dealt_this_turn)
            damage_dict[target_id] = damage_dict.get(target_id, 0) + damage
            game_state = game_state.model_copy(update={"damage_dealt_this_turn": damage_dict})

            return game_state

    logger.warning("_deal_damage: target %r not found on battlefield or as a player", target_id)
    return game_state


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

    # Wire: Token Created Trigger (CR 110.5/110.6). Fire once PER token created so
    # a "whenever a token enters the battlefield" watcher sees each as a separate
    # event, not one trigger for the whole batch (CR 110.6).
    from mtg_engine.engine.triggers import check_token_triggers as _check_token

    for _ in range(count):
        _, new_perm = put_permanent_onto_battlefield(game_state, token_card, controller, from_zone="hand", is_token=True)
        # One "token created" event per token (CR 110.6).
        game_state = _check_token(game_state, controller)

    logger.info("%s creates %d %s token(s) with %s", controller, count, token_name, keywords)

    return game_state


def _create_token_with_pt_and_keywords(game_state: GameState, controller: str, count_str: str, power: str, toughness: str, subtype: str, keywords: str, colors: list[str] | None = None) -> GameState:
    """Create token with power/toughness and keywords (and optionally colors).

    Sprint 7 (7-3): added the optional ``colors`` parameter so the investigate
    token (CR 701.32: 1/1 red Goblin with "investigate") can be built with a
    color identity. Backward compatible — existing callers pass no colors.
    """
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
        colors=list(colors) if colors else [],
        keywords=keywords.split(),
        parse_status="ok"
    )

    # Wire: Token Created Trigger (CR 110.5/110.6). Fire once PER token created so
    # a "whenever a token enters the battlefield" watcher sees each as a separate
    # event, not one trigger for the whole batch (CR 110.6).
    from mtg_engine.engine.triggers import check_token_triggers as _check_token

    for _ in range(count):
        _, new_perm = put_permanent_onto_battlefield(game_state, token_card, controller, from_zone="hand", is_token=True)
        # One "token created" event per token (CR 110.6).
        game_state = _check_token(game_state, controller)

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


# ─── EventBus emission helpers ────────────────────────────────────────────────

def _emit_life_changed(
    gs: GameState, player_name: str, old_life: int, new_life: int,
    change: int, reason: str = "",
) -> None:
    """Emit a LifeChangedEvent to the EventBus if available."""
    try:
        from mtg_engine.engine.events import get_default_bus, LifeChangedEvent, EventType
        bus = get_default_bus()
        if bus.get_listeners(EventType.LIFE_CHANGED):
            bus.emit(LifeChangedEvent(
                player=player_name,
                old_life=old_life,
                new_life=new_life,
                change_amount=change,
                reason=reason,
                game_id=gs.game_id,
            ))
    except Exception:
        pass


def _emit_damage_dealt(
    gs: GameState, source_id: str, source_controller: str,
    target_id: str, amount: int, is_combat: bool = False,
) -> None:
    """Emit a DamageDealtEvent to the EventBus if available."""
    try:
        from mtg_engine.engine.events import get_default_bus, DamageDealtEvent, EventType
        bus = get_default_bus()
        if bus.get_listeners(EventType.DAMAGE_DEALT):
            bus.emit(DamageDealtEvent(
                source_id=source_id,
                source_controller=source_controller,
                target_id=target_id,
                damage_amount=amount,
                is_combat=is_combat,
                game_id=gs.game_id,
            ))
    except Exception:
        pass


def _emit_counter_placed(
    gs: GameState, permanent_id: str, counter_type: str, count: int, action: str = "add",
) -> None:
    """Emit a CounterPlacedEvent to the EventBus if available."""
    try:
        from mtg_engine.engine.events import get_default_bus, CounterPlacedEvent, EventType
        bus = get_default_bus()
        if bus.get_listeners(EventType.COUNTER_PLACED):
            bus.emit(CounterPlacedEvent(
                permanent_id=permanent_id,
                counter_type=counter_type,
                count=count,
                action=action,
                game_id=gs.game_id,
            ))
    except Exception:
        pass
