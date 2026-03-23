"""
Layer system for continuous effects. REQ-R02, REQ-R03, REQ-R04.
CR 613: applied in layer order 1–7, timestamp within layer, dependency override.
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from mtg_engine.models.game import Card, GameState, Permanent

logger = logging.getLogger(__name__)


class EffectLayer(int, Enum):
    COPY         = 1
    CONTROL      = 2
    TEXT         = 3
    TYPE         = 4
    COLOR        = 5
    ABILITY      = 6
    PT           = 7


class PTSublayer(str, Enum):
    A = "7a"   # CDA sets P/T
    B = "7b"   # Set P/T to specific value
    C = "7c"   # Modify P/T (+/-)
    D = "7d"   # Switch P/T


@dataclass
class ContinuousEffect:
    """A single continuous effect from a permanent or spell."""
    source_id: str            # permanent ID that generates this effect
    layer: EffectLayer
    sublayer: PTSublayer | None
    timestamp: float
    is_cda: bool              # characteristic-defining ability (CR 613.3)
    description: str

    # The actual effect function: (game_state, permanent) → None
    # Modifies permanent in place
    apply_fn: Callable[[GameState, Permanent], None] = field(repr=False, default=lambda gs, p: None)

    # Which permanents this applies to: None = all applicable, or list of IDs
    affected_ids: list[str] | None = None


def _get_effects_for_layer(
    effects: list[ContinuousEffect], layer: EffectLayer, sublayer: PTSublayer | None = None
) -> list[ContinuousEffect]:
    return [e for e in effects if e.layer == layer and e.sublayer == sublayer]


def _sort_by_timestamp(effects: list[ContinuousEffect]) -> list[ContinuousEffect]:
    """CR 613.7: apply in timestamp order."""
    return sorted(effects, key=lambda e: e.timestamp)


def _apply_with_dependency(
    effects: list[ContinuousEffect],
    game_state: GameState,
    targets: list[Permanent],
) -> None:
    """
    Apply effects in timestamp order, with dependency override. CR 613.8.

    An effect B depends on effect A if:
    - They're in the same layer
    - Applying A changes what B applies to or what B does
    - Neither is a CDA or both are CDAs

    Simplified implementation: apply CDAs first (CR 613.3), then rest in timestamp order.
    Full dependency graph is approximated — for the Humility+Opalescence case the
    timestamp order naturally produces the correct result since Humility (layer 6,
    removes abilities) wins over Opalescence's ability-granting effect in layer 6.
    """
    # CDAs first (CR 613.3, 613.4a)
    cdas = _sort_by_timestamp([e for e in effects if e.is_cda])
    non_cdas = _sort_by_timestamp([e for e in effects if not e.is_cda])
    ordered = cdas + non_cdas

    for effect in ordered:
        applicable = targets if effect.affected_ids is None else [
            p for p in targets if p.id in effect.affected_ids
        ]
        for perm in applicable:
            try:
                effect.apply_fn(game_state, perm)
            except Exception as exc:
                logger.warning("Effect %s failed on %s: %s", effect.description, perm.card.name, exc)


def collect_continuous_effects(game_state: GameState) -> list[ContinuousEffect]:
    """
    Gather all active continuous effects from permanents on the battlefield.
    Each permanent with a static ability generates a ContinuousEffect for the relevant layer(s).
    CR 613: layers 1–7 in order.
    """
    import re as _re

    effects: list[ContinuousEffect] = []

    # ── Layer 1: Copy effects ──────────────────────────────────────────────────
    # US5: When a permanent has copy_of_permanent_id set, copy copiable values from source.
    for perm in game_state.battlefield:
        if perm.copy_of_permanent_id is not None:
            source = next(
                (p for p in game_state.battlefield if p.id == perm.copy_of_permanent_id), None
            )
            if source is not None:
                def _make_copy_fn(src: Permanent):
                    def _apply_copy(gs: GameState, target: Permanent) -> None:
                        # Copiable values: name, mana_cost, type_line, oracle_text,
                        # power, toughness, colors, keywords (CR 706.2)
                        target.card = target.card.model_copy(update={
                            "name": src.card.name,
                            "mana_cost": src.card.mana_cost,
                            "type_line": src.card.type_line,
                            "oracle_text": src.card.oracle_text,
                            "power": src.card.power,
                            "toughness": src.card.toughness,
                            "colors": list(src.card.colors),
                            "keywords": list(src.card.keywords),
                        })
                    return _apply_copy
                effects.append(ContinuousEffect(
                    source_id=perm.id,
                    layer=EffectLayer.COPY,
                    sublayer=None,
                    timestamp=perm.timestamp,
                    is_cda=False,
                    description=f"{perm.card.name}: copy of {source.card.name}",
                    apply_fn=_make_copy_fn(source),
                    affected_ids=[perm.id],
                ))

    # ── Layer 3: Text-change effects ───────────────────────────────────────────
    # Scaffold only — text-change effects (e.g. Magical Hack) are not pattern-matched here.
    # The layer is applied in apply_continuous_effects layer order.

    for perm in game_state.battlefield:
        card = perm.card
        oracle = (card.oracle_text or "").lower()

        # ── Layer 2: Control-change effects ───────────────────────────────────
        # US5: Aura with "you control enchanted creature" (e.g. Control Magic)
        if perm.attached_to and (
            "you control enchanted creature" in oracle
            or "gain control of enchanted" in oracle
        ):
            attached_id = perm.attached_to
            def _make_control_fn(new_controller: str):
                def _change_control(gs: GameState, target: Permanent) -> None:
                    target.controller = new_controller
                return _change_control
            effects.append(ContinuousEffect(
                source_id=perm.id,
                layer=EffectLayer.CONTROL,
                sublayer=None,
                timestamp=perm.timestamp,
                is_cda=False,
                description=f"{card.name}: control of enchanted creature → {perm.controller}",
                apply_fn=_make_control_fn(perm.controller),
                affected_ids=[attached_id],
            ))

        # ── Layer 4: Type-change effects ───────────────────────────────────────
        # US5: "is [a/an] X in addition to", "becomes a [type]", "is all types"
        type_addition = _re.search(
            r"is (?:a|an) (\w+) in addition to",
            oracle,
        )
        if type_addition:
            added_type = type_addition.group(1).capitalize()
            def _make_type_adder(new_type: str):
                def _add_type(gs: GameState, target: Permanent) -> None:
                    if new_type.lower() not in target.card.type_line.lower():
                        target.card = target.card.model_copy(
                            update={"type_line": target.card.type_line + f" — {new_type}"}
                            if "—" in target.card.type_line
                            else {"type_line": target.card.type_line + f" {new_type}"}
                        )
                return _add_type
            effects.append(ContinuousEffect(
                source_id=perm.id,
                layer=EffectLayer.TYPE,
                sublayer=None,
                timestamp=perm.timestamp,
                is_cda=False,
                description=f"{card.name}: is {added_type} in addition",
                apply_fn=_make_type_adder(added_type),
            ))

        # ── Layer 5: Color-change effects ──────────────────────────────────────
        # US5: "is [color]", "is all colors", "is colorless"
        if "is all colors" in oracle:
            def _make_all_colors():
                def _set_all_colors(gs: GameState, target: Permanent) -> None:
                    target.card = target.card.model_copy(
                        update={"colors": ["W", "U", "B", "R", "G"]}
                    )
                return _set_all_colors
            effects.append(ContinuousEffect(
                source_id=perm.id,
                layer=EffectLayer.COLOR,
                sublayer=None,
                timestamp=perm.timestamp,
                is_cda=False,
                description=f"{card.name}: is all colors",
                apply_fn=_make_all_colors(),
            ))
        elif "is colorless" in oracle:
            def _make_colorless():
                def _set_colorless(gs: GameState, target: Permanent) -> None:
                    target.card = target.card.model_copy(update={"colors": []})
                return _set_colorless
            effects.append(ContinuousEffect(
                source_id=perm.id,
                layer=EffectLayer.COLOR,
                sublayer=None,
                timestamp=perm.timestamp,
                is_cda=False,
                description=f"{card.name}: is colorless",
                apply_fn=_make_colorless(),
            ))
        else:
            # Single color override (e.g. "enchanted creature is red")
            _COLOR_SET_RE = _re.search(
                r"(?:enchanted creature|it) is (white|blue|black|red|green)",
                oracle,
            )
            if _COLOR_SET_RE:
                _color_name_map = {
                    "white": "W", "blue": "U", "black": "B", "red": "R", "green": "G"
                }
                color_abbrev = _color_name_map[_COLOR_SET_RE.group(1)]
                def _make_color_setter(color: str, src_id: str):
                    def _set_color(gs: GameState, target: Permanent) -> None:
                        target.card = target.card.model_copy(update={"colors": [color]})
                    return _set_color
                effects.append(ContinuousEffect(
                    source_id=perm.id,
                    layer=EffectLayer.COLOR,
                    sublayer=None,
                    timestamp=perm.timestamp,
                    is_cda=False,
                    description=f"{card.name}: enchanted creature is {_COLOR_SET_RE.group(1)}",
                    apply_fn=_make_color_setter(color_abbrev, perm.id),
                    affected_ids=[perm.attached_to] if perm.attached_to else None,
                ))

        # ── Layer 6: Ability removal — Humility pattern ─────────────────────
        # "creatures lose all abilities" or "creatures lose all abilities and are 1/1"
        if "lose all abilities" in oracle or "loses all abilities" in oracle:
            # This removes abilities from all creatures (layer 6)
            def _make_ability_remover(source_perm: Permanent):
                def _remove_abilities(gs: GameState, target: Permanent) -> None:
                    if "creature" in target.card.type_line.lower() and target.id != source_perm.id:
                        # Mark keywords as cleared
                        target.card = target.card.model_copy(update={"keywords": [], "oracle_text": ""})
                return _remove_abilities
            effects.append(ContinuousEffect(
                source_id=perm.id,
                layer=EffectLayer.ABILITY,
                sublayer=None,
                timestamp=perm.timestamp,
                is_cda=False,
                description=f"{card.name}: creatures lose all abilities",
                apply_fn=_make_ability_remover(perm),
            ))

        # Layer 7b: "creatures are 1/1" (Humility) or similar static P/T setters
        # Match patterns like: "creatures are 1/1", "and are 1/1", "creatures become 1/1"
        pt_set = _re.search(r"(?:creatures?(?: you control)? (?:are|become)|(?:and (?:are|become))) (\d+)/(\d+)", oracle)
        if pt_set:
            pw, pt = pt_set.group(1), pt_set.group(2)
            def _make_pt_setter(p_val: str, t_val: str, src_id: str):
                def _set_pt(gs: GameState, target: Permanent) -> None:
                    if "creature" in target.card.type_line.lower():
                        target.card = target.card.model_copy(update={
                            "power": p_val, "toughness": t_val
                        })
                return _set_pt
            effects.append(ContinuousEffect(
                source_id=perm.id,
                layer=EffectLayer.PT,
                sublayer=PTSublayer.B,
                timestamp=perm.timestamp,
                is_cda=False,
                description=f"{card.name}: creatures are {pw}/{pt}",
                apply_fn=_make_pt_setter(pw, pt, perm.id),
            ))

        # Aura continuous effects — only apply if this enchantment is attached to something
        if perm.attached_to and "enchant" in oracle:
            attached_id = perm.attached_to

            # Layer 7c: "enchanted creature gets +X/+Y"
            boost = _re.search(r"enchanted creature gets? \+(\d+)/\+(\d+)", oracle)
            if boost:
                dp, dt = int(boost.group(1)), int(boost.group(2))
                def _make_aura_boost(dp: int, dt: int):
                    def _apply(gs: GameState, target: Permanent) -> None:
                        try:
                            p = int(target.card.power or "0") + dp
                            t = int(target.card.toughness or "0") + dt
                            target.card = target.card.model_copy(update={"power": str(p), "toughness": str(t)})
                        except (ValueError, TypeError):
                            pass
                    return _apply
                effects.append(ContinuousEffect(
                    source_id=perm.id,
                    layer=EffectLayer.PT,
                    sublayer=PTSublayer.C,
                    timestamp=perm.timestamp,
                    is_cda=False,
                    description=f"{card.name}: +{dp}/+{dt} to enchanted creature",
                    apply_fn=_make_aura_boost(dp, dt),
                    affected_ids=[attached_id],
                ))

            # Layer 6: "enchanted creature has/gets/gains [keyword(s)]"
            _KEYWORDS = (
                "trample", "flying", "first strike", "double strike", "deathtouch",
                "lifelink", "vigilance", "reach", "haste", "indestructible",
                "hexproof", "menace", "ward", "prowess", "flash",
            )
            kw_section = _re.search(
                r"enchanted creature (?:has|gets?|gains?)\s+(.+?)(?:\.|$)", oracle
            )
            if kw_section:
                kw_text = kw_section.group(1)
                for kw in _KEYWORDS:
                    if kw in kw_text:
                        def _make_kw_grant(keyword: str):
                            def _apply(gs: GameState, target: Permanent) -> None:
                                if keyword not in target.card.keywords:
                                    target.card = target.card.model_copy(
                                        update={"keywords": list(target.card.keywords) + [keyword]}
                                    )
                            return _apply
                        effects.append(ContinuousEffect(
                            source_id=perm.id,
                            layer=EffectLayer.ABILITY,
                            sublayer=None,
                            timestamp=perm.timestamp,
                            is_cda=False,
                            description=f"{card.name}: grants {kw} to enchanted creature",
                            apply_fn=_make_kw_grant(kw),
                            affected_ids=[attached_id],
                        ))

        # Layer 7c: Counter modifications (+1/+1, -1/-1) — applied as modifications
        # The P/T modification from counters is applied here in layer 7c
        plus_counters = perm.counters.get("+1/+1", 0)
        minus_counters = perm.counters.get("-1/-1", 0)
        if plus_counters or minus_counters:
            net = plus_counters - minus_counters
            def _make_counter_modifier(n: int, src_id: str):
                def _modify_pt(gs: GameState, target: Permanent) -> None:
                    if target.id == src_id:
                        try:
                            p = int(target.card.power or "0") + n
                            t = int(target.card.toughness or "0") + n
                            target.card = target.card.model_copy(update={
                                "power": str(p), "toughness": str(t)
                            })
                        except (ValueError, TypeError):
                            pass
                return _modify_pt
            effects.append(ContinuousEffect(
                source_id=perm.id,
                layer=EffectLayer.PT,
                sublayer=PTSublayer.C,
                timestamp=perm.timestamp,
                is_cda=False,
                description=f"{card.name}: {net:+d}/{net:+d} from counters",
                apply_fn=_make_counter_modifier(net, perm.id),
                affected_ids=[perm.id],
            ))

    return effects


def apply_continuous_effects(game_state: GameState) -> GameState:
    """
    Apply all continuous effects to all permanents in layer order. REQ-R02.

    IMPORTANT: This operates on a snapshot of the battlefield.
    The actual game state permanents are mutated via the apply_fn closures.

    CR 613: layers 1 → 2 → 3 → 4 → 5 → 6 → 7a → 7b → 7c → 7d
    """
    effects = collect_continuous_effects(game_state)
    targets = list(game_state.battlefield)

    layer_order = [
        (EffectLayer.COPY,    None),
        (EffectLayer.CONTROL, None),
        (EffectLayer.TEXT,    None),
        (EffectLayer.TYPE,    None),
        (EffectLayer.COLOR,   None),
        (EffectLayer.ABILITY, None),
        (EffectLayer.PT,      PTSublayer.A),
        (EffectLayer.PT,      PTSublayer.B),
        (EffectLayer.PT,      PTSublayer.C),
        (EffectLayer.PT,      PTSublayer.D),
    ]

    for layer, sublayer in layer_order:
        layer_effects = _get_effects_for_layer(effects, layer, sublayer)
        if layer_effects:
            _apply_with_dependency(layer_effects, game_state, targets)

    return game_state


def get_effective_power_toughness(perm: Permanent) -> tuple[int, int]:
    """
    Compute effective P/T for a permanent, accounting for counters.
    Used by SBA and combat damage checks.
    """
    try:
        p = int(perm.card.power or "0")
    except (ValueError, TypeError):
        p = 0
    try:
        t = int(perm.card.toughness or "0")
    except (ValueError, TypeError):
        t = 0
    p += perm.counters.get("+1/+1", 0) - perm.counters.get("-1/-1", 0)
    t += perm.counters.get("+1/+1", 0) - perm.counters.get("-1/-1", 0)
    return p, t
