"""
Zone management for MTG engine.
REQ-G06: tracks library, hand, graveyard, exile (per player) + stack, battlefield (shared)
REQ-G07: zone changes are atomic
REQ-G08: library order is preserved
"""
import logging
import time
import uuid
from typing import Callable

from mtg_engine.models.game import Card, GameState, Permanent, PlayerState, StackObject

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
    from_zone: str,   # "hand" | "library" | "graveyard" | "exile" | "battlefield" | "stack"
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

    # Commander redirect: if a commander would go to graveyard or exile, send to command zone
    if (
        game_state.format == "commander"
        and to_zone in ("graveyard", "exile")
        and player.commander_name is not None
        and card.name == player.commander_name
    ):
        zone_list = _get_player_zone(player, from_zone) if from_zone in ("hand", "library", "graveyard", "exile", "command_zone") else None
        if zone_list is not None:
            zone_list[:] = [c for c in zone_list if c.id != card.id]
        elif from_zone == "stack":
            game_state.stack[:] = [s for s in game_state.stack if s.source_card.id != card.id]
        return move_card_to_command_zone(game_state, card, player_name)

    # Remove from source zone (REQ-G07: atomic removal before insertion)
    if from_zone in ("hand", "library", "graveyard", "exile"):
        zone_list = _get_player_zone(player, from_zone)
        zone_list[:] = [c for c in zone_list if c.id != card.id]
    elif from_zone == "stack":
        game_state.stack[:] = [s for s in game_state.stack if s.source_card.id != card.id]
    # battlefield removal is handled by move_permanent_to_zone

    # Add to destination zone (REQ-G08: library position is preserved)
    if to_zone in ("hand", "library", "graveyard", "exile"):
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
    }
    _emit_zone_change(event, game_state)

    # Tokens cease to exist when leaving the battlefield — do NOT put in graveyard (CR 704.5d)
    if is_token:
        return game_state

    # Commander redirect: if commander would go to graveyard or exile, send to command zone
    if game_state.format == "commander" and to_zone in ("graveyard", "exile"):
        player = get_player(game_state, controller)
        if player.commander_name is not None and card.name == player.commander_name:
            return move_card_to_command_zone(game_state, card, controller)

    # Move card to destination zone (REQ-G08: preserve library order)
    if to_zone in ("hand", "library", "graveyard", "exile"):
        player = get_player(game_state, controller)
        dest = _get_player_zone(player, to_zone)
        if to_zone == "library":
            if position == "top":
                dest.insert(0, card)
            elif position == "bottom":
                dest.append(card)
        else:
            dest.append(card)

    return game_state


def put_permanent_onto_battlefield(
    game_state: GameState,
    card: Card,
    controller: str,
    tapped: bool = False,
    is_token: bool = False,
    turn_entered: int | None = None,
) -> tuple[GameState, Permanent]:
    """Create a Permanent from a Card and add it to the battlefield."""
    perm = Permanent(
        id=str(uuid.uuid4()),
        card=card,
        controller=controller,
        tapped=tapped,
        is_token=is_token,
        turn_entered_battlefield=turn_entered if turn_entered is not None else game_state.turn,
        summoning_sick=True,
        timestamp=time.time(),
    )
    game_state.battlefield.append(perm)

    event: ZoneChangeEvent = {
        "card_id": perm.id,
        "card_name": card.name,
        "from_zone": "unknown",
        "to_zone": "battlefield",
        "player": controller,
        "is_token": is_token,
        "permanent_id": perm.id,
    }
    _emit_zone_change(event, game_state)
    return game_state, perm


def draw_card(game_state: GameState, player_name: str) -> tuple[GameState, Card | None]:
    """
    Draw the top card from the player's library. REQ-G08.
    Returns None if the library is empty (SBA 704.5b will catch this).
    Emits a zone-change event with is_draw=True so the verbose logger can record
    the draw without revealing the card identity.
    """
    player = get_player(game_state, player_name)
    if not player.library:
        return game_state, None  # SBA will handle the loss condition
    card = player.library.pop(0)
    player.hand.append(card)
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
    return game_state, card
