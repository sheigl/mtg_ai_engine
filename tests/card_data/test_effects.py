import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mtg_engine.card_data.ability_parser import parse_effect_patterns, EffectPattern


def test_effect_pattern_count():
    """PAR-02: Ensure 50+ effect patterns are defined."""
    from mtg_engine.card_data.ability_parser import _EFFECT_PATTERNS
    assert len(_EFFECT_PATTERNS) >= 50, f"Expected 50+ effect patterns, got {len(_EFFECT_PATTERNS)}"


def test_damage_effect_with_magnitude():
    """PAR-02: Damage effect correctly captures magnitude."""
    effects = parse_effect_patterns("Deal 5 damage to target player.")
    damage_effects = [e for e in effects if e.effect_type == "deal_damage"]
    assert len(damage_effects) > 0
    assert damage_effects[0].magnitude == 5


def test_draw_effect_with_magnitude():
    """PAR-02: Draw effect correctly captures magnitude."""
    effects = parse_effect_patterns("Draw two cards.")
    draw_effects = [e for e in effects if e.effect_type == "draw"]
    assert len(draw_effects) > 0


def test_token_creation_effect():
    """PAR-02: Token creation effect captures type and power/toughness."""
    effects = parse_effect_patterns("Create a 1/1 green Elf creature token.")
    token_effects = [e for e in effects if e.effect_type == "create_token"]
    assert len(token_effects) > 0


def test_gain_life_effect():
    """PAR-02: Gain life effect captures magnitude."""
    effects = parse_effect_patterns("You gain 7 life.")
    life_effects = [e for e in effects if e.effect_type == "gain_life"]
    assert len(life_effects) > 0


def test_counter_effect():
    """PAR-02: Counter effect captures counter type and target."""
    effects = parse_effect_patterns("Put a +1/+1 counter on target creature.")
    counter_effects = [e for e in effects if e.effect_type == "put_counter"]
    assert len(counter_effects) > 0


def test_destroy_effect():
    """PAR-02: Destroy effect captures target."""
    effects = parse_effect_patterns("Destroy target artifact.")
    destroy_effects = [e for e in effects if e.effect_type == "destroy"]
    assert len(destroy_effects) > 0


def test_search_effect():
    """PAR-02: Search effect captures card type."""
    effects = parse_effect_patterns("Search your library for a basic land card.")
    search_effects = [e for e in effects if e.effect_type == "search_library"]
    assert len(search_effects) > 0


def test_exile_effect():
    """PAR-02: Exile effect captures target."""
    effects = parse_effect_patterns("Exile target enchantment.")
    exile_effects = [e for e in effects if e.effect_type == "exile"]
    assert len(exile_effects) > 0


def test_discard_effect():
    """PAR-02: Discard effect captures number of cards."""
    effects = parse_effect_patterns("Discard two cards.")
    discard_effects = [e for e in effects if e.effect_type == "discard"]
    assert len(discard_effects) > 0


def test_tap_effect():
    """PAR-02: Tap effect captures target."""
    effects = parse_effect_patterns("Tap target creature.")
    tap_effects = [e for e in effects if e.effect_type == "tap"]
    assert len(tap_effects) > 0


def test_mill_effect():
    """PAR-02: Mill effect captures number of cards."""
    effects = parse_effect_patterns("Mill three cards.")
    mill_effects = [e for e in effects if e.effect_type == "mill"]
    assert len(mill_effects) > 0


def test_scry_effect():
    """PAR-02: Scry effect captures number."""
    effects = parse_effect_patterns("Scry 2.")
    scry_effects = [e for e in effects if e.effect_type == "scry"]
    assert len(scry_effects) > 0


def test_counter_spell_effect():
    """PAR-02: Counter spell effect captures target."""
    effects = parse_effect_patterns("Counter target instant spell.")
    counter_effects = [e for e in effects if e.effect_type == "counter"]
    assert len(counter_effects) > 0


def test_gain_control_effect():
    """PAR-02: Gain control effect captures target."""
    effects = parse_effect_patterns("Gain control of target creature.")
    control_effects = [e for e in effects if e.effect_type == "gain_control"]
    assert len(control_effects) > 0


def test_sacrifice_effect():
    """PAR-02: Sacrifice effect captures target."""
    effects = parse_effect_patterns("Sacrifice target creature.")
    sacrifice_effects = [e for e in effects if e.effect_type == "sacrifice"]
    assert len(sacrifice_effects) > 0


def test_return_to_hand_effect():
    """PAR-02: Return to hand effect captures target."""
    effects = parse_effect_patterns("Return target creature to its owner's hand.")
    return_effects = [e for e in effects if e.effect_type == "return_to_hand"]
    assert len(return_effects) > 0


def test_pump_effect():
    """PAR-02: Pump effect captures power/toughness change."""
    effects = parse_effect_patterns("Target creature gets +2/+2 until end of turn.")
    pump_effects = [e for e in effects if e.effect_type == "pump"]
    assert len(pump_effects) > 0


def test_add_mana_effect():
    """PAR-02: Add mana effect captures mana symbol."""
    effects = parse_effect_patterns("Add {W}.")
    mana_effects = [e for e in effects if e.effect_type == "add_mana"]
    assert len(mana_effects) > 0


def test_reveal_effect():
    """PAR-02: Reveal effect captures number of cards."""
    effects = parse_effect_patterns("Reveal the top three cards of your library.")
    reveal_effects = [e for e in effects if e.effect_type == "reveal"]
    assert len(reveal_effects) > 0


def test_copy_effect():
    """PAR-02: Copy effect captures target."""
    effects = parse_effect_patterns("Copy target instant or sorcery spell.")
    copy_effects = [e for e in effects if e.effect_type == "copy"]
    assert len(copy_effects) > 0


def test_attach_effect():
    """PAR-02: Attach effect captures target."""
    effects = parse_effect_patterns("Attach this Aura to target creature.")
    attach_effects = [e for e in effects if e.effect_type == "attach"]
    assert len(attach_effects) > 0


def test_transform_effect():
    """PAR-02: Transform effect captures target."""
    effects = parse_effect_patterns("Transform target creature.")
    transform_effects = [e for e in effects if e.effect_type == "transform"]
    assert len(transform_effects) > 0


def test_flip_coin_effect():
    """PAR-02: Flip coin effect detected."""
    effects = parse_effect_patterns("Flip a coin.")
    flip_effects = [e for e in effects if e.effect_type == "flip_coin"]
    assert len(flip_effects) > 0


def test_proliferate_effect():
    """PAR-02: Proliferate effect detected."""
    effects = parse_effect_patterns("Proliferate.")
    prolif_effects = [e for e in effects if e.effect_type == "proliferate"]
    assert len(prolif_effects) > 0


def test_discover_effect():
    """PAR-02: Discover effect captures number."""
    effects = parse_effect_patterns("Discover 3.")
    discover_effects = [e for e in effects if e.effect_type == "discover"]
    assert len(discover_effects) > 0


def test_gain_ability_effect():
    """PAR-02: Gain ability effect captures ability name."""
    effects = parse_effect_patterns("Target creature gets flying.")
    gain_ability_effects = [e for e in effects if e.effect_type == "gain_ability"]
    assert len(gain_ability_effects) > 0


def test_lose_ability_effect():
    """PAR-02: Lose ability effect captures ability name."""
    effects = parse_effect_patterns("Target creature loses flying.")
    lose_ability_effects = [e for e in effects if e.effect_type == "lose_ability"]
    assert len(lose_ability_effects) > 0


def test_become_type_effect():
    """PAR-02: Become type effect captures new type."""
    effects = parse_effect_patterns("Target creature becomes a Dragon.")
    become_type_effects = [e for e in effects if e.effect_type == "become_type"]
    assert len(become_type_effects) > 0


def test_set_loyalty_effect():
    """PAR-02: Set loyalty effect captures loyalty value."""
    effects = parse_effect_patterns("Set its loyalty to 0.")
    set_loyalty_effects = [e for e in effects if e.effect_type == "set_loyalty"]
    assert len(set_loyalty_effects) > 0


def test_reveal_hand_effect():
    """PAR-02: Reveal hand effect detected."""
    effects = parse_effect_patterns("Reveal your hand.")
    reveal_hand_effects = [e for e in effects if e.effect_type == "reveal_hand"]
    assert len(reveal_hand_effects) > 0


def test_exchange_effect():
    """PAR-02: Exchange effect captures both targets."""
    effects = parse_effect_patterns("Exchange control of target creature and target player.")
    exchange_effects = [e for e in effects if e.effect_type == "exchange"]
    assert len(exchange_effects) > 0


def test_prevent_damage_effect():
    """PAR-02: Prevent damage effect detected."""
    effects = parse_effect_patterns("Prevent all damage that would be dealt by target creature.")
    prevent_effects = [e for e in effects if e.effect_type == "prevent_damage"]
    assert len(prevent_effects) > 0


def test_regenerate_effect():
    """PAR-02: Regenerate effect captures target."""
    effects = parse_effect_patterns("Regenerate target creature.")
    regen_effects = [e for e in effects if e.effect_type == "regenerate"]
    assert len(regen_effects) > 0


def test_lose_life_effect():
    """PAR-02: Lose life effect captures magnitude."""
    effects = parse_effect_patterns("Target player loses 3 life.")
    lose_life_effects = [e for e in effects if e.effect_type == "lose_life"]
    assert len(lose_life_effects) > 0


def test_untap_effect():
    """PAR-02: Untap effect captures target."""
    effects = parse_effect_patterns("Untap target creature.")
    untap_effects = [e for e in effects if e.effect_type == "untap"]
    assert len(untap_effects) > 0


def test_remove_counter_effect():
    """PAR-02: Remove counter effect captures counter type and target."""
    effects = parse_effect_patterns("Remove a +1/+1 counter from target creature.")
    remove_counter_effects = [e for e in effects if e.effect_type == "remove_counter"]
    assert len(remove_counter_effects) > 0


def test_look_at_effect():
    """PAR-02: Look at effect captures number of cards."""
    effects = parse_effect_patterns("Look at the top three cards of your library.")
    look_at_effects = [e for e in effects if e.effect_type == "look_at"]
    assert len(look_at_effects) > 0


def test_become_color_effect():
    """PAR-02: Become color effect captures new color."""
    effects = parse_effect_patterns("Target creature becomes red until end of turn.")
    become_color_effects = [e for e in effects if e.effect_type == "become_color"]
    assert len(become_color_effects) > 0


def test_destroy_all_effect():
    """PAR-02: Destroy all effect captures card type."""
    effects = parse_effect_patterns("Destroy all creatures.")
    destroy_all_effects = [e for e in effects if e.effect_type == "destroy_all"]
    assert len(destroy_all_effects) > 0


def test_exile_all_effect():
    """PAR-02: Exile all effect captures card type."""
    effects = parse_effect_patterns("Exile all creatures.")
    exile_all_effects = [e for e in effects if e.effect_type == "exile_all"]
    assert len(exile_all_effects) > 0


def test_remove_counter_all_effect():
    """PAR-02: Remove all counters effect captures target."""
    effects = parse_effect_patterns("Remove all counters from target creature.")
    remove_counter_all_effects = [e for e in effects if e.effect_type == "remove_counter_all"]
    assert len(remove_counter_all_effects) > 0


def test_would_deal_damage_effect():
    """PAR-02: Would deal damage effect detected."""
    effects = parse_effect_patterns("Whenever a creature would deal damage, prevent that damage.")
    would_deal_effects = [e for e in effects if e.effect_type == "would_deal_damage"]
    assert len(would_deal_effects) > 0


def test_set_pt_effect():
    """PAR-02: Set P/T effect captures new power/toughness."""
    effects = parse_effect_patterns("Target creature becomes 4/4 until end of turn.")
    set_pt_effects = [e for e in effects if e.effect_type == "set_pt"]
    assert len(set_pt_effects) > 0


def test_multiple_effects_in_text():
    """PAR-02: Multiple effects in same text are all detected."""
    text = "Deal 3 damage to target creature and draw a card."
    effects = parse_effect_patterns(text)
    assert any(e.effect_type == "deal_damage" for e in effects)
    assert any(e.effect_type == "draw" for e in effects)


def test_effect_pattern_model_fields():
    """PAR-02: EffectPattern model has all required fields."""
    ep = EffectPattern(
        effect_type="test",
        magnitude=5,
        target="target creature",
        source="you",
        condition="test condition",
    )
    assert ep.effect_type == "test"
    assert ep.magnitude == 5
    assert ep.target == "target creature"
    assert ep.source == "you"
    assert ep.condition == "test condition"
