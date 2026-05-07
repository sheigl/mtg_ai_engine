import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.card_data.ability_parser import (
    KEYWORDS,
    parse_effect_patterns,
    parse_targets,
    EffectPattern,
    TargetInfo,
)


# =============================================================================
# PAR-01: Extended keyword support tests
# =============================================================================

def test_keyword_count_50_plus():
    """PAR-01: Keyword set must contain 50+ keywords."""
    assert len(KEYWORDS) >= 50, f"Expected 50+ keywords, got {len(KEYWORDS)}"


def test_core_keywords_present():
    """PAR-01: All core combat keywords present."""
    core = {
        "deathtouch", "defender", "double strike", "equip",
        "first strike", "flash", "flying", "haste", "hexproof",
        "indestructible", "lifelink", "menace", "protection",
        "reach", "shroud", "trample", "vigilance", "ward",
    }
    assert core.issubset(KEYWORDS), f"Missing core keywords: {core - KEYWORDS}"


def test_casting_keywords_present():
    """PAR-01: Casting & alternative cost keywords present."""
    casting = {"kicker", "cascade", "convoke", "entwine", "escape",
               "foretell", "fuse", "overload", "suspend", "morph",
               "mutate", "madness", "manifest", "megamorph", "modular",
               "level up", "prowess", "replicate", "rampage", "scry",
               "split second", "tribute", "undying", "vanishing"}
    missing = casting - KEYWORDS
    assert not missing, f"Missing casting keywords: {missing}"


def test_creature_interaction_keywords_present():
    """PAR-01: Creature interaction keywords present."""
    interaction = {"banding", "bushido", "changeling", "champion", "cipher",
                   "companion", "conspire", "crew", "cycling", "dredge",
                   "echo", "evolve", "exalted", "extort", "fear",
                   "flanking", "frenzy", "fortify", "grapple", "guard",
                   "haunt", "hideaway", "horsemanship", "imprint",
                   "infect", "jump-start", "menace", "myriad",
                   "ninjutsu", "outlast", "partner", "persist",
                   "phasing", "poisonous", "provoke", "prowl",
                   "recover", "reconfigure", "reflect", "renown",
                   "retrace", "riot", "ripple", "saddle", "scavenge",
                   "shadow", "skulk", "soulbond", "splice", "squad",
                   "station", "strive", "sunburst", "surge",
                   "toxic", "training", "transmute", "typecycling",
                   "undaunted", "unearth", "unleash", "venture",
                   "web-slinging", "wither"}
    missing = interaction - KEYWORDS
    assert not missing, f"Missing creature interaction keywords: {missing}"


def test_token_counter_keywords_present():
    """PAR-01: Token & counter keywords present."""
    token_counter = {"afterlife", "aftermath", "amplify", "annihilator",
                     "ascend", "assist", "aura swap", "awaken",
                     "backup", "bargain", "battle cry", "bestow",
                     "blitz", "bloodthirst", "casualty", "craft",
                     "devour", "devoid", "disguise", "disturb",
                     "double team", "demonstrate", "dethrone",
                     "eternalize", "evoke", "fabricate", "gift",
                     "graft", "gravestorm", "harmonize", "heist",
                     "investigate", "intensify", "learn", "mentor",
                     "meld", "mobilize", "multikicker", "offspring",
                     "proliferate", "scry", "seek", "set in motion",
                     "spree", "soulshift", "take initiative",
                     "toxic", "transfigure", "transmute", "tribute",
                     "typecycling", "umbra armor", "undaunted",
                     "undying", "unearth", "unleash", "venture",
                     "ward", "web-slinging", "wither"}
    missing = token_counter - KEYWORDS
    assert not missing, f"Missing token/counter keywords: {missing}"


# =============================================================================
# PAR-02: Extended effect pattern tests
# =============================================================================

def test_deal_damage_pattern():
    """PAR-02: Deal damage effect pattern."""
    effects = parse_effect_patterns("Lightning Bolt deals 3 damage to any target.")
    assert len(effects) > 0
    assert any(e.effect_type == "deal_damage" for e in effects)


def test_draw_card_pattern():
    """PAR-02: Draw card effect pattern."""
    effects = parse_effect_patterns("Draw a card.")
    assert len(effects) > 0
    assert any(e.effect_type == "draw" for e in effects)


def test_create_token_pattern():
    """PAR-02: Create token effect pattern."""
    effects = parse_effect_patterns("Create a 1/1 green Elf creature token.")
    assert len(effects) > 0
    assert any(e.effect_type == "create_token" for e in effects)


def test_gain_life_pattern():
    """PAR-02: Gain life effect pattern."""
    effects = parse_effect_patterns("You gain 4 life.")
    assert len(effects) > 0
    assert any(e.effect_type == "gain_life" for e in effects)


def test_put_counter_pattern():
    """PAR-02: Put counter effect pattern."""
    effects = parse_effect_patterns("Put a +1/+1 counter on target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "put_counter" for e in effects)


def test_destroy_pattern():
    """PAR-02: Destroy effect pattern."""
    effects = parse_effect_patterns("Destroy target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "destroy" for e in effects)


def test_search_library_pattern():
    """PAR-02: Search library effect pattern."""
    effects = parse_effect_patterns("Search your library for a basic land card.")
    assert len(effects) > 0
    assert any(e.effect_type == "search_library" for e in effects)


def test_exile_pattern():
    """PAR-02: Exile effect pattern."""
    effects = parse_effect_patterns("Exile target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "exile" for e in effects)


def test_discard_pattern():
    """PAR-02: Discard effect pattern."""
    effects = parse_effect_patterns("Discard a card.")
    assert len(effects) > 0
    assert any(e.effect_type == "discard" for e in effects)


def test_tap_pattern():
    """PAR-02: Tap effect pattern."""
    effects = parse_effect_patterns("Tap target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "tap" for e in effects)


def test_mill_pattern():
    """PAR-02: Mill effect pattern."""
    effects = parse_effect_patterns("Target player mills three cards.")
    assert len(effects) > 0
    assert any(e.effect_type == "mill" for e in effects)


def test_scry_pattern():
    """PAR-02: Scry effect pattern."""
    effects = parse_effect_patterns("Scry 2.")
    assert len(effects) > 0
    assert any(e.effect_type == "scry" for e in effects)


def test_counter_spell_pattern():
    """PAR-02: Counter spell effect pattern."""
    effects = parse_effect_patterns("Counter target spell.")
    assert len(effects) > 0
    assert any(e.effect_type == "counter" for e in effects)


def test_gain_control_pattern():
    """PAR-02: Gain control effect pattern."""
    effects = parse_effect_patterns("Gain control of target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "gain_control" for e in effects)


def test_sacrifice_pattern():
    """PAR-02: Sacrifice effect pattern."""
    effects = parse_effect_patterns("Sacrifice target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "sacrifice" for e in effects)


def test_return_to_hand_pattern():
    """PAR-02: Return to hand effect pattern."""
    effects = parse_effect_patterns("Return target creature to its owner's hand.")
    assert len(effects) > 0
    assert any(e.effect_type == "return_to_hand" for e in effects)


def test_pump_pattern():
    """PAR-02: Pump effect pattern."""
    effects = parse_effect_patterns("Target creature gets +1/+1 until end of turn.")
    assert len(effects) > 0
    assert any(e.effect_type == "pump" for e in effects)


def test_add_mana_pattern():
    """PAR-02: Add mana effect pattern."""
    effects = parse_effect_patterns("Add {W}.")
    assert len(effects) > 0
    assert any(e.effect_type == "add_mana" for e in effects)


def test_reveal_pattern():
    """PAR-02: Reveal effect pattern."""
    effects = parse_effect_patterns("Reveal the top three cards of your library.")
    assert len(effects) > 0
    assert any(e.effect_type == "reveal" for e in effects)


def test_copy_pattern():
    """PAR-02: Copy effect pattern."""
    effects = parse_effect_patterns("Copy target instant or sorcery spell.")
    assert len(effects) > 0
    assert any(e.effect_type == "copy" for e in effects)


def test_attach_pattern():
    """PAR-02: Attach effect pattern."""
    effects = parse_effect_patterns("Attach this Aura to target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "attach" for e in effects)


def test_transform_pattern():
    """PAR-02: Transform effect pattern."""
    effects = parse_effect_patterns("Transform target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "transform" for e in effects)


def test_flip_coin_pattern():
    """PAR-02: Flip coin effect pattern."""
    effects = parse_effect_patterns("Flip a coin. If you lose, sacrifice this creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "flip_coin" for e in effects)


def test_proliferate_pattern():
    """PAR-02: Proliferate effect pattern."""
    effects = parse_effect_patterns("Proliferate.")
    assert len(effects) > 0
    assert any(e.effect_type == "proliferate" for e in effects)


def test_discover_pattern():
    """PAR-02: Discover effect pattern."""
    effects = parse_effect_patterns("Discover 3.")
    assert len(effects) > 0
    assert any(e.effect_type == "discover" for e in effects)


def test_gain_ability_pattern():
    """PAR-02: Gain ability effect pattern."""
    effects = parse_effect_patterns("Target creature gets flying.")
    assert len(effects) > 0
    assert any(e.effect_type == "gain_ability" for e in effects)


def test_lose_ability_pattern():
    """PAR-02: Lose ability effect pattern."""
    effects = parse_effect_patterns("Target creature loses flying.")
    assert len(effects) > 0
    assert any(e.effect_type == "lose_ability" for e in effects)


def test_become_type_pattern():
    """PAR-02: Become type effect pattern."""
    effects = parse_effect_patterns("Target creature becomes a Dragon.")
    assert len(effects) > 0
    assert any(e.effect_type == "become_type" for e in effects)


def test_set_loyalty_pattern():
    """PAR-02: Set loyalty effect pattern."""
    effects = parse_effect_patterns("Set its loyalty to 0.")
    assert len(effects) > 0
    assert any(e.effect_type == "set_loyalty" for e in effects)


def test_reveal_hand_pattern():
    """PAR-02: Reveal hand effect pattern."""
    effects = parse_effect_patterns("Reveal your hand.")
    assert len(effects) > 0
    assert any(e.effect_type == "reveal_hand" for e in effects)


def test_exchange_pattern():
    """PAR-02: Exchange effect pattern."""
    effects = parse_effect_patterns("Exchange control of target creature and target player.")
    assert len(effects) > 0
    assert any(e.effect_type == "exchange" for e in effects)


def test_prevent_damage_pattern():
    """PAR-02: Prevent damage effect pattern."""
    effects = parse_effect_patterns("Prevent all damage that would be dealt by target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "prevent_damage" for e in effects)


def test_regenerate_pattern():
    """PAR-02: Regenerate effect pattern."""
    effects = parse_effect_patterns("Regenerate target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "regenerate" for e in effects)


def test_lose_life_pattern():
    """PAR-02: Lose life effect pattern."""
    effects = parse_effect_patterns("Target player loses 3 life.")
    assert len(effects) > 0
    assert any(e.effect_type == "lose_life" for e in effects)


def test_untap_pattern():
    """PAR-02: Untap effect pattern."""
    effects = parse_effect_patterns("Untap target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "untap" for e in effects)


def test_remove_counter_pattern():
    """PAR-02: Remove counter effect pattern."""
    effects = parse_effect_patterns("Remove a +1/+1 counter from target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "remove_counter" for e in effects)


def test_look_at_pattern():
    """PAR-02: Look at effect pattern."""
    effects = parse_effect_patterns("Look at the top three cards of your library.")
    assert len(effects) > 0
    assert any(e.effect_type == "look_at" for e in effects)


def test_become_color_pattern():
    """PAR-02: Become color effect pattern."""
    effects = parse_effect_patterns("Target creature becomes red until end of turn.")
    assert len(effects) > 0
    assert any(e.effect_type == "become_color" for e in effects)


def test_destroy_all_pattern():
    """PAR-02: Destroy all effect pattern."""
    effects = parse_effect_patterns("Destroy all creatures.")
    assert len(effects) > 0
    assert any(e.effect_type == "destroy_all" for e in effects)


def test_exile_all_pattern():
    """PAR-02: Exile all effect pattern."""
    effects = parse_effect_patterns("Exile all creatures.")
    assert len(effects) > 0
    assert any(e.effect_type == "exile_all" for e in effects)


def test_remove_counter_all_pattern():
    """PAR-02: Remove all counters effect pattern."""
    effects = parse_effect_patterns("Remove all counters from target creature.")
    assert len(effects) > 0
    assert any(e.effect_type == "remove_counter_all" for e in effects)


def test_would_deal_damage_pattern():
    """PAR-02: Would deal damage effect pattern."""
    effects = parse_effect_patterns("Whenever a creature would deal damage, prevent that damage.")
    assert len(effects) > 0
    assert any(e.effect_type == "would_deal_damage" for e in effects)


def test_set_pt_pattern():
    """PAR-02: Set P/T effect pattern."""
    effects = parse_effect_patterns("Target creature becomes 4/4 until end of turn.")
    assert len(effects) > 0
    assert any(e.effect_type == "set_pt" for e in effects)


# =============================================================================
# PAR-03: Targeting pattern tests
# =============================================================================

def test_target_creature():
    """PAR-03: Target creature pattern."""
    targets = parse_targets("Deal 3 damage to target creature.")
    assert len(targets) > 0
    assert any(t.target_type == "creature" for t in targets)


def test_target_player():
    """PAR-03: Target player pattern."""
    targets = parse_targets("Target player draws a card.")
    assert len(targets) > 0
    assert any(t.target_type == "player" for t in targets)


def test_target_spell():
    """PAR-03: Target spell pattern."""
    targets = parse_targets("Counter target spell.")
    assert len(targets) > 0
    assert any(t.target_type == "spell" for t in targets)


def test_target_permanent():
    """PAR-03: Target permanent pattern."""
    targets = parse_targets("Destroy target permanent.")
    assert len(targets) > 0
    assert any(t.target_type == "permanent" for t in targets)


def test_target_land():
    """PAR-03: Target land pattern."""
    targets = parse_targets("Tap target land.")
    assert len(targets) > 0
    assert any(t.target_type == "land" for t in targets)


def test_target_card():
    """PAR-03: Target card pattern."""
    targets = parse_targets("Exile target card.")
    assert len(targets) > 0
    assert any(t.target_type == "card" for t in targets)


def test_target_any():
    """PAR-03: Target any pattern."""
    targets = parse_targets("Deal 3 damage to any target.")
    assert len(targets) > 0
    assert any(t.target_type == "any" for t in targets)


def test_target_restricted_creature():
    """PAR-03: Restricted target creature pattern."""
    targets = parse_targets("Deal 3 damage to target red creature.")
    assert len(targets) > 0
    creature_targets = [t for t in targets if t.target_type == "creature"]
    assert len(creature_targets) > 0
    assert creature_targets[0].target_restriction is not None


def test_target_multiple():
    """PAR-03: Multiple targets pattern."""
    targets = parse_targets("Return target creature and target enchantment to their owners' hands.")
    assert len(targets) >= 1


def test_target_optional():
    """PAR-03: Optional target pattern."""
    targets = parse_targets("Target creature, if able.")
    assert len(targets) > 0
    assert any(t.is_optional for t in targets)


def test_target_number():
    """PAR-03: Target number pattern."""
    targets = parse_targets("Deal 2 damage to target 3 creatures.")
    assert len(targets) > 0


def test_target_battlefield():
    """PAR-03: Target battlefield pattern."""
    targets = parse_targets("Put a +1/+1 counter on target battlefield.")
    assert len(targets) > 0
    assert any(t.target_type == "battlefield" for t in targets)
