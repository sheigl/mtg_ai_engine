"""Ninjutsu keyword (CR 702.61).

Ninjutsu {cost} is an activated ability that lets an unblocked attacking
creature be returned to its owner's hand, and this card enters the
battlefield tapped and attacking.
"""
from __future__ import annotations
import logging
import re
from typing import TYPE_CHECKING
from mtg_engine.ability.keywords.base import CostKeyword

logger = logging.getLogger(__name__)

from mtg_engine.models.game import AttackerInfo

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

_NINJUTSU_PATTERN = re.compile(
    r"ninjutsu\s*[—\-]?\s*(\{(?:[^}]+}\s*)+)", re.IGNORECASE
)
_NINJUTSU_PLAIN = re.compile(r"\bninjutsu\b", re.IGNORECASE)


class Ninjutsu(CostKeyword):
    name = "ninjutsu"

    def __init__(self, cost: str | None = None):
        self.cost = cost

    def applies(self, game_state: GameState, permanent: Permanent) -> bool:
        keywords = permanent.card.keywords or []
        oracle = permanent.card.oracle_text or ""
        return (
            any("ninjutsu" in k.lower() for k in keywords)
            or bool(_NINJUTSU_PLAIN.search(oracle))
        )

    @staticmethod
    def has_ninjutsu(keywords: list[str]) -> bool:
        return any("ninjutsu" in k.lower() for k in keywords)

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        if not oracle_text:
            return False
        return bool(_NINJUTSU_PLAIN.search(oracle_text))

    @staticmethod
    def parse_ninjutsu_cost(oracle_text: str) -> str | None:
        match = _NINJUTSU_PATTERN.search(oracle_text or "")
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def from_oracle(cls, oracle_text: str) -> Ninjutsu | None:
        if cls.from_oracle_text(oracle_text):
            return cls(cost=cls.parse_ninjutsu_cost(oracle_text))
        return None

    def apply(
        self,
        game_state: GameState,
        ninja_perm: Permanent,
        attacker_perm_id: str | None = None,
        defending_player: str | None = None,
    ) -> GameState:
        """
        Apply Ninjutsu keyword effect (CR 702.61).

        Activate ninjutsu by returning an unblocked attacking creature to its owner's hand,
        then put this card onto the battlefield tapped and attacking the same target.

        For human players: queue pending_ninjutsu_choice on GameState for player to decide.
        For AI players: auto-resolve — find an unblocked attacker, return it to hand,
        put ninja creature onto battlefield tapped and attacking.

        Args:
            game_state: Current game state.
            ninja_perm: The permanent (in hand) with Ninjutsu keyword.
            attacker_perm_id: ID of the unblocked attacking creature to return.
            defending_player: Player being attacked by the returned creature.

        Returns:
            Modified game state with Ninjutsu choice queued or resolved.
        """
        from mtg_engine.engine.zones import get_player, put_permanent_onto_battlefield

        card = ninja_perm.card
        oracle_text = card.oracle_text or ""
        controller = ninja_perm.controller

        # Guard: only process cards that actually have the Ninjutsu keyword
        if not self.from_oracle_text(oracle_text):
            logger.debug("%s: %s does not have Ninjutsu keyword, returning unchanged state", controller, card.name)
            return game_state.model_copy(update={})

        # Determine if player is human or AI
        is_human = (
            getattr(game_state, "human_player_name", None) is not None
            and controller == game_state.human_player_name
        )

        if is_human:
            # Queue Ninjutsu choice for human player
            game_state = game_state.model_copy(update={
                "pending_ninjutsu_choice": {
                    "player": controller,
                    "ninja_card_id": card.id,
                    "ninja_card_name": card.name,
                    "attacker_perm_id": attacker_perm_id,
                    "defending_player": defending_player,
                    "resolved": False,
                }
            })
            logger.info(
                "%s: queued Ninjutsu choice for %s",
                controller, card.name,
            )
        else:
            # AI auto-resolves Ninjutsu
            player = get_player(game_state, controller)
            if not player:
                logger.warning("Player not found for Ninjutsu resolution: %s", controller)
                return game_state

            # Find an unblocked attacking creature controlled by this player
            attacker_perm = None
            defending_id = defending_player or ""
            if game_state.combat and game_state.combat.attackers:
                for ai in game_state.combat.attackers:
                    perm = next(
                        (p for p in game_state.battlefield if p.id == ai.permanent_id),
                        None,
                    )
                    if perm and perm.controller == controller and not ai.is_blocked:
                        attacker_perm = perm
                        defending_id = ai.defending_id
                        break

            if attacker_perm is None:
                logger.info(
                    "%s: AI skipped Ninjutsu for %s (no unblocked attacker found)",
                    controller, card.name,
                )
                game_state = game_state.model_copy(update={
                    "pending_ninjutsu_choice": {
                        "player": controller,
                        "ninja_card_id": card.id,
                        "ninja_card_name": card.name,
                        "attacker_perm_id": None,
                        "defending_player": defending_id,
                        "resolved": True,
                    }
                })
            else:
                # AI resolves Ninjutsu: return attacker to hand, put ninja on battlefield
                # 1. Remove attacker from combat state and battlefield, add to hand
                new_attackers = [
                    a for a in game_state.combat.attackers
                    if a.permanent_id != attacker_perm.id
                ]
                new_battlefield = [
                    p for p in game_state.battlefield
                    if p.id != attacker_perm.id
                ]

                # Add attacker card to owner's hand
                attacker_owner = attacker_perm.controller
                attacker_player = get_player(game_state, attacker_owner)
                new_hand = list(attacker_player.hand) + [attacker_perm.card]

                # Update player with new hand
                players_update = []
                for p in game_state.players:
                    if p.name == attacker_owner:
                        players_update.append(p.model_copy(update={"hand": new_hand}))
                    else:
                        players_update.append(p)

                combat_update = game_state.combat.model_copy(update={"attackers": new_attackers})

                game_state = game_state.model_copy(
                    update={
                        "battlefield": new_battlefield,
                        "players": players_update,
                        "combat": combat_update,
                    }
                )

                # 2. Put ninja creature onto battlefield tapped and attacking
                game_state, ninja_on_field = put_permanent_onto_battlefield(
                    game_state, card, controller, tapped=True, from_zone="hand"
                )

                # Remove the ninja card from hand (put_permanent_onto_battlefield doesn't remove it)
                ninja_player = get_player(game_state, controller)
                ninja_hand = [c for c in ninja_player.hand if c.id != card.id]
                game_state = game_state.model_copy(
                    update={
                        "players": [
                            p.model_copy(update={"hand": ninja_hand})
                            if p.name == controller else p
                            for p in game_state.players
                        ]
                    }
                )

                # 3. Add ninja to combat attackers, tapped and attacking the same target
                new_attacker_info = AttackerInfo(
                    permanent_id=ninja_on_field.id,
                    defending_id=defending_id,
                )
                new_attackers_list = list(game_state.combat.attackers) + [new_attacker_info]
                game_state = game_state.model_copy(
                    update={
                        "combat": game_state.combat.model_copy(update={"attackers": new_attackers_list})
                    }
                )

                game_state = game_state.model_copy(update={
                    "pending_ninjutsu_choice": {
                        "player": controller,
                        "ninja_card_id": card.id,
                        "ninja_card_name": card.name,
                        "attacker_perm_id": attacker_perm.id,
                        "defending_player": defending_id,
                        "resolved": True,
                    }
                })
                logger.info(
                    "%s: AI resolved Ninjutsu for %s (returned %s to hand)",
                    controller, card.name, attacker_perm.card.name,
                )

        return game_state


def apply_ninjutsu(
    game_state: GameState,
    ninja_card_id: str,
    attacker_perm_id: str | None = None,
    defending_player: str | None = None,
) -> GameState:
    """
    Module-level convenience function for Ninjutsu resolution.

    Finds the ninjutsu card in the player's hand and applies the keyword effect.
    """
    from mtg_engine.engine.zones import get_player

    # Find the ninja card in any player's hand
    ninja_perm = None
    controller = None
    for p in game_state.players:
        c = next((c for c in p.hand if c.id == ninja_card_id), None)
        if c:
            from mtg_engine.models.game import Permanent
            ninja_perm = Permanent(card=c, controller=p.name)
            controller = p.name
            break

    if ninja_perm is None:
        logger.warning("Ninjutsu card %s not found in any player's hand", ninja_card_id)
        return game_state.model_copy(update={})

    ninjutsu = Ninjutsu()
    return ninjutsu.apply(game_state, ninja_perm, attacker_perm_id, defending_player)
