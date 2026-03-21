"""Prompt building and default deck for the AI CLI client."""

# Built-in 40-card test deck (T007)
DEFAULT_DECK: list[str] = (
    ["Plains"] * 20
    + ["Llanowar Elves"] * 4
    + ["Grizzly Bears"] * 4
    + ["Giant Growth"] * 4
    + ["Lightning Bolt"] * 4
    + ["Counterspell"] * 4
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

    lines = [
        f"=== MTG Game — Turn {turn} | {phase} / {step} ===",
        f"You are: {priority_player}",
        f"Your life: {my_info.get('life', '?')}  |  Opponent life: {opp_info.get('life', '?')}",
        f"Your hand ({len(hand_names)} cards): {', '.join(hand_names) if hand_names else '(empty)'}",
        f"Your mana pool: {my_info.get('mana_pool', {})}",
        f"Your battlefield: {', '.join(battlefield_names) if battlefield_names else '(none)'}",
        f"Opponent battlefield: {', '.join(opp_battlefield) if opp_battlefield else '(none)'}",
        f"Stack: {', '.join(stack_desc) if stack_desc else '(empty)'}",
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
