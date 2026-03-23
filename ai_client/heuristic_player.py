"""Competitive heuristic AI player — no LLM calls, pure score-based evaluation."""
import re
from typing import Callable

from .models import PlayerConfig

_MANA_ADD_RE = re.compile(r'Add\s+\{')
_PUMP_RE = re.compile(r'target creature gets \+\d+/\+\d+', re.IGNORECASE)
_COMBAT_STEPS = {"declare_attackers", "declare_blockers", "first_strike_damage", "combat_damage", "end_of_combat"}
_DESTROY_RE = re.compile(r'destroy target|exile target', re.IGNORECASE)
_DAMAGE_TO_TARGET_RE = re.compile(r'deals?\s+(\d+)\s+damage\s+to\s+(?:any\s+target|target\s+creature|target\s+player\s+or\s+planeswalker)', re.IGNORECASE)
_AURA_BOOST_RE = re.compile(r'enchanted creature gets \+(\d+)/\+(\d+)', re.IGNORECASE)


def _perm_power(perm: dict) -> int:
    try:
        return int(perm.get("card", {}).get("power") or 0)
    except (ValueError, TypeError):
        return 0


def _perm_toughness(perm: dict) -> int:
    try:
        return int(perm.get("card", {}).get("toughness") or 0)
    except (ValueError, TypeError):
        return 0


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

        for blk in legal_blockers:
            blk_power = _perm_power(blk)
            blk_cmc = _cmc_str(blk.get("card", {}).get("mana_cost") or "")

            if blk_power >= att_toughness:
                trade_value = att_cmc - blk_cmc
                if trade_value > best_value:
                    best_value = trade_value
                    best_blocker = blk
            elif must_survive:
                chump_value = -blk_cmc
                if chump_value > best_value:
                    best_value = chump_value
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
    ) -> tuple[int, str]:
        """
        Return (action_index, reasoning).
        Scores all legal actions; returns the highest-scoring index.
        Never raises — returns (0, fallback) on any error.
        """
        if not legal_actions:
            return 0, "Heuristic: no actions available (pass)"

        gs = game_state or {}
        my_name = gs.get("priority_player", self._config.name)

        best_idx = 0
        best_score = -1e9
        best_desc = "pass"

        for i, action in enumerate(legal_actions):
            try:
                score = self._score_action(action, gs, my_name)
            except Exception:  # pragma: no cover — defensive catch
                score = 0.0
            if score > best_score:
                best_score = score
                best_idx = i
                best_desc = action.get("description", action.get("action_type", "?"))

        return best_idx, f"Heuristic: {best_desc} (score={best_score:.1f})"

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
            return 0.0

        if action_type == "play_land":
            return self._score_play_land(action, game_state, my_name)

        if action_type == "cast":
            return self._score_cast(action, game_state, my_name)

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
            return 20.0

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

    def _has_any_creatures(self, game_state: dict, my_name: str) -> bool:
        """Return True if the player controls any creature on the battlefield."""
        return any(
            p for p in self._extract_battlefield(game_state, my_name)
            if "creature" in (p.get("card", {}).get("type_line") or "").lower()
        )

    def _score_cast(self, action: dict, game_state: dict, my_name: str) -> float:
        """Score a cast action by CMC, P/T, keywords, timing, and opponent life pressure."""
        mana_options = action.get("mana_options", [{}])
        mana_cost = mana_options[0].get("mana_cost", "") if mana_options else ""
        score = self._cmc(mana_cost) * 10.0

        # Look up full card details from hand for keyword/stat bonuses
        my_info = self._extract_my_info(game_state, my_name)
        card = None
        card_id = action.get("card_id", "")
        card_name = action.get("card_name", "")
        for c in my_info.get("hand", []):
            if c.get("id") == card_id or c.get("name") == card_name:
                card = c
                break

        if card:
            type_line = (card.get("type_line") or "").lower()
            try:
                power = int(card.get("power") or 0)
            except (ValueError, TypeError):
                power = 0

            # Combat tricks (e.g. Giant Growth): require a friendly creature to target.
            # Even if the engine shows the action (opponent has creatures), we should
            # never buff an opponent's creature. Also avoid casting when nothing will
            # be in combat.
            if self._is_combat_trick(card):
                if not self._has_any_creatures(game_state, my_name):
                    # No friendly creatures — nothing useful to target
                    return -100.0
                step = self._current_step(game_state)
                phase = (game_state.get("phase") or "").lower()
                in_combat = step in _COMBAT_STEPS
                has_attacker = self._has_attackable_creatures(game_state, my_name)
                if not in_combat and not has_attacker:
                    # No attack and no combat — pointless to cast now
                    return -50.0
                if in_combat:
                    # During combat: highly valuable
                    score += 40.0
                elif has_attacker and phase == "precombat_main":
                    # Pre-combat main phase with a ready attacker: worth holding for combat
                    score += 15.0
                else:
                    # Upkeep, draw, or other non-combat steps — wasteful to cast pump now
                    return -50.0

            if "creature" in type_line:
                if power >= 3:
                    score += 20.0

                # ── Evasion (Forge: power × multiplier) ──────────────────
                if self._has_keyword(card, "flying"):
                    score += power * 8.0   # strongest evasion
                elif self._has_keyword(card, "fear") or self._has_keyword(card, "intimidate"):
                    score += power * 5.0
                elif self._has_keyword(card, "menace"):
                    score += power * 3.0

                # ── Combat power keywords ─────────────────────────────────
                if self._has_keyword(card, "double strike"):
                    score += 10.0 + power * 10.0   # exponential advantage
                elif self._has_keyword(card, "first strike"):
                    score += 5.0 + power * 3.0

                if self._has_keyword(card, "deathtouch"):
                    score += 25.0   # fixed — even a 1/1 is excellent
                if self._has_keyword(card, "lifelink"):
                    score += power * 5.0
                if self._has_keyword(card, "trample"):
                    score += max(0, power - 1) * 4.0
                if self._has_keyword(card, "haste"):
                    score += power * 4.0   # can attack immediately
                if self._has_keyword(card, "vigilance"):
                    try:
                        toughness = int(card.get("toughness") or 0)
                    except (ValueError, TypeError):
                        toughness = 0
                    score += (power * 3.0) + (toughness * 3.0)

                # ── Defensive keywords ────────────────────────────────────
                if self._has_keyword(card, "indestructible"):
                    score += 40.0
                elif self._has_keyword(card, "hexproof"):
                    score += 20.0
                elif self._has_keyword(card, "shroud"):
                    score += 15.0

            # ── Planeswalker ──────────────────────────────────────────────
            elif "planeswalker" in type_line:
                try:
                    loyalty = int(card.get("loyalty") or 0)
                except (ValueError, TypeError):
                    loyalty = 0
                score += 40.0 + loyalty * 8.0  # planeswalkers generate sustained card advantage

            # ── Aura (enchant creature) ───────────────────────────────────
            elif "enchantment" in type_line:
                oracle = card.get("oracle_text") or ""
                if "enchant creature" in oracle.lower():
                    if not self._has_any_creatures(game_state, my_name):
                        return -20.0  # no target, can't cast meaningfully
                    boost_m = _AURA_BOOST_RE.search(oracle)
                    if boost_m:
                        p_boost = int(boost_m.group(1))
                        t_boost = int(boost_m.group(2))
                        score += p_boost * 8.0 + t_boost * 4.0
                    # Keyword grants on the aura
                    for kw in ("flying", "trample", "deathtouch", "lifelink", "haste"):
                        if kw in oracle.lower():
                            score += 10.0

            # ── Instant/Sorcery: removal and burn ────────────────────────
            elif "instant" in type_line or "sorcery" in type_line:
                oracle = card.get("oracle_text") or ""
                all_perms = game_state.get("battlefield", [])
                opp_name_local = next(
                    (p.get("name") for p in game_state.get("players", []) if p.get("name") != my_name), ""
                )
                opp_creatures = [
                    p for p in all_perms
                    if p.get("controller") == opp_name_local
                    and "creature" in (p.get("card", {}).get("type_line") or "").lower()
                ]

                if _DESTROY_RE.search(oracle):
                    # Removal: value = best target's CMC, capped
                    best_target_cmc = max(
                        (_cmc_str(p.get("card", {}).get("mana_cost") or "") for p in opp_creatures),
                        default=0,
                    )
                    if best_target_cmc > 0:
                        score += min(best_target_cmc * 12.0, 80.0)
                    else:
                        score -= 20.0  # no valid target, don't cast now

                damage_m = _DAMAGE_TO_TARGET_RE.search(oracle)
                if damage_m:
                    dmg = int(damage_m.group(1))
                    # Burn: value = kills a creature OR deals meaningful face damage
                    kills_creature = any(
                        _perm_toughness(p) <= dmg for p in opp_creatures
                    )
                    if kills_creature:
                        best_kill_cmc = max(
                            (_cmc_str(p.get("card", {}).get("mana_cost") or "")
                             for p in opp_creatures if _perm_toughness(p) <= dmg),
                            default=0,
                        )
                        score += best_kill_cmc * 10.0 + 20.0
                    else:
                        # Face burn: value proportional to damage relative to opponent life
                        opp_life_local = next(
                            (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") != my_name), 20
                        )
                        score += (dmg / max(opp_life_local, 1)) * 40.0

        # Aggression multiplier when opponent life is low
        opp_life = next(
            (p.get("life", 20) for p in game_state.get("players", []) if p.get("name") != my_name),
            20,
        )
        if opp_life <= 6:
            score *= 1.5

        return score

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

        # Never return negative — pass is always score 0
        return max(score, 0.0)

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
        my_creatures = [
            p for p in all_perms
            if p.get("controller") == my_name
            and not p.get("tapped")
            and not p.get("summoning_sick")
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
