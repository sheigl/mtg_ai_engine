"""
Rules Q&A generator. REQ-D07, REQ-D08, REQ-D09.
Generates Q&A pairs from actual game events with CR citations.
Triggered by: SBA application, damage assignment, replacement effects,
layer resolution, targeting validation.
"""
import uuid
from typing import Any
from pydantic import BaseModel, Field


class QAPair(BaseModel):
    """REQ-D08 schema."""
    qa_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    answer: str
    game_id: str
    turn: int
    trigger_event: str
    cards_involved: list[str]
    rules_cited: list[str]


# ─── Q&A Templates ────────────────────────────────────────────────────────────
# Each template is a function (context_dict) → QAPair | None
# Context dict contains card names, values, and game state info.
# REQ-D09: questions use real card names from context.

def _qa_lethal_damage(ctx: dict) -> QAPair | None:
    """SBA: creature destroyed by lethal damage (CR 704.5g)."""
    creature = ctx.get("creature_name")
    damage = ctx.get("damage_marked")
    toughness = ctx.get("toughness")
    if not creature:
        return None
    return QAPair(
        question=f"{creature} has {damage} damage marked on it and toughness {toughness}. What happens?",
        answer=f"{creature} is destroyed as a state-based action because the total damage marked on it ({damage}) is greater than or equal to its toughness ({toughness}). This is covered by CR 704.5g.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="lethal_damage_sba",
        cards_involved=[creature],
        rules_cited=["704.5g"],
    )


def _qa_toughness_zero(ctx: dict) -> QAPair | None:
    """SBA: creature with toughness 0 or less (CR 704.5f)."""
    creature = ctx.get("creature_name")
    toughness = ctx.get("toughness")
    if not creature:
        return None
    return QAPair(
        question=f"{creature} has toughness {toughness}. What happens?",
        answer=f"{creature} is put into its owner's graveyard as a state-based action because its toughness is 0 or less. This is covered by CR 704.5f. Note that regeneration cannot replace this event.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="toughness_zero_sba",
        cards_involved=[creature],
        rules_cited=["704.5f"],
    )


def _qa_life_loss(ctx: dict) -> QAPair | None:
    """SBA: player at 0 or less life (CR 704.5a)."""
    player = ctx.get("player_name")
    life = ctx.get("life")
    if not player:
        return None
    return QAPair(
        question=f"{player} is at {life} life. What happens?",
        answer=f"{player} loses the game as a state-based action because their life total is 0 or less. This is covered by CR 704.5a.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="life_loss_sba",
        cards_involved=[],
        rules_cited=["704.5a"],
    )


def _qa_legend_rule(ctx: dict) -> QAPair | None:
    """SBA: legend rule (CR 704.5j)."""
    card = ctx.get("card_name")
    if not card:
        return None
    return QAPair(
        question=f"A player controls two legendary permanents both named {card}. What happens?",
        answer=f"The legend rule applies (CR 704.5j): the player chooses one to keep, and the rest are put into their owners' graveyards as a state-based action.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="legend_rule_sba",
        cards_involved=[card],
        rules_cited=["704.5j"],
    )


def _qa_poison_counters(ctx: dict) -> QAPair | None:
    """SBA: 10+ poison counters (CR 704.5c)."""
    player = ctx.get("player_name")
    count = ctx.get("poison_count")
    if not player:
        return None
    return QAPair(
        question=f"{player} has {count} poison counters. What happens?",
        answer=f"{player} loses the game as a state-based action because they have 10 or more poison counters. This is covered by CR 704.5c.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="poison_sba",
        cards_involved=[],
        rules_cited=["704.5c"],
    )


def _qa_deathtouch(ctx: dict) -> QAPair | None:
    """Deathtouch: any nonzero damage is lethal (CR 702.2b, CR 702.2c)."""
    source = ctx.get("source_name")
    target = ctx.get("target_name")
    damage = ctx.get("damage", 1)
    if not source or not target:
        return None
    return QAPair(
        question=f"{source} (with deathtouch) deals {damage} damage to {target}. Is that lethal?",
        answer=f"Yes. Any nonzero amount of damage from a source with deathtouch is considered lethal for state-based action purposes (CR 702.2c). {target} will be destroyed the next time state-based actions are checked (CR 702.2b, CR 704.5h).",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="deathtouch_damage",
        cards_involved=[source, target],
        rules_cited=["702.2b", "702.2c", "704.5h"],
    )


def _qa_trample(ctx: dict) -> QAPair | None:
    """Trample: excess damage after lethal to blockers (CR 702.19b)."""
    attacker = ctx.get("attacker_name")
    blocker = ctx.get("blocker_name")
    power = ctx.get("power")
    blocker_toughness = ctx.get("blocker_toughness")
    excess = ctx.get("excess_damage")
    if not attacker or not blocker:
        return None
    return QAPair(
        question=f"{attacker} (power {power}, trample) is blocked by {blocker} (toughness {blocker_toughness}). How is combat damage assigned?",
        answer=f"Because {attacker} has trample, its controller must assign at least {blocker_toughness} (lethal) damage to {blocker}. The remaining {excess} damage may be assigned to the defending player (CR 702.19b). The assignment is validated: the player cannot assign damage to the defending player unless all blockers have been assigned lethal damage.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="trample_damage",
        cards_involved=[attacker, blocker],
        rules_cited=["702.19b", "510.1c"],
    )


def _qa_lifelink(ctx: dict) -> QAPair | None:
    """Lifelink: damage dealt causes life gain (CR 702.15b)."""
    source = ctx.get("source_name")
    controller = ctx.get("controller")
    amount = ctx.get("amount")
    if not source or not controller:
        return None
    return QAPair(
        question=f"{source} (with lifelink) deals {amount} damage. What else happens?",
        answer=f"Because {source} has lifelink, its controller ({controller}) gains {amount} life simultaneously with the damage being dealt (CR 702.15b). Lifelink is a static ability that modifies the damage event.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="lifelink_damage",
        cards_involved=[source],
        rules_cited=["702.15b", "510.2"],
    )


def _qa_infect_creature(ctx: dict) -> QAPair | None:
    """Infect: damage to creatures as -1/-1 counters (CR 702.90b)."""
    source = ctx.get("source_name")
    target = ctx.get("target_name")
    amount = ctx.get("amount")
    if not source or not target:
        return None
    return QAPair(
        question=f"{source} (with infect) deals {amount} damage to {target} (a creature). What happens?",
        answer=f"Because {source} has infect, the {amount} damage is dealt to {target} as -1/-1 counters rather than marked damage (CR 702.90b). This means {target} gets {amount} -1/-1 counters instead of {amount} damage marked on it.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="infect_damage_creature",
        cards_involved=[source, target],
        rules_cited=["702.90b", "704.5q"],
    )


def _qa_infect_player(ctx: dict) -> QAPair | None:
    """Infect: damage to players as poison counters (CR 702.90b)."""
    source = ctx.get("source_name")
    player = ctx.get("target_name")
    amount = ctx.get("amount")
    if not source or not player:
        return None
    return QAPair(
        question=f"{source} (with infect) deals {amount} damage to {player} (a player). What happens?",
        answer=f"Because {source} has infect, the damage is dealt to {player} as poison counters rather than life loss (CR 702.90b). {player} gets {amount} poison counters. A player with 10 or more poison counters loses the game (CR 704.5c).",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="infect_damage_player",
        cards_involved=[source],
        rules_cited=["702.90b", "704.5c"],
    )


def _qa_shield_counter(ctx: dict) -> QAPair | None:
    """Shield counter prevents destruction (replacement effect)."""
    creature = ctx.get("creature_name")
    if not creature:
        return None
    return QAPair(
        question=f"{creature} has a shield counter on it and would be destroyed. What happens?",
        answer=f"Instead of being destroyed, a shield counter is removed from {creature}. This is a replacement effect — the destruction event is replaced by the counter removal. If {creature} has multiple shield counters, only one is removed per destruction event.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="shield_counter_replacement",
        cards_involved=[creature],
        rules_cited=["614.1a", "616.1"],
    )


def _qa_aura_illegal(ctx: dict) -> QAPair | None:
    """Aura not attached to legal permanent (CR 704.5m)."""
    aura = ctx.get("aura_name")
    if not aura:
        return None
    return QAPair(
        question=f"{aura} is an Aura that is no longer attached to a legal permanent. What happens?",
        answer=f"{aura} is put into its owner's graveyard as a state-based action (CR 704.5m). An Aura that becomes unattached (because its enchanted permanent left the battlefield) is placed in the graveyard.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="aura_illegal_sba",
        cards_involved=[aura],
        rules_cited=["704.5m"],
    )


def _qa_equipment_detach(ctx: dict) -> QAPair | None:
    """Equipment attached to illegal permanent (CR 704.5n)."""
    equipment = ctx.get("equipment_name")
    if not equipment:
        return None
    return QAPair(
        question=f"{equipment} is attached to a permanent that is no longer a creature. What happens?",
        answer=f"{equipment} becomes unattached as a state-based action (CR 704.5n). Unlike Auras, Equipment that becomes detached remains on the battlefield — it simply stops being attached.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="equipment_detach_sba",
        cards_involved=[equipment],
        rules_cited=["704.5n"],
    )


def _qa_counter_annihilation(ctx: dict) -> QAPair | None:
    """Counter annihilation: +1/+1 and -1/-1 counters (CR 704.5q, REQ-R14)."""
    creature = ctx.get("creature_name")
    plus = ctx.get("plus_count")
    minus = ctx.get("minus_count")
    if not creature:
        return None
    return QAPair(
        question=f"{creature} has {plus} +1/+1 counter(s) and {minus} -1/-1 counter(s) on it. What happens?",
        answer=f"As a state-based action, {min(plus, minus)} of each type of counter are removed simultaneously (CR 704.5q). {plus} +1/+1 and {minus} -1/-1 counters result in {abs(plus-minus)} {'+1/+1' if plus > minus else '-1/-1'} counter(s) remaining.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="counter_annihilation_sba",
        cards_involved=[creature],
        rules_cited=["704.5q"],
    )


def _qa_planeswalker_loyalty_zero(ctx: dict) -> QAPair | None:
    """Planeswalker at 0 loyalty (CR 704.5i)."""
    pw = ctx.get("card_name")
    if not pw:
        return None
    return QAPair(
        question=f"{pw} (a planeswalker) has 0 loyalty counters. What happens?",
        answer=f"{pw} is put into its owner's graveyard as a state-based action because it has 0 loyalty (CR 704.5i). This happens before any player receives priority.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="planeswalker_loyalty_zero_sba",
        cards_involved=[pw],
        rules_cited=["704.5i"],
    )


def _qa_token_non_battlefield(ctx: dict) -> QAPair | None:
    """Token in non-battlefield zone (CR 704.5d)."""
    token = ctx.get("token_name", "a token")
    zone = ctx.get("zone", "graveyard")
    return QAPair(
        question=f"A token ({token}) is put into the {zone}. What happens?",
        answer=f"The token ceases to exist as a state-based action (CR 704.5d). Tokens that are in any zone other than the battlefield immediately cease to exist — they do not remain in the {zone}.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="token_non_battlefield_sba",
        cards_involved=[token],
        rules_cited=["704.5d"],
    )


def _qa_split_second(ctx: dict) -> QAPair | None:
    """Split second prevents responses (CR 702.61b)."""
    spell = ctx.get("spell_name")
    if not spell:
        return None
    return QAPair(
        question=f"{spell} has split second and is on the stack. Can any player cast spells or activate non-mana abilities?",
        answer=f"No. While {spell} is on the stack, players cannot cast spells or activate non-mana abilities (CR 702.61b). Triggered abilities still trigger and go on the stack normally — split second only prevents new spells and non-mana activated abilities.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="split_second",
        cards_involved=[spell],
        rules_cited=["702.61b"],
    )


def _qa_flying_blocking(ctx: dict) -> QAPair | None:
    """Flying: can only be blocked by flying or reach (CR 702.9b)."""
    attacker = ctx.get("attacker_name")
    if not attacker:
        return None
    return QAPair(
        question=f"{attacker} has flying and is attacking. Which creatures can block it?",
        answer=f"Only creatures with flying or reach can block {attacker} (CR 702.9b). Creatures without either keyword cannot be declared as blockers for a creature with flying.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="flying_blocking",
        cards_involved=[attacker],
        rules_cited=["702.9b"],
    )


def _qa_summoning_sickness(ctx: dict) -> QAPair | None:
    """Summoning sickness: creature can't attack first turn (CR 302.6)."""
    creature = ctx.get("creature_name")
    if not creature:
        return None
    return QAPair(
        question=f"{creature} just entered the battlefield. Can it attack this turn?",
        answer=f"No, unless {creature} has haste (CR 702.10a). A creature is affected by summoning sickness if it has not been under its controller's control continuously since the beginning of that player's most recent turn (CR 302.6). It cannot attack or use activated abilities that include the tap symbol.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="summoning_sickness",
        cards_involved=[creature],
        rules_cited=["302.6", "702.10a"],
    )


def _qa_layer_system(ctx: dict) -> QAPair | None:
    """Layer system: continuous effects applied in order (CR 613.1)."""
    card1 = ctx.get("card1_name")
    card2 = ctx.get("card2_name")
    if not card1 or not card2:
        return None
    return QAPair(
        question=f"Both {card1} and {card2} have continuous effects that affect creatures. In what order are they applied?",
        answer=f"Continuous effects are applied in layer order (CR 613.1): Layer 1 (copy), Layer 2 (control), Layer 3 (text), Layer 4 (type), Layer 5 (color), Layer 6 (ability), Layer 7 (power/toughness: 7a CDA, 7b set, 7c modify, 7d switch). Within a layer, effects are applied in timestamp order (CR 613.7) unless a dependency exists (CR 613.8).",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="layer_interaction",
        cards_involved=[card1, card2],
        rules_cited=["613.1", "613.7", "613.8"],
    )


def _qa_apnap_triggers(ctx: dict) -> QAPair | None:
    """APNAP ordering for simultaneous triggers (CR 603.3b)."""
    return QAPair(
        question="Multiple triggered abilities trigger simultaneously. In what order do they go on the stack?",
        answer="When multiple triggered abilities trigger at the same time, they are put on the stack in APNAP (Active Player, Non-Active Player) order: first the active player puts all of their triggers on the stack in the order they choose, then the non-active player does the same (CR 603.3b). Because the stack is LIFO, the non-active player's triggers resolve first.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="apnap_triggers",
        cards_involved=[],
        rules_cited=["603.3b", "101.4"],
    )


def _qa_dies_trigger(ctx: dict) -> QAPair | None:
    """'When this creature dies' trigger (CR 603.6c)."""
    creature = ctx.get("creature_name")
    if not creature:
        return None
    return QAPair(
        question=f"{creature} has an ability that says 'When {creature} dies, ...'. {creature} is destroyed. When does this ability trigger?",
        answer=f"The ability triggers when {creature} moves from the battlefield to the graveyard (CR 603.6c). It is placed on the stack the next time a player would receive priority, after state-based actions have been checked.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="dies_trigger",
        cards_involved=[creature],
        rules_cited=["603.6c", "603.3", "704.3"],
    )


def _qa_first_strike(ctx: dict) -> QAPair | None:
    """First strike: two combat damage steps (CR 510.4)."""
    creature = ctx.get("creature_name")
    if not creature:
        return None
    return QAPair(
        question=f"{creature} has first strike and is in combat. How does the combat damage step work?",
        answer=f"Because {creature} has first strike, there are two combat damage steps (CR 510.4). In the first step, only creatures with first strike or double strike deal damage. State-based actions are checked, then a second damage step occurs where creatures without first strike deal damage. Creatures with double strike deal damage in both steps.",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="first_strike_damage",
        cards_involved=[creature],
        rules_cited=["510.4", "702.7a", "702.4a"],
    )


def _qa_replacement_multiple(ctx: dict) -> QAPair | None:
    """Multiple replacement effects (CR 616.1)."""
    return QAPair(
        question="Two replacement effects both apply to the same event. Who chooses which applies first?",
        answer="The controller of the affected object (or the affected player) chooses which replacement effect to apply first (CR 616.1). Self-replacement effects must be chosen before others (CR 616.1a). After the chosen effect is applied, the process repeats with remaining applicable effects (CR 616.1f).",
        game_id=ctx["game_id"],
        turn=ctx["turn"],
        trigger_event="multiple_replacement_effects",
        cards_involved=[],
        rules_cited=["616.1", "616.1a", "616.1f"],
    )


# ─── Template registry ────────────────────────────────────────────────────────

TEMPLATES = [
    _qa_lethal_damage,
    _qa_toughness_zero,
    _qa_life_loss,
    _qa_legend_rule,
    _qa_poison_counters,
    _qa_deathtouch,
    _qa_trample,
    _qa_lifelink,
    _qa_infect_creature,
    _qa_infect_player,
    _qa_shield_counter,
    _qa_aura_illegal,
    _qa_equipment_detach,
    _qa_counter_annihilation,
    _qa_planeswalker_loyalty_zero,
    _qa_token_non_battlefield,
    _qa_split_second,
    _qa_flying_blocking,
    _qa_summoning_sickness,
    _qa_layer_system,
    _qa_apnap_triggers,
    _qa_dies_trigger,
    _qa_first_strike,
    _qa_replacement_multiple,
]


class RulesQARecorder:
    """Per-game Q&A store. Generates Q&A pairs from game events."""

    def __init__(self, game_id: str) -> None:
        self.game_id = game_id
        self._pairs: list[QAPair] = []

    def _base_ctx(self, turn: int) -> dict:
        return {"game_id": self.game_id, "turn": turn}

    def on_sba(self, sba_type: str, turn: int, **kwargs: Any) -> None:
        """Generate Q&A when an SBA fires. REQ-D07."""
        ctx = {**self._base_ctx(turn), **kwargs}
        template_map = {
            "lethal_damage":        _qa_lethal_damage,
            "toughness_zero":       _qa_toughness_zero,
            "life_loss":            _qa_life_loss,
            "legend_rule":          _qa_legend_rule,
            "poison":               _qa_poison_counters,
            "deathtouch":           _qa_deathtouch,
            "planeswalker_loyalty": _qa_planeswalker_loyalty_zero,
            "aura_illegal":         _qa_aura_illegal,
            "equipment_detach":     _qa_equipment_detach,
            "counter_annihilation": _qa_counter_annihilation,
        }
        fn = template_map.get(sba_type)
        if fn:
            qa = fn(ctx)
            if qa:
                self._pairs.append(qa)

    def on_damage(self, source_name: str, source_keywords: list[str], target_name: str, amount: int, turn: int) -> None:
        """Generate Q&A for notable damage events."""
        ctx = {**self._base_ctx(turn), "source_name": source_name, "target_name": target_name, "amount": amount}
        if "deathtouch" in source_keywords:
            qa = _qa_deathtouch({**ctx, "damage": amount})
            if qa:
                self._pairs.append(qa)
        if "lifelink" in source_keywords:
            qa = _qa_lifelink({**ctx, "controller": "controller"})
            if qa:
                self._pairs.append(qa)
        if "infect" in source_keywords:
            # Determine if target is a creature name or player name
            qa = _qa_infect_creature(ctx)
            if qa:
                self._pairs.append(qa)

    def on_trample(self, attacker_name: str, blocker_name: str, power: int, blocker_toughness: int, excess: int, turn: int) -> None:
        ctx = {**self._base_ctx(turn), "attacker_name": attacker_name, "blocker_name": blocker_name, "power": power, "blocker_toughness": blocker_toughness, "excess_damage": excess}
        qa = _qa_trample(ctx)
        if qa:
            self._pairs.append(qa)

    def on_layer_interaction(self, card1: str, card2: str, turn: int) -> None:
        ctx = {**self._base_ctx(turn), "card1_name": card1, "card2_name": card2}
        qa = _qa_layer_system(ctx)
        if qa:
            self._pairs.append(qa)

    def on_replacement(self, creature_name: str, turn: int, replacement_type: str = "shield_counter") -> None:
        if replacement_type == "shield_counter":
            qa = _qa_shield_counter({**self._base_ctx(turn), "creature_name": creature_name})
            if qa:
                self._pairs.append(qa)

    def get_all(self) -> list[QAPair]:
        return list(self._pairs)

    def to_json(self) -> list[dict]:
        return [p.model_dump() for p in self._pairs]
