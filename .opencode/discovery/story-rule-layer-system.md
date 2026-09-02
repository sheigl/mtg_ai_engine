# Story: Layer System (CR 613)

## User Story
As a game engine developer, I want continuous effects to be applied in the correct layer order (1-7), so that effects like "creature becomes a 1/1" and "+3/+3" resolve in the right order per CR 613.

## Context
The layer system determines how multiple continuous effects interact. Effects are applied in 7 layers in order: copy effects (1), control-changing effects (2), text-changing effects (3), type-changing effects (4), color-changing effects (5), ability-adding/removing effects (6), and power/toughness-modifying effects (7). Layer 7 is further subdivided into sublayers for setting P/T, modifying P/T via counters, and modifying P/T via effects.

### Comprehensive Rules Grounding
- **CR 613.1**: "Continuous effects are applied in a series of layers in order: (1) copy, (2) control, (3) text, (4) type, (5) color, (6) add/remove abilities, (7) power/toughness."
- **CR 613.1a**: "Layer 1: Copy effects are applied."
- **CR 613.1b**: "Layer 2: Control-changing effects are applied."
- **CR 613.1c**: "Layer 3: Text-changing effects are applied."
- **CR 613.1d**: "Layer 4: Type-changing effects are applied."
- **CR 613.1e**: "Layer 5: Color-changing effects are applied."
- **CR 613.1f**: "Layer 6: Ability-adding and ability-removing effects are applied."
- **CR 613.1g-i**: "Layer 7: Power/toughness effects are applied in sublayers: (a) P/T-setting effects, (b) P/T-modifying effects, (c) P/T counters."
- **CR 613.3**: "Within each layer, effects are applied in timestamp order (older effects before newer effects)."
- **CR 613.4**: "Except in layers 2 and 3, dependency rules may override timestamp order."
- **Example card**: Ensoul Artifact vs. an animated land — layer interactions determine final P/T

## Acceptance Criteria
- [ ] Layered effect manager collects all continuous effects from battlefield permanents
- [ ] Effects are sorted into their correct layers (1-7)
- [ ] Within each layer, effects are applied in timestamp order (CR 613.3)
- [ ] Dependency rules are checked before applying within-layer order (CR 613.4)
- [ ] Layer 7 sublayers: (a) P/T-setting, (b) P/T-modifying, (c) P/T counters (CR 613.1g-i)
- [ ] Copy effects (layer 1) are applied first — copied objects use the copy's characteristics as "base"
- [ ] Control-changing effects (layer 2) are applied after copy
- [ ] Type-changing effects (layer 4) affect type line (e.g., "becomes an artifact")
- [ ] Color-changing effects (layer 5) affect colors
- [ ] Ability-adding/removing effects (layer 6) add/remove abilities like flying, deathtouch
- [ ] P/T effects (layer 7): setting (e.g., "base 1/1") vs. modifying (e.g., "+1/+1") vs. counters
- [ ] Integration tests cover: P/T setting vs. modifying interaction, two +1/+1 effects stacking, "becomes creature" + P/T setting, copy + P/T setting
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone system that can be developed independently)

## Priority: High

## Status: 🔄 Partial

### Gap Description
Full layer system framework exists (EffectLayer enum, ContinuousEffect model, collect_continuous_effects(), apply_continuous_effects() with layers 1-7 and P/T sublayers, timestamp ordering, dependency computation). But limited to basic pattern matching: only captures +1/+1 pumps, aura bonuses, 'creatures lose all abilities', 'creatures are 1/1', 'is all colors' patterns. Many continuous effect types (land animation, anthem effects from non-aura sources, type-setting effects) are not collected.

## Estimated Effort: L

## Notes
- This is arguably the most complex subsystem in Magic's rules — getting layer ordering wrong breaks many cards
- The engine needs a centralized `ContinuousEffectLayerManager` that all effect-adding code paths go through
- Timestamp ordering: track the order in which effects entered the battlefield or were created
- Dependency: if effect A depends on effect B (A's text refers to B), then B is applied before A (CR 613.4)
- Key interaction to test: "Creatures you control get +1/+1" (layer 7b) vs "Target creature becomes a 1/1" (layer 7a) — the setting effect applies first, then the modifying effect
- Counters (sublayer 7c) are applied last, so they always count regardless of P/T-setting effects
- The layer system currently may be partially implemented — this story formalizes the complete 7-layer pipeline
