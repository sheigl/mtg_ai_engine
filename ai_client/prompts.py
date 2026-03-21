"""Prompt building and default deck for the AI CLI client."""

# Built-in 99-card mono-green Commander deck (for use with a legendary green commander).
# NOTE: This deck contains duplicates for testing convenience; real Commander games
# require a proper singleton deck provided via --deck1/--deck2.
DEFAULT_COMMANDER_DECK: list[str] = (
    ["Forest"] * 37
    + ["Llanowar Elves"] * 4
    + ["Elvish Mystic"] * 4
    + ["Grizzly Bears"] * 4
    + ["Giant Growth"] * 4
    + ["Elvish Warrior"] * 4
    + ["Troll Ascetic"] * 4
    + ["Leatherback Baloth"] * 4
    + ["Garruk's Companion"] * 4
    + ["Rancor"] * 4
    + ["Giant Spider"] * 4
    + ["Kalonian Tusker"] * 4
    + ["Prey Upon"] * 4
    + ["Titanic Growth"] * 4
    + ["Woodfall Primus"] * 3
    + ["Elvish Visionary"] * 4
    + ["Reclamation Sage"] * 3
)

# Built-in 60-card test deck
DEFAULT_DECK: list[str] = (
    ["Plains"] * 24
    + ["Forest"] * 8
    + ["Llanowar Elves"] * 4
    + ["Grizzly Bears"] * 4
    + ["Giant Growth"] * 4
    + ["Lightning Bolt"] * 4
    + ["Counterspell"] * 4
    + ["Elvish Warrior"] * 4
    + ["Rancor"] * 4
)


def build_game_state_prompt(state: dict, legal_actions: list[dict]) -> str:
    """
    Serialise current game state and legal actions into a plain-text LLM prompt.

    Returns a string the LLM should respond to with JSON:
      {"action_index": N, "reasoning": "..."}
    """
    phase = state.get("phase", "?")
    step = state.get("step", "?")
    priority_player = state.get("priority_player", state.get("priority_holder", "?"))
    turn = state.get("turn", "?")

    # Find the priority player's info from the players list
    players = state.get("players", [])
    my_info: dict = {}
    opp_info: dict = {}
    for p in players:
        if p.get("name") == priority_player:
            my_info = p
        else:
            opp_info = p

    hand_names = [c.get("name", "?") for c in my_info.get("hand", [])]
    battlefield_names = [
        f"{perm.get('card', {}).get('name', '?')} ({'tapped' if perm.get('tapped') else 'untapped'})"
        for perm in state.get("battlefield", [])
        if perm.get("controller") == priority_player
    ]
    opp_battlefield = [
        f"{perm.get('card', {}).get('name', '?')} ({'tapped' if perm.get('tapped') else 'untapped'})"
        for perm in state.get("battlefield", [])
        if perm.get("controller") != priority_player
    ]
    stack = state.get("stack", [])
    stack_desc = [s.get("description", str(s)) for s in stack]

    # Commander-specific info
    game_format = state.get("format", "standard")
    commander_lines: list[str] = []
    if game_format == "commander":
        my_cmd_zone = [c.get("name", "?") for c in my_info.get("command_zone", [])]
        opp_cmd_zone = [c.get("name", "?") for c in opp_info.get("command_zone", [])]
        my_cast_count = my_info.get("commander_cast_count", 0)
        my_tax = my_cast_count * 2
        opp_cast_count = opp_info.get("commander_cast_count", 0)
        opp_tax = opp_cast_count * 2
        commander_lines.append(
            f"Your command zone: {', '.join(my_cmd_zone) if my_cmd_zone else '(empty)'}"
            + (f" (tax: +{my_tax})" if my_tax else "")
        )
        commander_lines.append(
            f"Opponent command zone: {', '.join(opp_cmd_zone) if opp_cmd_zone else '(empty)'}"
            + (f" (tax: +{opp_tax})" if opp_tax else "")
        )
        # Commander damage totals
        cmd_damage = state.get("commander_damage", {})
        if cmd_damage:
            for perm_id, dmg_by_player in cmd_damage.items():
                for player_name, total in dmg_by_player.items():
                    commander_lines.append(f"Commander damage to {player_name} from {perm_id[:8]}: {total}")

    lines = [
        f"=== MTG Game — Turn {turn} | {phase} / {step} ===",
        f"You are: {priority_player}",
        f"Your life: {my_info.get('life', '?')}  |  Opponent life: {opp_info.get('life', '?')}",
        f"Your hand ({len(hand_names)} cards): {', '.join(hand_names) if hand_names else '(empty)'}",
        f"Your mana pool: {my_info.get('mana_pool', {})}",
        f"Your battlefield: {', '.join(battlefield_names) if battlefield_names else '(none)'}",
        f"Opponent battlefield: {', '.join(opp_battlefield) if opp_battlefield else '(none)'}",
        f"Stack: {', '.join(stack_desc) if stack_desc else '(empty)'}",
    ]
    lines.extend(commander_lines)
    lines += [
        "",
        "Legal actions (choose one by index):",
    ]
    for i, action in enumerate(legal_actions):
        desc = action.get("description", action.get("action_type", "?"))
        lines.append(f"  [{i}] {desc}")

    lines += [
        "",
        "Respond with JSON only — no markdown, no explanation outside the JSON:",
        '{"action_index": <number>, "reasoning": "<your reasoning>"}',
    ]

    return "\n".join(lines)
