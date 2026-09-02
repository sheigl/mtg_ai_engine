"""Convoke keyword (CR 702.43).

Convoke is an additional cost: "As an additional cost to cast this spell, you
may tap any number of untapped creatures you control. Each creature tapped
this way reduces the cost by {1} or by one mana of that creature's color."
Cost reduction applies before other reductions.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING

from mtg_engine.ability.keywords.base import CostKeyword

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_CONVOKE_PATTERN = re.compile(r"\bconvoke\b", re.IGNORECASE)


class Convoke(CostKeyword):
    name = "convoke"

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("convoke" in k.lower() for k in keywords)
            or bool(_CONVOKE_PATTERN.search(oracle))
        )

    @staticmethod
    def has_convoke(keywords: list[str]) -> bool:
        return "convoke" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_CONVOKE_PATTERN.search(oracle_text))

    def apply(self, game_state: GameState, permanent: Permanent, target: Permanent | None = None) -> GameState:
        """Apply convoke (CR 702.43).

        During spell declaration, convoke offers cost reduction by tapping
        controlled untapped creatures.

        - Human caster: queues ``pending_convoke_choice`` with eligible
          untapped creatures list; cast is deferred until choice resolves.
        - AI caster: auto-resolves by greedily tapping creatures to maximize
          reduction, preferring colored mana matching.

        Returns a pure-transform GameState.
        """
        card = permanent.card
        controller = permanent.controller

        # No-op guard: card must have convoke
        if not (
            self.has_convoke(card.keywords or [])
            or bool(_CONVOKE_PATTERN.search(card.oracle_text or ""))
        ):
            return game_state

        # Gather untapped creatures controlled by caster
        eligible = []
        for perm in game_state.battlefield:
            if (
                perm.controller == controller
                and not perm.tapped
                and "creature" in (perm.card.type_line or "").lower()
            ):
                eligible.append({
                    "id": perm.id,
                    "name": perm.card.name,
                    "colors": perm.card.colors or [],
                })

        # Human vs AI
        is_human = (
            getattr(game_state, "human_player_name", None) is not None
            and controller == game_state.human_player_name
        )

        base_cost = card.mana_cost or ""

        if is_human:
            pending = {
                "player": controller,
                "card_id": card.id,
                "card_name": card.name,
                "base_cost": base_cost,
                "eligible_creatures": eligible,
                "tapped_creature_ids": [],
                "resolved": False,
            }
            logger.info(
                "%s: queued convoke choice for %s (%d eligible creatures)",
                controller, card.name, len(eligible)
            )
            return game_state.model_copy(update={"pending_convoke_choice": pending})

        # AI auto-resolution
        from mtg_engine.engine.mana import parse_mana_cost

        # Parse cost
        cost_dict = parse_mana_cost(base_cost)
        # Make mutable copy
        needed = {k: int(v) for k, v in cost_dict.items()}

        tapped_ids = []

        # Greedy color-matching heuristic
        # Sort eligible creatures by number of colors descending to prefer
        # more flexible creatures first
        eligible_perms = [
            p for p in game_state.battlefield
            if p.id in [e["id"] for e in eligible]
        ]
        # Simple sort: more colors first, then by name
        eligible_perms.sort(key=lambda p: (len(p.card.colors or []), p.card.name), reverse=True)

        for perm in eligible_perms:
            if all(v <= 0 for k, v in needed.items() if k != "generic"):
                # Colored needs satisfied, continue for generic
                pass

            # Determine if we can reduce a colored cost
            creature_colors = perm.card.colors or []
            reduced = False
            for color in creature_colors:
                if needed.get(color, 0) > 0:
                    needed[color] -= 1
                    reduced = True
                    break
            if not reduced:
                # Reduce generic
                if needed.get("generic", 0) > 0:
                    needed["generic"] -= 1
                    reduced = True
                elif needed.get("C", 0) > 0:
                    # Treat C as generic for parsing
                    needed["C"] -= 1
                    reduced = True

            if reduced:
                tapped_ids.append(perm.id)

            # Stop if cost fully reduced
            if all(v <= 0 for v in needed.values()):
                break

        # Tap selected creatures (pure transform)
        new_battlefield = []
        for perm in game_state.battlefield:
            if perm.id in tapped_ids:
                new_perm = perm.model_copy(update={"tapped": True})
                new_battlefield.append(new_perm)
            else:
                new_battlefield.append(perm)

        pending = {
            "player": controller,
            "card_id": card.id,
            "card_name": card.name,
            "base_cost": base_cost,
            "eligible_creatures": eligible,
            "tapped_creature_ids": tapped_ids,
            "resolved": True,
        }

        logger.info(
            "%s: AI resolved convoke for %s, tapped %d creatures",
            controller, card.name, len(tapped_ids)
        )
        return game_state.model_copy(update={
            "battlefield": new_battlefield,
            "pending_convoke_choice": pending,
        })
