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

# Built-in 60-card test deck (mono-green — all spells castable with Forest mana)
DEFAULT_DECK: list[str] = (
    ["Forest"] * 24
    + ["Llanowar Elves"] * 4      # {G}
    + ["Elvish Mystic"] * 4       # {G}
    + ["Grizzly Bears"] * 4       # {1}{G}
    + ["Elvish Warrior"] * 4      # {1}{G}
    + ["Giant Growth"] * 4        # {G}
    + ["Rancor"] * 4              # {G}
    + ["Kalonian Tusker"] * 4     # {G}{G}
    + ["Garruk's Companion"] * 4  # {G}{G}
    + ["Leatherback Baloth"] * 4  # {G}{G}{G}
)


import re as _re


def _parse_mana_symbols(cost: str) -> dict[str, int]:
    """Parse a mana cost string like '{1}{G}{G}' into {color: count, generic: N}."""
    result: dict[str, int] = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0, "generic": 0}
    for sym in _re.findall(r'\{([^}]+)\}', cost):
        if sym in result:
            result[sym] += 1
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "X":
            pass  # ignore X costs
    return result


def _can_pay(cost_str: str, pool: dict[str, int]) -> bool:
    """Return True if pool can cover cost_str (ignoring X costs)."""
    if not cost_str:
        return True
    cost = _parse_mana_symbols(cost_str)
    remaining = dict(pool)
    # Pay colored symbols first
    for color in ("W", "U", "B", "R", "G", "C"):
        needed = cost.get(color, 0)
        have = remaining.get(color, 0)
        if have < needed:
            return False
        remaining[color] = have - needed
    # Pay generic with whatever is left
    generic = cost.get("generic", 0)
    total_left = sum(max(0, v) for v in remaining.values())
    return total_left >= generic


def _max_available_mana(my_info: dict, battlefield: list[dict], legal_actions: list[dict]) -> dict[str, int]:
    """
    Compute the maximum mana available this turn:
    current mana pool + mana from activate actions (lands/mana sources not yet tapped).
    """
    pool = dict(my_info.get("mana_pool", {}))
    # Collect mana from available activate actions
    for action in legal_actions:
        if action.get("action_type") != "activate":
            continue
        desc = action.get("description", "")
        # Parse "{T}: Add {G}" style descriptions
        add_match = _re.search(r'Add\s+((?:\{[^}]+\})+)', desc)
        if add_match:
            for sym in _re.findall(r'\{([^}]+)\}', add_match.group(1)):
                if sym in pool:
                    pool[sym] = pool.get(sym, 0) + 1
    return pool


def _castable_cards(hand: list[dict], max_pool: dict[str, int], step: str) -> list[str]:
    """Return card names from hand castable given max_pool, at appropriate timing."""
    is_main = step.lower() == "main"
    castable = []
    for card in hand:
        type_lower = (card.get("type_line") or "").lower()
        oracle = (card.get("oracle_text") or "").lower()
        cost = card.get("mana_cost") or ""
        if not cost:
            continue
        # Timing: instants/flash can be cast anytime, others only at sorcery speed
        is_instant_speed = "instant" in type_lower or "flash" in oracle
        if not is_main and not is_instant_speed:
            continue
        if _can_pay(cost, max_pool):
            castable.append(card.get("name", "?"))
    return castable


def _context_hint(priority_player: str, active_player: str, phase: str, step: str, legal_actions: list[dict]) -> str:
    """Return a plain-English sentence explaining why this player has priority right now."""
    is_active = priority_player == active_player
    non_pass = [a for a in legal_actions if a.get("action_type") != "pass"]
    only_pass = len(non_pass) == 0

    if is_active:
        return "It is YOUR turn. You are the active player."

    # Non-active player
    step_lower = step.lower()
    phase_lower = phase.lower()

    if step_lower == "declare_blockers":
        if only_pass:
            return (
                f"It is {active_player}'s turn. You are the defending player. "
                "No attackers were declared, so you have nothing to block — pass priority."
            )
        return (
            f"It is {active_player}'s turn and they have declared attackers. "
            "You must now DECLARE BLOCKERS — assign your untapped creatures to block incoming attackers, "
            "or pass to take the damage unblocked."
        )

    if "combat" in phase_lower or step_lower in ("declare_attackers", "combat_damage", "first_strike_damage", "end_of_combat"):
        if only_pass:
            return (
                f"It is {active_player}'s turn (combat phase). "
                "You have no instants or abilities to use right now — pass priority."
            )
        return (
            f"It is {active_player}'s turn (combat phase). "
            "You may cast instants or activate abilities before combat resolves."
        )

    if only_pass:
        return (
            f"It is {active_player}'s turn. You have no instants or abilities to play right now — pass priority."
        )

    return (
        f"It is {active_player}'s turn. You may respond with instants or activated abilities "
        "before they continue, or pass priority."
    )


def _card_detail(card: dict, permanent: dict | None = None) -> str:
    """Format a rich one-liner for a card, including type, cost, P/T, oracle text."""
    name = card.get("name", "?")
    cost = card.get("mana_cost") or ""
    type_line = card.get("type_line", "")
    oracle = (card.get("oracle_text") or "").replace("\n", " | ")
    kws = card.get("keywords") or []

    parts = [f"  • {name}"]
    if cost:
        parts[0] += f" [{cost}]"
    parts[0] += f" — {type_line}"

    p, t = card.get("power"), card.get("toughness")
    if p is not None and t is not None:
        dmg = permanent.get("damage_marked", 0) if permanent else 0
        parts[0] += f" ({p}/{t})" + (f" [{dmg} damage marked]" if dmg else "")

    if kws:
        parts.append(f"    Keywords: {', '.join(kws)}")
    if oracle:
        parts.append(f"    Text: {oracle}")

    if permanent:
        extras = []
        if permanent.get("tapped"):
            extras.append("TAPPED")
        if permanent.get("summoning_sick") and "creature" in type_line.lower():
            extras.append("summoning sickness — cannot attack this turn")
        counters = {k: v for k, v in (permanent.get("counters") or {}).items() if v and not k.startswith("__")}
        if counters:
            extras.append("counters: " + ", ".join(f"{k}×{v}" for k, v in counters.items()))
        if extras:
            parts.append(f"    Status: {', '.join(extras)}")

    return "\n".join(parts)


def build_game_state_prompt(state: dict, legal_actions: list[dict]) -> str:
    """
    Serialise current game state and legal actions into a rich plain-text LLM prompt.

    Returns a string the LLM should respond to with JSON:
      {"action_index": N, "reasoning": "..."}
    """
    phase = state.get("phase", "?")
    step = state.get("step", "?")
    priority_player = state.get("priority_player", state.get("priority_holder", "?"))
    active_player = state.get("active_player", priority_player)
    turn = state.get("turn", "?")

    players = state.get("players", [])
    my_info: dict = {}
    opp_info: dict = {}
    for p in players:
        if p.get("name") == priority_player:
            my_info = p
        else:
            opp_info = p

    all_perms = state.get("battlefield", [])
    my_perms = [p for p in all_perms if p.get("controller") == priority_player]
    opp_perms = [p for p in all_perms if p.get("controller") != priority_player]

    stack = state.get("stack", [])
    mana_pool = my_info.get("mana_pool", {})
    total_mana = sum(v for v in mana_pool.values() if isinstance(v, int))
    hand_cards = my_info.get("hand", [])

    game_format = state.get("format", "standard")
    context = _context_hint(priority_player, active_player, phase, step, legal_actions)
    max_pool = _max_available_mana(my_info, all_perms, legal_actions)
    castable = _castable_cards(hand_cards, max_pool, step)
    non_pass_actions = [a for a in legal_actions if a.get("action_type") != "pass"]
    activate_only = bool(non_pass_actions) and all(a.get("action_type") == "activate" for a in non_pass_actions)

    lines = [
        f"=== MTG Game — Turn {turn} | {phase} / {step} ===",
        f"",
        f"SITUATION: {context}",
        f"",
        f"You are: {priority_player}  |  Life: {my_info.get('life', '?')}",
        f"Opponent: {opp_info.get('name', '?')}  |  Life: {opp_info.get('life', '?')}",
        f"Mana pool: {total_mana} available {mana_pool}",
    ]

    # Commander zones
    if game_format == "commander":
        my_cmd = [c.get("name", "?") for c in my_info.get("command_zone", [])]
        opp_cmd = [c.get("name", "?") for c in opp_info.get("command_zone", [])]
        my_tax = my_info.get("commander_cast_count", 0) * 2
        opp_tax = opp_info.get("commander_cast_count", 0) * 2
        lines.append(f"Your command zone: {', '.join(my_cmd) or '(empty)'}" + (f" (tax: +{my_tax})" if my_tax else ""))
        lines.append(f"Opponent command zone: {', '.join(opp_cmd) or '(empty)'}" + (f" (tax: +{opp_tax})" if opp_tax else ""))
        cmd_damage = state.get("commander_damage", {})
        for perm_id, dmg_by_player in cmd_damage.items():
            for pname, total in dmg_by_player.items():
                lines.append(f"Commander damage to {pname}: {total}")

    # Hand
    lines += ["", f"YOUR HAND ({len(hand_cards)} cards):"]
    if hand_cards:
        for card in hand_cards:
            lines.append(_card_detail(card))
    else:
        lines.append("  (empty)")

    # Castable note
    if castable:
        lines += ["", f"  → Castable this turn if you tap available lands: {', '.join(castable)}"]
    elif activate_only:
        lines += ["", "  → You have no spells to cast this turn. Unused mana drains at end of turn."]

    # Your battlefield
    lines += ["", f"YOUR BATTLEFIELD ({len(my_perms)} permanents):"]
    if my_perms:
        for perm in my_perms:
            lines.append(_card_detail(perm.get("card", {}), perm))
    else:
        lines.append("  (none)")

    # Opponent's battlefield
    lines += ["", f"OPPONENT'S BATTLEFIELD ({len(opp_perms)} permanents):"]
    if opp_perms:
        for perm in opp_perms:
            lines.append(_card_detail(perm.get("card", {}), perm))
    else:
        lines.append("  (none)")

    # Stack
    if stack:
        lines += ["", "STACK (top resolves first):"]
        for obj in reversed(stack):
            lines.append(f"  • {obj.get('description', str(obj))}")

    # Legal actions
    lines += ["", "LEGAL ACTIONS (choose one by index):"]
    for i, action in enumerate(legal_actions):
        desc = action.get("description", action.get("action_type", "?"))
        marker = ">>>" if action.get("action_type") != "pass" else "   "
        lines.append(f"  [{i}] {marker} {desc}")

    lines += [
        "",
        "Respond with JSON only — no markdown, no explanation outside the JSON:",
        '{"action_index": <number>, "reasoning": "<your reasoning>"}',
    ]

    return "\n".join(lines)
