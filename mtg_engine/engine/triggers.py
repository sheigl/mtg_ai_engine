"""
Trigger detection. REQ-A08, REQ-S04.
CR 603: handling triggered abilities.
Listens for zone-change, phase-change, and damage events.
Queues triggers for APNAP ordering.
"""
import logging
import uuid
import re as _re

from mtg_engine.models.game import GameState, PendingTrigger, Permanent, StackObject
from mtg_engine.engine.zones import register_zone_change_listener, ZoneChangeEvent

logger = logging.getLogger(__name__)

# Extended trigger patterns - now 50+

# Trigger patterns for "whenever you cast" and "whenever a player casts"
CAST_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you cast (?:(?:a|an) )?(.*?)(?:,|\.|\?|$)", _re.IGNORECASE),
    _re.compile(r"whenever a (?:creature|artifact|instant|sorcery|enchantment|planeswalker|land) is cast", _re.IGNORECASE),
    _re.compile(r"whenever (?:(?:a|an) )?(.*?)(?:,|\.|\?|$) is cast", _re.IGNORECASE),
    _re.compile(r"whenever you cast (?:a|an) (.*?), create", _re.IGNORECASE),
    _re.compile(r"whenever you cast a (.*?) spell", _re.IGNORECASE),
]

# Trigger patterns for "whenever [creature] attacks"
ATTACK_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:this|~|this creature) attacks", _re.IGNORECASE),
    _re.compile(r"whenever a (?:creature|creature with) (?:(?:that|which) )?(?:attacks|is attacking)", _re.IGNORECASE),
    _re.compile(r"whenever (?:(?:a|an) )?(.*?)(?:,|\.|\?|$) attacks", _re.IGNORECASE),
    _re.compile(r"whenever (?:a|an) (.*?) attacks a player", _re.IGNORECASE),
    _re.compile(r"whenever (?:a|an) (.*?) attacks (?:a|an) (.*?)", _re.IGNORECASE),
]

# Trigger patterns for "whenever [creature] blocks"
BLOCK_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:this|~|this creature) blocks", _re.IGNORECASE),
    _re.compile(r"whenever a (?:creature|creature with) (?:(?:that|which) )?(?:blocks|is blocking)", _re.IGNORECASE),
    _re.compile(r"whenever (?:(?:a|an) )?(.*?)(?:,|\.|\?|$) blocks", _re.IGNORECASE),
]

# Trigger patterns for "at the beginning of your upkeep"
UPKEEP_TRIGGER_PATTERNS = [
    _re.compile(r"at the beginning of (?:your|each player's) upkeep", _re.IGNORECASE),
    _re.compile(r"at the beginning of (?:your|opponent's|each opponent's) precombat main phase", _re.IGNORECASE),
    _re.compile(r"at the beginning of (?:your|opponent's|each opponent's) postcombat main phase", _re.IGNORECASE),
    _re.compile(r"at the beginning of (?:your|opponent's|each opponent's) turn", _re.IGNORECASE),
]

# Trigger patterns for "at the beginning of your end step"
END_STEP_TRIGGER_PATTERNS = [
    _re.compile(r"at the beginning of (?:your|each player's) end step", _re.IGNORECASE),
    _re.compile(r"at the beginning of (?:your|opponent's|each opponent's) end step", _re.IGNORECASE),
]

# Trigger patterns for "whenever a creature dies" or "whenever [creature] dies"
DEATH_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:a|an|your) (?:creature|permanent) (?:you control )?dies", _re.IGNORECASE),
    _re.compile(r"whenever (?:this|~|this creature) dies", _re.IGNORECASE),
    _re.compile(r"whenever (?:a|an) (.*?) you control dies", _re.IGNORECASE),
    _re.compile(r"whenever (?:a|an) (.*?) dies", _re.IGNORECASE),
    _re.compile(r"whenever (?:a|an) (.*?) is put into a graveyard from the battlefield", _re.IGNORECASE),
]

# Trigger patterns for "whenever you draw a card" / "whenever a player draws a card"
DRAW_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you draw (?:a|an|one) .*?", _re.IGNORECASE),
    _re.compile(r"whenever a player draws (?:a|an|one) .*?", _re.IGNORECASE),
]

# Trigger patterns for "whenever damage is dealt"
DAMAGE_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:a|an|your) (?:creature|player) (?:you control )?deals damage", _re.IGNORECASE),
    _re.compile(r"whenever (?:a|an) (.*?) would deal damage", _re.IGNORECASE),
    _re.compile(r"whenever damage is dealt to (?:a|an)", _re.IGNORECASE),
]

# Trigger patterns for "enters the battlefield" (ETB)
ETB_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:a|an) (.*?) enters the battlefield", _re.IGNORECASE),
    _re.compile(r"when (?:a|an) (.*?) enters the battlefield", _re.IGNORECASE),
    _re.compile(r"whenever this enters the battlefield", _re.IGNORECASE),
]

# Trigger patterns for "leaves the battlefield" (LTB)
LTB_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:a|an) (.*?) leaves the battlefield", _re.IGNORECASE),
    _re.compile(r"when (?:a|an) (.*?) leaves the battlefield", _re.IGNORECASE),
]

# Trigger patterns for "at end of turn"
END_TURN_TRIGGER_PATTERNS = [
    _re.compile(r"at the end of (?:your|each) turn", _re.IGNORECASE),
]

# Trigger patterns for "at the start of combat"
COMBAT_START_TRIGGER_PATTERNS = [
    _re.compile(r"at the beginning of (?:each|your) combat", _re.IGNORECASE),
    _re.compile(r"at the start of (?:each|your) combat", _re.IGNORECASE),
]

# Trigger patterns for "whenever you discard a card" / "whenever a player discards a card"
DISCARD_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you discard (?:a|an|one) .*?", _re.IGNORECASE),
    _re.compile(r"whenever a player discards (?:a|an|one) .*?", _re.IGNORECASE),
]

# Trigger patterns for "whenever a token enters the battlefield" / "whenever you create a token"
TOKEN_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you create .*? token", _re.IGNORECASE),
    _re.compile(r"whenever .*? token enters the battlefield", _re.IGNORECASE),
]

# Trigger patterns for "whenever a counter is put on / removed from"
COUNTER_TRIGGER_PATTERNS = [
    _re.compile(r"whenever a .*? counter is put on (?:a|an) .*? you control", _re.IGNORECASE),
    _re.compile(r"whenever a .*? counter is put on", _re.IGNORECASE),
    _re.compile(r"whenever a counter is removed from", _re.IGNORECASE),
]

# Trigger patterns for landfall
LANDFALL_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you play (?:a|an) land", _re.IGNORECASE),
    _re.compile(r"whenever a land enters the battlefield under your control", _re.IGNORECASE),
    _re.compile(r"landfall", _re.IGNORECASE),
]

# Trigger patterns for "whenever this planeswalker planeswalks" / loyalty abilities
PLANESWALK_TRIGGER_PATTERNS = [
    _re.compile(r"whenever a planeswalker you control planeswalks", _re.IGNORECASE),
    _re.compile(r"whenever this planeswalker planeswalks", _re.IGNORECASE),
]

# Trigger patterns for "whenever a creature is turned face up"
FACE_UP_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:a|an) (.*?) becomes face-up", _re.IGNORECASE),
    _re.compile(r"whenever you turn (?:a|an) (.*?) face-up", _re.IGNORECASE),
]

# MANA-03: Trigger patterns for "whenever you tap lands for mana" / mana production
MANA_PRODUCTION_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you tap (?:a|an) land for mana", _re.IGNORECASE),
    _re.compile(r"whenever a land produces mana", _re.IGNORECASE),
    _re.compile(r"whenever you add mana", _re.IGNORECASE),
    _re.compile(r"whenever a source you control adds mana", _re.IGNORECASE),
    # NOTE: "whenever a player spends mana" is a MANA-SPENT trigger (CR 118.9),
    # NOT a mana-production trigger. It lives in MANA_SPENT_TRIGGER_PATTERNS only.
    # (Removed here to prevent it firing on mana production — MAJOR 5.)
]

# ─── B1: Missing Trigger Categories (Sprint 3) ──────────────────────────────

# Sacrifice triggers — e.g. [[Zulaport Cutthroat]]
# NOTE: "dies" triggers are NOT listed here. A sacrifice is a death, and "dies"
# triggers are owned by the zone-change listener (single owner, CR 704.5d token
# suppression applied there). The sacrifice path emits a zone-change event so
# "dies" triggers fire exactly once. check_sacrifice_triggers() only handles
# "is sacrificed" triggers (which DO fire for tokens — CR 701.19).
SACRIFICE_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:a|an) (.*?) you control is sacrificed", _re.IGNORECASE),
    _re.compile(r"whenever you sacrifice (?:a|an) (.*?)(?:,|\.|\?|$)", _re.IGNORECASE),
    _re.compile(r"whenever a player sacrifices (?:a|an) (.*?)(?:,|\.|\?|$)", _re.IGNORECASE),
]

# Life gain/loss triggers — e.g. [[Karametra's Blessing]], [[Geth's Grimoire]]
LIFE_GAIN_LOST_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you (?:gain|lose) life", _re.IGNORECASE),
    _re.compile(r"whenever a player (?:gains|loses) life", _re.IGNORECASE),
    _re.compile(r"whenever (?:(?:a|an) )?(.*?)(?:,|\.|\?|$) gains life", _re.IGNORECASE),
]

# Fight triggers — e.g. [[Ulvenwald Tracker]]
FIGHT_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:this|~|this creature) fights", _re.IGNORECASE),
    _re.compile(r"whenever a creature you control fights", _re.IGNORECASE),
]

# Proliferated triggers — e.g. [[Flux Channeler]]
PROLIFERATED_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you proliferate", _re.IGNORECASE),
    _re.compile(r"whenever a player proliferates", _re.IGNORECASE),
]

# Transformed triggers — e.g. [[Jace, Vryn's Prodigy]], [[Tovolar's Huntmaster]]
TRANSFORMED_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:this(?:\s+creature)?|~) transforms", _re.IGNORECASE),
    _re.compile(r"whenever a double-faced card you control transforms", _re.IGNORECASE),
]

# Library search/tutor triggers — e.g. [[Psychogenic Probe]]
TUTOR_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you search (?:your|a player's) library", _re.IGNORECASE),
    _re.compile(r"whenever a player searches (?:their|his|her) library", _re.IGNORECASE),
]

# Becomes target triggers — e.g. [[Shiny Impetus]]
BECOMES_TARGET_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:this|~|this creature) becomes the target of a spell or ability", _re.IGNORECASE),
    _re.compile(r"whenever (?:a|an) (.*?) you control becomes the target of a spell", _re.IGNORECASE),
]

# Attached/unattach triggers — e.g. [[Sun Titan]] returning auras
ATTACH_TRIGGER_PATTERNS = [
    _re.compile(r"whenever this becomes attached to another permanent", _re.IGNORECASE),
    _re.compile(r"whenever an aura you control becomes unattached", _re.IGNORECASE),
]

# Day/night change triggers — e.g. [[Tovolar's Huntmaster]]
DAY_NIGHT_CHANGE_TRIGGER_PATTERNS = [
    _re.compile(r"whenever day becomes night", _re.IGNORECASE),
    _re.compile(r"whenever night becomes day", _re.IGNORECASE),
]

# Completed dungeon triggers — e.g. [[Hama Pashar]]
COMPLETED_DUNGEON_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you complete (?:a|an) (.*?)(?:,|\.|\?|$)", _re.IGNORECASE),
    _re.compile(r"whenever a player completes (?:a|an) dungeon", _re.IGNORECASE),
]

# Mana spent triggers — e.g. [[Karametra's Blessing]] for mana value paid
MANA_SPENT_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you spend mana", _re.IGNORECASE),
    _re.compile(r"whenever a player spends mana", _re.IGNORECASE),
]

# Countered triggers (CR 701.5) — e.g. "whenever a spell is countered"
COUNTERED_TRIGGER_PATTERNS = [
    # index 0 — self-referential: "whenever this is countered" / "whenever ~ is countered"
    _re.compile(r"whenever (?:this|~) (?:spell )?is countered", _re.IGNORECASE),
    # index 1 — "you control" filter: "whenever a spell you control is countered"
    _re.compile(r"whenever (?:a|an) spell you control is countered", _re.IGNORECASE),
    # index 2 — general: "whenever a spell is countered" / "whenever a spell <modifier> is countered"
    # NOTE: the modifier ("you control" handled at index 1, or e.g. "your opponent controls")
    # is optional, so the bare "a spell is countered" form matches too.
    _re.compile(r"whenever (?:a|an) spell (?:.*? )?is countered", _re.IGNORECASE),
]

# Investigated triggers (CR 701.32) — e.g. "whenever you investigate"
#
# Pattern-ownership split (7-3 test round 1 fix): token-entering-the-battlefield
# phrasings ("whenever a/an [clue|investigate] token enters...") are deliberately
# NOT in this list — they are matched by the generic token-trigger path
# (TOKEN_TRIGGER_PATTERNS / check_token_triggers, which fires when the 1/1 red
# Goblin "investigate" token enters via _investigate), so each watcher fires
# exactly once. Keeping them here double-queued such watchers (1x "token" +
# 1x "investigated" for the same effect), violating exactly-once (CR 110.6-style
# per-event single firing).
INVESTIGATED_TRIGGER_PATTERNS = [
    # index 0 — "you" filter: "whenever you investigate"
    _re.compile(r"whenever you investigate", _re.IGNORECASE),
    # index 1 — general: "whenever a player investigates"
    _re.compile(r"whenever a player investigates?", _re.IGNORECASE),
]

# Combined trigger dictionary
TRIGGER_PATTERNS = {
    "cast": CAST_TRIGGER_PATTERNS,
    "attack": ATTACK_TRIGGER_PATTERNS,
    "block": BLOCK_TRIGGER_PATTERNS,
    "upkeep": UPKEEP_TRIGGER_PATTERNS,
    "end_step": END_STEP_TRIGGER_PATTERNS,
    "death": DEATH_TRIGGER_PATTERNS,
    "draw": DRAW_TRIGGER_PATTERNS,
    "damage": DAMAGE_TRIGGER_PATTERNS,
    "etb": ETB_TRIGGER_PATTERNS,
    "ltb": LTB_TRIGGER_PATTERNS,
    "end_turn": END_TURN_TRIGGER_PATTERNS,
    "combat_start": COMBAT_START_TRIGGER_PATTERNS,
    "discard": DISCARD_TRIGGER_PATTERNS,
    "token": TOKEN_TRIGGER_PATTERNS,
    "counter": COUNTER_TRIGGER_PATTERNS,
    "landfall": LANDFALL_TRIGGER_PATTERNS,
    "planeswalk": PLANESWALK_TRIGGER_PATTERNS,
    "face_up": FACE_UP_TRIGGER_PATTERNS,
    "mana_production": MANA_PRODUCTION_TRIGGER_PATTERNS,
    # B1: Missing trigger categories (Sprint 3)
    "sacrifice": SACRIFICE_TRIGGER_PATTERNS,
    "life_gain_lost": LIFE_GAIN_LOST_TRIGGER_PATTERNS,
    "fight": FIGHT_TRIGGER_PATTERNS,
    "proliferated": PROLIFERATED_TRIGGER_PATTERNS,
    "transformed": TRANSFORMED_TRIGGER_PATTERNS,
    "tutor": TUTOR_TRIGGER_PATTERNS,
    "becomes_target": BECOMES_TARGET_TRIGGER_PATTERNS,
    "attach": ATTACH_TRIGGER_PATTERNS,
    "day_night_change": DAY_NIGHT_CHANGE_TRIGGER_PATTERNS,
    "completed_dungeon": COMPLETED_DUNGEON_TRIGGER_PATTERNS,
    "mana_spent": MANA_SPENT_TRIGGER_PATTERNS,
    # Sprint 7 P0: Countered (CR 701.5) + Investigated (CR 701.32)
    "countered": COUNTERED_TRIGGER_PATTERNS,
    "investigated": INVESTIGATED_TRIGGER_PATTERNS,
}


def initialize_triggers(game_state: GameState) -> None:
    """
    Register the zone-change listener for trigger detection.
    Call once when a game is created. CR 603.2.
    Guard against duplicate registration (idempotent).
    """
    from mtg_engine.engine.zones import _zone_change_listeners
    if _on_zone_change not in _zone_change_listeners:
        register_zone_change_listener(_on_zone_change)


def _on_zone_change(event: ZoneChangeEvent, game_state: GameState) -> None:
    """
    Inspect zone change event and queue matching triggers from all permanents.
    CR 603.2, CR 603.6: triggered abilities fire automatically when conditions are met.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    for perm in list(game_state.battlefield):
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        
        # Check for Landfall keyword in type_line (inline ability without keyword parsing)
        has_landfall = "landfall" in (card.type_line or "").lower()
        
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            if _matches_zone_change(ab, event, perm, game_state):
                # CR 603.3: "you may" triggers are optional — detect and mark
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="zone_change",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                game_state.pending_triggers.append(trigger)
                logger.debug(
                    "Trigger queued: %r from %s (controller: %s)",
                    ab.trigger_condition, card.name, perm.controller,
                )
        
        # Handle Landfall triggers separately (keyword inline with triggered ability)
        if has_landfall and event.get("to_zone") == "battlefield":
            # Check if the entering card is a land
            entering_card_id = event.get("card_id", "")
            entering_perm = next((p for p in game_state.battlefield if p.id == entering_card_id), None)
            if entering_perm and "land" in entering_perm.card.type_line.lower():
                # Parse the inline triggered ability from oracle text
                oracle = card.oracle_text or ""
                if "landfall" in oracle.lower() and "enters" in oracle.lower():
                    # Extract effect: "put a +1/+1 counter on this creature"
                    import re as _re_lf
                    counter_match = _re_lf.search(r"put a \+1/\+1 counter on (?:this|~)", oracle, _re_lf.IGNORECASE)
                    if counter_match:
                        effect = "put a +1/+1 counter on this creature"
                        trigger = PendingTrigger(
                            id=str(uuid.uuid4()),
                            source_permanent_id=perm.id,
                            controller=perm.controller,
                            trigger_type="zone_change",
                            effect_description=effect,
                            source_card_name=card.name,
                            is_optional=False,
                        )
                        game_state.pending_triggers.append(trigger)
                        logger.debug("Landfall trigger queued from %s", card.name)

    # Death-trigger wiring for Afterlife, Undying, Persist (CR 702.108, 702.51, 702.61)
    # MUST be OUTSIDE the battlefield loop — dying permanent is already removed by this point
    if event.get("to_zone") == "graveyard" and event.get("from_zone") == "battlefield":
        # CR 704.5d: tokens cease to exist when leaving battlefield — no death triggers fire
        if not event.get("is_token", False):
            _queue_death_triggers(event, game_state)


def _queue_death_triggers(event: ZoneChangeEvent, game_state: GameState) -> None:
    """Queue afterlife, undying, persist triggers when a creature dies.

    CR 702.108 (Afterlife), CR 702.51 (Undying), CR 702.61 (Persist).
    These are triggered abilities that fire when the permanent with the keyword
    moves from battlefield to graveyard ("dies").

    Counter guard checks happen here at trigger-queuing time, not during resolution.
    """
    card_name = event.get("card_name", "")
    player = event.get("player", "")
    perm_id = event.get("permanent_id", "") or event.get("card_id", "")
    keywords = [k.lower() for k in (event.get("permanent_keywords") or [])]
    counters = event.get("permanent_counters") or {}
    power_str = event.get("permanent_power", "0")
    toughness_str = event.get("permanent_toughness", "0")
    oracle_text = event.get("oracle_text", "")

    # --- Afterlife (CR 702.108) ---
    if "afterlife" in keywords:
        from mtg_engine.ability.keywords.afterlife import AfterlifeKeyword
        count = AfterlifeKeyword.parse_afterlife_count(oracle_text) or 1
        trigger = AfterlifeKeyword(count=count).create_trigger(
            card=None, controller=player, perm_id=perm_id
        )
        # Store token count for resolution
        from mtg_engine.models.game import PendingTrigger as PT
        if isinstance(trigger, PT):
            trigger.trigger_data = {"count": count}
        game_state.pending_triggers.append(trigger)
        logger.debug("Afterlife %d trigger queued for %s", count, card_name)

    # --- Undying (CR 702.51): only if no +1/+1 counters on dying creature ---
    if "undying" in keywords and counters.get("+1/+1", 0) == 0:
        from mtg_engine.models.game import Card, Permanent
        from mtg_engine.ability.keywords.undying import UndyingKeyword
        dummy_perm = Permanent(
            card=Card(name=card_name, power=str(power_str), toughness=str(toughness_str)),
            controller=player,
            id=perm_id,
            counters=counters,
        )
        kw = UndyingKeyword()
        trigger = kw.create_trigger(game_state, dummy_perm, dummy_perm, to_zone="graveyard")
        if trigger is not None:
            # Store P/T for resolution (source_card on stack may lack these)
            from mtg_engine.models.game import PendingTrigger as PT
            if isinstance(trigger, PT):
                trigger.trigger_data = {"power": str(power_str), "toughness": str(toughness_str)}
            game_state.pending_triggers.append(trigger)
            logger.debug("Undying trigger queued for %s", card_name)

    # --- Persist (CR 702.61): only if no -1/-1 counters on dying creature ---
    if "persist" in keywords and counters.get("-1/-1", 0) == 0:
        from mtg_engine.models.game import Card, Permanent
        from mtg_engine.ability.keywords.persist import PersistKeyword
        dummy_perm = Permanent(
            card=Card(name=card_name), controller=player, id=perm_id, counters=counters
        )
        kw = PersistKeyword()
        trigger = kw.create_trigger(game_state, dummy_perm, dummy_perm, to_zone="graveyard")
        if trigger is not None:
            game_state.pending_triggers.append(trigger)
            logger.debug("Persist trigger queued for %s", card_name)


def _matches_zone_change(
    ability,
    event: ZoneChangeEvent,
    source_perm: Permanent,
    game_state: GameState,
) -> bool:
    """
    Check if a triggered ability's condition matches a zone-change event.
    Simplified pattern matching against common trigger conditions. CR 603.2.
    """
    cond = ability.trigger_condition.lower()
    from_z = event.get("from_zone", "")
    to_z = event.get("to_zone", "")
    event_card_id = event.get("card_id", "")

    # Token triggers (CR 704.5c) are owned by check_token_triggers(), NOT the
    # zone listener. Skip them here to avoid double-firing: the zone listener
    # would otherwise match "whenever a token enters the battlefield" via the
    # generic "enters" branch below. check_token_triggers() is invoked at every
    # token-creation site (stack.py, ability/effects/base.py, ability/loyalty.py).
    for _tp in TOKEN_TRIGGER_PATTERNS:
        if _tp.search(cond):
            return False

    # "when this creature dies" / "whenever a creature dies"
    # "dies" = moves from battlefield to graveyard
    if "dies" in cond or ("graveyard" in cond and from_z == "battlefield"):
        if to_z == "graveyard" and from_z == "battlefield":
            # CR 704.5d: tokens cease to exist when leaving the battlefield —
            # they do not "die", so "dies" triggers do not fire for tokens.
            if event.get("is_token", False):
                return False
            # Self-referential trigger: "when this creature dies"
            if "this" in cond or "enchanted" in cond:
                return event_card_id == source_perm.id
            return True

    # "when [this permanent] enters [the battlefield]" / "whenever a creature enters"
    if "enters" in cond and to_z == "battlefield":
        if "this" in cond or "enchanted" in cond:
            return event_card_id == source_perm.id
        return True

    # "when [this permanent] leaves the battlefield"
    if "leaves the battlefield" in cond and from_z == "battlefield":
        if "this" in cond:
            return event_card_id == source_perm.id
        return True
    
    # "whenever a land you control enters" / landfall triggers
    if "landfall" in cond and "enters" in cond and to_z == "battlefield":
        event_card = next((c for c in game_state.battlefield if c.id == event_card_id), None)
        if event_card and "land" in event_card.card.type_line.lower():
            return True
        return False

    return False


def check_phase_triggers(game_state: GameState) -> GameState:
    """
    Check for "at the beginning of [phase/step]" triggers. CR 603.2b.
    Called at the start of each step (after begin_step).
    REQ-A08: engine automatically detects and queues triggered abilities.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    current_step = game_state.step.value
    current_phase = game_state.phase.value

    # US17 (T042): Also check emblems for phase triggers
    emblem_sources = []
    for emblem in game_state.emblems:
        for ability_text in emblem.abilities:
            # Create a minimal fake Card-like oracle text holder
            emblem_sources.append((emblem.id, emblem.controller, ability_text, emblem.source_planeswalker))

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            if _matches_phase_trigger(cond, current_step, current_phase, perm, game_state):
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="phase_change",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                game_state.pending_triggers.append(trigger)
                logger.debug(
                    "Phase trigger queued: %r from %s", ab.trigger_condition, card.name
                )

    # US17 (T042): Check emblem phase triggers
    for emblem_id, controller, ability_text, source_name in emblem_sources:
        cond_lower = ability_text.lower()
        # Simple phase match for emblems using the same logic
        step_match = False
        if "beginning of your upkeep" in cond_lower and current_step == "upkeep":
            step_match = (controller == game_state.active_player)
        elif "beginning of each upkeep" in cond_lower and current_step == "upkeep":
            step_match = True
        elif "beginning of your end step" in cond_lower and current_step == "end":
            step_match = (controller == game_state.active_player)
        elif "beginning of each end step" in cond_lower and current_step == "end":
            step_match = True
        if step_match:
            trigger = PendingTrigger(
                id=str(uuid.uuid4()),
                source_permanent_id=emblem_id,
                controller=controller,
                trigger_type="phase_change",
                effect_description=ability_text,
                source_card_name=source_name,
            )
            game_state.pending_triggers.append(trigger)
            logger.debug("Emblem phase trigger queued from %s (controller: %s)", source_name, controller)

    return game_state


def _matches_phase_trigger(
    cond: str,
    step: str,
    phase: str,
    source_perm: Permanent,
    game_state: GameState,
) -> bool:
    """
    Match "at the beginning of [step]" triggers. CR 603.2b.
    """
    if "beginning of your upkeep" in cond and step == "upkeep":
        return source_perm.controller == game_state.active_player
    if "beginning of each upkeep" in cond and step == "upkeep":
        return True
    if "beginning of your end step" in cond and step == "end":
        return source_perm.controller == game_state.active_player
    if "beginning of each end step" in cond and step == "end":
        return True
    if "beginning of combat" in cond and step == "beginning_of_combat":
        return True
    return False


def _is_inside_parenthetical(text: str, start: int) -> bool:
    """Return True if position ``start`` in ``text`` is inside a parenthetical.

    Paren depth at ``start`` is the count of ``(`` minus ``)`` over
    ``text[:start]``; depth > 0 means the position is inside parentheses.

    Used to distinguish real self-referential trigger text (top-level, e.g.
    "Whenever this creature deals combat damage to a player, draw a card.")
    from keyword reminder text (inside parentheses, e.g. the Toxic reminder
    "(whenever this creature deals combat damage to a player, ...)"), which
    must not queue a spurious no-op combat_damage trigger.
    """
    depth = 0
    for ch in text[:start]:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
    return depth > 0


def check_damage_triggers(
    game_state: GameState,
    assignments: list,
) -> GameState:
    """
    Check for "whenever this deals combat damage" triggers after damage assignment.
    CR 603.2: triggered abilities use a triggering event.
    Scans permanents for combat-damage trigger patterns and queues PendingTriggers.
    """
    import re as _re
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    # Build set of permanent IDs that dealt damage to a player this assignment
    player_names = {p.name for p in game_state.players}
    damaging_perm_ids: set[str] = set()
    for assign in assignments:
        if assign.target_id in player_names and assign.damage > 0:
            damaging_perm_ids.add(assign.source_id)

    if not damaging_perm_ids:
        return game_state

    # MON-01: Check monarch combat damage transfer for each assignment that hit a player
    from mtg_engine.engine.monarch import check_combat_damage_monarch
    for assign in assignments:
        if assign.target_id not in player_names or assign.damage <= 0:
            continue
        source_perm = None
        for p in game_state.battlefield:
            if p.id == assign.source_id:
                source_perm = p
                break
        if source_perm is None:
            continue
        game_state = check_combat_damage_monarch(
            game_state, assign.target_id, source_perm.controller
        )

    # INT-01: Check initiative combat damage transfer for each assignment that hit a player
    from mtg_engine.engine.initiative import check_combat_damage_initiative
    for assign in assignments:
        if assign.target_id not in player_names or assign.damage <= 0:
            continue
        source_perm = None
        for p in game_state.battlefield:
            if p.id == assign.source_id:
                source_perm = p
                break
        if source_perm is None:
            continue
        game_state = check_combat_damage_initiative(
            game_state, assign.target_id, source_perm.controller
        )

    for perm in game_state.battlefield:
        if perm.id not in damaging_perm_ids:
            continue
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern in DAMAGE_TRIGGER_PATTERNS:
                if pattern.search(cond):
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="damage_dealt",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Damage dealt trigger queued: %r from %s (controller: %s)",
                        ab.trigger_condition, card.name, perm.controller,
                    )
                    break

        # Fallback: direct regex match for "this creature deals combat damage" patterns
        # that may not be parsed correctly by the ability parser.
        #
        # Only TOP-LEVEL matches are real self-referential triggers. Keyword
        # reminder text (e.g. "Toxic 2 (whenever this creature deals combat
        # damage to a player, that player gets 2 poison counters.)") lives inside
        # a parenthetical group and must NOT queue a spurious no-op trigger —
        # those keywords are handled by their dedicated apply_*() paths
        # (e.g. apply_toxic in combat/core.py).
        _COMBAT_DAMAGE_TRIGGER_RE = _re.compile(
            r"whenever (?:this|~|this creature) deals? (?:combat )?damage(?: to a player)?",
            _re.IGNORECASE,
        )
        oracle_text = perm.card.oracle_text or ""
        for _match in _COMBAT_DAMAGE_TRIGGER_RE.finditer(oracle_text):
            if _is_inside_parenthetical(oracle_text, _match.start()):
                continue  # keyword reminder text, not a real trigger
            trigger = PendingTrigger(
                id=str(uuid.uuid4()),
                source_permanent_id=perm.id,
                controller=perm.controller,
                trigger_type="combat_damage",
                effect_description=oracle_text,
                source_card_name=card.name,
            )
            game_state.pending_triggers.append(trigger)
            logger.debug(
                "Combat damage trigger queued from %s (controller: %s)",
                card.name, perm.controller,
            )
            break  # at most one fallback combat_damage trigger per permanent

    return game_state


# ─── B1: Check Functions for Missing Trigger Categories (Sprint 3) ──────────────

def _is_you_pattern(pattern_idx: int) -> bool:
    """Pattern index 0 in each list is the 'you' (self-referential) variant."""
    return pattern_idx == 0


def check_sacrifice_triggers(
    game_state: GameState,
    sacrificed_perms: list[Permanent],
    controller: str,
) -> GameState:
    """Check "is sacrificed" triggers (CR 701.19). Pure transform.

    Args:
        game_state: Current game state. The sacrificed permanents are already
            removed from the battlefield (so they cannot be watched here).
        sacrificed_perms: The Permanent objects that were sacrificed, captured
            BEFORE removal so type_line / controller / is_token are available.
        controller: The player who performed the sacrifice (the "you" for
            "whenever you sacrifice ..." patterns).

    Returns:
        New GameState with matching triggers queued.

    Semantics:
        - "whenever a/an <type> you control is sacrificed": fires if any
          sacrificed permanent is controlled by the watcher AND its type matches.
        - "whenever you sacrifice a/an <type>": fires if the sacrificer is the
          watcher's controller AND a sacrificed permanent's type matches.
        - "whenever a player sacrifices a/an <type>": fires if any sacrificed
          permanent's type matches (any player may be the sacrificer).
        - Self-referential "whenever this <perm> is sacrificed": checked against
          each sacrificed permanent's own oracle text (it is off the battlefield).
        - "dies" triggers are NOT handled here — they fire via the zone-change
          event emitted by the sacrifice path (single owner, with the CR 704.5d
          token suppression applied in the zone listener).
        - "is sacrificed" triggers fire for tokens (sacrifice != death for
          trigger purposes, CR 701.19).
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    def _type_matches(captured: str, type_line: str) -> bool:
        cap = (captured or "").strip()
        if not cap:
            return True
        return cap in (type_line or "").lower()

    # --- Self-referential: "whenever this ... is sacrificed" on the sacrificed
    #     permanent itself (it is off the battlefield, so check its own text). ---
    _self_sac_re = _re.compile(
        r"whenever this (?:creature|permanent|card|land|artifact|planeswalker|enchantment) is sacrificed",
        _re.IGNORECASE,
    )
    for sac in sacrificed_perms:
        abilities = parse_oracle_text(sac.card.oracle_text or "", sac.card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            if _self_sac_re.search(cond):
                is_optional = ab.effect.lower().startswith("you may")
                new_triggers.append(PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=sac.id,
                    controller=sac.controller,
                    trigger_type="sacrifice",
                    effect_description=ab.effect,
                    source_card_name=sac.card.name,
                    is_optional=is_optional,
                ))
                logger.debug("Self sacrifice trigger queued: %r from %s", cond, sac.card.name)
                break

    # --- Battlefield watchers ---
    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern_idx, pattern in enumerate(SACRIFICE_TRIGGER_PATTERNS):
                m = pattern.search(cond)
                if not m:
                    continue
                captured = m.group(1) if m.lastindex and m.lastindex >= 1 else ""
                if pattern_idx == 0:
                    # "whenever a/an <type> you control is sacrificed"
                    if not any(
                        sac.controller == perm.controller
                        and _type_matches(captured, sac.card.type_line)
                        for sac in sacrificed_perms
                    ):
                        continue
                elif pattern_idx == 1:
                    # "whenever you sacrifice a/an <type>"
                    if controller != perm.controller:
                        continue
                    if not any(_type_matches(captured, sac.card.type_line) for sac in sacrificed_perms):
                        continue
                elif pattern_idx == 2:
                    # "whenever a player sacrifices a/an <type>" (any player)
                    if not any(_type_matches(captured, sac.card.type_line) for sac in sacrificed_perms):
                        continue
                else:
                    continue
                is_optional = ab.effect.lower().startswith("you may")
                new_triggers.append(PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="sacrifice",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                ))
                logger.debug("Sacrifice trigger queued: %r from %s", ab.trigger_condition, card.name)
                break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_life_gain_lost_triggers(
    game_state: GameState,
    player_name: str,
    amount: int,
) -> GameState:
    """Check for "whenever you gain/lose life" triggers. Pure transform.

    amount > 0 means life was gained; amount < 0 means life was lost.
    Only matching trigger types fire (gain triggers on gain, lose on loss).
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)
    is_gain = amount > 0

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern_idx, pattern in enumerate(LIFE_GAIN_LOST_TRIGGER_PATTERNS):
                if pattern.search(cond):
                    # TRG-20 Fix 2: "whenever you gain/lose life" only fires for controller
                    if _is_you_pattern(pattern_idx) and perm.controller != player_name:
                        continue
                    # FIX: Distinguish between gain and loss triggers
                    # Only fire "gain life" triggers when amount > 0, and vice versa
                    cond_has_gain = "gain" in cond
                    cond_has_lose = "lose" in cond
                    if is_gain and not cond_has_gain:
                        continue
                    if not is_gain and not cond_has_lose:
                        continue
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="life_gain_lost",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Life gain/lost trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_fight_triggers(
    game_state: GameState,
    fighter_ids: list[str],
) -> GameState:
    """Check for "whenever this creature fights" triggers. Pure transform."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            # "this creature fights" only fires if this perm is a fighter
            is_this_trigger = bool(_re.compile(r"whenever (?:this(?:\s+creature)?|~) fights", _re.IGNORECASE).search(cond))
            if is_this_trigger and perm.id not in fighter_ids:
                continue
            for pattern in FIGHT_TRIGGER_PATTERNS:
                if pattern.search(cond):
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="fight",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Fight trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_proliferated_triggers(
    game_state: GameState,
    player_name: str,
) -> GameState:
    """Check for "whenever you proliferate" triggers. Pure transform."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern_idx, pattern in enumerate(PROLIFERATED_TRIGGER_PATTERNS):
                if pattern.search(cond):
                    # TRG-20 Fix 3: "whenever you proliferate" only fires for controller
                    if _is_you_pattern(pattern_idx) and perm.controller != player_name:
                        continue
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="proliferated",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Proliferated trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_transformed_triggers(
    game_state: GameState,
    transformed_perm_ids: list[str],
) -> GameState:
    """Check for "whenever this transforms" triggers. Pure transform."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            # "this transforms" only fires if this perm is the one that transformed
            is_this_trigger = bool(_re.compile(r"whenever (?:this(?:\s+creature)?|~) transforms", _re.IGNORECASE).search(cond))
            if is_this_trigger and perm.id not in transformed_perm_ids:
                continue
            for pattern in TRANSFORMED_TRIGGER_PATTERNS:
                if pattern.search(cond):
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="transformed",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Transformed trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_tutor_triggers(
    game_state: GameState,
    player_name: str,
) -> GameState:
    """Check for "whenever you search your library" triggers. Pure transform."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern_idx, pattern in enumerate(TUTOR_TRIGGER_PATTERNS):
                if pattern.search(cond):
                    # TRG-20 Fix 5: "whenever you search" only fires for controller
                    if _is_you_pattern(pattern_idx) and perm.controller != player_name:
                        continue
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="tutor",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Tutor trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_becomes_target_triggers(
    game_state: GameState,
    target_perm_id: str,
) -> GameState:
    """Check for "whenever this becomes the target of a spell or ability" triggers. Pure transform.

    Only fires for permanents that are actually targeted (target_perm_id), not all permanents.
    Self-referential abilities ("this creature", "~") only fire if perm.id == target_perm_id.
    Broad abilities ("a creature you control") fire if the targeted permanent matches.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    # Find the targeted permanent for type/controller checks
    target_perm = next((p for p in game_state.battlefield if p.id == target_perm_id), None)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern in BECOMES_TARGET_TRIGGER_PATTERNS:
                if pattern.search(cond):
                    # FIX: Only fire for the targeted permanent or matching broad triggers
                    is_this_trigger = bool(_re.compile(
                        r"whenever (?:this|~)", _re.IGNORECASE
                    ).search(cond))

                    if is_this_trigger and perm.id != target_perm_id:
                        continue

                    # For "a <type> you control becomes the target", check if target matches type
                    is_you_control = bool(_re.compile(
                        r"whenever (?:a|an) .*? you control becomes the target", _re.IGNORECASE
                    ).search(cond))
                    if is_you_control and perm.id != target_perm_id:
                        # Only fire if this perm controls a creature that was targeted
                        if target_perm and target_perm.controller == perm.controller:
                            pass  # OK — controlled permanent was targeted
                        else:
                            continue

                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="becomes_target",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Becomes target trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_attach_triggers(
    game_state: GameState,
    aura_perm_id: str,
    attach_event: str = "attach",
    attached_controller: str | None = None,
) -> GameState:
    """Check attach / unattach triggers. Pure transform.

    Args:
        game_state: Current game state.
        aura_perm_id: ID of the aura/equipment being attached or unattached.
        attach_event: "attach" (default) fires the "whenever this becomes
            attached to another permanent" pattern (index 0) with a
            self-referential "this" guard. "unattach" fires the "whenever an
            aura you control becomes unattached" pattern (index 1) with a
            "you control" filter (the unattached aura must be controlled by the
            watcher). Splitting the two event types prevents an unattach
            trigger from firing when an aura/equipment ATTACHES, and vice-versa.
        attached_controller: Controller of the aura being attached/unattached.
            Required for the "unattach" path because the aura has already left
            the battlefield by call time — a battlefield lookup would return ""
            and the "you control" filter could never match. For "attach" it may
            be omitted (the aura is still on the battlefield) or passed through.

    Returns:
        New GameState with matching triggers queued.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    # Select the single relevant pattern for this event type.
    pattern = ATTACH_TRIGGER_PATTERNS[1] if attach_event == "unattach" else ATTACH_TRIGGER_PATTERNS[0]
    is_this_trigger = attach_event == "attach"

    # Controller of the aura/equipment being attached/unattached (for the
    # "you control" filter on the unattach pattern). For "attach" the aura is
    # still on the battlefield and looked up below; for "unattach" it has left,
    # so the caller passes the controller captured BEFORE removal.
    if attached_controller is not None:
        attached_perm_controller = attached_controller
    else:
        attached_perm = next((p for p in game_state.battlefield if p.id == aura_perm_id), None)
        attached_perm_controller = attached_perm.controller if attached_perm else ""

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        found_trigger = False
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            # TRG-20 Fix 6: "whenever this becomes attached" only fires for the aura being attached
            if is_this_trigger and perm.id != aura_perm_id:
                continue
            if not pattern.search(cond):
                continue
            # "you control" filter for the unattach pattern: the unattached aura
            # must be controlled by the watcher (CR 702.5). Uses the controller
            # captured before the aura left the battlefield (see attached_perm_controller).
            if attach_event == "unattach" and "you control" in cond and attached_perm_controller != perm.controller:
                continue
            is_optional = ab.effect.lower().startswith("you may")
            trigger = PendingTrigger(
                id=str(uuid.uuid4()),
                source_permanent_id=perm.id,
                controller=perm.controller,
                trigger_type="attach",
                effect_description=ab.effect,
                source_card_name=card.name,
                is_optional=is_optional,
            )
            new_triggers.append(trigger)
            logger.debug("Attach trigger queued: %r from %s", ab.trigger_condition, card.name)
            found_trigger = True
            break

        # Fallback: check raw oracle text when the parser can't handle mixed
        # static+triggered abilities (attach pattern only — "whenever this
        # becomes attached" embedded in mixed text).
        if attach_event == "attach" and not found_trigger and card.oracle_text:
            oracle_lower = card.oracle_text.lower()
            if is_this_trigger and perm.id != aura_perm_id:
                continue
            if not pattern.search(oracle_lower):
                continue
            # Extract effect text after the comma/period following "attached"
            effect_match = _re.search(r"whenever this becomes attached[^.]*?,\s*(.+?)(?:\.|$)", oracle_lower)
            effect_text = effect_match.group(1).strip().rstrip(".") if effect_match else card.oracle_text
            trigger = PendingTrigger(
                id=str(uuid.uuid4()),
                source_permanent_id=perm.id,
                controller=perm.controller,
                trigger_type="attach",
                effect_description=effect_text,
                source_card_name=card.name,
                is_optional=False,
            )
            new_triggers.append(trigger)
            logger.debug("Attach trigger queued (oracle fallback): %s", card.name)
            break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_day_night_change_triggers(
    game_state: GameState,
) -> GameState:
    """Check for "whenever day becomes night" / "whenever night becomes day" triggers. Pure transform."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern in DAY_NIGHT_CHANGE_TRIGGER_PATTERNS:
                if pattern.search(cond):
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="day_night_change",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Day/night change trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_completed_dungeon_triggers(
    game_state: GameState,
    player_name: str,
) -> GameState:
    """Check for "whenever you complete a dungeon" triggers. Pure transform."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern_idx, pattern in enumerate(COMPLETED_DUNGEON_TRIGGER_PATTERNS):
                if pattern.search(cond):
                    # TRG-20 Fix 7: "whenever you complete" only fires for controller
                    if _is_you_pattern(pattern_idx) and perm.controller != player_name:
                        continue
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="completed_dungeon",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Completed dungeon trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_mana_spent_triggers(
    game_state: GameState,
    player_name: str,
) -> GameState:
    """Check for "whenever you spend mana" triggers. Pure transform."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern_idx, pattern in enumerate(MANA_SPENT_TRIGGER_PATTERNS):
                if pattern.search(cond):
                    # TRG-20 Fix 8: "whenever you spend mana" only fires for controller
                    if _is_you_pattern(pattern_idx) and perm.controller != player_name:
                        continue
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="mana_spent",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Mana spent trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


# ─── TRG-20 Part B: 5 New Trigger Types ─────────────────────────────────────

def check_draw_triggers(
    game_state: GameState,
    player_name: str,
) -> GameState:
    """Check for 'whenever you draw a card' / 'whenever a player draws a card' triggers. Pure transform."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern_idx, pattern in enumerate(DRAW_TRIGGER_PATTERNS):
                if pattern.search(cond):
                    # Filter "you" patterns by controller — break to skip general fallback
                    if _is_you_pattern(pattern_idx) and perm.controller != player_name:
                        break
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="draw",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Draw trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_discard_triggers(
    game_state: GameState,
    player_name: str,
) -> GameState:
    """Check for 'whenever you discard a card' / 'whenever a player discards a card' triggers. Pure transform."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern_idx, pattern in enumerate(DISCARD_TRIGGER_PATTERNS):
                if pattern.search(cond):
                    # Filter "you" patterns by controller — break to skip general fallback
                    if _is_you_pattern(pattern_idx) and perm.controller != player_name:
                        break
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="discard",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Discard trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_token_triggers(
    game_state: GameState,
    player_name: str,
) -> GameState:
    """Check for 'whenever a token enters the battlefield' / 'whenever you create a token' triggers. Pure transform."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern_idx, pattern in enumerate(TOKEN_TRIGGER_PATTERNS):
                if pattern.search(cond):
                    # Filter "you" patterns by controller — break to skip general fallback
                    if _is_you_pattern(pattern_idx) and perm.controller != player_name:
                        break
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="token",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Token trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_counter_triggers(
    game_state: GameState,
    perm_id: str,
    player_name: str,
    counter_event: str = "placed",
) -> GameState:
    """Check 'whenever a counter is put on' / 'removed from' triggers. Pure transform.

    Args:
        game_state: Current game state.
        perm_id: ID of the permanent a counter was placed/removed on.
        player_name: The player who caused the counter change (for "you" filters).
        counter_event: "placed" (default) fires "counter is put on" patterns
            (indices 0-1); "removed" fires the "counter is removed from"
            pattern (index 2) only. Splitting the two event types prevents a
            "counter is put on" trigger from firing when a counter is removed
            (e.g., Fading upkeep) and vice-versa.

    Returns:
        New GameState with matching triggers queued.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    # Pattern indices to consider, based on the event type.
    candidate_idxs = [2] if counter_event == "removed" else [0, 1]

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()

            # Self-referential "this" guard: "whenever a counter is put on this
            # creature" only fires for the permanent that actually changed.
            if "this" in cond and perm.id != perm_id:
                continue

            for pattern_idx in candidate_idxs:
                pattern = COUNTER_TRIGGER_PATTERNS[pattern_idx]
                if not pattern.search(cond):
                    continue
                # Filter "you" patterns by controller — break to skip general fallback
                if _is_you_pattern(pattern_idx) and perm.controller != player_name:
                    break
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="counter",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                new_triggers.append(trigger)
                logger.debug("Counter trigger queued: %r from %s", ab.trigger_condition, card.name)
                break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_countered_triggers(
    game_state: GameState,
    countered_stack_obj: "StackObject",
) -> GameState:
    """Check "whenever a spell is countered" triggers (CR 701.5). Pure transform.

    Must be called BEFORE the countered spell is removed from the stack so that
    self-referential triggers ("whenever this is countered") can still read the
    source card (Q3: pre-removal capture).

    Args:
        game_state: Current game state.
        countered_stack_obj: The StackObject being countered (still on the stack
            at call time, so its source_card data is readable).

    Returns:
        New GameState with matching triggers queued.

    Semantics (pattern-index → filter, COUNTERED_TRIGGER_PATTERNS):
        - index 0 — self-referential "this"/"~": fires only when the countered
          spell's source card is this permanent's own card (name match, the
          engine's identity model).
        - index 1 — "a spell you control is countered": fires only when the
          watcher controls the countered spell. Note: the "you" variant here is
          at index 1 (not index 0), so it is filtered explicitly rather than via
          _is_you_pattern (which is index-0 keyed).
        - index 2 — general "a spell is countered": fires for any countered spell.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)
    countered_name = countered_stack_obj.source_card.name

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()

            for pattern_idx, pattern in enumerate(COUNTERED_TRIGGER_PATTERNS):
                if not pattern.search(cond):
                    continue
                # CR 701.5 self-referential guard (index 0): "whenever this is
                # countered" fires only for the permanent whose own spell was
                # countered.
                if pattern_idx == 0 and countered_name != card.name:
                    break
                # "you control" filter (index 1): the watcher must control the
                # countered spell.
                if pattern_idx == 1 and perm.controller != countered_stack_obj.controller:
                    break
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="countered",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                new_triggers.append(trigger)
                logger.debug("Countered trigger queued: %r from %s", ab.trigger_condition, card.name)
                break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_investigated_triggers(
    game_state: GameState,
    player_name: str,
) -> GameState:
    """Check "whenever you investigate" triggers (CR 701.32). Pure transform.

    Called after a player performs the investigate action (and after the
    1/1 red Goblin "investigate" token has been created).

    Args:
        game_state: Current game state.
        player_name: The player who just investigated (the "you" for
            "whenever you investigate"; the actor for
            "whenever a player investigates").

    Returns:
        New GameState with matching triggers queued.

    Semantics (pattern-index → filter, INVESTIGATED_TRIGGER_PATTERNS):
        - index 0 — "you" filter: "whenever you investigate" fires only when the
          watcher is the player who just investigated.
        - index 1 — general: "whenever a player investigates" (any player).

    Note: token-entering-the-battlefield phrasings ("whenever a/an
    clue/investigate token enters...") are owned by the generic token-trigger
    path (check_token_triggers), not this function — see the
    INVESTIGATED_TRIGGER_PATTERNS comment for the exactly-once rationale.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()

            for pattern_idx, pattern in enumerate(INVESTIGATED_TRIGGER_PATTERNS):
                if not pattern.search(cond):
                    continue
                # "you" filter (index 0): the watcher must be the investigating
                # player.
                if _is_you_pattern(pattern_idx) and perm.controller != player_name:
                    break
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="investigated",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                new_triggers.append(trigger)
                logger.debug("Investigated trigger queued: %r from %s", ab.trigger_condition, card.name)
                break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def check_planeswalk_triggers(
    game_state: GameState,
    perm_id: str,
    player_name: str,
) -> GameState:
    """Check for 'whenever this planeswalker planeswalks' / loyalty ability triggers. Pure transform."""
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            for pattern_idx, pattern in enumerate(PLANESWALK_TRIGGER_PATTERNS):
                if pattern.search(cond):
                    # "this planeswalker" pattern: self-referential guard — break to skip fallback
                    is_this_trigger = bool(_re.compile(r"whenever this planeswalker", _re.IGNORECASE).search(cond))
                    if is_this_trigger and perm.id != perm_id:
                        break
                    # Filter "you control" patterns by controller — break to skip general fallback
                    if _is_you_pattern(pattern_idx) and perm.controller != player_name:
                        break
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="planeswalk",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug("Planeswalk trigger queued: %r from %s", ab.trigger_condition, card.name)
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


# ─── MANA-03: Mana Production Triggers ────────────────────────────────────────

def check_mana_production_triggers(
    game_state: GameState,
    source_permanent_id: str,
    controller: str,
    mana_symbols: list[str],
) -> GameState:
    """
    Check for "whenever you tap a land for mana" / mana production triggers.
    Called after a land produces mana. Pure transform.

    CR 603.2: triggered abilities fire when mana is produced.

    Args:
        game_state: Current game state.
        source_permanent_id: ID of the permanent that produced mana.
        controller: Controller of the source permanent.
        mana_symbols: List of mana symbols produced (e.g., ["W", "U"]).

    Returns:
        Updated game state with triggers queued.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    new_triggers = list(game_state.pending_triggers)

    for perm in game_state.battlefield:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()

            # Check for mana production triggers
            for pattern in MANA_PRODUCTION_TRIGGER_PATTERNS:
                if pattern.search(cond):
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="mana_production",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    new_triggers.append(trigger)
                    logger.debug(
                        "Mana production trigger queued: %r from %s (controller: %s)",
                        ab.trigger_condition, card.name, perm.controller,
                    )
                    break

    return game_state.model_copy(update={"pending_triggers": new_triggers})


def get_pending_triggers_for_player(
    game_state: GameState, player_name: str
) -> list[PendingTrigger]:
    """Return all pending triggers controlled by player_name. REQ-A09."""
    return [t for t in game_state.pending_triggers if t.controller == player_name]


def apnap_order_triggers(game_state: GameState) -> list[PendingTrigger]:
    """
    Return pending triggers in APNAP order. REQ-S04, CR 603.3b.
    Active player's triggers are placed on the stack first,
    then non-active player's triggers.
    """
    active_triggers = [
        t for t in game_state.pending_triggers
        if t.controller == game_state.active_player
    ]
    other_triggers = [
        t for t in game_state.pending_triggers
        if t.controller != game_state.active_player
    ]
    return active_triggers + other_triggers


def check_cast_triggers(
    game_state: GameState,
    caster: str,
    spell_type_line: str,
    spell_name: str,
) -> GameState:
    """
    Check for "whenever you cast" and "whenever a player casts" triggers.
    Called from cast_spell() in stack.py after placing spell on stack.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    # Check all permanents for cast triggers
    all_permanents = list(game_state.battlefield)

    for perm in all_permanents:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            
            # Check for "whenever you cast" triggers
            if "whenever you cast" in cond:
                # Check if the caster matches the trigger
                if caster in cond or "you" in cond:
                    # Check if the spell type matches
                    if spell_type_line.lower() in cond or spell_name.lower() in cond:
                        is_optional = ab.effect.lower().startswith("you may")
                        trigger = PendingTrigger(
                            id=str(uuid.uuid4()),
                            source_permanent_id=perm.id,
                            controller=perm.controller,
                            trigger_type="cast",
                            effect_description=ab.effect,
                            source_card_name=card.name,
                            is_optional=is_optional,
                        )
                        game_state.pending_triggers.append(trigger)
                        logger.debug(
                            "Cast trigger queued: %r from %s (controller: %s)",
                            ab.trigger_condition, card.name, perm.controller,
                        )
            
            # Check for "whenever a player casts" triggers
            elif "whenever a player casts" in cond:
                # This is a general trigger for any player casting any spell
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="cast",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                game_state.pending_triggers.append(trigger)
                logger.debug(
                    "Cast trigger queued: %r from %s (controller: %s)",
                    ab.trigger_condition, card.name, perm.controller,
                )

    return game_state


def check_attack_triggers(
    game_state: GameState,
    attacker_ids: list[str],
) -> GameState:
    """
    Check for "whenever [creature] attacks" triggers.
    Called from declare_attackers() in combat.py after validation.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    # Check all permanents for attack triggers
    all_permanents = list(game_state.battlefield)
    
    for perm in all_permanents:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            
            # Check for "whenever this creature attacks" triggers
            if "whenever this creature attacks" in cond or "whenever ~ attacks" in cond:
                # Check if this permanent is among the attackers
                if perm.id in attacker_ids:
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="attack",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Attack trigger queued: %r from %s (controller: %s)",
                        ab.trigger_condition, card.name, perm.controller,
                    )
            
            # Check for "whenever a creature attacks" triggers
            elif "whenever a creature attacks" in cond:
                # This is a general trigger for any creature attacking
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="attack",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                game_state.pending_triggers.append(trigger)
                logger.debug(
                    "Attack trigger queued: %r from %s (controller: %s)",
                    ab.trigger_condition, card.name, perm.controller,
                )
            
            # Check for "whenever [creature] attacks" triggers with specific creature names
            elif any(pattern.search(cond) for pattern in ATTACK_TRIGGER_PATTERNS):
                # Check if this permanent is among the attackers
                if perm.id in attacker_ids:
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="attack",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Attack trigger queued: %r from %s (controller: %s)",
                        ab.trigger_condition, card.name, perm.controller,
                    )

    # Handle exalted and battle cry triggers
    if len(attacker_ids) == 1:
        # Exalted: Find all permanents with "exalted" keyword owned by the attacking player
        attacker_id = attacker_ids[0]
        attacker_permanent = next((p for p in all_permanents if p.id == attacker_id), None)
        if attacker_permanent:
            attacker_controller = attacker_permanent.controller
            
            # Check for exalted triggers
            for perm in all_permanents:
                card = perm.card
                # Check if this permanent has "exalted" in its oracle text or keywords
                if "exalted" in (card.oracle_text or "").lower() or "exalted" in (card.keywords or []):
                    # This is an exalted permanent, create a trigger for it
                    is_optional = False  # Exalted triggers are not optional
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="attack",
                        effect_description="Exalted trigger",
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Exalted trigger queued from %s (controller: %s)",
                        card.name, perm.controller,
                    )
    
    # Handle battle cry triggers
    # For each attacker, check if it has battle cry and add triggers for other attackers
    for attacker_id in attacker_ids:
        attacker_permanent = next((p for p in all_permanents if p.id == attacker_id), None)
        if attacker_permanent:
            card = attacker_permanent.card
            # Check if this attacker has "battle cry" in its oracle text or keywords
            if "battle cry" in (card.oracle_text or "").lower() or "battle cry" in (card.keywords or []):
                # This attacker has battle cry, so create triggers for all other attackers
                for other_attacker_id in attacker_ids:
                    if other_attacker_id != attacker_id:
                        # Find the other attacker permanent
                        other_attacker_permanent = next((p for p in all_permanents if p.id == other_attacker_id), None)
                        if other_attacker_permanent:
                            # Create a trigger for the other attacker
                            is_optional = False  # Battle cry triggers are not optional
                            trigger = PendingTrigger(
                                id=str(uuid.uuid4()),
                                source_permanent_id=other_attacker_permanent.id,
                                controller=other_attacker_permanent.controller,
                                trigger_type="attack",
                                effect_description="Battle cry trigger",
                                source_card_name=other_attacker_permanent.card.name,
                                is_optional=is_optional,
                            )
                            game_state.pending_triggers.append(trigger)
                            logger.debug(
                                "Battle cry trigger queued from %s (controller: %s) for %s",
                                card.name, attacker_permanent.controller, other_attacker_permanent.card.name,
                            )

    return game_state


def check_block_triggers(
    game_state: GameState,
    blocker_ids: list[str],
) -> GameState:
    """
    Check for "whenever [creature] blocks" triggers.
    Called from declare_blockers() in combat.py after validation.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    # Check all permanents for block triggers
    all_permanents = list(game_state.battlefield)
    
    for perm in all_permanents:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()
            
            # Check for "whenever this creature blocks" triggers
            if "whenever this creature blocks" in cond or "whenever ~ blocks" in cond:
                # Check if this permanent is among the blockers
                if perm.id in blocker_ids:
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="block",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Block trigger queued: %r from %s (controller: %s)",
                        ab.trigger_condition, card.name, perm.controller,
                    )
            
            # Check for "whenever a creature blocks" triggers
            elif "whenever a creature blocks" in cond:
                # This is a general trigger for any creature blocking
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="block",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                game_state.pending_triggers.append(trigger)
                logger.debug(
                    "Block trigger queued: %r from %s (controller: %s)",
                    ab.trigger_condition, card.name, perm.controller,
                )
            
            # Check for "whenever [creature] blocks" triggers with specific creature names
            elif any(pattern.search(cond) for pattern in BLOCK_TRIGGER_PATTERNS):
                # Check if this permanent is among the blockers
                if perm.id in blocker_ids:
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="block",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Block trigger queued: %r from %s (controller: %s)",
                        ab.trigger_condition, card.name, perm.controller,
                    )

    return game_state


def put_trigger_on_stack(
    game_state: GameState, trigger_id: str, targets: list[str]
) -> GameState:
    """
    Move a pending trigger onto the stack as a StackObject. REQ-A10.
    CR 603.3: triggered abilities go on stack next time a player receives priority.
    """
    from mtg_engine.models.game import StackObject, Card

    trigger = next(
        (t for t in game_state.pending_triggers if t.id == trigger_id), None
    )
    if trigger is None:
        raise ValueError(f"Trigger {trigger_id!r} not found in pending triggers")

    # Find source permanent on battlefield (may have left since trigger fired)
    source_perm = next(
        (p for p in game_state.battlefield if p.id == trigger.source_permanent_id), None
    )
    source_card = (
        source_perm.card
        if source_perm is not None
        else Card(
            name=trigger.source_card_name,
            type_line="",
            id=trigger.source_permanent_id,
        )
    )

    stack_obj = StackObject(
        id=str(uuid.uuid4()),
        source_card=source_card,
        controller=trigger.controller,
        targets=targets,
        effects=[trigger.effect_description],
        trigger_type=trigger.trigger_type,
        trigger_data=getattr(trigger, "trigger_data", {}) or {},
    )
    game_state.stack.append(stack_obj)
    game_state.pending_triggers[:] = [
        t for t in game_state.pending_triggers if t.id != trigger_id
    ]

    logger.info(
        "Trigger from %s placed on stack by %s",
        trigger.source_card_name,
        trigger.controller,
    )
    return game_state


def check_cycle_triggers(
    game_state: GameState,
    card_name: str,
    card_type_line: str,
) -> GameState:
    """
    Check for "whenever you cycle" triggers.
    Called from the cycle endpoint after cycling a card.
    US9: Cycling mechanics with triggered abilities.
    """
    from mtg_engine.card_data.ability_parser import parse_oracle_text, TriggeredAbility

    # Get the cycling player (usually the active player)
    # For now, assume it's the player who just cycled (priority_holder)
    cycler = game_state.priority_holder

    # Check all permanents for cycle triggers
    all_permanents = list(game_state.battlefield)

    for perm in all_permanents:
        card = perm.card
        abilities = parse_oracle_text(card.oracle_text or "", card.type_line)
        for ab in abilities:
            if not isinstance(ab, TriggeredAbility):
                continue
            cond = ab.trigger_condition.lower()

            # Check for "whenever you cycle" triggers
            if "whenever you cycle" in cond:
                # Check if the cycling player matches the trigger controller
                if cycler == perm.controller:
                    is_optional = ab.effect.lower().startswith("you may")
                    trigger = PendingTrigger(
                        id=str(uuid.uuid4()),
                        source_permanent_id=perm.id,
                        controller=perm.controller,
                        trigger_type="cycle",
                        effect_description=ab.effect,
                        source_card_name=card.name,
                        is_optional=is_optional,
                    )
                    game_state.pending_triggers.append(trigger)
                    logger.debug(
                        "Cycle trigger queued: %r from %s (controller: %s)",
                        ab.trigger_condition, card.name, perm.controller,
                    )

            # Check for "whenever a player cycles" triggers
            elif "whenever a player cycles" in cond or "whenever you cycle" in cond:
                is_optional = ab.effect.lower().startswith("you may")
                trigger = PendingTrigger(
                    id=str(uuid.uuid4()),
                    source_permanent_id=perm.id,
                    controller=perm.controller,
                    trigger_type="cycle",
                    effect_description=ab.effect,
                    source_card_name=card.name,
                    is_optional=is_optional,
                )
                game_state.pending_triggers.append(trigger)
                logger.debug(
                    "Cycle trigger queued: %r from %s (controller: %s)",
                    ab.trigger_condition, card.name, perm.controller,
                )

    return game_state
