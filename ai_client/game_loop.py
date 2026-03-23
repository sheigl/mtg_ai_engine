"""Game loop: drives AI players through a complete MTG game."""
import logging
import re
import sys
import time

from .ai_player import AIPlayer
from .client import EngineClient, EngineError
from .heuristic_player import HeuristicPlayer, compute_block_declarations
from .debug_forwarder import DebugForwarder
from .models import GameConfig, GameSummary, TurnRecord
from .observer import ObserverAI
from .prompts import build_game_state_prompt

logger = logging.getLogger(__name__)

_SEPARATOR = "─" * 41
_DOUBLE_SEPARATOR = "═" * 40
_MANA_ADD_RE = re.compile(r'Add\s+\{')


def _parse_mana_cost_to_payment(mana_cost: str, mana_pool: dict) -> dict:
    """
    Convert a mana cost string like "{1}{G}" into a payment dict like {"G": 1, "W": 1}.
    Colored symbols are paid with their matching color; generic is paid with whatever is left.
    """
    payment: dict[str, int] = {}
    pool = dict(mana_pool)
    generic = 0

    for sym in re.findall(r'\{([^}]+)\}', mana_cost):
        if sym in ('W', 'U', 'B', 'R', 'G', 'C'):
            payment[sym] = payment.get(sym, 0) + 1
            pool[sym] = pool.get(sym, 0) - 1
        elif sym.isdigit():
            generic += int(sym)
        elif sym == 'X':
            pass  # treat X as 0 for now

    # Pay generic with any available mana (prefer colorless first, then colors)
    for color in ('C', 'W', 'U', 'B', 'R', 'G'):
        if generic <= 0:
            break
        available = max(0, pool.get(color, 0))
        take = min(generic, available)
        if take > 0:
            payment[color] = payment.get(color, 0) + take
            pool[color] = pool.get(color, 0) - take
            generic -= take

    return payment


def _map_action_to_request(action: dict, mana_pool: dict | None = None) -> tuple[str, dict]:
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
        mana_cost_str = mana_options[0].get("mana_cost", "") if mana_options else ""
        mana_payment = _parse_mana_cost_to_payment(mana_cost_str, mana_pool or {})
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
        attacker_ids = action.get("valid_targets", [])
        defending_player = action.get("card_name", "")
        return "declare_attackers", {
            "attack_declarations": [
                {"attacker_id": aid, "defending_id": defending_player}
                for aid in attacker_ids
            ]
        }

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

    if action_type == "cast_commander":
        return "cast", {
            "card_id": action.get("card_id", ""),
            "targets": [],
            "mana_payment": {},
            "from_command_zone": True,
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
    if summary.commander_damage:
        print("Commander damage totals:")
        for perm_id, dmg_by_player in summary.commander_damage.items():
            for player_name, total in dmg_by_player.items():
                print(f"  {perm_id[:8]}... → {player_name}: {total}")
    print(_DOUBLE_SEPARATOR)


def _format_gs_summary(gs: dict) -> str:
    """Format a concise game-state summary for the observer AI prompt."""
    lines = []
    for p in gs.get("players", []):
        hand_count = len(p.get("hand", []))
        bf = [
            perm.get("card", {}).get("name", "?")
            for perm in gs.get("battlefield", [])
            if perm.get("controller") == p.get("name")
        ]
        lines.append(
            f"{p.get('name')}: life={p.get('life', '?')}, hand={hand_count} cards, "
            f"battlefield=[{', '.join(bf) if bf else 'empty'}]"
        )
    return "\n".join(lines)


class GameLoop:
    """Drives two AI players through a complete MTG game."""

    def __init__(
        self,
        config: GameConfig,
        engine: EngineClient,
        players: "list[AIPlayer | HeuristicPlayer]",
        debug: bool = False,
        observer: "ObserverAI | None" = None,
    ) -> None:
        self._config = config
        self._engine = engine
        self._players = players
        self._debug = debug
        self._observer = observer
        self._forwarder: DebugForwarder | None = None
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
            game_id = self._engine.create_game(self._config, debug=self._debug)
        except EngineError as exc:
            print(f"[ERROR] Failed to create game: {exc}")
            sys.exit(1)

        if self._config.verbose:
            try:
                self._engine.set_verbose(game_id, True)
            except EngineError:
                pass  # non-fatal

        # Create the DebugForwarder when debug panel or observer commentary is active
        if self._debug or self._observer:
            self._forwarder = DebugForwarder(self._config.engine_url, game_id)

        turn_count = 0
        decision_count = 0
        termination_reason = "game_over"
        winner = None

        # Print startup banner
        is_commander = self._config.format == "commander"
        title_suffix = " [Commander]" if is_commander else ""
        print(f"Starting MTG AI Game{title_suffix}")
        print(f"Engine  : {self._config.engine_url}")
        for i, pc in enumerate(self._config.players):
            label = "Players :" if i == 0 else "          "
            if pc.player_type == "heuristic":
                print(f"{label} {pc.name} [heuristic — no LLM]")
            else:
                print(f"{label} {pc.name} ({pc.model} @ {pc.base_url}) [LLM]")
        if is_commander:
            print(f"Commanders: {self._config.commander1} vs {self._config.commander2}")
        print(f"Game ID : {game_id}")
        print()

        while True:
            # Safety: max turns (0 = unlimited)
            if self._config.max_turns > 0 and turn_count >= self._config.max_turns:
                termination_reason = "max_turns_reached"
                break

            # Fetch legal actions
            try:
                legal_data = self._engine.get_legal_actions(game_id)
            except EngineError as exc:
                print(f"[ERROR] Engine error fetching legal actions: {exc}")
                termination_reason = "engine_error"
                break

            # Hold while paused (UI pause button)
            if legal_data.get("is_paused"):
                print("[PAUSED] Game paused — resume from the debug panel to continue.")
                while True:
                    time.sleep(2.0)
                    try:
                        legal_data = self._engine.get_legal_actions(game_id)
                    except EngineError:
                        break
                    if not legal_data.get("is_paused"):
                        print("[RESUMED] Game resuming.")
                        break
                continue

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

            # Debug: POST initial entry and wire streaming callback.
            # Heuristic players have no LLM prompt/response — skip debug entry for them.
            _debug_entry_id: str | None = None
            if self._forwarder and not isinstance(ai_player, HeuristicPlayer):
                _debug_entry_id = self._forwarder.new_entry_id()
                self._forwarder.post_entry({
                    "entry_id": _debug_entry_id,
                    "entry_type": "prompt_response",
                    "source": priority_player,
                    "turn": turn_number,
                    "phase": phase,
                    "step": step,
                    "timestamp": time.time(),
                    "prompt": prompt,
                    "response": "",
                    "is_complete": False,
                })
                _eid = _debug_entry_id
                _fwd = self._forwarder

                def _debug_cb(event: str, text: str, _: str) -> None:
                    if event == "response_chunk":
                        _fwd.patch_entry(_eid, text, False)
                    elif event == "response_done":
                        _fwd.patch_entry(_eid, "", True)

                ai_player._debug_callback = _debug_cb
            else:
                ai_player._debug_callback = None

            chosen_index, reasoning = ai_player.decide(
                prompt,
                legal_actions=legal_actions,
                game_state={**gs, "priority_player": priority_player, "phase": phase, "step": step},
            )
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
            priority_pool = next(
                (p.get("mana_pool", {}) for p in gs.get("players", []) if p.get("name") == priority_player),
                {},
            )
            # Just-in-time mana tapping: only tap when the AI has decided to cast.
            # This avoids wasted taps when the AI would pass anyway.
            if chosen_action.get("action_type") in ("cast", "cast_commander"):
                legal_data = self._auto_tap_mana(game_id, legal_data)
                # Re-fetch mana pool after tapping
                priority_pool = next(
                    (p.get("mana_pool", {}) for p in gs.get("players", []) if p.get("name") == priority_player),
                    {},
                )
                try:
                    gs_tapped = self._engine.get_game_state(game_id)
                    priority_pool = next(
                        (p.get("mana_pool", {}) for p in gs_tapped.get("players", []) if p.get("name") == priority_player),
                        priority_pool,
                    )
                except EngineError:
                    pass

            action_type, payload = _map_action_to_request(chosen_action, priority_pool)
            if action_type == "declare_attackers" and isinstance(ai_player, HeuristicPlayer):
                gs_with_priority = {**gs, "priority_player": priority_player}
                selected_ids = ai_player.select_attackers(chosen_action, gs_with_priority, priority_player)
                defending_player = chosen_action.get("card_name", "")
                payload["attack_declarations"] = [
                    {"attacker_id": aid, "defending_id": defending_player}
                    for aid in selected_ids
                ]
            if action_type == "declare_blockers":
                gs_with_priority = {**gs, "priority_player": priority_player, "phase": phase, "step": step}
                payload["block_declarations"] = compute_block_declarations(chosen_action, gs_with_priority)
            try:
                self._engine.submit_action(game_id, action_type, payload)
            except EngineError as exc:
                print(f"[ERROR] Engine rejected action: {exc}")
                termination_reason = "engine_error"
                break

            decision_count += 1
            turn_count += 1

            # Observer AI: analyze all non-pass actions — heuristic and LLM alike
            if self._observer and self._forwarder and chosen_action.get("action_type") != "pass":
                gs_summary = _format_gs_summary(gs)
                commentary = self._observer.analyze(
                    player_name=priority_player,
                    turn=turn_number,
                    phase=phase,
                    step=step,
                    chosen_action_desc=action_desc,
                    legal_actions=legal_actions,
                    game_state_summary=gs_summary,
                )
                obs_entry_id = self._forwarder.new_entry_id()
                obs_entry = {
                    "entry_id": obs_entry_id,
                    "entry_type": "commentary",
                    "source": "Observer AI",
                    "turn": turn_number,
                    "phase": phase,
                    "step": step,
                    "timestamp": time.time(),
                    "prompt": "",
                    "response": commentary.get("explanation", ""),
                    "is_complete": True,
                    "rating": commentary.get("rating"),
                    "explanation": commentary.get("explanation"),
                    "alternative": commentary.get("alternative"),
                }
                self._forwarder.post_entry(obs_entry)

            # Re-check game state after action
            try:
                gs_after = self._engine.get_game_state(game_id)
                if gs_after.get("is_game_over"):
                    termination_reason = "game_over"
                    winner = gs_after.get("winner")
                    break
            except EngineError:
                pass

        # Fetch final game state for commander damage totals
        final_commander_damage: dict = {}
        if self._config.format == "commander":
            try:
                final_gs = self._engine.get_game_state(game_id)
                final_commander_damage = final_gs.get("commander_damage", {})
            except EngineError:
                pass

        summary = GameSummary(
            game_id=game_id,
            winner=winner,
            total_turns=turn_count,
            total_decisions=decision_count,
            termination_reason=termination_reason,
            commander_damage=final_commander_damage,
        )
        print_game_summary(summary)
        return summary

    def _auto_tap_mana(self, game_id: str, legal_data: dict) -> dict:
        """
        Silently activate all available mana-producing abilities before the AI decides.
        Returns updated legal_data (with refreshed legal_actions reflecting the full mana pool).
        Mana abilities are detected by "Add {" in their description.
        """
        while True:
            legal_actions = legal_data.get("legal_actions", [])
            mana_acts = [
                a for a in legal_actions
                if a.get("action_type") == "activate"
                and _MANA_ADD_RE.search(a.get("description", ""))
            ]
            if not mana_acts:
                break
            # Execute the first available mana activation
            action = mana_acts[0]
            try:
                self._engine.submit_action(
                    game_id,
                    "activate",
                    {
                        "permanent_id": action.get("permanent_id", ""),
                        "ability_index": action.get("ability_index", 0),
                        "targets": [],
                        "mana_payment": {},
                    },
                )
            except EngineError:
                break
            try:
                legal_data = self._engine.get_legal_actions(game_id)
            except EngineError:
                break
            if legal_data.get("is_game_over") or legal_data.get("is_paused"):
                break
        return legal_data

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
