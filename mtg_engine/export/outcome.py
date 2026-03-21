"""Win/loss outcome recorder. REQ-D10."""
from pydantic import BaseModel
from mtg_engine.models.game import GameState


class GameOutcome(BaseModel):
    """REQ-D10 schema."""
    game_id: str
    winner: str | None          # player name, "draw", or None if in progress
    win_condition: str | None   # "life" | "mill" | "poison" | "concede" | "timeout"
    total_turns: int
    player_1_name: str
    player_2_name: str
    player_1_deck: list[str]    # card names (from graveyard + hand + library + battlefield)
    player_2_deck: list[str]
    player_1_final_life: int
    player_2_final_life: int
    snapshot_count: int
    transcript_length: int


def build_outcome(
    gs: GameState,
    snapshot_count: int,
    transcript_length: int,
    win_condition: str | None = None,
) -> GameOutcome:
    """Build an outcome record from the terminal game state."""
    p1, p2 = gs.players[0], gs.players[1]

    # Determine winner
    winner: str | None = gs.winner
    if winner is None and gs.is_game_over:
        winner = "draw"

    # Determine win condition if not provided
    if win_condition is None and gs.is_game_over:
        if p1.has_lost and p1.life <= 0:
            win_condition = "life"
        elif p1.has_lost and p1.poison_counters >= 10:
            win_condition = "poison"
        elif p2.has_lost and p2.life <= 0:
            win_condition = "life"
        elif p2.has_lost and p2.poison_counters >= 10:
            win_condition = "poison"
        else:
            win_condition = "life"

    def _all_card_names(p) -> list[str]:
        cards = list(p.hand) + list(p.library) + list(p.graveyard) + list(p.exile)
        bf_cards = [perm.card for perm in gs.battlefield if perm.controller == p.name]
        return [c.name for c in cards + bf_cards]

    return GameOutcome(
        game_id=gs.game_id,
        winner=winner,
        win_condition=win_condition,
        total_turns=gs.turn,
        player_1_name=p1.name,
        player_2_name=p2.name,
        player_1_deck=_all_card_names(p1),
        player_2_deck=_all_card_names(p2),
        player_1_final_life=p1.life,
        player_2_final_life=p2.life,
        snapshot_count=snapshot_count,
        transcript_length=transcript_length,
    )
