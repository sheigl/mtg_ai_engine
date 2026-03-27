"""Competitive heuristic AI player — no LLM calls, pure score-based evaluation."""
import re
from typing import Callable

from .models import AIMemory, AiPersonalityProfile, PlayerConfig

_MANA_ADD_RE = re.compile(r'Add\s+\{')
_PUMP_RE = re.compile(r'target creature gets \+\d+/\+\d+', re.IGNORECASE)
_COMBAT_STEPS = {"declare_attackers", "declare_blockers", "first_strike_damage", "combat_damage", "end_of_combat"}
_DESTROY_RE = re.compile(r'destroy target|exile target', re.IGNORECASE)
_DAMAGE_TO_TARGET_RE = re.compile(r'deals?\s+(\d+)\s+damage\s+to\s+(?:any\s+target|target\s+creature|target\s+player\s+or\s+planeswalker)', re.IGNORECASE)
_AURA_BOOST_RE = re.compile(r'enchanted creature gets \+(\d+)/\+(\d+)', re.IGNORECASE)
_CONTROL_RE = re.compile(r'gain control of target', re.IGNORECASE)
_LIFE_LOSS_RE = re.compile(r'target player loses \d+ life|target opponent loses \d+ life', re.IGNORECASE)
_DRAW_RE = re.compile(r'draw (\d+) card|draw a card', re.IGNORECASE)
_RAMP_RE = re.compile(r'search your library for.*?land|put.*?land.*?onto the battlefield', re.IGNORECASE)
_WIPE_RE = re.compile(r'destroy all creatures|exile all creatures|all creatures get -\d+/-\d+', re.IGNORECASE)
_SACRIFICE_COST_RE = re.compile(r'sacrifice a|sacrifice an', re.IGNORECASE)
_SCRY_RE = re.compile(r'^scry (\d+)', re.IGNORECASE)
_SURVEIL_RE = re.compile(r'^surveil (\d+)', re.IGNORECASE)
_GRAVEYARD_SYNERGY_KW = {"flashback", "escape", "unearth", "disturb", "jump-start"}
_TOKEN_RE = re.compile(r'create.*?token|put.*?token.*?onto the battlefield', re.IGNORECASE)
_FIGHT_RE = re.compile(r'target creature you control fights target creature|each deals damage equal to its power', re.IGNORECASE)
_TUTOR_RE = re.compile(r'search your library for (?:a |an |any )?(\w+(?:\s\w+)?)\s*(?:card|spell)', re.IGNORECASE)
_ANIMATE_RE = re.compile(r'becomes? a (\d+)/(\d+) creature|animate target', re.IGNORECASE)
_GOAD_RE = re.compile(r'\bgoad\b', re.IGNORECASE)
_FOG_RE = re.compile(r'prevent all combat damage|no creatures can block', re.IGNORECASE)
_COUNTER_RE = re.compile(r'counter target spell|counter target.*?spell', re.IGNORECASE)
_BOUNCE_RE = re.compile(r'return target.*?to its owner.*?hand|return target permanent.*?hand', re.IGNORECASE)
_LIFEGAIN_RE = re.compile(r'you gain (\d+) life|gain (\d+) life', re.IGNORECASE)
_CONNIVE_RE = re.compile(r'connive', re.IGNORECASE)
_EXPLORE_RE = re.compile(r'explore', re.IGNORECASE)
_MUTATE_RE = re.compile(r'mutate', re.IGNORECASE)
_REMOVE_COMBAT_RE = re.compile(r'tap target attacking|remove target blocking|target creature loses all abilities until end of combat', re.IGNORECASE)
_DELAYED_DRAW_RE = re.compile(r'at the beginning of (?:your )?next (?:upkeep|draw step).*draw (\d+) card|draw a card', re.IGNORECASE)
_DELAYED_DAMAGE_RE = re.compile(r'at the beginning of (?:your )?next (?:upkeep).*deals?\s+(\d+)\s+damage', re.IGNORECASE)
_ARTIFACT_REMOVAL_RE = re.compile(r'destroy target artifact|exile target artifact|destroy target enchantment|exile target enchantment', re.IGNORECASE)
# ETB / dies trigger patterns (US12, T042)
_ETB_DRAW_RE = re.compile(r'when.*enters.*draw (\d+) card|when.*enters.*draw a card', re.IGNORECASE)
_ETB_DAMAGE_RE = re.compile(r'when.*enters.*deals?\s+(\d+)\s+damage', re.IGNORECASE)
_ETB_TOKEN_RE = re.compile(r'when.*enters.*create.*token', re.IGNORECASE)
_DIES_VALUE_RE = re.compile(r'when.*dies.*draw|when.*dies.*create.*token', re.IGNORECASE)


def _perm_power(perm: dict) -> int:
    try:
        base = int(perm.get("card", {}).get("power") or 0)
    except (ValueError, TypeError):
        base = 0
    base += perm.get("power_bonus", 0)
    counters = perm.get("counters", {})
    base += counters.get("+1/+1", 0) - counters.get("-1/-1", 0)
    return max(0, base)


def _perm_toughness(perm: dict) -> int:
    try:
        base = int(perm.get("card", {}).get("toughness") or 0)
    except (ValueError, TypeError):
        base = 0
    base += perm.get("toughness_bonus", 0)
    counters = perm.get("counters", {})
    base += counters.get("+1/+1", 0) - counters.get("-1/-1", 0)
    return max(0, base)


def _cmc_str(mana_cost: str) -> int:
    if not mana_cost:
        return 0
    total = 0
    for sym in re.findall(r'\{([^}]+)\}', mana_cost):
        if sym.isdigit():
            total += int(sym)
        elif sym in ('W', 'U', 'B', 'R', 'G', 'C'):
            total += 1
    return total


def _card_has_kw(card: dict, keyword: str) -> bool:
    """Check keyword on a raw card dict (keywords list or oracle text)."""
    kw_lower = keyword.lower()
    for kw in (card.get("keywords") or []):
        if kw.lower() == kw_lower:
            return True
    return kw_lower in (card.get("oracle_text") or "").lower()


def _can_block(blocker: dict, attacker: dict) -> bool:
    """
    Return True if the blocker can legally block the attacker.
    Handles flying (requires flying or reach to block), menace (requires 2+ blockers —
    not checked here; menace is handled at gang-block tier), and shadow (ignored for now).
    """
    att_card = attacker.get("card", {})
    blk_card = blocker.get("card", {})
    # Flying: can only be blocked by flying or reach
    if _card_has_kw(att_card, "flying"):
        if not (_card_has_kw(blk_card, "flying") or _card_has_kw(blk_card, "reach")):
            return False
    return True


def _classify_block(blocker: dict, attacker: dict):
    """
    Classify a proposed block outcome. (US36, T101)
    SAFE: blocker kills attacker AND blocker survives.
    TRADE: mutual lethal.
    CHUMP: only blocker dies.
    """
    from .models import BlockClassification
    blk_power = _perm_power(blocker)
    blk_toughness = _perm_toughness(blocker)
    att_power = _perm_power(attacker)
    att_toughness = _perm_toughness(attacker)

    blk_card = blocker.get("card", {})
    att_card = attacker.get("card", {})
    blk_deathtouch = _card_has_kw(blk_card, "deathtouch")
    att_deathtouch = _card_has_kw(att_card, "deathtouch")

    # Lethal calculations
    blocker_kills_attacker = blk_power >= att_toughness or blk_deathtouch
    attacker_kills_blocker = att_power >= blk_toughness or att_deathtouch

    if blocker_kills_attacker and not attacker_kills_blocker:
        return BlockClassification.SAFE
    elif blocker_kills_attacker and attacker_kills_blocker:
        return BlockClassification.TRADE
    else:
        return BlockClassification.CHUMP


def compute_block_declarations(action: dict, game_state: dict) -> list[dict]:
    """
    Compute optimal block declarations for the declare_blockers step.
    Returns a list of {blocker_id, attacker_id} dicts to send to the engine.
    Works for any player type — heuristic or LLM.
    """
    all_perms = game_state.get("battlefield", [])
    my_name = game_state.get("priority_player", "")
    opp_name = next(
        (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name),
        "",
    )

    incoming_attackers = [
        p for p in all_perms
        if p.get("controller") == opp_name
        and p.get("tapped")
        and "creature" in (p.get("card", {}).get("type_line") or "").lower()
    ]
    if not incoming_attackers:
        return []

    available_blocker_ids = set(action.get("valid_targets", []))
    available_blockers = [p for p in all_perms if p.get("id") in available_blocker_ids]
    if not available_blockers:
        return []

    my_life = next(
        (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") == my_name),
        20,
    )
    total_incoming = sum(_perm_power(a) for a in incoming_attackers)
    must_survive = total_incoming >= my_life

    declarations = []
    used_blocker_ids: set[str] = set()

    for att in sorted(incoming_attackers, key=_perm_power, reverse=True):
        att_toughness = _perm_toughness(att)
        att_cmc = _cmc_str(att.get("card", {}).get("mana_cost") or "")

        # Legal blockers for this attacker (evasion filter)
        legal_blockers = [
            blk for blk in available_blockers
            if blk.get("id") not in used_blocker_ids and _can_block(blk, att)
        ]

        best_blocker = None
        best_value = -999.0

        from .models import BlockClassification
        for blk in legal_blockers:
            blk_cmc = _cmc_str(blk.get("card", {}).get("mana_cost") or "")
            classification = _classify_block(blk, att)

            if classification == BlockClassification.SAFE:
                block_value = att_cmc * 2.0  # SAFE: highest priority
            elif classification == BlockClassification.TRADE:
                block_value = att_cmc - blk_cmc  # TRADE: positive if we trade up
            else:
                # CHUMP: only assign when must_survive
                block_value = -blk_cmc if must_survive else -999.0

            if block_value > best_value:
                best_value = block_value
                best_blocker = blk

        if best_blocker is not None and (best_value >= 0 or must_survive):
            declarations.append({
                "blocker_id": best_blocker.get("id"),
                "attacker_id": att.get("id"),
            })
            used_blocker_ids.add(best_blocker.get("id"))
        elif best_blocker is None or best_value < 0:
            # ── Gang block tier (Forge: makeGangBlocks) ───────────────────
            # Try 2-blocker combos: two smaller creatures that together kill the attacker.
            # Only commit if the attacker is worth more than both blockers combined.
            gang_found = False
            candidates = [
                blk for blk in legal_blockers
                if blk.get("id") not in used_blocker_ids
            ]
            for i in range(len(candidates)):
                if gang_found:
                    break
                for j in range(i + 1, len(candidates)):
                    blk1, blk2 = candidates[i], candidates[j]
                    combined_power = _perm_power(blk1) + _perm_power(blk2)
                    if combined_power >= att_toughness:
                        blk1_cmc = _cmc_str(blk1.get("card", {}).get("mana_cost") or "")
                        blk2_cmc = _cmc_str(blk2.get("card", {}).get("mana_cost") or "")
                        # Gang-block when attacker CMC > sum of both blockers (trade up),
                        # OR when lethal is incoming and we must survive.
                        if att_cmc >= blk1_cmc + blk2_cmc or must_survive:
                            declarations.append({"blocker_id": blk1.get("id"), "attacker_id": att.get("id")})
                            declarations.append({"blocker_id": blk2.get("id"), "attacker_id": att.get("id")})
                            used_blocker_ids.add(blk1.get("id"))
                            used_blocker_ids.add(blk2.get("id"))
                            gang_found = True
                            break

    return declarations


class HeuristicPlayer:
    """
    Score-based MTG player. Evaluates every legal action using board state,
    life totals, and combat math, then selects the highest-scoring action.
    Duck-type peer of AIPlayer — same interface, no external calls.
    """

    def __init__(self, config: PlayerConfig) -> None:
        self._config = config
        self._profile: AiPersonalityProfile = getattr(
            config, "personality", AiPersonalityProfile.DEFAULT  # type: ignore[attr-defined]
        )
        self._memory: AIMemory | None = None
        # Mutable attribute set by GameLoop when --debug is active (mirroring AIPlayer).
        # HeuristicPlayer does not call it — no LLM prompt/response to stream.
        self._debug_callback: Callable[[str, str, str], None] | None = None

    # ------------------------------------------------------------------
    # Public interface (matches AIPlayer.decide signature)
    # ------------------------------------------------------------------

    def decide(
        self,
        prompt: str,  # noqa: ARG002 — prompt is ignored; we use structured data
        legal_actions: list[dict] | None = None,
        game_state: dict | None = None,
        memory: "AIMemory | None" = None,
    ) -> tuple[int, str]:
        """
        Return (action_index, reasoning).
        Scores all legal actions; returns the highest-scoring index.
        Never raises — returns (0, fallback) on any error.
        """
        if not legal_actions:
            return 0, "Heuristic: no actions available (pass)"

        # Update per-decision memory reference so scoring methods can access it
        if memory is not None:
            self._memory = memory

        gs = game_state or {}
        my_name = gs.get("priority_player", self._config.name)

        # Lazy-initialize lookahead simulator (US14, T049)
        if not hasattr(self, "_lookahead") or self._lookahead is None:
            from .lookahead import LookaheadSimulator
            self._lookahead = LookaheadSimulator(self)

        # Compute baseline board position for delta scoring (US16, T053)
        before_position = self._score_board_position(gs, my_name)

        best_idx = 0
        best_score = -1e9
        best_desc = "pass"

        for i, action in enumerate(legal_actions):
            try:
                score = self._score_action(action, gs, my_name)
                # Add lookahead bonus for land/cast actions (US14, T049)
                if action.get("action_type") in ("play_land", "cast") and score > -100.0:
                    score += self._lookahead.evaluate_bonus(action, gs, memory)
                    # Board-position delta modifier (US16, T053)
                    simulated = self._lookahead._apply_action_to_state(action, gs)
                    after_position = self._score_board_position(simulated, my_name)
                    delta = min(15.0, max(-15.0, (after_position - before_position) * 0.2))
                    score += delta
            except Exception:  # pragma: no cover — defensive catch
                score = 0.0
            if score > best_score:
                best_score = score
                best_idx = i
                best_desc = action.get("description", action.get("action_type", "?"))

        return best_idx, f"Heuristic: {best_desc} (score={best_score:.1f})"

    # ------------------------------------------------------------------
    # Board position evaluation (US16, T052-T053)
    # ------------------------------------------------------------------

    def _score_board_position(self, game_state: dict, player_name: str) -> float:
        """
        Compute a holistic board position score for the given player.
        FR-048: sum(CMC friendly perms) + hand×5 + life×0.5 - sum(CMC opp perms) - opp_hand×5
        """
        my_info = self._extract_my_info(game_state, player_name)
        my_hand_size = len(my_info.get("hand", []))
        my_life = my_info.get("life", 20)

        my_perm_cmc = sum(
            _cmc_str(p.get("card", {}).get("mana_cost") or "")
            for p in game_state.get("battlefield", [])
            if p.get("controller") == player_name
        )

        opp_info = next(
            (p for p in game_state.get("players", []) if p.get("name") != player_name), {}
        )
        opp_name = opp_info.get("name", "")
        opp_hand_size = len(opp_info.get("hand", []))
        opp_perm_cmc = sum(
            _cmc_str(p.get("card", {}).get("mana_cost") or "")
            for p in game_state.get("battlefield", [])
            if p.get("controller") == opp_name
        )

        return (my_perm_cmc + my_hand_size * 5 + my_life * 0.5
                - opp_perm_cmc - opp_hand_size * 5)

    # ------------------------------------------------------------------
    # State extraction helpers (T005, T006)
    # ------------------------------------------------------------------

    def _extract_my_info(self, game_state: dict, my_name: str) -> dict:
        """Return the priority player's PlayerState dict."""
        for p in game_state.get("players", []):
            if p.get("name") == my_name:
                return p
        return {}

    def _extract_battlefield(self, game_state: dict, controller: str) -> list[dict]:
        """Return all permanents controlled by the given player."""
        return [
            p for p in game_state.get("battlefield", [])
            if p.get("controller") == controller
        ]

    # ------------------------------------------------------------------
    # Mana cost helpers (T007)
    # ------------------------------------------------------------------

    def _cmc(self, mana_cost: str) -> int:
        """Parse a mana cost string like '{2}{G}{G}' into its converted mana cost."""
        if not mana_cost:
            return 0
        total = 0
        for sym in re.findall(r'\{([^}]+)\}', mana_cost):
            if sym.isdigit():
                total += int(sym)
            elif sym in ('W', 'U', 'B', 'R', 'G', 'C'):
                total += 1
            # X, S, hybrid etc. → 0 (conservative)
        return total

    # ------------------------------------------------------------------
    # Keyword helper (T008)
    # ------------------------------------------------------------------

    def _has_keyword(self, card: dict, keyword: str) -> bool:
        """Return True if the card has the given keyword (by list or oracle text)."""
        kw_lower = keyword.lower()
        for kw in (card.get("keywords") or []):
            if kw.lower() == kw_lower:
                return True
        oracle = (card.get("oracle_text") or "").lower()
        return kw_lower in oracle

    # ------------------------------------------------------------------
    # Permanent stat helpers
    # ------------------------------------------------------------------

    def _perm_power(self, perm: dict) -> int:
        return _perm_power(perm)

    def _perm_toughness(self, perm: dict) -> int:
        return _perm_toughness(perm)

    # ------------------------------------------------------------------
    # Action scoring dispatcher (T009)
    # ------------------------------------------------------------------

    def _score_action(self, action: dict, game_state: dict, my_name: str) -> float:
        """Assign a numeric score to a single legal action. Higher = better."""
        action_type = action.get("action_type", "pass")

        if action_type == "pass":
            # Apply penalty when holding a fog or trick to incentivize waiting
            if self._memory:
                if self._memory.chosen_fog_effect:
                    return -5.0  # hold fog — slightly prefer pass over random cast
                if self._memory.trick_attackers and self._has_combat_trick_in_hand(game_state, my_name):
                    return -5.0  # hold trick — prefer casting it over passing
            return 0.0

        if action_type == "play_land":
            return self._score_play_land(action, game_state, my_name)

        if action_type == "cast":
            return self._score_cast(action, game_state, my_name)

        if action_type == "cascade_choice":
            # Score the cascade card using normal cast scoring
            return self._score_cast(action, game_state, my_name)

        if action_type == "activate_loyalty":
            return self._score_loyalty_ability(action, game_state, my_name)

        if action_type == "declare_mulligan":
            return self._score_mulligan(action, game_state, my_name)

        if action_type == "assign_combat_damage":
            # Always assign damage when available — never pass through this step
            return 500.0

        if action_type == "put_trigger":
            return 30.0

        if action_type == "declare_attackers":
            return self._score_declare_attackers(action, game_state, my_name)

        if action_type == "declare_blockers":
            return self._score_declare_blockers(action, game_state, my_name)

        if action_type == "activate":
            # Mana activations are pre-handled by auto_tap — deprioritise them here
            if _MANA_ADD_RE.search(action.get("description", "")):
                return -1.0
            # Equipment activation
            desc = action.get("description", "").lower()
            if "equip" in desc:
                valid_targets = action.get("valid_targets", [])
                best = self._select_equip_target(valid_targets, game_state, my_name)
                if best:
                    action["equip_target"] = best
                    if self._memory:
                        self._memory.attached_this_turn.add(action.get("permanent_id", ""))
                return 25.0
            return 20.0

        if action_type == "copy_spell":
            # Copy spell: 90% of the value of the copied spell (US34, T098)
            copied_action = dict(action)
            copied_action["action_type"] = "cast"
            try:
                copied_score = self._score_cast(copied_action, game_state, my_name)
            except Exception:
                copied_score = 10.0
            return copied_score * 0.9

        if action_type == "choice":
            # Scry/surveil choice: score the revealed card and set selection (US8, T033)
            choice_subtype = action.get("choice_subtype", "")
            revealed_card = action.get("revealed_card", {})
            turn = game_state.get("turn", 1)
            if choice_subtype == "scry":
                selection = self._score_scry_choice(revealed_card, turn)
                action["selection"] = selection
                return 5.0
            elif choice_subtype == "surveil":
                selection = self._score_surveil_choice(revealed_card, turn)
                action["selection"] = selection
                return 5.0
            return 5.0

        # Unknown action type — prefer over passing
        return 5.0

    # ------------------------------------------------------------------
    # Land scoring (T024)
    # ------------------------------------------------------------------

    def _score_play_land(self, action: dict, game_state: dict, my_name: str) -> float:
        my_lands = [
            p for p in self._extract_battlefield(game_state, my_name)
            if "land" in (p.get("card", {}).get("type_line") or "").lower()
        ]
        # Personality: hold land for main2 if profile requests and we haven't cast anything
        # Check step: if step is MAIN and active_player == my_name and phase = PRECOMBAT_MAIN
        if self._profile.hold_land_drop_for_main2_if_unused:
            step = self._current_step(game_state)
            phase = game_state.get("phase", "")
            if step == "main" and phase == "precombat_main":
                return 30.0  # reduced score to deprioritize early land drop
        # First land is critical for mana development
        return 80.0 if len(my_lands) == 0 else 50.0

    # ------------------------------------------------------------------
    # Spell scoring (T016, T017)
    # ------------------------------------------------------------------

    def _is_combat_trick(self, card: dict) -> bool:
        """Return True if the card is an instant that pumps a target creature."""
        type_line = (card.get("type_line") or "").lower()
        if "instant" not in type_line:
            return False
        oracle = card.get("oracle_text") or ""
        return bool(_PUMP_RE.search(oracle))

    def _current_step(self, game_state: dict) -> str:
        return (game_state.get("step") or "").lower()

    def _has_attackable_creatures(self, game_state: dict, my_name: str) -> bool:
        """Return True if the player has creatures that can attack this turn."""
        return any(
            p for p in self._extract_battlefield(game_state, my_name)
            if "creature" in (p.get("card", {}).get("type_line") or "").lower()
            and not p.get("tapped")
            and not p.get("summoning_sick")
        )

    def _has_combat_trick_in_hand(self, game_state: dict, my_name: str) -> bool:
        """Return True if the player has an instant pump spell in hand."""
        my_info = self._extract_my_info(game_state, my_name)
        return any(
            self._is_combat_trick(c)
            for c in my_info.get("hand", [])
        )

    def _should_hold_for_combat(self, game_state: dict, my_name: str) -> bool:
        """Return True when we should hold up mana for an instant-speed response."""
        step = self._current_step(game_state)
        phase = (game_state.get("phase") or "").lower()
        active_player = game_state.get("active_player", game_state.get("priority_player", ""))
        is_active = active_player == my_name
        in_main = "main" in phase and step not in _COMBAT_STEPS
        return in_main and is_active and self._has_combat_trick_in_hand(game_state, my_name)

    def _has_any_creatures(self, game_state: dict, my_name: str) -> bool:
        """Return True if the player controls any creature on the battlefield."""
        return any(
            p for p in self._extract_battlefield(game_state, my_name)
            if "creature" in (p.get("card", {}).get("type_line") or "").lower()
        )

    # ------------------------------------------------------------------
    # Target selection (US1, T010-T012)
    # ------------------------------------------------------------------

    def _select_best_target(
        self,
        valid_targets: list[str],
        game_state: dict,
        effect_type: str,
        my_name: str,
    ) -> str | None:
        """
        Given a list of valid target IDs (permanents or player names), return
        the best single target ID for the given effect type.

        effect_type values: "removal", "burn", "aura", "control", "lifedrain"
        """
        if not valid_targets:
            return None

        all_perms = game_state.get("battlefield", [])
        perm_map = {p.get("id"): p for p in all_perms}
        opp_name = next(
            (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name),
            "",
        )
        opp_life = next(
            (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") == opp_name),
            20,
        )

        if effect_type == "removal":
            # Highest-CMC opponent creature (or planeswalker)
            opp_perms = [
                perm_map[tid] for tid in valid_targets
                if tid in perm_map and perm_map[tid].get("controller") == opp_name
            ]
            if not opp_perms:
                return None
            return max(
                opp_perms,
                key=lambda p: _cmc_str(p.get("card", {}).get("mana_cost") or ""),
            ).get("id")

        elif effect_type == "burn":
            # Lethal face damage first, then highest-toughness creature we can kill,
            # then face damage if nothing else
            my_burn = 0  # caller will re-compute; we return best target
            # Try opponent player — face burn if we can deal lethal
            # (caller computes damage amount; we just rank targets by priority)
            opp_creatures = [
                perm_map[tid] for tid in valid_targets
                if tid in perm_map
                and perm_map[tid].get("controller") == opp_name
                and "creature" in (perm_map[tid].get("card", {}).get("type_line") or "").lower()
            ]
            # Prefer opponent's face if they're a valid target
            if opp_name in valid_targets:
                return opp_name  # face damage is usually highest priority
            if opp_creatures:
                return min(opp_creatures, key=lambda p: _perm_toughness(p)).get("id")
            return valid_targets[0]

        elif effect_type == "aura":
            # Highest-power friendly creature
            my_creatures = [
                perm_map[tid] for tid in valid_targets
                if tid in perm_map and perm_map[tid].get("controller") == my_name
                and "creature" in (perm_map[tid].get("card", {}).get("type_line") or "").lower()
            ]
            if not my_creatures:
                return None
            return max(my_creatures, key=_perm_power).get("id")

        elif effect_type == "control":
            # Highest-CMC opponent permanent
            opp_perms = [
                perm_map[tid] for tid in valid_targets
                if tid in perm_map and perm_map[tid].get("controller") == opp_name
            ]
            if not opp_perms:
                return None
            return max(
                opp_perms,
                key=lambda p: _cmc_str(p.get("card", {}).get("mana_cost") or ""),
            ).get("id")

        elif effect_type == "lifedrain":
            # Target opponent player
            if opp_name in valid_targets:
                return opp_name
            return valid_targets[0]

        return valid_targets[0]

    # ------------------------------------------------------------------
    # Non-creature spell sub-scoring (T017-T019, T024-T025, many more)
    # ------------------------------------------------------------------

    def _score_draw_spell(self, oracle: str) -> float:
        """Score draw effects: +15 per card drawn."""
        m = _DRAW_RE.search(oracle)
        if not m:
            # "draw a card" with no number → 1
            if "draw a card" in oracle.lower():
                return 15.0
            return 0.0
        try:
            n = int(m.group(1))
        except (IndexError, TypeError, ValueError):
            n = 1
        return n * 15.0

    def _score_ramp_spell(self, card: dict, game_state: dict, my_name: str) -> float:
        """Score land-fetch ramp spells. +20 per turn of acceleration."""
        oracle = card.get("oracle_text") or ""
        my_lands = len([
            p for p in self._extract_battlefield(game_state, my_name)
            if "land" in (p.get("card", {}).get("type_line") or "").lower()
        ])
        turn_now = game_state.get("turn", 1)
        # Rough estimate: how many turns ahead does this ramp put us?
        turns_ahead = 1
        if "two basic land" in oracle.lower() or "two lands" in oracle.lower():
            turns_ahead = 2
        # Value diminishes in late game
        land_value = max(0, 6 - my_lands)
        return turns_ahead * 20.0 * (land_value / 6.0 + 0.5)

    def _score_board_wipe(self, game_state: dict, my_name: str) -> float:
        """Score board wipes: positive when net CMC destroyed favors the AI."""
        all_perms = game_state.get("battlefield", [])
        opp_name = next(
            (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
        )

        def _cmc_if_not_indestructible(perm: dict) -> int:
            card = perm.get("card", {})
            if _card_has_kw(card, "indestructible"):
                return 0
            return _cmc_str(card.get("mana_cost") or "")

        my_cmc_lost = sum(
            _cmc_if_not_indestructible(p) for p in all_perms
            if p.get("controller") == my_name
            and "creature" in (p.get("card", {}).get("type_line") or "").lower()
        )
        opp_cmc_destroyed = sum(
            _cmc_if_not_indestructible(p) for p in all_perms
            if p.get("controller") == opp_name
            and "creature" in (p.get("card", {}).get("type_line") or "").lower()
        )

        if my_cmc_lost >= opp_cmc_destroyed:
            return -20.0  # do not cast — hurts us more
        return (opp_cmc_destroyed - my_cmc_lost) * 10.0

    def _score_token_spell(self, oracle: str, game_state: dict, my_name: str) -> float:
        """Score token producers based on token count and stats."""
        # Look for count patterns like "create two 1/1 tokens"
        count = 1
        count_m = re.search(r'create (\w+) (?:\d+/\d+ )?(?:\w+ )?token', oracle, re.IGNORECASE)
        if count_m:
            word = count_m.group(1).lower()
            word_to_num = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3,
                           "four": 4, "five": 5, "six": 6, "three": 3}
            try:
                count = int(word)
            except ValueError:
                count = word_to_num.get(word, 1)
        # Extract token P/T if present
        pt_m = re.search(r'(\d+)/(\d+)', oracle)
        token_power = int(pt_m.group(1)) if pt_m else 1
        # Scale by personality profile
        base = count * (token_power * 8.0 + 10.0)
        return base * self._profile.token_generation_chance

    def _score_fight(self, card: dict, game_state: dict, my_name: str) -> float:
        """Score fight effects: value = kills high-CMC threat while our creature survives."""
        all_perms = game_state.get("battlefield", [])
        opp_name = next(
            (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
        )
        opp_creatures = [
            p for p in all_perms
            if p.get("controller") == opp_name
            and "creature" in (p.get("card", {}).get("type_line") or "").lower()
        ]
        my_creatures = [
            p for p in all_perms
            if p.get("controller") == my_name
            and "creature" in (p.get("card", {}).get("type_line") or "").lower()
        ]
        if not opp_creatures or not my_creatures:
            return -10.0

        best_fighter = max(my_creatures, key=_perm_power)
        best_target = max(opp_creatures, key=lambda p: _cmc_str(p.get("card", {}).get("mana_cost") or ""))

        fighter_power = _perm_power(best_fighter)
        target_toughness = _perm_toughness(best_target)
        fighter_toughness = _perm_toughness(best_fighter)
        target_power = _perm_power(best_target)
        target_cmc = _cmc_str(best_target.get("card", {}).get("mana_cost") or "")

        kills_target = fighter_power >= target_toughness
        survives = fighter_toughness > target_power

        if kills_target and survives:
            return target_cmc * 12.0 + 15.0  # SAFE fight
        elif kills_target:
            return target_cmc * 8.0  # mutual kill — worth it if target is higher CMC
        return -5.0

    def _score_goad(self, game_state: dict, my_name: str) -> float:
        """Score goad effect: forces opponent creatures to attack away from controller."""
        opp_name = next(
            (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
        )
        opp_creatures = [
            p for p in game_state.get("battlefield", [])
            if p.get("controller") == opp_name
            and "creature" in (p.get("card", {}).get("type_line") or "").lower()
        ]
        if not opp_creatures:
            return 5.0
        best = max(opp_creatures, key=_perm_power)
        return _perm_power(best) * 5.0 + 10.0

    def _score_life_gain(self, oracle: str, my_life: int = 20) -> float:
        """Score life gain effects. Doubles value when at low life (US15, T051)."""
        m = _LIFEGAIN_RE.search(oracle)
        if m:
            n = int(m.group(1) or m.group(2) or 1)
            base = n * 3.0
            if my_life <= 5:
                base *= 2.0
            return base
        return 5.0

    def _score_life_loss(self, oracle: str, game_state: dict, my_name: str) -> float:
        """Score life loss effects (same formula as burn, per spec)."""
        m = re.search(r'loses? (\d+) life', oracle, re.IGNORECASE)
        if not m:
            return 5.0
        dmg = int(m.group(1))
        opp_life = next(
            (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") != my_name), 20
        )
        if dmg >= opp_life:
            return 10000.0  # lethal
        return (dmg / max(opp_life, 1)) * 40.0

    def _score_control_steal(self, oracle: str, game_state: dict, my_name: str) -> float:
        """Score control-steal effects: value = stolen permanent's CMC × 15."""
        opp_name = next(
            (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
        )
        opp_perms = [
            p for p in game_state.get("battlefield", [])
            if p.get("controller") == opp_name
        ]
        if not opp_perms:
            return 0.0
        best_cmc = max(
            _cmc_str(p.get("card", {}).get("mana_cost") or "") for p in opp_perms
        )
        return best_cmc * 15.0

    def _score_tutor(self, card: dict, game_state: dict, my_name: str) -> float:
        """Score tutor effects: fixed high value — tutors find the right answer."""
        my_info = self._extract_my_info(game_state, my_name)
        hand_size = len(my_info.get("hand", []))
        # More valuable when hand is small (less redundancy)
        return 35.0 + max(0, 3 - hand_size) * 5.0

    def _select_connive_discard(self, hand: list[dict], current_turn: int) -> str | None:
        """
        Select the worst card to discard for connive.
        Prefer highest CMC cards we can't cast in next 2 turns. (US29, T084)
        """
        if not hand:
            return None
        lands = [c for c in hand if "land" in (c.get("type_line") or "").lower()]
        non_lands = [c for c in hand if "land" not in (c.get("type_line") or "").lower()]
        # Can't cast in next 2 turns = CMC > current_turn + 2
        too_expensive = [c for c in non_lands if _cmc_str(c.get("mana_cost") or "") > current_turn + 2]
        if too_expensive:
            return max(too_expensive, key=lambda c: _cmc_str(c.get("mana_cost") or "")).get("id")
        # All castable: discard a redundant land if we have many
        if len(lands) >= 4:
            return lands[0].get("id")
        # Default: discard highest CMC
        if non_lands:
            return max(non_lands, key=lambda c: _cmc_str(c.get("mana_cost") or "")).get("id")
        return hand[-1].get("id") if hand else None

    def _select_explore_outcome(
        self, revealed_card: dict, my_land_count: int, needed_lands: int
    ) -> str:
        """
        Decide what to do with an explored card.
        Returns 'land' (put onto battlefield) or 'hand' (keep in hand). (US29, T085)
        """
        is_land = "land" in (revealed_card.get("type_line") or "").lower()
        if is_land and my_land_count < needed_lands:
            return "land"
        return "hand"

    def _score_remove_from_combat(
        self, oracle: str, game_state: dict, my_name: str
    ) -> float:
        """Score tap-attacker / remove-blocker combat manipulation. (US30, T087)"""
        all_perms = game_state.get("battlefield", [])
        opp_name = next(
            (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
        )
        # Tap attacker: score = attacker power (unblocked damage prevented)
        if "tap target attacking" in oracle.lower():
            attacking = [
                p for p in all_perms
                if p.get("controller") == opp_name and p.get("tapped")
                and "creature" in (p.get("card", {}).get("type_line") or "").lower()
            ]
            if attacking:
                biggest = max(attacking, key=_perm_power)
                return self._perm_power(biggest) * 6.0
            return 5.0
        # Remove blocker: score = damage enabled for blocked attacker
        if "remove target blocking" in oracle.lower():
            my_attackers = [
                p for p in all_perms
                if p.get("controller") == my_name and p.get("tapped")
                and "creature" in (p.get("card", {}).get("type_line") or "").lower()
            ]
            if my_attackers:
                biggest = max(my_attackers, key=_perm_power)
                return self._perm_power(biggest) * 5.0
        return 5.0

    def _score_delayed_trigger_bonus(self, oracle: str) -> float:
        """Score delayed trigger bonuses (US32, T092): draw at upkeep, damage at upkeep."""
        bonus = 0.0
        draw_m = _DELAYED_DRAW_RE.search(oracle)
        if draw_m:
            try:
                n = int(draw_m.group(1))
            except (IndexError, ValueError, TypeError):
                n = 1
            bonus += n * 15.0
        dmg_m = _DELAYED_DAMAGE_RE.search(oracle)
        if dmg_m:
            bonus += int(dmg_m.group(1)) * 5.0
        return bonus

    def _score_animate(self, card: dict, game_state: dict, my_name: str) -> float:
        """Score effects that animate a permanent into a creature."""
        # Look for P/T in oracle text
        pt_m = re.search(r'(\d+)/(\d+)', card.get("oracle_text") or "")
        if pt_m:
            power = int(pt_m.group(1))
            return power * 8.0 + 15.0
        return 20.0

    def _score_fog(self, game_state: dict, my_name: str) -> float:
        """
        Fog effects: hold the spell unless incoming damage is life-threatening.
        US22 T068: score at 200.0 when predicted damage >= life - phyrexian threshold.
        """
        card_id = game_state.get("_scoring_card_id", "")
        step = self._current_step(game_state)
        my_life = self._extract_my_info(game_state, my_name).get("life", 20)

        # During opponent's declare_attackers or combat steps, evaluate urgency
        if step in ("declare_attackers", "declare_blockers", "first_strike_damage", "combat_damage"):
            predicted = self._predict_incoming_damage(game_state, my_name)
            if predicted >= my_life - self._profile.phyrexian_life_threshold:
                # Use the Fog now to prevent lethal
                if self._memory:
                    self._memory.chosen_fog_effect = None
                return 200.0

        # Otherwise, hold the fog for defensive use
        if self._memory and card_id:
            self._memory.chosen_fog_effect = card_id
        return -5.0  # slightly prefer passing to hold fog

    def _predict_incoming_damage(self, game_state: dict, my_name: str) -> int:
        """
        Estimate total unblocked damage the AI will take next attack.
        US24 T072: sum power of untapped opp creatures - total toughness of available blockers.
        """
        all_perms = game_state.get("battlefield", [])
        opp_name = next(
            (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
        )
        # Opponent attackers: untapped creatures without summoning sickness
        opp_attackers = [
            p for p in all_perms
            if p.get("controller") == opp_name
            and not p.get("tapped")
            and not p.get("summoning_sick")
            and "creature" in (p.get("card", {}).get("type_line") or "").lower()
        ]
        total_power = sum(self._perm_power(p) for p in opp_attackers)

        # My blockers: untapped creatures
        my_blockers = [
            p for p in all_perms
            if p.get("controller") == my_name
            and not p.get("tapped")
            and "creature" in (p.get("card", {}).get("type_line") or "").lower()
        ]
        total_block_toughness = sum(self._perm_toughness(p) for p in my_blockers)

        return max(0, total_power - total_block_toughness)

    def _score_counterspell(self, card: dict, game_state: dict, my_name: str, oracle: str) -> float:
        """Score counterspells based on profile thresholds."""
        # Check what's on the stack to counter
        stack = game_state.get("stack", [])
        if not stack:
            # Nothing to counter yet — hold up mana
            return -5.0  # slight preference to not cast early

        target_spell = stack[-1] if stack else {}
        spell_cmc = _cmc_str(target_spell.get("mana_cost") or "")

        # Always-counter profile flags
        target_oracle = (target_spell.get("oracle_text") or "").lower()
        if self._profile.always_counter_other_counterspells and _COUNTER_RE.search(target_oracle):
            return 80.0
        if self._profile.always_counter_damage_spells and _DAMAGE_TO_TARGET_RE.search(target_oracle):
            return 75.0
        if self._profile.always_counter_removal_spells and _DESTROY_RE.search(target_oracle):
            return 75.0
        if self._profile.always_counter_pump_spells and _PUMP_RE.search(target_oracle):
            return 60.0
        if self._profile.always_counter_auras and "enchant creature" in target_oracle:
            return 60.0

        # Probability-based CMC thresholds
        import random
        if spell_cmc <= 1:
            threshold = self._profile.chance_to_counter_cmc_1
        elif spell_cmc == 2:
            threshold = self._profile.chance_to_counter_cmc_2
        else:
            threshold = self._profile.chance_to_counter_cmc_3_plus

        if random.random() < threshold:
            return spell_cmc * 15.0 + 10.0
        return -10.0  # decided not to counter

    def _score_noncreature_spell(self, card: dict, game_state: dict, my_name: str) -> float:
        """
        Score instants and sorceries using sub-dispatch on oracle text patterns.
        """
        oracle = card.get("oracle_text") or ""
        score = 0.0
        has_scored_primary = False

        # ── Counter ─────────────────────────────────────────────────────
        if _COUNTER_RE.search(oracle):
            return self._score_counterspell(card, game_state, my_name, oracle)

        # ── Fog / prevent combat damage ──────────────────────────────────
        if _FOG_RE.search(oracle):
            return self._score_fog(game_state, my_name)

        # ── Board wipe ───────────────────────────────────────────────────
        if _WIPE_RE.search(oracle):
            return self._score_board_wipe(game_state, my_name)

        # ── Removal (destroy/exile target) ───────────────────────────────
        if _DESTROY_RE.search(oracle):
            opp_name = next(
                (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
            )
            opp_targets = [
                p for p in game_state.get("battlefield", [])
                if p.get("controller") == opp_name
                and (
                    "creature" in (p.get("card", {}).get("type_line") or "").lower()
                    or "planeswalker" in (p.get("card", {}).get("type_line") or "").lower()
                )
            ]
            if opp_targets:
                best_cmc = max(_cmc_str(p.get("card", {}).get("mana_cost") or "") for p in opp_targets)
                score += min(best_cmc * 12.0, 80.0)
            else:
                score -= 20.0
            has_scored_primary = True

        # ── Burn (deals N damage to any target) ──────────────────────────
        dmg_m = _DAMAGE_TO_TARGET_RE.search(oracle)
        if dmg_m:
            dmg = int(dmg_m.group(1))
            opp_name = next(
                (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
            )
            opp_creatures = [
                p for p in game_state.get("battlefield", [])
                if p.get("controller") == opp_name
                and "creature" in (p.get("card", {}).get("type_line") or "").lower()
            ]
            opp_life = next(
                (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") == opp_name), 20
            )
            if dmg >= opp_life:
                score += 10000.0  # lethal face burn
            elif any(_perm_toughness(p) <= dmg for p in opp_creatures):
                best_kill_cmc = max(
                    (_cmc_str(p.get("card", {}).get("mana_cost") or "") for p in opp_creatures if _perm_toughness(p) <= dmg),
                    default=0,
                )
                score += best_kill_cmc * 10.0 + 20.0
            else:
                score += (dmg / max(opp_life, 1)) * 40.0
            has_scored_primary = True

        # ── Control steal ─────────────────────────────────────────────────
        if _CONTROL_RE.search(oracle):
            score += self._score_control_steal(oracle, game_state, my_name)
            has_scored_primary = True

        # ── Life loss ─────────────────────────────────────────────────────
        if _LIFE_LOSS_RE.search(oracle) and not has_scored_primary:
            score += self._score_life_loss(oracle, game_state, my_name)
            has_scored_primary = True

        # ── Ramp ─────────────────────────────────────────────────────────
        if _RAMP_RE.search(oracle):
            score += self._score_ramp_spell(card, game_state, my_name)
            has_scored_primary = True

        # ── Fight ────────────────────────────────────────────────────────
        if _FIGHT_RE.search(oracle):
            score += self._score_fight(card, game_state, my_name)
            has_scored_primary = True

        # ── Goad ─────────────────────────────────────────────────────────
        if _GOAD_RE.search(oracle):
            score += self._score_goad(game_state, my_name)
            has_scored_primary = True

        # ── Tutor ────────────────────────────────────────────────────────
        if _TUTOR_RE.search(oracle):
            score += self._score_tutor(card, game_state, my_name)
            has_scored_primary = True

        # ── Token producer ────────────────────────────────────────────────
        if _TOKEN_RE.search(oracle):
            score += self._score_token_spell(oracle, game_state, my_name)
            has_scored_primary = True

        # ── Bounce ───────────────────────────────────────────────────────
        if _BOUNCE_RE.search(oracle) and not has_scored_primary:
            opp_name = next(
                (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
            )
            opp_perms = [
                p for p in game_state.get("battlefield", [])
                if p.get("controller") == opp_name
            ]
            if opp_perms:
                best_cmc = max(_cmc_str(p.get("card", {}).get("mana_cost") or "") for p in opp_perms)
                score += best_cmc * 8.0
            has_scored_primary = True

        # ── Life gain ─────────────────────────────────────────────────────
        if "gain" in oracle.lower() and "life" in oracle.lower() and not has_scored_primary:
            my_life = self._extract_my_info(game_state, my_name).get("life", 20)
            score += self._score_life_gain(oracle, my_life)
            has_scored_primary = True

        # ── Artifact/enchantment removal (US23, T071) ─────────────────────
        if _ARTIFACT_REMOVAL_RE.search(oracle) and self._profile.actively_destroy_artifacts_and_enchantments:
            opp_name2 = next(
                (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
            )
            opp_ae = [
                p for p in game_state.get("battlefield", [])
                if p.get("controller") == opp_name2
                and ("artifact" in (p.get("card", {}).get("type_line") or "").lower()
                     or "enchantment" in (p.get("card", {}).get("type_line") or "").lower())
            ]
            if opp_ae:
                target_cmc = max(_cmc_str(p.get("card", {}).get("mana_cost") or "") for p in opp_ae)
                score += target_cmc * 10.0
                has_scored_primary = True

        # ── Remove from combat (US30, T087) ──────────────────────────────
        if _REMOVE_COMBAT_RE.search(oracle):
            score += self._score_remove_from_combat(oracle, game_state, my_name)
            has_scored_primary = True

        # ── Delayed trigger bonus (US32, T092) ───────────────────────────
        score += self._score_delayed_trigger_bonus(oracle)

        # ── Draw (bonus on top of primary effect) ────────────────────────
        score += self._score_draw_spell(oracle)

        # ── Fallback for unrecognized instants/sorceries ─────────────────
        if not has_scored_primary:
            score += 5.0  # generic positive

        return score

    def _score_cast(self, action: dict, game_state: dict, my_name: str) -> float:
        """Score a cast action by CMC, P/T, keywords, timing, and opponent life pressure."""
        mana_options = action.get("mana_options", [{}])
        mana_cost = mana_options[0].get("mana_cost", "") if mana_options else ""
        score = self._cmc(mana_cost) * 10.0

        # Graveyard cast bonus (flashback, escape, unearth, disturb) — free resource
        if action.get("from_graveyard") or action.get("alternative_cost") in {
            "flashback", "escape", "unearth", "disturb"
        }:
            score += 10.0

        # Alternative cost tradeoff scoring (US18, T060)
        alt_cost = action.get("alternative_cost")
        if alt_cost == "convoke":
            # Convoke: compare spell value vs attack value of tapped creatures
            tapped_power = sum(
                self._perm_power(p)
                for p in game_state.get("battlefield", [])
                if p.get("id") in action.get("valid_targets", [])
            )
            if score < tapped_power * 5.0:
                score -= 10.0  # not worth tapping attackers for this
        elif alt_cost == "emerge":
            # Emerge: deduct sacrificed creature's CMC from score benefit
            sac_ids = action.get("valid_targets", [])
            if sac_ids:
                sac_perm = next(
                    (p for p in game_state.get("battlefield", []) if p.get("id") == sac_ids[0]),
                    {},
                )
                sac_cmc = _cmc_str(sac_perm.get("card", {}).get("mana_cost") or "")
                score -= sac_cmc * 5.0
        elif alt_cost == "phyrexian":
            # Phyrexian mana: penalize life payment by threshold (US33, T095)
            my_info = self._extract_my_info(game_state, my_name)
            my_life = my_info.get("life", 20)
            mana_cost = mana_cost  # already computed above
            phyrexian_count = len(re.findall(r'\{[WUBRG]/P\}', mana_cost, re.IGNORECASE))
            life_cost = phyrexian_count * 2
            if my_life <= self._profile.phyrexian_life_threshold + life_cost:
                return -999.0  # don't pay life when we're low
            score -= life_cost * 1.0  # mild penalty for life payment

        # Look up full card details from hand (or graveyard for alternative casts)
        my_info = self._extract_my_info(game_state, my_name)
        card = None
        card_id = action.get("card_id", "")
        card_name = action.get("card_name", "")

        search_zones = [my_info.get("hand", [])]
        if action.get("from_graveyard"):
            search_zones.append(my_info.get("graveyard", []))

        for zone in search_zones:
            for c in zone:
                if c.get("id") == card_id or c.get("name") == card_name:
                    card = c
                    break
            if card:
                break

        if card:
            type_line = (card.get("type_line") or "").lower()
            try:
                power = int(card.get("power") or 0)
            except (ValueError, TypeError):
                power = 0

            # ── Combat tricks ─────────────────────────────────────────────
            if self._is_combat_trick(card):
                if not self._has_any_creatures(game_state, my_name):
                    return -100.0
                step = self._current_step(game_state)
                in_combat = step in _COMBAT_STEPS
                has_attacker = self._has_attackable_creatures(game_state, my_name)
                # Hold trick for blockers step if we have trick_attackers in memory
                if self._memory and self._memory.trick_attackers and step == "declare_blockers":
                    pump_m = _PUMP_RE.search(card.get("oracle_text") or "")
                    if pump_m:
                        parts = re.findall(r'\d+', pump_m.group(0))
                        pump_power = int(parts[0]) if parts else 1
                        score += pump_power * 8.0 + 20.0
                        return score
                if not in_combat and not has_attacker:
                    return -50.0
                if in_combat:
                    score += 40.0
                else:
                    return -50.0

            # ── Creature ──────────────────────────────────────────────────
            if "creature" in type_line:
                if power >= 3:
                    score += 20.0

                # ETB bonus (US12)
                etb_bonus = self._score_etb(card, game_state, my_name)
                score += etb_bonus

                # Mana dork bonus (US3)
                if _MANA_ADD_RE.search(card.get("oracle_text") or ""):
                    score += 15.0

                # Evasion
                if self._has_keyword(card, "flying"):
                    score += power * 8.0
                elif self._has_keyword(card, "fear") or self._has_keyword(card, "intimidate"):
                    score += power * 5.0
                elif self._has_keyword(card, "menace"):
                    score += power * 3.0

                # Combat keywords
                if self._has_keyword(card, "double strike"):
                    score += 10.0 + power * 10.0
                elif self._has_keyword(card, "first strike"):
                    score += 5.0 + power * 3.0

                if self._has_keyword(card, "deathtouch"):
                    score += 25.0
                if self._has_keyword(card, "lifelink"):
                    score += power * 5.0
                if self._has_keyword(card, "trample"):
                    score += max(0, power - 1) * 4.0
                if self._has_keyword(card, "haste"):
                    score += power * 4.0
                if self._has_keyword(card, "vigilance"):
                    try:
                        toughness = int(card.get("toughness") or 0)
                    except (ValueError, TypeError):
                        toughness = 0
                    score += (power * 3.0) + (toughness * 3.0)

                # Defensive keywords
                if self._has_keyword(card, "indestructible"):
                    score += 40.0
                elif self._has_keyword(card, "hexproof"):
                    score += 20.0
                elif self._has_keyword(card, "shroud"):
                    score += 15.0

                # dies bonus (US12)
                dies_bonus = self._score_dies_trigger(card)
                score += dies_bonus

                # transform/DFC bonus (US21, T065-T066)
                score += self._score_transform_bonus(card, game_state, my_name)

            # ── Planeswalker ──────────────────────────────────────────────
            elif "planeswalker" in type_line:
                try:
                    loyalty = int(card.get("loyalty") or 0)
                except (ValueError, TypeError):
                    loyalty = 0
                score += 40.0 + loyalty * 8.0

            # ── Aura (enchant creature) ───────────────────────────────────
            elif "enchantment" in type_line:
                oracle = card.get("oracle_text") or ""
                if "enchant creature" in oracle.lower():
                    if not self._has_any_creatures(game_state, my_name):
                        return -20.0
                    # Pick best target and store for routing
                    best_target = self._select_best_target(
                        action.get("valid_targets", []), game_state, "aura", my_name
                    )
                    if best_target:
                        action["chosen_target"] = best_target
                    boost_m = _AURA_BOOST_RE.search(oracle)
                    if boost_m:
                        p_boost = int(boost_m.group(1))
                        t_boost = int(boost_m.group(2))
                        score += p_boost * 8.0 + t_boost * 4.0
                    for kw in ("flying", "trample", "deathtouch", "lifelink", "haste"):
                        if kw in oracle.lower():
                            score += 10.0
                elif self._profile.actively_destroy_artifacts_and_enchantments:
                    # Non-aura enchantments are generally good
                    score += 10.0

            # ── Artifact (equipment) ──────────────────────────────────────
            elif "artifact" in type_line:
                if "equipment" in (card.get("oracle_text") or "").lower():
                    # Equipment scored when equipped (activate), not when cast
                    score += 15.0
                else:
                    score += 10.0

            # ── Instant / Sorcery ─────────────────────────────────────────
            elif "instant" in type_line or "sorcery" in type_line:
                # Modal spell handling (US9, T034): detect choose-N and select best modes
                oracle_text = card.get("oracle_text") or ""
                if "choose one" in oracle_text.lower() or "choose two" in oracle_text.lower() or "choose three" in oracle_text.lower():
                    modes = self._select_modes(card, game_state, my_name)
                    if not modes:
                        return -1000.0
                    action["modes_chosen"] = modes

                # Store card_id in game_state scratch so _score_fog can access it
                game_state["_scoring_card_id"] = card_id
                spell_score = self._score_noncreature_spell(card, game_state, my_name)
                game_state.pop("_scoring_card_id", None)
                score += spell_score

                # Target selection for removal and burn
                valid_targets = action.get("valid_targets", [])
                oracle = card.get("oracle_text") or ""
                if valid_targets:
                    if _DESTROY_RE.search(oracle):
                        best = self._select_best_target(valid_targets, game_state, "removal", my_name)
                        if best:
                            action["chosen_target"] = best
                    elif _DAMAGE_TO_TARGET_RE.search(oracle):
                        best = self._select_best_target(valid_targets, game_state, "burn", my_name)
                        if best:
                            action["chosen_target"] = best
                    elif _CONTROL_RE.search(oracle):
                        best = self._select_best_target(valid_targets, game_state, "control", my_name)
                        if best:
                            action["chosen_target"] = best
                    elif _LIFE_LOSS_RE.search(oracle):
                        best = self._select_best_target(valid_targets, game_state, "lifedrain", my_name)
                        if best:
                            action["chosen_target"] = best

        # ── Counter-awareness penalty (US13, T046) ────────────────────────
        # If opponent has a revealed counterspell and open mana, penalize our best spell
        if card and self._memory:
            my_info = self._extract_my_info(game_state, my_name)
            opp = next(
                (p for p in game_state.get("players", []) if p.get("name") != my_name), {}
            )
            opp_name = opp.get("name", "")
            revealed = self._memory.get_revealed_cards(opp_name)
            for rev_card in revealed:
                rev_oracle = (rev_card.get("oracle_text") or "").lower()
                if "counter target spell" in rev_oracle:
                    score -= 20.0
                    break

        # ── Sacrifice cost handling (US7, T031) ───────────────────────────
        if card:
            oracle = card.get("oracle_text") or ""
            if _SACRIFICE_COST_RE.search(oracle):
                sac_candidates = action.get("valid_targets", [])
                sac_target = self._select_sacrifice_target(sac_candidates, game_state, my_name)
                if sac_target:
                    action["sacrifice_target"] = sac_target
                else:
                    # Can't satisfy sacrifice cost — do not cast
                    return -1000.0

        # Aggression multiplier when opponent life is low
        opp_life = next(
            (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") != my_name),
            20,
        )
        if opp_life <= 6:
            score *= 1.5

        return score

    # ------------------------------------------------------------------
    # Transform / meld bonus (US21, T065-T066)
    # ------------------------------------------------------------------

    def _score_transform_bonus(self, card: dict, game_state: dict, my_name: str) -> float:
        """
        Compute bonus for DFC cards that transform into stronger creatures.
        delta = (back_power - front_power) * 10 + (back_toughness - front_toughness) * 5
        """
        faces = card.get("faces") or []
        if len(faces) < 2:
            return 0.0

        front = faces[0]
        back = faces[1]
        # Only relevant if back face has creature P/T
        try:
            back_power = int(back.get("power") or 0)
            back_toughness = int(back.get("toughness") or 0)
            front_power = int(card.get("power") or front.get("power") or 0)
            front_toughness = int(card.get("toughness") or front.get("toughness") or 0)
        except (ValueError, TypeError):
            return 0.0

        # Skip "if no spells were cast" style near-impossible transform conditions
        oracle = (back.get("oracle_text") or "").lower()
        if "if no spells" in oracle or "no other spells" in oracle:
            return 0.0

        delta = (back_power - front_power) * 10.0 + (back_toughness - front_toughness) * 5.0
        return max(0.0, delta)

    # ------------------------------------------------------------------
    # ETB / dies trigger scoring (US12, T042)
    # ------------------------------------------------------------------

    def _score_etb(self, card: dict, game_state: dict, my_name: str) -> float:
        """Score ETB trigger effects on a creature card."""
        oracle = (card.get("oracle_text") or "").lower()
        bonus = 0.0
        # Draw on ETB
        if "when" in oracle and "enters" in oracle and "draw" in oracle:
            bonus += self._score_draw_spell(oracle)
        # Damage/burn on ETB
        etb_dmg_m = re.search(r'when.*?enters.*?deals?\s+(\d+)\s+damage', oracle, re.IGNORECASE)
        if etb_dmg_m:
            bonus += int(etb_dmg_m.group(1)) * 5.0
        # Token on ETB
        if "when" in oracle and "enters" in oracle and "create" in oracle and "token" in oracle:
            bonus += 15.0
        # Destroy/exile on ETB
        if "when" in oracle and "enters" in oracle and ("destroy" in oracle or "exile" in oracle):
            bonus += 20.0
        return bonus

    def _score_dies_trigger(self, card: dict) -> float:
        """Score dies-trigger effects on a creature card."""
        oracle = (card.get("oracle_text") or "").lower()
        bonus = 0.0
        if "when" in oracle and "dies" in oracle:
            if "draw" in oracle:
                bonus += 10.0
            if "create" in oracle and "token" in oracle:
                bonus += 10.0
            if "damage" in oracle:
                bonus += 8.0
        return bonus

    # ------------------------------------------------------------------
    # Equipment helpers (US10, T036-T037)
    # ------------------------------------------------------------------

    def _is_equipment(self, perm: dict) -> bool:
        """Return True if the permanent is an Equipment."""
        return "equipment" in (perm.get("card", {}).get("type_line") or "").lower()

    def _select_equip_target(
        self, valid_targets: list[str], game_state: dict, my_name: str
    ) -> str | None:
        """Return the ID of the highest-power friendly creature to equip."""
        all_perms = game_state.get("battlefield", [])
        perm_map = {p.get("id"): p for p in all_perms}
        my_creatures = [
            perm_map[tid] for tid in valid_targets
            if tid in perm_map
            and perm_map[tid].get("controller") == my_name
            and "creature" in (perm_map[tid].get("card", {}).get("type_line") or "").lower()
        ]
        if not my_creatures:
            return None
        return max(my_creatures, key=_perm_power).get("id")

    # ------------------------------------------------------------------
    # Sacrifice target selection (US7, T030-T031)
    # ------------------------------------------------------------------

    def _select_sacrifice_target(
        self, valid_targets: list[str], game_state: dict, my_name: str
    ) -> str | None:
        """Return the best sacrifice target (tokens preferred, then lowest CMC)."""
        if not valid_targets:
            return None
        all_perms = game_state.get("battlefield", [])
        perm_map = {p.get("id"): p for p in all_perms}

        candidates = [perm_map[tid] for tid in valid_targets if tid in perm_map]
        if not candidates:
            return valid_targets[0]

        # Tokens first
        tokens = [p for p in candidates if p.get("is_token")]
        if tokens:
            return min(tokens, key=lambda p: _cmc_str(p.get("card", {}).get("mana_cost") or "")).get("id")

        # Lowest CMC non-token
        return min(
            candidates,
            key=lambda p: _cmc_str(p.get("card", {}).get("mana_cost") or ""),
        ).get("id")

    # ------------------------------------------------------------------
    # Planeswalker loyalty ability scoring (US4, T023)
    # ------------------------------------------------------------------

    def _score_loyalty_ability(self, action: dict, game_state: dict, my_name: str) -> float:
        """
        Score a planeswalker loyalty ability activation.
        + abilities score loyalty_change × 8.
        0 abilities score 25.
        − abilities score based on effect (removal, draw, damage).
        """
        loyalty_change = action.get("loyalty_change", 0)
        description = (action.get("description") or "").lower()
        effect_text = action.get("effect_text") or description

        if loyalty_change > 0:
            return loyalty_change * 8.0
        elif loyalty_change == 0:
            return 25.0
        else:
            # Minus ability — score by effect
            if "draw" in effect_text:
                return 15.0 * abs(loyalty_change)
            if "destroy" in effect_text or "exile" in effect_text:
                # Removal ultimate
                opp_creatures = [
                    p for p in game_state.get("battlefield", [])
                    if p.get("controller") != my_name
                    and "creature" in (p.get("card", {}).get("type_line") or "").lower()
                ]
                best_cmc = max(
                    (_cmc_str(p.get("card", {}).get("mana_cost") or "") for p in opp_creatures),
                    default=0,
                )
                return best_cmc * 10.0 + 20.0
            if "damage" in effect_text:
                dmg_m = re.search(r'(\d+) damage', effect_text)
                dmg = int(dmg_m.group(1)) if dmg_m else 3
                opp_life = next(
                    (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") != my_name), 20
                )
                return (dmg / max(opp_life, 1)) * 40.0 + 10.0
            return abs(loyalty_change) * 5.0

    # ------------------------------------------------------------------
    # Mulligan scoring (US6, T028)
    # ------------------------------------------------------------------

    def _score_mulligan(self, action: dict, game_state: dict, my_name: str) -> float:
        """Score a mulligan action — used in the _score_action dispatcher."""
        # evaluate_mulligan() is the primary decision point; this is fallback
        my_info = self._extract_my_info(game_state, my_name)
        hand = my_info.get("hand", [])
        return 50.0 if self.evaluate_mulligan(hand, len(hand)) else -50.0

    def evaluate_mulligan(self, hand: list[dict], hand_size: int) -> bool:
        """
        Evaluate whether to mulligan.
        Returns True to mulligan, False to keep.

        Rules (London mulligan heuristics):
        - Always keep if hand_size <= 5 (floor)
        - Mulligan if 0 lands
        - Mulligan if all cards are lands
        - Mulligan if no spells castable within first 4 turns given land count
        """
        if hand_size <= 5:
            return False  # always keep at floor

        land_count = sum(
            1 for c in hand
            if "land" in (c.get("type_line") or "").lower()
        )

        if land_count == 0:
            return True  # zero lands — always mulligan
        if land_count == len(hand):
            return True  # all lands — always mulligan

        # Check if any spell is castable in the first 4 turns
        spells = [c for c in hand if "land" not in (c.get("type_line") or "").lower()]
        on_curve = any(
            self._cmc(c.get("mana_cost") or "") <= land_count + 1
            for c in spells
        )
        if not on_curve:
            return True  # no early plays — mulligan

        return False  # keep

    # ------------------------------------------------------------------
    # Scry / Surveil decisions (US8, T032-T033)
    # ------------------------------------------------------------------

    def _score_scry_choice(self, revealed_card: dict, current_turn: int) -> str:
        """Return 'top' or 'bottom' for a scry decision."""
        cmc = self._cmc(revealed_card.get("mana_cost") or "")
        # Keep on top if castable within 2 turns
        return "top" if cmc <= current_turn + 2 else "bottom"

    def _score_surveil_choice(self, revealed_card: dict, current_turn: int) -> str:
        """Return 'top' or 'graveyard' for a surveil decision."""
        oracle = (revealed_card.get("oracle_text") or "").lower()
        kws = revealed_card.get("keywords") or []
        for kw in kws:
            if kw.lower() in _GRAVEYARD_SYNERGY_KW:
                return "graveyard"
        if any(kw in oracle for kw in _GRAVEYARD_SYNERGY_KW):
            return "graveyard"
        result = self._score_scry_choice(revealed_card, current_turn)
        return "graveyard" if result == "bottom" else "top"

    # ------------------------------------------------------------------
    # Modal spell mode selection (US9, T034-T035)
    # ------------------------------------------------------------------

    def _select_modes(self, card: dict, game_state: dict, my_name: str) -> list[int]:
        """
        Score each mode of a modal spell and return the best mode index(es).
        Returns [] if no modes can be scored positively.
        """
        oracle = card.get("oracle_text") or ""
        # Detect choose-N pattern
        choose_n = 1
        if "choose two" in oracle.lower():
            choose_n = 2
        elif "choose three" in oracle.lower():
            choose_n = 3

        # Split modes by bullet/semicolon/mode markers
        mode_texts = re.split(r'•|\n—\n|; |(?:Mode \d+:)', oracle)
        mode_texts = [m.strip() for m in mode_texts if m.strip() and len(m.strip()) > 5]

        if not mode_texts:
            return []

        scored = []
        for i, mode_text in enumerate(mode_texts):
            fake_card = dict(card)
            fake_card["oracle_text"] = mode_text
            fake_card["type_line"] = "Instant"  # treat as instant for scoring
            try:
                s = self._score_noncreature_spell(fake_card, game_state, my_name)
            except Exception:
                s = 0.0
            scored.append((i, s))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:choose_n]
        return [i for i, _ in top if _ > 0]

    # ------------------------------------------------------------------
    # Combat simulation (T018)
    # ------------------------------------------------------------------

    def _simulate_combat(
        self,
        attacker_perms: list[dict],
        blocker_perms: list[dict],
        opp_life: int,
    ) -> float:
        """
        Estimate the net value of attacking with the given creatures.
        Returns 10,000 on lethal, positive for net-advantageous attacks,
        negative for net-losing attacks (caller should cap at 0 = don't attack).
        """
        if not attacker_perms:
            return 0.0

        total_power = sum(self._perm_power(p) for p in attacker_perms)

        # Lethal check — always attack for the win
        if total_power >= opp_life:
            return 10000.0

        # No blockers — uncontested chip damage
        if not blocker_perms:
            return total_power * 15.0

        # Greedy blocker simulation: model opponent's optimal blocking response.
        # Opponent will block with the cheapest creature that can KILL our attacker.
        # If no killing blocker exists, check for chump blocks (opponent sacrifices
        # a creature to stop damage). Unblocked attackers deal chip damage.
        remaining_blockers = list(blocker_perms)
        net_score = 0.0

        for att in sorted(attacker_perms, key=lambda p: self._perm_power(p), reverse=True):
            att_power = self._perm_power(att)
            att_toughness = self._perm_toughness(att)
            att_cmc = self._cmc(att.get("card", {}).get("mana_cost") or "")
            att_card = att.get("card", {})
            att_has_dt = _card_has_kw(att_card, "deathtouch")
            att_has_trample = _card_has_kw(att_card, "trample")
            att_has_fs = _card_has_kw(att_card, "first strike") or _card_has_kw(att_card, "double strike")

            # Only consider blockers that can legally block this attacker (evasion check)
            eligible = [blk for blk in remaining_blockers if _can_block(blk, att)]

            # Find cheapest blocker that can KILL our attacker.
            # With deathtouch on the blocker, 1 damage = lethal → any blocker with power≥1 kills us.
            # With first strike on the blocker (and no first strike on attacker), blocker kills us first
            # if its power ≥ our toughness.
            killing_blocker = None
            for blk in sorted(eligible, key=lambda p: self._cmc(p.get("card", {}).get("mana_cost") or "")):
                blk_power = self._perm_power(blk)
                blk_card = blk.get("card", {})
                blk_has_dt = _card_has_kw(blk_card, "deathtouch")
                blk_has_fs = _card_has_kw(blk_card, "first strike") or _card_has_kw(blk_card, "double strike")

                # Blocker kills our attacker if:
                # - Normal: blk_power >= att_toughness
                # - Deathtouch blocker: any non-zero damage kills us
                # - First-strike blocker vs no-first-strike attacker: kills us if power >= toughness
                #   (same formula, but the attacker can't deal damage back before dying)
                blocker_kills_attacker = (
                    (blk_has_dt and blk_power > 0)
                    or blk_power >= att_toughness
                )
                if blocker_kills_attacker:
                    killing_blocker = blk
                    break

            if killing_blocker:
                blk_power = self._perm_power(killing_blocker)
                blk_toughness = self._perm_toughness(killing_blocker)
                blk_cmc = self._cmc(killing_blocker.get("card", {}).get("mana_cost") or "")
                blk_has_dt = _card_has_kw(killing_blocker.get("card", {}), "deathtouch")
                blk_has_fs = _card_has_kw(killing_blocker.get("card", {}), "first strike") or \
                             _card_has_kw(killing_blocker.get("card", {}), "double strike")

                # Does our attacker also kill the blocker?
                # Deathtouch attacker: kills any blocker with 1 damage
                # First-strike attacker vs no-first-strike blocker: kills if power ≥ toughness
                #   (blocker can't deal damage back before dying)
                attacker_kills_blocker = (
                    (att_has_dt and att_power > 0)
                    or att_power >= blk_toughness
                )
                # If blocker has first strike and attacker doesn't, attacker can't deal damage back
                if blk_has_fs and not att_has_fs:
                    attacker_kills_blocker = False  # blocker kills us before we can retaliate

                if attacker_kills_blocker:
                    # Mutual trade
                    net_score += (att_cmc - blk_cmc) * 8.0
                else:
                    # Our attacker dies, their blocker survives
                    net_score -= att_cmc * 8.0

                remaining_blockers.remove(killing_blocker)
            else:
                # No killing blocker — check if opponent can chump block
                chump = next(
                    (blk for blk in sorted(eligible, key=lambda p: self._cmc(p.get("card", {}).get("mana_cost") or ""))
                     if self._perm_toughness(blk) <= att_power or att_has_dt),
                    None,
                )
                if chump:
                    blk_toughness = self._perm_toughness(chump)
                    blk_cmc = self._cmc(chump.get("card", {}).get("mana_cost") or "")
                    net_score += blk_cmc * 8.0
                    # Trample: excess damage bleeds through even if blocked
                    if att_has_trample:
                        excess = max(0, att_power - blk_toughness)
                        net_score += excess * 6.0
                    remaining_blockers.remove(chump)
                else:
                    # Truly unblocked — chip damage
                    net_score += att_power * 10.0

        # Small aggression bonus to break ties with pass (prefer attacking over waiting)
        if net_score >= 0.0:
            net_score += 5.0

        return net_score

    # ------------------------------------------------------------------
    # Selective attacker subset (Forge: shouldAttack per-creature filtering)
    # ------------------------------------------------------------------

    def select_attackers(self, action: dict, game_state: dict, my_name: str) -> list[str]:
        """
        Return the optimal subset of valid_targets to actually attack with.
        Strategy:
          1. Score the full group — if positive, send everyone.
          2. Otherwise, greedily drop the attacker with the worst individual
             contribution (marginal score) until the group score turns positive
             or only one attacker remains (try it anyway if unblocked/evasion).
        """
        all_ids = action.get("valid_targets", [])
        if not all_ids:
            return []

        all_perms = game_state.get("battlefield", [])
        opp_name = next(
            (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
        )
        blocker_perms = [
            p for p in all_perms
            if p.get("controller") == opp_name
            and not p.get("tapped")
            and "creature" in (p.get("card", {}).get("type_line") or "").lower()
        ]
        opp_life = next(
            (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") == opp_name), 20
        )
        all_perm_map = {p.get("id"): p for p in all_perms}
        candidates = [all_perm_map[aid] for aid in all_ids if aid in all_perm_map]

        # Full group score
        if self._simulate_combat(candidates, blocker_perms, opp_life) >= 0:
            return all_ids  # all attack

        # Greedy pruning: remove the worst individual contributor
        remaining = list(candidates)
        while len(remaining) > 1:
            # Marginal contribution of each creature = score(all) - score(all minus this one)
            base = self._simulate_combat(remaining, blocker_perms, opp_life)
            worst = min(
                remaining,
                key=lambda p: base - self._simulate_combat(
                    [x for x in remaining if x is not p], blocker_perms, opp_life
                ),
            )
            remaining.remove(worst)
            if self._simulate_combat(remaining, blocker_perms, opp_life) >= 0:
                break

        # Check if reduced group is worth attacking with
        if self._simulate_combat(remaining, blocker_perms, opp_life) >= 0:
            return [p.get("id") for p in remaining]

        # Last resort: any evasion attacker that has no eligible blocker
        unblocked = [
            p for p in candidates
            if not any(_can_block(blk, p) for blk in blocker_perms)
        ]
        if unblocked:
            return [p.get("id") for p in unblocked]

        return []  # don't attack

    # ------------------------------------------------------------------
    # Attacker scoring (T019, T020)
    # ------------------------------------------------------------------

    def _score_declare_attackers(self, action: dict, game_state: dict, my_name: str) -> float:
        """Score a declare_attackers action using combat simulation."""
        attacker_ids = set(action.get("valid_targets", []))
        all_perms = game_state.get("battlefield", [])

        attacker_perms = [p for p in all_perms if p.get("id") in attacker_ids]

        opp_name = next(
            (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name),
            "",
        )
        blocker_perms = [
            p for p in all_perms
            if p.get("controller") == opp_name
            and not p.get("tapped")
            and "creature" in (p.get("card", {}).get("type_line") or "").lower()
        ]
        opp_life = next(
            (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") == opp_name),
            20,
        )

        score = self._simulate_combat(attacker_perms, blocker_perms, opp_life)

        # ── Personality: trade aggression gating (US17, T055) ─────────────
        # check_to_attack_into_trade gates trade-into attacks by probability
        if score < 0 and opp_life > 10:
            import random as _rand
            if not _rand.random() < self._profile.chance_to_attack_into_trade:
                return 0.0
            # Additional gate: if opponent has open mana and we're not tapped out
            if not self._profile.attack_into_trade_when_tapped_out:
                opp_has_mana = any(
                    sum(p.get("mana_pool", {}).values()) > 0
                    for p in game_state.get("players", []) if p.get("name") == opp_name
                )
                if opp_has_mana and not _rand.random() < self._profile.chance_to_atktrade_when_opp_has_mana:
                    return 0.0

        # ── Life-pressure clock (Forge: aiAggression escalation) ─────────
        # When opponent is low on life, press the attack even into unfavourable trades.
        # At ≤5 life any attack that can deal damage is correct; at ≤10 add pressure bonus.
        my_life = next(
            (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") == my_name),
            20,
        )
        if score < 0 and opp_life <= 5:
            # Opponent near death — accept unfavourable trades, but don't attack into
            # a board that will kill us in response
            total_unblocked_evasion = sum(
                self._perm_power(p) for p in attacker_perms
                if _card_has_kw(p.get("card", {}), "flying")
            )
            if total_unblocked_evasion >= opp_life:
                score = max(score, 200.0)   # near-lethal evasion swing
            elif score > -30:
                # Small unfavourable trade is acceptable when opponent is nearly dead
                score = max(score, 10.0)
        elif opp_life <= 10:
            # Clock pressure: bonus scales with how close to lethal we are
            pressure_bonus = (10 - opp_life) * 4.0
            score += pressure_bonus

        # ── Race awareness: if we're losing the life race, attack harder ──
        if my_life < opp_life and score > 0:
            score *= 1.2

        # ── Combat trick baiting (US2, T016) ──────────────────────────────
        # When we hold a combat trick and score is positive, designate
        # the chosen attackers as trick_attackers in memory so the
        # declare-blockers step knows to cast the pump spell if blocked.
        if score > 0 and self._memory and self._has_combat_trick_in_hand(game_state, my_name):
            for pid in attacker_ids:
                self._memory.trick_attackers.add(pid)

        # Never return negative — pass is always score 0
        return max(score, 0.0)

    # ------------------------------------------------------------------
    # Attack direction selection (US20, T063-T064)
    # ------------------------------------------------------------------

    def _select_attack_direction(
        self, game_state: dict, my_name: str, attacking_power: int
    ) -> str:
        """
        Select which opponent to attack.
        Prefers opponents at lethal range; otherwise the one with most permanents.
        Returns a player name string.
        """
        opponents = [p for p in game_state.get("players", []) if p.get("name") != my_name]
        if not opponents:
            return ""
        # Lethal check
        for opp in opponents:
            if opp.get("life", 20) <= attacking_power:
                return opp.get("name", "")
        # Most threatening (highest permanent CMC sum)
        def _opp_threat(opp: dict) -> float:
            opp_name = opp.get("name", "")
            return sum(
                _cmc_str(p.get("card", {}).get("mana_cost") or "")
                for p in game_state.get("battlefield", [])
                if p.get("controller") == opp_name
            )
        return max(opponents, key=_opp_threat).get("name", "")

    # ------------------------------------------------------------------
    # Blocker scoring (T021, T022)
    # ------------------------------------------------------------------


    def _score_declare_blockers(self, action: dict, game_state: dict, my_name: str) -> float:
        """Score a declare_blockers action based on threat assessment."""
        all_perms = game_state.get("battlefield", [])
        opp_name = next(
            (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name),
            "",
        )

        # Tapped opponent creatures = attacking this turn
        incoming_attackers = [
            p for p in all_perms
            if p.get("controller") == opp_name
            and p.get("tapped")
            and "creature" in (p.get("card", {}).get("type_line") or "").lower()
        ]

        if not incoming_attackers:
            return 0.0

        my_life = next(
            (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") == my_name),
            20,
        )
        total_incoming = sum(self._perm_power(a) for a in incoming_attackers)

        # Must block if incoming damage is lethal
        if total_incoming >= my_life:
            return 1000.0

        # Score favourable trades: our blocker kills their attacker and nets positive CMC
        # CR 302.6: summoning sickness doesn't prevent blocking — only tapped = can't block
        my_creatures = [
            p for p in all_perms
            if p.get("controller") == my_name
            and not p.get("tapped")
            and "creature" in (p.get("card", {}).get("type_line") or "").lower()
        ]

        net_score = 0.0
        for att in incoming_attackers:
            att_toughness = self._perm_toughness(att)
            att_cmc = self._cmc(att.get("card", {}).get("mana_cost") or "")
            att_has_dt = _card_has_kw(att.get("card", {}), "deathtouch")

            best_trade = -999.0
            for blk in my_creatures:
                if not _can_block(blk, att):
                    continue
                blk_power = self._perm_power(blk)
                blk_cmc = self._cmc(blk.get("card", {}).get("mana_cost") or "")
                blk_has_dt = _card_has_kw(blk.get("card", {}), "deathtouch")

                # Deathtouch: 1 damage is lethal, so any non-zero power kills
                can_kill_attacker = (blk_power >= att_toughness) or (blk_has_dt and blk_power > 0)
                # Attacker kills our blocker if it has enough power or deathtouch
                blk_toughness = self._perm_toughness(blk)
                attacker_kills_blocker = (self._perm_power(att) >= blk_toughness) or (att_has_dt and self._perm_power(att) > 0)

                if can_kill_attacker:
                    trade_value = att_cmc - blk_cmc
                    # Bonus if we survive the trade (our blocker lives)
                    if not attacker_kills_blocker:
                        trade_value += blk_cmc * 0.5
                    if trade_value > best_trade:
                        best_trade = trade_value

            if best_trade >= 0:
                net_score += best_trade * 10.0 + 15.0

        return net_score
