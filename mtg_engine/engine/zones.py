"""
Zone management for MTG engine.
REQ-G06: tracks library, hand, graveyard, exile (per player) + stack, battlefield (shared)
REQ-G07: zone changes are atomic
REQ-G08: library order is preserved
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from mtg_engine.models.game import Card, GameState, Permanent, PlayerState, ExileStack
from mtg_engine.engine.formats.commander import (
    _is_commander,
    move_card_to_command_zone as _cmd_move_to_command_zone,
)

logger = logging.getLogger(__name__)

# Event type for zone change events
ZoneChangeEvent = dict  # {card_id, card_name, from_zone, to_zone, player, is_token}

# Global event listeners (for trigger detection to hook into)
_zone_change_listeners: list[Callable[[ZoneChangeEvent, GameState], None]] = []


def register_zone_change_listener(fn: Callable[[ZoneChangeEvent, GameState], None]) -> None:
    """Register a listener for zone change events."""
    _zone_change_listeners.append(fn)


def _emit_zone_change(event: ZoneChangeEvent, game_state: GameState) -> None:
    """Emit a zone-change event to all registered listeners."""
    for fn in _zone_change_listeners:
        fn(event, game_state)
    _emit_eventbus_zone(event, game_state)


def _emit_eventbus_zone(event: ZoneChangeEvent, game_state: GameState) -> None:
    """Emit a typed ZoneChangeEvent to the EventBus if available."""
    try:
        from mtg_engine.engine.events import (
            get_default_bus, ZoneChangeEvent as TypedZCE,
            PermanentEntersEvent, PermanentLeavesEvent, EventType,
        )
        bus = get_default_bus()
        game_id = game_state.game_id
        if bus.get_listeners(EventType.ZONE_CHANGE):
            bus.emit(TypedZCE(
                card_id=event.get("card_id", ""),
                card_name=event.get("card_name"),
                from_zone=event.get("from_zone", ""),
                to_zone=event.get("to_zone", ""),
                player=event.get("player", ""),
                is_token=event.get("is_token", False),
                game_id=game_id,
            ))
        if event.get("to_zone") == "battlefield" and bus.get_listeners(EventType.PERMANENT_ENTERS):
            bus.emit(PermanentEntersEvent(
                permanent_id=event.get("card_id", ""),
                controller=event.get("player", ""),
                card_name=event.get("card_name") or "",
                game_id=game_id,
            ))
        if event.get("from_zone") == "battlefield" and bus.get_listeners(EventType.PERMANENT_LEAVES):
            bus.emit(PermanentLeavesEvent(
                permanent_id=event.get("card_id", ""),
                controller=event.get("player", ""),
                card_name=event.get("card_name") or "",
                from_zone=event.get("from_zone", ""),
                to_zone=event.get("to_zone", ""),
                game_id=game_id,
            ))
    except Exception:
        logger.debug("EventBus not available for zone event", exc_info=True)


def get_player(game_state: GameState, player_name: str) -> PlayerState:
    """Get player state by name."""
    for p in game_state.players:
        if p.name == player_name:
            return p
    raise ValueError(f"Player {player_name!r} not found")


def _get_player_zone(player: PlayerState, zone: str) -> list[Card]:
    """Return the mutable list for the named player zone."""
    zone_map: dict[str, list[Card]] = {
        "hand": player.hand,
        "library": player.library,
        "graveyard": player.graveyard,
        "exile": player.exile,
        "command_zone": player.command_zone,
        "sideboard": player.sideboard,
    }
    if zone not in zone_map:
        raise ValueError(f"Unknown player zone: {zone!r}")
    return zone_map[zone]


def move_card_to_command_zone(
    game_state: GameState,
    card: Card,
    player_name: str,
) -> GameState:
    """Move a card directly to a player's command zone and emit a zone-change event."""
    player = get_player(game_state, player_name)
    player.command_zone.append(card)
    event: ZoneChangeEvent = {
        "card_id": card.id,
        "card_name": card.name,
        "from_zone": "unknown",
        "to_zone": "command_zone",
        "player": player_name,
        "is_token": False,
    }
    _emit_zone_change(event, game_state)
    return game_state


def move_card_to_zone(
    game_state: GameState,
    card: Card,
    from_zone: str,   # "hand" | "library" | "graveyard" | "exile" | "battlefield" | "stack" | "sideboard" | "command_zone"
    to_zone: str,
    player_name: str,
    position: str = "top",  # "top" | "bottom" | "random" (for library) — REQ-G08
) -> GameState:
    """
    Atomically move a card from one zone to another. REQ-G07
    Emits a zone-change event for trigger detection.
    Tokens that leave the battlefield cease to exist (CR 704.5d).
    """
    player = get_player(game_state, player_name)

    # Commander redirect: CR 903.9 — if a commander would go to graveyard or exile,
    # owner may put it into command zone instead.
    if (
        game_state.format == "commander"
        and to_zone in ("graveyard", "exile")
        and _is_commander(card.name, player)
    ):
        zone_list = _get_player_zone(player, from_zone) if from_zone in ("hand", "library", "graveyard", "exile", "command_zone", "sideboard") else None
        if zone_list is not None:
            zone_list[:] = [c for c in zone_list if c.id != card.id]
        elif from_zone == "stack":
            game_state.stack[:] = [s for s in game_state.stack if s.source_card.id != card.id]
        # Human player: queue pending choice and return without completing zone change
        if game_state.human_player_name == player_name:
            return game_state.model_copy(update={
                "pending_commander_zone_choice": {
                    "player": player_name,
                    "card": card,
                    "permanent_id": None,
                    "intended_destination": to_zone,
                    "from_zone": from_zone,
                }
            })
        # AI player: auto-redirect to command zone
        return move_card_to_command_zone(game_state, card, player_name)

    # Remove from source zone (REQ-G07: atomic removal before insertion)
    if from_zone in ("hand", "library", "graveyard", "exile", "command_zone", "sideboard"):
        zone_list = _get_player_zone(player, from_zone)
        zone_list[:] = [c for c in zone_list if c.id != card.id]
    elif from_zone == "stack":
        game_state.stack[:] = [s for s in game_state.stack if s.source_card.id != card.id]
    # battlefield removal is handled by move_permanent_to_zone

    # Add to destination zone (REQ-G08: library position is preserved)
    if to_zone in ("hand", "library", "graveyard", "exile", "command_zone", "sideboard"):
        dest_list = _get_player_zone(player, to_zone)
        if to_zone == "library":
            if position == "top":
                dest_list.insert(0, card)
            elif position == "bottom":
                dest_list.append(card)
            else:  # "random"
                import random as _random
                idx = _random.randint(0, len(dest_list))
                dest_list.insert(idx, card)
        else:
            dest_list.append(card)
    # "battlefield" handled by put_permanent_onto_battlefield
    # "stack" handled by cast_spell

    event: ZoneChangeEvent = {
        "card_id": card.id,
        "card_name": card.name,
        "from_zone": from_zone,
        "to_zone": to_zone,
        "player": player_name,
        "is_token": False,
    }
    _emit_zone_change(event, game_state)
    return game_state


def move_permanent_to_zone(
    game_state: GameState,
    permanent: Permanent,
    to_zone: str,   # where to put the card face
    position: str = "top",
) -> GameState:
    """
    Remove permanent from battlefield and move its underlying card to to_zone.
    Tokens cease to exist when leaving the battlefield (CR 704.5d).
    """
    # US16: Unearth replacement — unearthed creatures that would go to non-exile zones
    # are redirected to exile instead (CR 702.83b)
    if permanent.unearthed and to_zone not in ("exile",):
        to_zone = "exile"
        logger.debug("Unearth replacement: redirecting %s to exile", permanent.card.name)

    # US16: Unearth clear on bounce — bouncing an unearthed permanent removes unearthed flag
    if to_zone == "hand" and permanent.unearthed:
        permanent.unearthed = False
        logger.debug("Unearth cleared on bounce for %s", permanent.card.name)

    # Remove from battlefield (REQ-G07: atomic)
    game_state.battlefield[:] = [p for p in game_state.battlefield if p.id != permanent.id]

    card = permanent.card
    controller = permanent.controller
    is_token = permanent.is_token

    event: ZoneChangeEvent = {
        "card_id": permanent.id,
        "card_name": card.name,
        "from_zone": "battlefield",
        "to_zone": to_zone,
        "player": controller,
        "is_token": is_token,
        "permanent_id": permanent.id,
        # Enriched data for death-trigger detection (afterlife, undying, persist)
        "permanent_keywords": card.keywords or [],
        "permanent_counters": dict(permanent.counters) if permanent.counters else {},
        "permanent_power": permanent.card.power or "",
        "permanent_toughness": permanent.card.toughness or "",
        "oracle_text": card.oracle_text or "",
    }
    _emit_zone_change(event, game_state)

    # Tokens cease to exist when leaving the battlefield — do NOT put in graveyard (CR 704.5d)
    if is_token:
        return game_state

    # Commander redirect: CR 903.9 — if a commander would go to graveyard or exile,
    # owner may put it into command zone instead.
    if game_state.format == "commander" and to_zone in ("graveyard", "exile"):
        player = get_player(game_state, controller)
        if _is_commander(card.name, player):
            # Human player: queue pending choice and return without completing zone change
            if game_state.human_player_name == controller:
                return game_state.model_copy(update={
                    "pending_commander_zone_choice": {
                        "player": controller,
                        "card": card,
                        "permanent_id": permanent.id,
                        "intended_destination": to_zone,
                        "from_zone": "battlefield",
                    }
                })
            # AI player: auto-redirect to command zone
            return move_card_to_command_zone(game_state, card, controller)

    # Clean up attachment references: if this permanent was attached to something,
    # remove it from that permanent's attachments list
    if permanent.attached_to:
        import re as _re
        host = next((p for p in game_state.battlefield if p.id == permanent.attached_to), None)
        if host and permanent.id in host.attachments:
            host.attachments[:] = [a for a in host.attachments if a != permanent.id]
        # Reverse aura P/T bonus and keyword grants when the aura leaves.
        if host and "aura" in permanent.card.type_line.lower():
            oracle_lower = (permanent.card.oracle_text or "").lower()
            pt_match = _re.search(r"enchanted creature gets? \+(\d+)/\+(\d+)", oracle_lower)
            if pt_match:
                host.power_bonus -= int(pt_match.group(1))
                host.toughness_bonus -= int(pt_match.group(2))
            # Remove keywords that this aura granted (only remove if not intrinsic to the host)
            for kw in ("trample", "flying", "lifelink", "deathtouch", "first strike",
                       "double strike", "haste", "vigilance", "reach", "hexproof",
                       "indestructible", "menace"):
                if kw in oracle_lower and kw in host.card.keywords:
                    # Only remove if no other attached aura also grants this keyword
                    other_aura_grants = any(
                        kw in (a_perm.card.oracle_text or "").lower()
                        for a_perm in game_state.battlefield
                        if a_perm.id != permanent.id and a_perm.attached_to == host.id
                    )
                    if not other_aura_grants:
                        host.card = host.card.model_copy(
                            update={"keywords": [k for k in host.card.keywords if k != kw]}
                        )

    # Move card to destination zone (REQ-G08: preserve library order)
    if to_zone == "battlefield":
        # Re-entering the battlefield (replacement effect scenario) — put back on battlefield
        game_state.battlefield.append(permanent)
        return game_state

    # Wire: Unattach Trigger (CR 702.5). The aura has just left the battlefield
    # permanently, so fire "whenever an aura you control becomes unattached" /
    # "whenever this enchantment is unattached". check_attach_triggers can no
    # longer find the aura on the battlefield (it was removed at the top of this
    # function), so pass the controller captured BEFORE removal — otherwise the
    # "you control" filter could never match. Only fires when it was attached.
    if permanent.attached_to:
        from mtg_engine.engine.triggers import check_attach_triggers as _check_attach_unattach
        game_state = _check_attach_unattach(
            game_state, permanent.id, attach_event="unattach", attached_controller=controller
        )

    if to_zone in ("hand", "library", "graveyard", "exile", "sideboard"):
        player = get_player(game_state, controller)

        # Check for "return to owner's hand" replacement effect (e.g. Rancor)
        # Pattern: "when [this] is put into a graveyard from the battlefield, return [this] to..."
        oracle_lower = (card.oracle_text or "").lower()
        if (to_zone == "graveyard"
                and "return" in oracle_lower
                and "hand" in oracle_lower
                and ("graveyard" in oracle_lower or "put into" in oracle_lower)):
            player.hand.append(card)
            return game_state

        dest = _get_player_zone(player, to_zone)
        if to_zone == "library":
            if position == "top":
                dest.insert(0, card)
            elif position == "bottom":
                dest.append(card)
        else:
            dest.append(card)

    return game_state


def _parse_enters_tapped(oracle_text: str) -> bool:
    """Parse 'enters tapped' replacement effect from oracle text.

    Matches both modern ("~ enters tapped.") and legacy
    ("~ enters the battlefield tapped.") wording.

    Note: Conditional forms (checklands, shocklands) now delegate to
    _detect_etb_choice() which creates pending choices. This function
    only returns True for unconditional "enters tapped" effects.
    """
    if not oracle_text:
        return False
    import re as _re
    text_lower = oracle_text.lower()

    # Checkland: "enters tapped unless …" — now handles via ETB choice
    if _re.search(r'\benters tapped unless\b', text_lower):
        return False
    # Shockland-style: "As ~ enters … if you don't, it enters tapped." — now handles via ETB choice
    if _re.search(r"if you don'?t,?\s*it enters tapped", text_lower):
        return False
    # Snow dual: similar pattern
    if _re.search(r"if you don'?t,?\s*~? enters tapped", text_lower):
        return False

    if _re.search(r'\benters (?:(?:the )?battlefield )?tapped\b', text_lower):
        return True
    return False


class ETBChoiceType:
    """Types of ETB choices we can detect and handle."""
    SHOCKLAND = "shockland"      # Pay X life or enter tapped
    CHECKLAND = "checkland"       # Enter untapped if you control X
    FETCHLAND = "fetchland"       # Pay X and exile Y or enter tapped
    SNOW_DUAL = "snow_dual"      # Pay X snow mana or enter tapped
    NONE = None


@dataclass
class ETBChoice:
    """Information about an ETB choice from a card's oracle text."""
    choice_type: str
    cost_amount: int = 0
    cost_type: str = ""  # "life", "snow", "mana"
    required_type: str = ""  # For checklands: "forest", "plains", etc.
    required_zone: str = ""  # For fetchlands: "graveyard"
    alternatives: list[str] = field(default_factory=list)


def _detect_etb_choice(oracle_text: str) -> ETBChoice | None:
    """Detect ETB choice from oracle text and return choice info.

    Returns ETBChoice if a choice is detected, None if not.

    Examples:
    - "As this land enters, you may pay 2 life. If you don't, it enters tapped."
      -> Returns ETBChoice(choice_type="shockland", cost_amount=2, cost_type="life")
    - "enters tapped unless you control a Forest or a Plains"
      -> Returns ETBChoice(choice_type="checkland", required_type="forest_or_plains")
    - "As this land enters, you may pay 1 life and exile a land card..."
      -> Returns ETBChoice(choice_type="fetchland", cost_amount=1, cost_type="life")
    """
    if not oracle_text:
        return None

    import re as _re
    text_lower = oracle_text.lower()

    # Shockland: "As ~ enters, you may pay X life. If you don't, it enters tapped."
    shock_match = _re.search(
        r"as .*? enters.*? you may pay (\d+) life.*?enters tapped",
        text_lower
    )
    if shock_match:
        return ETBChoice(
            choice_type=ETBChoiceType.SHOCKLAND,
            cost_amount=int(shock_match.group(1)),
            cost_type="life",
            alternatives=["pay life", "enter tapped"]
        )

    # Checkland: "enters tapped unless you control a Forest or a Plains"
    check_match = _re.search(
        r"enters tapped unless you control (?:a|an|one or more )?(.+?)(?:\.|$)",
        text_lower
    )
    if check_match:
        required = check_match.group(1).strip()
        return ETBChoice(
            choice_type=ETBChoiceType.CHECKLAND,
            required_type=required,
            alternatives=["enter untapped", "enter tapped"]
        )

    # Fetchland: "As ~ enters, you may pay X life and exile a land card..."
    fetch_match = _re.search(
        r"as (?:this|~) enters?,? you may pay (\d+) (?:life|snow mana) "
        r"and exile",
        text_lower
    )
    if fetch_match:
        cost_type = "snow mana" if "snow mana" in text_lower else "life"
        return ETBChoice(
            choice_type=ETBChoiceType.FETCHLAND,
            cost_amount=int(fetch_match.group(1)),
            cost_type=cost_type,
            required_zone="graveyard",
            alternatives=["pay and exile", "enter tapped"]
        )

    # Snow dual: "As ~ enters, you may pay X snow mana..."
    snow_match = _re.search(
        r"as (?:this|~) enters?,? you may pay (\d+) snow mana\.?",
        text_lower
    )
    if snow_match:
        return ETBChoice(
            choice_type=ETBChoiceType.SNOW_DUAL,
            cost_amount=int(snow_match.group(1)),
            cost_type="snow",
            alternatives=["pay snow mana", "enter tapped"]
        )

    return None


def _parse_enters_with_counters(oracle_text: str) -> dict[str, int]:
    """Parse 'enters with X counters' replacement effect from oracle text."""
    counters: dict[str, int] = {}
    if not oracle_text:
        return counters

    import re as _re

    word_to_num = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }

    counter_type_patterns = [
        (r'\+1/\+1', "+1/+1"),
        (r'charge', "charge"),
        (r'spore', "spore"),
        (r'faith', "faith"),
        (r'mine', "mine"),
        (r'doom', "doom"),
        (r'wind', "wind"),
        (r'strife', "strife"),
        (r'lore', "lore"),
        (r'ice', "ice"),
        (r'fade', "fade"),
        (r'verse', "verse"),
        (r'velocity', "velocity"),
    ]

    etb_pattern = _re.compile(r'enters battlefield (?:tapped )?with (\w+) (.*?) counters?', _re.IGNORECASE)
    match = etb_pattern.search(oracle_text)
    if match:
        num_str = match.group(1).lower()
        num = word_to_num.get(num_str)
        if num is None:
            try:
                num = int(num_str)
            except ValueError:
                return counters

        rest = match.group(2).lower()
        counter_type = None
        for pattern, ctype in counter_type_patterns:
            if _re.search(pattern, rest):
                counter_type = ctype
                break

        if counter_type is None:
            for pattern, ctype in counter_type_patterns:
                if _re.search(pattern, rest):
                    counter_type = ctype
                    break

        if counter_type is None:
            words = rest.split()
            if words:
                candidate = words[0].rstrip('s')
                if candidate not in ("a", "an", "the", "with"):
                    counter_type = candidate

        if counter_type:
            counters[counter_type] = num
        return counters

    return counters


def _has_counter_doubling_on_battlefield(game_state: GameState) -> bool:
    """Check if any permanent on battlefield doubles counters on ETB."""
    import re as _re
    for perm in game_state.battlefield:
        if perm.card and perm.card.oracle_text:
            text = perm.card.oracle_text.lower()
            if _re.search(r'if.*enter.*battlefield.*with.*counters.*instead.*double', text):
                return True
            if 'double the number of each counter' in text:
                return True
            if 'enters the battlefield with twice' in text:
                return True
    return False


def _resolve_etb_choice_with_ai(
    game_state: GameState,
    player_name: str,
    choice: ETBChoice,
    permanent_id: str,
    permanent_name: str,
) -> tuple[GameState, bool]:
    """Use AI heuristic to resolve an ETB choice.
    
    Returns (game_state, should_be_tapped).
    AI makes decision based on board state and game conditions.
    """
    
    player = next((p for p in game_state.players if p.name == player_name), None)
    if not player:
        return game_state, True  # Default to tapped if player not found
    
    opponent = next((p for p in game_state.players if p.name != player_name), None)
    
    # Get opponent's life for threat assessment
    opponent_life = opponent.life if opponent else 10
    
    # For shocklands: decide whether to pay life
    if choice.choice_type == ETBChoiceType.SHOCKLAND:
        cost = choice.cost_amount
        
        # Pay if: enough life buffer, need mana now
        if player.life > cost + 3:  # Keep 3 life buffer
            # Check if opponent has removal (rough heuristic)
            has_opponent_removal = any(
                "destroy" in (p.card.oracle_text or "").lower() or 
                "exile" in (p.card.oracle_text or "").lower()
                for p in game_state.battlefield
                if p.controller != player_name
            )
            if has_opponent_removal or player.life > cost + 6:
                # Pay life, enter untapped
                if player.life >= cost:
                    player.life -= cost
                    return game_state, False
        # Don't pay, enter tapped
        return game_state, True
    
    # For checklands: check if required type is on battlefield
    if choice.choice_type == ETBChoiceType.CHECKLAND:
        required = choice.required_type.lower()
        # Check if player controls required land type
        for perm in game_state.battlefield:
            if perm.controller == player_name:
                type_line = perm.card.type_line.lower()
                if required in type_line or required.replace(" or ", " ").replace(" and ", " ") in type_line:
                    # Has required - enter untapped
                    return game_state, False
        # Doesn't have required - enter tapped
        return game_state, True
    
    # For fetchlands: decide whether to pay and exile
    if choice.choice_type == ETBChoiceType.FETCHLAND:
        cost = choice.cost_amount
        
        # Need life > cost + 3 and land in graveyard
        has_land_graveyard = any(
            c.type_line.lower().startswith("land")
            for c in player.graveyard
        )
        
        if player.life > cost + 3 and has_land_graveyard:
            if player.life >= cost:
                player.life -= cost
                # Exile land from graveyard (would need additional logic)
                return game_state, False
        
        return game_state, True
    
    # For snow duals: check if has snow mana
    if choice.choice_type == ETBChoiceType.SNOW_DUAL:
        cost = choice.cost_amount
        
        # Check if player can produce snow mana
        # Simplified: assume can pay snow cost if enough generic mana available
        if player.life > cost + 3 or True:  # Could check mana pool
            player.life -= cost
            return game_state, False
        
        return game_state, True
    
    # Default: enter tapped
    return game_state, True


def put_permanent_onto_battlefield(
    game_state: GameState,
    card: Card,
    controller: str,
    tapped: bool = False,
    is_token: bool = False,
    turn_entered: int | None = None,
    from_zone: str = "unknown",
) -> tuple[GameState, Permanent]:
    """Create a Permanent from a Card and add it to the battlefield."""
    init_loyalty = 0
    if "planeswalker" in card.type_line.lower() and card.loyalty:
        try:
            init_loyalty = int(card.loyalty)
        except (ValueError, TypeError):
            init_loyalty = 0

    oracle_text = card.oracle_text or ""

    etb_counter_doubling = _has_counter_doubling_on_battlefield(game_state)

    # Check for ETB choice BEFORE setting tapped state
    etb_choice = _detect_etb_choice(oracle_text)
    etb_choice_pending = False
    permanent_id = ""
    
    if etb_choice and not tapped:
        # Check if player is human - queue pending choice instead of AI heuristic
        is_human_player = bool(
            game_state.human_player_name and game_state.human_player_name == controller
        )
        
        if is_human_player:
            # Queue pending choice for human to decide
            # Create permanent first (tapped), then queue choice
            tapped = True  # Default to tapped until choice made
            game_state.pending_etb_choice = {
                "player": controller,
                "permanent_id": "",  # Will be set after permanent created
                "permanent_name": card.name,
                "choice_type": etb_choice.choice_type,
                "cost_amount": etb_choice.cost_amount,
                "cost_type": etb_choice.cost_type,
                "required_type": etb_choice.required_type,
                "alternatives": etb_choice.alternatives,
            }
            etb_choice_pending = True
        else:
            # AI player - use heuristic
            game_state, should_tap = _resolve_etb_choice_with_ai(
                game_state, controller, etb_choice, "", card.name
            )
            tapped = should_tap
    elif not tapped and _parse_enters_tapped(oracle_text):
        # Unconditional enters tapped
        tapped = True

    perm = Permanent(
        id=str(uuid.uuid4()),
        card=card,
        controller=controller,
        tapped=tapped,
        is_token=is_token,
        turn_entered_battlefield=turn_entered if turn_entered is not None else game_state.turn,
        summoning_sick=True,
        timestamp=time.time(),
        loyalty=init_loyalty,
    )

    etb_counters = _parse_enters_with_counters(oracle_text)
    for counter_type, count in etb_counters.items():
        if etb_counter_doubling:
            count *= 2
        perm.counters[counter_type] = count

    game_state.battlefield.append(perm)

    # Update pending ETB choice with permanent_id now that we have it
    if etb_choice_pending and game_state.pending_etb_choice:
        game_state.pending_etb_choice["permanent_id"] = perm.id

    event: ZoneChangeEvent = {
        "card_id": perm.id,
        "card_name": card.name,
        "from_zone": from_zone,
        "to_zone": "battlefield",
        "player": controller,
        "is_token": is_token,
        "permanent_id": perm.id,
    }
    _emit_zone_change(event, game_state)

    # US14 (T032): Saga ETB — add one lore counter and queue chapter I trigger
    if "saga" in card.type_line.lower():
        perm.counters["lore"] = 1
        from mtg_engine.models.game import PendingTrigger
        import uuid as _uuid
        trigger = PendingTrigger(
            id=str(_uuid.uuid4()),
            source_permanent_id=perm.id,
            controller=controller,
            trigger_type="saga_chapter",
            effect_description=f"Saga chapter I: {_get_saga_chapter_text(card, 1)}",
            source_card_name=card.name,
        )
        game_state.pending_triggers.append(trigger)
        logger.debug("Saga ETB: %s entered with 1 lore counter, chapter I queued", card.name)

    # US26 (T058): Fading — parse "Fading N" from oracle text and add fade counters
    import re as _re_fading
    _FADING_RE = _re_fading.compile(r'Fading\s+(\d+)')
    fading_match = _FADING_RE.search(card.oracle_text or "")
    if fading_match:
        fade_count = int(fading_match.group(1))
        perm.counters["fade"] = fade_count
        logger.debug("Fading: %s entered with %d fade counter(s)", card.name, fade_count)

    # KW-04 Sunburst (CR 702.103): Apply counters when permanent enters from being cast
    if from_zone == "stack" and not is_token:
        _kws = [kw.lower() for kw in (card.keywords or [])]
        if "sunburst" in _kws:
            from mtg_engine.ability.keywords.sunburst import SunburstKeyword as _Sunburst
            game_state = _Sunburst.apply_sunburst_counters(
                game_state, perm.id, card.mana_cost
            )
            logger.debug("Sunburst: %s entered with counters applied", card.name)

    # KW-22 Bloodthirst (CR 702.22): ETB counters if opponent was dealt damage this turn
    from mtg_engine.ability.keywords.bloodthirst import BloodthirstKeyword as _Bloodthirst
    if _Bloodthirst.from_oracle(card.oracle_text or ""):
        kw = _Bloodthirst.from_oracle(card.oracle_text or "")
        if kw:
            game_state = kw.apply(game_state, perm)
            logger.debug("Bloodthirst applied to %s", card.name)
            # Update perm reference to the possibly updated version in game_state
            perm = next((p for p in game_state.battlefield if p.id == perm.id), perm)

    return game_state, perm


def _get_saga_chapter_text(card: Card, chapter: int) -> str:
    """Extract the ability text for a given Saga chapter number."""
    import re as _re
    oracle = card.oracle_text or ""
    # Roman numerals for chapters 1-10
    _ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
               6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X"}
    roman = _ROMAN.get(chapter, str(chapter))
    # Pattern: "I — effect text" or "I, II — effect text"
    pattern = _re.compile(rf"(?:^|(?<=\n)){roman}(?:,\s*[IVX]+)*\s*—\s*(.*?)(?=\n[IVX]|\Z)", _re.DOTALL)
    m = pattern.search(oracle)
    if m:
        return m.group(1).strip()
    return f"chapter {roman}"


def draw_card(game_state: GameState, player_name: str) -> tuple[GameState, Card | None]:
    """
    Draw the top card from the player's library. REQ-G08. Pure transform.
    Returns None if the library is empty (SBA 704.5b will catch this).
    Emits a zone-change event with is_draw=True so the verbose logger can record
    the draw without revealing the card identity.
    """
    player = get_player(game_state, player_name)
    if not player.library:
        # CR 704.5b: player who cannot draw loses the game
        new_players = []
        for p in game_state.players:
            if p.name == player_name:
                new_players.append(p.model_copy(update={"has_lost": True}))
            else:
                new_players.append(p)
        game_state = game_state.model_copy(update={"players": new_players})
        logger.warning("[SBA 704.5b] %s attempted to draw from empty library — player loses", player_name)
        return game_state, None

    # Pure transform: extract card without mutating original lists
    card = player.library[0]
    new_library = list(player.library[1:])
    new_hand = list(player.hand) + [card]

    # Update player's library and hand via model_copy
    new_players = []
    for p in game_state.players:
        if p.name == player_name:
            new_players.append(p.model_copy(update={"library": new_library, "hand": new_hand}))
        else:
            new_players.append(p)
    game_state = game_state.model_copy(update={"players": new_players})

    # Emit draw event (card_name intentionally omitted — private information)
    event: ZoneChangeEvent = {
        "card_id": card.id,
        "card_name": None,
        "from_zone": "library",
        "to_zone": "hand",
        "player": player_name,
        "is_token": False,
        "is_draw": True,
    }
    _emit_zone_change(event, game_state)

    # Track cards drawn this turn for Miracle (CR 702.93)
    cards_drawn = dict(game_state.cards_drawn_this_turn)
    current_count = cards_drawn.get(player_name, 0)
    is_first_draw = current_count == 0
    cards_drawn[player_name] = current_count + 1
    game_state = game_state.model_copy(update={"cards_drawn_this_turn": cards_drawn})

    # Wire: Draw Trigger (CR 701.16)
    from mtg_engine.engine.triggers import check_draw_triggers as _check_draw
    game_state = _check_draw(game_state, player_name)

    # Miracle keyword handling (CR 702.93)
    from mtg_engine.ability.keywords.miracle import MiracleKeyword
    from mtg_engine.engine.mana import can_pay_cost
    if is_first_draw and MiracleKeyword.from_oracle_text(card.oracle_text or ""):
        miracle_cost = MiracleKeyword.parse_miracle_cost(card.oracle_text or "")
        if miracle_cost:
            is_human = bool(game_state.human_player_name and game_state.human_player_name == player_name)
            if is_human:
                pending = {
                    "player": player_name,
                    "card_id": card.id,
                    "card_name": card.name,
                    "miracle_cost": miracle_cost,
                    "resolved": False,
                }
                game_state = game_state.model_copy(update={"pending_miracle_choice": pending})
                logger.info("Miracle: queued choice for %s drawing %s (cost %s)", player_name, card.name, miracle_cost)
            else:
                # AI auto-resolve: cast if affordable
                player_obj = get_player(game_state, player_name)
                if can_pay_cost(player_obj.mana_pool, miracle_cost):
                    try:
                        from mtg_engine.engine.stack import cast_spell
                        # Cast from hand using miracle cost as alternative cost
                        game_state = cast_spell(
                            game_state,
                            player_name,
                            card.id,
                            targets=[],
                            mana_payment={},
                            alternative_cost=miracle_cost,
                        )
                        logger.info("Miracle: AI auto-cast %s for %s", card.name, miracle_cost)
                    except Exception as e:
                        logger.debug("Miracle AI auto-cast failed for %s: %s", card.name, e)
                else:
                    logger.info("Miracle: AI cannot afford %s for %s", miracle_cost, card.name)
    return game_state, card


def _sacrifice_permanent(
    game_state: GameState,
    perm_id: str,
    sacrificer: str | None = None,
) -> GameState:
    """Sacrifice a permanent by ID. Pure transform.

    Finds the permanent on battlefield by perm_id, removes it, emits a
    zone-change event, moves its card to graveyard (non-tokens only), and
    fires sacrifice triggers.

    Args:
        game_state: Current game state.
        perm_id: ID of the permanent to sacrifice.
        sacrificer: The player who performed the sacrifice (the "you" for
            "whenever you sacrifice ..." patterns). Defaults to the permanent's
            controller (the common case where a player sacrifices their own
            permanent).

    Returns:
        New GameState with the permanent sacrificed and triggers queued.

    Zone-change / death triggers (CR 704.5d, "dies", "leaves the battlefield"):
        A zone-change event is emitted AFTER the permanent is removed from the
        battlefield (so self-referential "dies"/"leaves" triggers on the
        sacrificed permanent itself do not double-fire). The event carries the
        full metadata and is_token flag, and the zone listener's CR 704.5d
        guard suppresses "dies" triggers for tokens. "is sacrificed" triggers
        fire via check_sacrifice_triggers() (they DO fire for tokens,
        CR 701.19).
    """
    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if perm is None:
        logger.warning("Sacrifice: %s not found on battlefield", perm_id)
        return game_state

    controller_name = perm.controller
    effective_sacrificer = sacrificer if sacrificer is not None else controller_name
    is_token = perm.is_token

    # Remove from battlefield (pure transform)
    new_battlefield = [p for p in game_state.battlefield if p.id != perm_id]
    game_state = game_state.model_copy(update={"battlefield": new_battlefield})

    # CR 903.9 Commander replacement: a commander that would be sacrificed to the
    # graveyard may instead go to its owner's command zone. This mirrors the
    # redirect in move_permanent_to_zone / move_card_to_zone so direct sacrifice,
    # Evoke and Fading all route the commander consistently (previously this helper
    # moved straight to the graveyard, silently bypassing the replacement — an
    # evoked or fading Commander would be lost instead of returning to command zone).
    is_commander = (
        game_state.format == "commander"
        and not is_token
        and _is_commander(perm.card.name, get_player(game_state, controller_name))
    )

    if is_commander:
        # Emit the same zone-change event as the non-redirect path so death /
        # leaves-battlefield triggers observe the sacrifice consistently.
        event: ZoneChangeEvent = {
            "card_id": perm.id,
            "card_name": perm.card.name,
            "from_zone": "battlefield",
            "to_zone": "graveyard",
            "player": controller_name,
            "is_token": is_token,
            "permanent_id": perm.id,
            "permanent_keywords": perm.card.keywords or [],
            "permanent_counters": dict(perm.counters) if perm.counters else {},
            "permanent_power": perm.card.power or "",
            "permanent_toughness": perm.card.toughness or "",
            "oracle_text": perm.card.oracle_text or "",
        }
        _emit_zone_change(event, game_state)

        # Human player: queue the commander-zone choice (CR 903.9).
        if game_state.human_player_name == controller_name:
            return game_state.model_copy(update={
                "pending_commander_zone_choice": {
                    "player": controller_name,
                    "card": perm.card,
                    "permanent_id": perm.id,
                    "intended_destination": "graveyard",
                    "from_zone": "battlefield",
                }
            })

        # AI player: auto-redirect to the command zone.
        game_state = _cmd_move_to_command_zone(game_state, perm.card, controller_name)
    else:
        # Emit zone-change event AFTER removal so self-referential "dies" /
        # "leaves the battlefield" triggers on the sacrificed permanent do not
        # double-fire. to_zone="graveyard" is the intended destination; is_token
        # drives the CR 704.5d suppression in the zone listener.
        event: ZoneChangeEvent = {
            "card_id": perm.id,
            "card_name": perm.card.name,
            "from_zone": "battlefield",
            "to_zone": "graveyard",
            "player": controller_name,
            "is_token": is_token,
            "permanent_id": perm.id,
            # Enriched data for death-trigger detection (afterlife, undying, persist)
            "permanent_keywords": perm.card.keywords or [],
            "permanent_counters": dict(perm.counters) if perm.counters else {},
            "permanent_power": perm.card.power or "",
            "permanent_toughness": perm.card.toughness or "",
            "oracle_text": perm.card.oracle_text or "",
        }
        _emit_zone_change(event, game_state)

        # Tokens cease to exist when leaving the battlefield — do NOT put in graveyard (CR 704.5d)
        if not is_token:
            # Move card to graveyard (pure transform)
            player = get_player(game_state, controller_name)
            new_graveyard = list(player.graveyard) + [perm.card]
            players = []
            for p in game_state.players:
                if p.name == controller_name:
                    players.append(p.model_copy(update={"graveyard": new_graveyard}))
                else:
                    players.append(p)
            game_state = game_state.model_copy(update={"players": players})

    logger.info("Sacrifice: %s (%s) by %s", perm.card.name, perm_id, effective_sacrificer)

    # Wire: Sacrifice Trigger (CR 701.19). Pass the captured Permanent object(s)
    # (with type_line / controller / is_token) plus the sacrificer.
    from mtg_engine.engine.triggers import check_sacrifice_triggers as _check_sacrifice
    game_state = _check_sacrifice(game_state, [perm], effective_sacrificer)
    return game_state


# ---------------------------------------------------------------------------
# ZN-01: Exile Zone Enhancement
# ---------------------------------------------------------------------------

def create_exile_stack(
    game_state: GameState,
    cards: list[Card],
    reason: str,
    controller: str,
    face_down: bool = False,
) -> ExileStack:
    """Create a new exile stack grouping cards exiled together. CR 402.1

    Cards in the same exile stack remain grouped and can be manipulated
    together (e.g., "search among exiled cards", "reveal cards exiled with").
    """
    stack = ExileStack(
        cards=cards,
        reason=reason,
        controller=controller,
        face_down=face_down,
    )
    game_state.exile_stacks.append(stack)
    return stack


def get_exile_stack(
    game_state: GameState,
    stack_id: str,
) -> ExileStack | None:
    """Get an exile stack by its ID."""
    for stack in game_state.exile_stacks:
        if stack.stack_id == stack_id:
            return stack
    return None


def get_exile_stacks_by_reason(
    game_state: GameState,
    reason: str,
    controller: str | None = None,
) -> list[ExileStack]:
    """Get all exile stacks matching a reason (and optionally controller)."""
    result = []
    for stack in game_state.exile_stacks:
        if stack.reason == reason:
            if controller is None or stack.controller == controller:
                result.append(stack)
    return result


def add_to_exile_stack(
    game_state: GameState,
    stack_id: str,
    card: Card,
) -> ExileStack | None:
    """Add a card to an existing exile stack."""
    stack = get_exile_stack(game_state, stack_id)
    if stack is None:
        return None
    stack.cards.append(card)
    # Also add to player's flat exile list for backward compatibility
    player = get_player(game_state, stack.controller)
    player.exile.append(card)
    return stack


def remove_from_exile_stack(
    game_state: GameState,
    stack_id: str,
    card_id: str,
) -> Card | None:
    """Remove a card from an exile stack by card ID."""
    stack = get_exile_stack(game_state, stack_id)
    if stack is None:
        return None
    for i, card in enumerate(stack.cards):
        if card.id == card_id:
            removed = stack.cards.pop(i)
            # Also remove from player's flat exile list
            player = get_player(game_state, stack.controller)
            player.exile[:] = [c for c in player.exile if c.id != card_id]
            return removed
    return None


def exile_card_with_reason(
    game_state: GameState,
    card: Card,
    from_zone: str,
    player_name: str,
    reason: str,
    face_down: bool = False,
) -> ExileStack:
    """Exile a card from a zone, creating a tracked exile stack.

    This is the preferred way to exile cards when the reason matters
    (suspend, foretell, adventure, spell resolution, etc.).
    """
    player = get_player(game_state, player_name)

    # Remove from source zone
    if from_zone in ("hand", "library", "graveyard", "exile", "command_zone", "sideboard"):
        zone_list = _get_player_zone(player, from_zone)
        zone_list[:] = [c for c in zone_list if c.id != card.id]
    elif from_zone == "stack":
        game_state.stack[:] = [s for s in game_state.stack if s.source_card.id != card.id]

    # Add to exile
    player.exile.append(card)

    # Create exile stack for tracking
    stack = create_exile_stack(game_state, [card], reason, player_name, face_down)

    event: ZoneChangeEvent = {
        "card_id": card.id,
        "card_name": card.name,
        "from_zone": from_zone,
        "to_zone": "exile",
        "player": player_name,
        "is_token": False,
        "exile_reason": reason,
    }
    _emit_zone_change(event, game_state)
    return stack


def clear_exile_stack(
    game_state: GameState,
    stack_id: str,
) -> list[Card]:
    """Remove an exile stack entirely, returning the cards it contained."""
    for i, stack in enumerate(game_state.exile_stacks):
        if stack.stack_id == stack_id:
            removed_stack = game_state.exile_stacks.pop(i)
            # Remove cards from player's flat exile list
            player = get_player(game_state, stack.controller)
            card_ids = {c.id for c in removed_stack.cards}
            player.exile[:] = [c for c in player.exile if c.id not in card_ids]
            return removed_stack.cards
    return []


# ---------------------------------------------------------------------------
# ZN-02: Graveyard Enhancement
# ---------------------------------------------------------------------------

def get_graveyard_top(
    game_state: GameState,
    player_name: str,
) -> Card | None:
    """Get the top card of a player's graveyard (most recently added = last appended). CR 402.2"""
    player = get_player(game_state, player_name)
    if not player.graveyard:
        return None
    return player.graveyard[-1]


def get_graveyard_size(
    game_state: GameState,
    player_name: str,
) -> int:
    """Get the number of cards in a player's graveyard."""
    player = get_player(game_state, player_name)
    return len(player.graveyard)


def search_graveyard(
    game_state: GameState,
    player_name: str,
    card_name: str | None = None,
    card_type: str | None = None,
) -> list[Card]:
    """Search a player's graveyard for matching cards.

    CR 402.2: Graveyard is a public zone, so searching is allowed.
    """
    player = get_player(game_state, player_name)
    results = []
    for card in player.graveyard:
        if card_name and card.name.lower() != card_name.lower():
            continue
        if card_type and card_type.lower() not in card.type_line.lower():
            continue
        results.append(card)
    return results


def reorder_graveyard(
    game_state: GameState,
    player_name: str,
    order: list[str],
) -> GameState:
    """Reorder a player's graveyard by card IDs. CR 404.2

    Used for effects like "arrange cards in any order".
    """
    player = get_player(game_state, player_name)
    card_map = {c.id: c for c in player.graveyard}
    reordered = []
    for card_id in order:
        if card_id in card_map:
            reordered.append(card_map[card_id])
    # Add any cards not in the order list to the bottom
    for card in player.graveyard:
        if card.id not in order:
            reordered.append(card)
    player.graveyard = reordered
    return game_state


# ---------------------------------------------------------------------------
# ZN-03: Command Zone Enhancement
# ---------------------------------------------------------------------------

def get_command_zone_cards(
    game_state: GameState,
    player_name: str,
) -> list[Card]:
    """Get all cards in a player's command zone."""
    player = get_player(game_state, player_name)
    return player.command_zone


def move_card_from_command_zone(
    game_state: GameState,
    card: Card,
    player_name: str,
    to_zone: str,
) -> GameState:
    """Move a card from command zone to another zone."""
    player = get_player(game_state, player_name)
    player.command_zone[:] = [c for c in player.command_zone if c.id != card.id]

    if to_zone in ("hand", "library", "graveyard", "exile"):
        dest = _get_player_zone(player, to_zone)
        if to_zone == "library":
            dest.append(card)  # Bottom of library
        else:
            dest.append(card)

    event: ZoneChangeEvent = {
        "card_id": card.id,
        "card_name": card.name,
        "from_zone": "command_zone",
        "to_zone": to_zone,
        "player": player_name,
        "is_token": False,
    }
    _emit_zone_change(event, game_state)
    return game_state


# ---------------------------------------------------------------------------
# ZN-04: Sideboard
# ---------------------------------------------------------------------------

def swap_sideboard_card(
    game_state: GameState,
    player_name: str,
    hand_card_id: str,
    sideboard_card_id: str,
) -> tuple[GameState, Card, Card]:
    """Swap a card from hand with a card from sideboard.

    Returns (game_state, hand_card, sideboard_card).
    Sideboard swaps are typically only allowed between rounds in Commander.
    """
    player = get_player(game_state, player_name)

    # Find the card in hand
    hand_card = None
    for i, card in enumerate(player.hand):
        if card.id == hand_card_id:
            hand_card = player.hand.pop(i)
            break

    if hand_card is None:
        raise ValueError(f"Card {hand_card_id!r} not found in {player_name}'s hand")

    # Find the card in sideboard
    sideboard_card = None
    for i, card in enumerate(player.sideboard):
        if card.id == sideboard_card_id:
            sideboard_card = player.sideboard.pop(i)
            break

    if sideboard_card is None:
        raise ValueError(f"Card {sideboard_card_id!r} not found in {player_name}'s sideboard")

    # Perform the swap
    player.hand.append(sideboard_card)
    player.sideboard.append(hand_card)

    logger.info(
        "Sideboard swap for %s: %s <-> %s",
        player_name, hand_card.name, sideboard_card.name,
    )

    event: ZoneChangeEvent = {
        "card_id": hand_card.id,
        "card_name": hand_card.name,
        "from_zone": "hand",
        "to_zone": "sideboard",
        "player": player_name,
        "is_token": False,
    }
    _emit_zone_change(event, game_state)

    event: ZoneChangeEvent = {
        "card_id": sideboard_card.id,
        "card_name": sideboard_card.name,
        "from_zone": "sideboard",
        "to_zone": "hand",
        "player": player_name,
        "is_token": False,
    }
    _emit_zone_change(event, game_state)

    return game_state, hand_card, sideboard_card


def get_sideboard_size(
    game_state: GameState,
    player_name: str,
) -> int:
    """Get the number of cards in a player's sideboard."""
    player = get_player(game_state, player_name)
    return len(player.sideboard)


def search_sideboard(
    game_state: GameState,
    player_name: str,
    card_name: str | None = None,
    card_type: str | None = None,
) -> list[Card]:
    """Search a player's sideboard for matching cards."""
    player = get_player(game_state, player_name)
    results = []
    for card in player.sideboard:
        if card_name and card.name.lower() != card_name.lower():
            continue
        if card_type and card_type.lower() not in card.type_line.lower():
            continue
        results.append(card)
    return results
