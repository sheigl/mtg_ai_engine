"""Game loop: drives AI players through a complete MTG game."""
import logging
import sys

from .ai_player import AIPlayer
from .client import EngineClient, EngineError
from .models import GameConfig, GameSummary, TurnRecord
from .prompts import build_game_state_prompt

logger = logging.getLogger(__name__)

_SEPARATOR = "─" * 41
_DOUBLE_SEPARATOR = "═" * 40


def _map_action_to_request(action: dict) -> tuple[str, dict]:
    """
    Map a legal-action dict to (action_type, request_payload).

    The action_type is passed to EngineClient.submit_action which handles
    routing to the correct endpoint.
    """
    action_type = action.get("action_type", "pass")

    if action_type == "pass":
        return "pass", {}

    if action_type == "play_land":
        return "play_land", {"card_id": action.get("card_id", "")}

    if action_type == "cast":
        mana_options = action.get("mana_options", [{}])
        mana_payment = mana_options[0].get("mana_cost", "") if mana_options else ""
        return "cast", {
            "card_id": action.get("card_id", ""),
            "targets": action.get("valid_targets", []),
            "mana_payment": mana_payment,
        }

    if action_type == "activate":
        return "activate", {
            "permanent_id": action.get("permanent_id", ""),
            "ability_index": action.get("ability_index", 0),
            "targets": [],
            "mana_payment": {},
        }

    if action_type == "declare_attackers":
        return "declare_attackers", {"attack_declarations": []}

    if action_type == "declare_blockers":
        return "declare_blockers", {"block_declarations": []}

    if action_type == "order_blockers":
        return "order_blockers", {"orderings": []}

    if action_type == "assign_combat_damage":
        return "assign_combat_damage", {"assignments": []}

    if action_type == "put_trigger":
        return "put_trigger", {
            "trigger_id": action.get("trigger_id", ""),
            "targets": [],
        }

    # Fallback: pass
    return "pass", {}


def format_turn_header(record: TurnRecord) -> str:
    """Format the per-turn console block per the CLI output contract."""
    lines = [
        _SEPARATOR,
        f"Turn {record.turn_number} | {record.phase} / {record.step}",
        f"Player: {record.player_name}",
        f"Reasoning: {record.reasoning}",
        f"Action: {record.action_description}",
    ]
    if record.fallback_used:
        lines.append("[FALLBACK] AI failed — submitted pass priority")
    lines.append(_SEPARATOR)
    return "\n".join(lines)


def print_game_summary(summary: GameSummary) -> None:
    """Print the double-border game-over block."""
    winner_label = summary.winner if summary.winner else "(draw / timeout)"
    print(_DOUBLE_SEPARATOR)
    print("GAME OVER")
    print(f"Winner : {winner_label}")
    print(f"Game ID: {summary.game_id}")
    print(f"Turns  : {summary.total_turns}")
    print(f"Decisions made: {summary.total_decisions}")
    print(f"Reason : {summary.termination_reason}")
    print(_DOUBLE_SEPARATOR)


class GameLoop:
    """Drives two AI players through a complete MTG game."""

    def __init__(
        self,
        config: GameConfig,
        engine: EngineClient,
        players: list[AIPlayer],
    ) -> None:
        self._config = config
        self._engine = engine
        self._players = players
        # Map player name → AIPlayer
        self._player_map: dict[str, AIPlayer] = {
            config.players[i].name: players[i] for i in range(len(players))
        }

    def run(self) -> GameSummary:
        """
        Create a game and loop until game_over or max_turns.
        Returns a GameSummary.
        """
        try:
            game_id = self._engine.create_game(self._config)
        except EngineError as exc:
            print(f"[ERROR] Failed to create game: {exc}")
            sys.exit(1)

        if self._config.verbose:
            try:
                self._engine.set_verbose(game_id, True)
            except EngineError:
                pass  # non-fatal

        turn_count = 0
        decision_count = 0
        termination_reason = "game_over"
        winner = None

        # Print startup banner (T025)
        print("Starting MTG AI Game")
        print(f"Engine  : {self._config.engine_url}")
        for i, pc in enumerate(self._config.players):
            label = "Players :" if i == 0 else "          "
            print(f"{label} {pc.name} ({pc.model} @ {pc.base_url})")
        print(f"Game ID : {game_id}")
        print()

        while True:
            # Safety: max turns
            if turn_count >= self._config.max_turns:
                termination_reason = "max_turns_reached"
                break

            # Fetch legal actions
            try:
                legal_data = self._engine.get_legal_actions(game_id)
            except EngineError as exc:
                print(f"[ERROR] Engine error fetching legal actions: {exc}")
                termination_reason = "engine_error"
                break

            # Check game over
            if legal_data.get("is_game_over"):
                termination_reason = "game_over"
                winner = legal_data.get("winner")
                break

            legal_actions = legal_data.get("legal_actions", [])
            priority_player = legal_data.get("priority_player", "")
            phase = legal_data.get("phase", "?")
            step = legal_data.get("step", "?")
            turn_number = legal_data.get("turn", turn_count + 1)

            # Get full game state to check is_game_over properly
            try:
                gs = self._engine.get_game_state(game_id)
            except EngineError as exc:
                print(f"[ERROR] Engine error fetching game state: {exc}")
                termination_reason = "engine_error"
                break

            if gs.get("is_game_over"):
                termination_reason = "game_over"
                winner = gs.get("winner")
                break

            turn_number = gs.get("turn", turn_count + 1)

            if not legal_actions:
                # Nothing to do — shouldn't happen but guard against it
                break

            # Identify which AI player has priority
            ai_player = self._player_map.get(priority_player)
            if ai_player is None:
                # Unknown player name — fall back to player 0
                ai_player = self._players[0]

            # Build prompt and ask the AI
            prompt = build_game_state_prompt(
                {**gs, "priority_player": priority_player, "phase": phase, "step": step},
                legal_actions,
            )
            chosen_index, reasoning = ai_player.decide(prompt)
            fallback_used = reasoning == "(AI endpoint unreachable)"

            # Clamp chosen index to valid range
            if chosen_index < 0 or chosen_index >= len(legal_actions):
                chosen_index = 0
                fallback_used = True
                reasoning = "(index out of range — fallback to pass)"

            chosen_action = legal_actions[chosen_index]
            action_desc = chosen_action.get("description", chosen_action.get("action_type", "?"))

            # Build turn record and print
            record = TurnRecord(
                turn_number=turn_number,
                player_name=priority_player,
                phase=phase,
                step=step,
                legal_actions=legal_actions,
                chosen_index=chosen_index,
                reasoning=reasoning,
                action_description=action_desc,
                fallback_used=fallback_used,
            )
            print(format_turn_header(record))

            # Verbose: print board state
            if self._config.verbose:
                self._print_verbose_state(gs)

            # Submit the chosen action
            action_type, payload = _map_action_to_request(chosen_action)
            try:
                self._engine.submit_action(game_id, action_type, payload)
            except EngineError as exc:
                print(f"[ERROR] Engine rejected action: {exc}")
                termination_reason = "engine_error"
                break

            decision_count += 1
            turn_count += 1

            # Re-check game state after action
            try:
                gs_after = self._engine.get_game_state(game_id)
                if gs_after.get("is_game_over"):
                    termination_reason = "game_over"
                    winner = gs_after.get("winner")
                    break
            except EngineError:
                pass

        summary = GameSummary(
            game_id=game_id,
            winner=winner,
            total_turns=turn_count,
            total_decisions=decision_count,
            termination_reason=termination_reason,
        )
        print_game_summary(summary)
        return summary

    def _print_verbose_state(self, gs: dict) -> None:
        """Print abbreviated board state when verbose mode is on."""
        print("  [State]")
        for p in gs.get("players", []):
            hand_count = len(p.get("hand", []))
            life = p.get("life", "?")
            bf = [
                perm.get("card", {}).get("name", "?")
                for perm in gs.get("battlefield", [])
                if perm.get("controller") == p.get("name")
            ]
            print(f"    {p.get('name')}: life={life}, hand={hand_count}, "
                  f"battlefield={bf if bf else '(none)'}")
        print()
