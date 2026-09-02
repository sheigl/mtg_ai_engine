"""Crew keyword (CR 702.147).

Crew N means "Tap any number of untapped creatures you control with total
power N or more: This permanent becomes an artifact creature until end of
turn."
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import KeywordAbility

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)

_CREW_PATTERN = re.compile(r"crew\s+(\d+)", re.IGNORECASE)


class Crew(KeywordAbility):
    name = "crew"

    def __init__(self, value: int = 1):
        self.value = value

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("crew" in k.lower() for k in keywords)
            or bool(_CREW_PATTERN.search(oracle))
        )

    @staticmethod
    def has_crew(keywords: list[str]) -> bool:
        return any("crew" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_CREW_PATTERN.search(oracle_text))

    @staticmethod
    def parse_crew_value(oracle_text: str) -> int:
        match = _CREW_PATTERN.search(oracle_text or "")
        if match:
            return int(match.group(1))
        return 1

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Crew | None:
        if cls.from_oracle_text(oracle_text):
            return cls(value=cls.parse_crew_value(oracle_text))
        return None

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        """Crew an artifact Vehicle (CR 702.147).

        For a human player the acting controller has priority and must choose
        which untapped creatures to tap; ``pending_crew_choice`` is queued on
        the game state and NO creature is tapped yet. The choice is later
        resolved via the ``crew_confirm`` choice handler in the API router.

        For an AI player the ability auto-resolves by greedily tapping the
        cheapest (lowest-power) untapped creatures whose summed power meets or
        exceeds the crew value (partial taps allowed). If no valid combination
        exists the call is a pure no-op returning the same game state object.

        State transforms are pure: meaningful changes return a new GameState
        built with ``model_copy(update={...})``; no-op paths return the same
        object so callers can assert ``is gs``.
        """
        card = permanent.card
        oracle_text = card.oracle_text or ""

        # Guard (Q1): only process cards that actually have Crew. Anything else
        # is a strict no-op returning the SAME object so repeated events cannot
        # double-fire.
        if not self.from_oracle_text(oracle_text):
            logger.debug("Crew: %s has no Crew keyword, returning unchanged state", card.name)
            return game_state

        controller = permanent.controller
        vehicle_perm_id = permanent.id

        # Validate: the vehicle must be on the battlefield and controlled by
        # the acting player. Anything else is a strict no-op.
        if controller is None or not any(p.id == vehicle_perm_id for p in game_state.battlefield):
            logger.debug("Crew: %s not on battlefield under %s, returning unchanged state", card.name, controller)
            return game_state

        crew_value = self.value if self.value else Crew.parse_crew_value(oracle_text)

        # Human vs AI. A human player is identified by the presence of
        # human_player_name matching the vehicle's controller (mirrors Dash).
        is_human = (
            getattr(game_state, "human_player_name", None) is not None
            and controller == game_state.human_player_name
        )

        if is_human:
            # Queue the choice; do NOT tap anything yet. The human later picks
            # which untapped creatures to tap via the crew_confirm handler.
            available = [
                p.id
                for p in _available_untapped_creatures(game_state, controller, exclude_id=vehicle_perm_id)
            ]
            new_state = game_state.model_copy(update={
                "pending_crew_choice": {
                    "player": controller,
                    "card_id": card.id,
                    "permanent_id": vehicle_perm_id,
                    "card_name": card.name,
                    "crew_value": crew_value,
                    "available_creatures": available,
                    "resolved": False,
                }
            })
            logger.info(
                "Crew: queued choice for %s to crew %s (value %d), %d creature(s) available",
                controller, card.name, crew_value, len(available),
            )
            return new_state

        # AI path: greedily tap the cheapest untapped creatures meeting the
        # threshold. No creatures => no-op returning the SAME object.
        creatures = _available_untapped_creatures(game_state, controller, exclude_id=vehicle_perm_id)
        if not creatures:
            logger.debug("Crew: %s has no untapped creatures to crew with", card.name)
            return game_state

        selected = _select_cheapest_combination(creatures, crew_value)
        if selected is None:
            # No combination of untapped creatures meets the crew value -> pure
            # no-op returning the SAME object (Q4).
            logger.debug(
                "Crew: %s cannot meet crew value %d with available power, returning unchanged state",
                card.name, crew_value,
            )
            return game_state

        selected_ids = {p.id for p in selected}

        # Tap the selected creatures and animate the vehicle. Pure transform.
        new_battlefield = []
        for perm in game_state.battlefield:
            if perm.id == vehicle_perm_id:
                new_battlefield.append(_crew_permanent(perm))
            elif perm.id in selected_ids:
                new_battlefield.append(perm.model_copy(update={"tapped": True}))
            else:
                new_battlefield.append(perm)

        new_crewed = dict(getattr(game_state, "crewed_vehicles", {}) or {})
        new_crewed[vehicle_perm_id] = crew_value

        new_state = game_state.model_copy(update={
            "battlefield": new_battlefield,
            "crewed_vehicles": new_crewed,
        })
        logger.info(
            "Crew: %s AI crewed %s (value %d) with %d creature(s), total power %d",
            controller, card.name, crew_value, len(selected),
            sum(_creature_power(p) for p in selected),
        )
        return new_state


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _creature_power(perm: Permanent) -> int:
    """Return the current power of a creature permanent (0 if unparseable)."""
    try:
        return max(0, int(perm.card.power or "0"))
    except (ValueError, TypeError):
        return 0


def _is_creature_perm(perm: Permanent) -> bool:
    """True if the permanent's type line indicates a creature."""
    return "creature" in (perm.card.type_line or "").lower()


def _available_untapped_creatures(
    game_state: GameState,
    controller: str,
    exclude_id: str | None = None,
) -> list[Permanent]:
    """Return untapped creatures the controller controls on the battlefield.

    Excludes the vehicle being crewed (``exclude_id``). Token creatures count.
    """
    result: list[Permanent] = []
    for perm in game_state.battlefield:
        if exclude_id is not None and perm.id == exclude_id:
            continue
        if perm.controller != controller:
            continue
        if perm.tapped:
            continue
        if not _is_creature_perm(perm):
            continue
        result.append(perm)
    return result


def _select_cheapest_combination(
    creatures: list[Permanent],
    crew_value: int,
) -> list[Permanent] | None:
    """Greedily select the cheapest untapped creatures meeting the crew value.

    Creatures are ordered by ascending power; they are accumulated until their
    summed power meets or exceeds ``crew_value``. Returns the selected list, or
    ``None`` if the total available power is insufficient (partial taps allowed).
    """
    ordered = sorted(creatures, key=_creature_power)
    chosen: list[Permanent] = []
    running = 0
    for perm in ordered:
        p = _creature_power(perm)
        running += p
        chosen.append(perm)
        if running >= crew_value:
            return chosen
    # Ran out of creatures before meeting the threshold.
    return None


def _crew_type_line(type_line: str) -> str:
    """Return a type line with the 'Artifact' supertype present and 'Creature' added."""
    parts = (type_line or "").split(" — ")
    left = parts[0].strip() if parts else (type_line or "")
    right = parts[1].strip() if len(parts) > 1 else ""

    words = [w for w in left.split()]
    lowered = [w.lower() for w in words]
    if "artifact" not in lowered:
        words.insert(0, "Artifact")
    if "creature" not in lowered:
        # Append the creature type just before the dash (core-type position).
        words.append("Creature")

    new_left = " ".join(words)
    return f"{new_left} — {right}" if right else new_left


def _uncrew_type_line(type_line: str) -> str:
    """Revert a crewed type line back to its pre-vehicle form.

    Removes the 'Creature' core type added by crewing; keeps any existing
    'Artifact' supertype (which Vehicles already carry). Round-trips cleanly:
    "Artifact — Vehicle" -> "Artifact Creature — Vehicle" -> "Artifact — Vehicle".
    """
    parts = (type_line or "").split(" — ")
    left = parts[0].strip() if parts else (type_line or "")
    right = parts[1].strip() if len(parts) > 1 else ""

    words = [w for w in left.split()]
    lowered = [w.lower() for w in words]
    if "creature" in lowered:
        words.pop(lowered.index("creature"))

    new_left = " ".join(words)
    return f"{new_left} — {right}" if right else new_left


def _crew_permanent(perm: Permanent) -> Permanent:
    """Return a copy of the vehicle animated as an artifact creature until EOT."""
    new_card = perm.card.model_copy(update={
        "type_line": _crew_type_line(perm.card.type_line),
    })
    return perm.model_copy(update={
        "card": new_card,
        "crewed_until_end_of_turn": True,
    })


def _uncrew_permanent(perm: Permanent) -> Permanent:
    """Return a copy of the vehicle reverted to its non-vehicle form."""
    new_card = perm.card.model_copy(update={
        "type_line": _uncrew_type_line(perm.card.type_line),
    })
    return perm.model_copy(update={
        "card": new_card,
        "crewed_until_end_of_turn": False,
    })


def apply_crew(game_state: GameState, permanent: Permanent) -> GameState:
    """Module-level convenience wrapper reading the crew value from the card.

    The crew requirement is defined by the card's own oracle text (CR 702.147),
    so the keyword instance is constructed with that parsed value rather than
    a bare default ``Crew()`` (which would always use 1). A "Crew 5" vehicle
    therefore still requires total power 5 to animate.
    """
    value = Crew.parse_crew_value(permanent.card.oracle_text or "")
    return Crew(value).apply(game_state, permanent)


def resolve_crew_choice(game_state: GameState, player_name: str, creature_ids: list[str] | None = None) -> GameState:
    """Resolve a human Crew choice (CR 702.147).

    Taps the chosen untapped creatures the controller controls and animates the
    vehicle as an artifact creature until end of turn, recording it in
    ``crewed_vehicles`` for end-of-turn cleanup. When ``creature_ids`` is given,
    only those (among the available untapped creatures) are tapped; otherwise all
    available untapped creatures are tapped. If the selected power is less than
    the crew value nothing changes and the pending choice is simply cleared.

    Pure transform: returns a new GameState on success or the same object when
    there is no matching pending choice (Q4).
    """
    pending = getattr(game_state, "pending_crew_choice", None)
    if not pending or pending.get("player") != player_name:
        return game_state

    vehicle_perm_id = pending.get("permanent_id")
    crew_value = pending.get("crew_value", 1)
    vehicle = next((p for p in game_state.battlefield if p.id == vehicle_perm_id), None)

    if vehicle is None:
        # Dangling choice with no vehicle left to crew.
        return game_state.model_copy(update={"pending_crew_choice": None})

    available = [
        p for p in game_state.battlefield
        if p.controller == player_name
        and not p.tapped
        and "creature" in (p.card.type_line or "").lower()
        and p.id != vehicle_perm_id
    ]

    wanted_ids = set(creature_ids) if isinstance(creature_ids, list) else None
    to_tap = [p for p in available if wanted_ids is None or p.id in wanted_ids]

    total_power = sum(_creature_power(p) for p in to_tap)
    if not to_tap or total_power < crew_value:
        logger.debug(
            "Crew: %s crew choice insufficient (have %d power, need %d)",
            player_name, total_power, crew_value,
        )
        return game_state.model_copy(update={"pending_crew_choice": None})

    selected_ids = {p.id for p in to_tap}
    new_battlefield = [
        _crew_permanent(p) if p.id == vehicle_perm_id
        else (p.model_copy(update={"tapped": True}) if p.id in selected_ids else p)
        for p in game_state.battlefield
    ]

    new_crewed = dict(getattr(game_state, "crewed_vehicles", {}) or {})
    new_crewed[vehicle_perm_id] = crew_value

    logger.info(
        "Crew: %s resolved crew of %s (value %d) with %d creature(s), total power %d",
        player_name, vehicle.card.name, crew_value, len(to_tap), total_power,
    )
    return game_state.model_copy(update={
        "battlefield": new_battlefield,
        "crewed_vehicles": new_crewed,
        "pending_crew_choice": None,
    })


def handle_crew_expiration(game_state: GameState) -> GameState:
    """Revert all crewed vehicles at end of turn (CR 702.147b).

    Iterates ``game_state.crewed_vehicles`` and reverts each tracked vehicle to
    its non-vehicle artifact form, clearing the tracking dict. Pure transform:
    returns the SAME object when there is nothing to expire (Q4).
    """
    crewed = getattr(game_state, "crewed_vehicles", {}) or {}
    if not crewed:
        return game_state

    new_battlefield = []
    reverted: list[str] = []
    for perm in game_state.battlefield:
        if perm.id in crewed:
            new_battlefield.append(_uncrew_permanent(perm))
            reverted.append(perm.id)
        else:
            new_battlefield.append(perm)

    if not reverted:
        return game_state

    remaining = {k: v for k, v in crewed.items() if k not in reverted}
    logger.info("Crew: expired %d vehicle(s) at end of turn", len(reverted))
    return game_state.model_copy(update={
        "battlefield": new_battlefield,
        "crewed_vehicles": remaining,
    })
