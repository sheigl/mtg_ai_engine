# Story: Cost Reduction / Cost Modification (CR 118.7)

## User Story
As a game engine developer, I want cost reduction and cost increase effects to correctly modify the total cost of spells and abilities, so that effects like "This spell costs {1} less to cast for each artifact you control" work per CR 118.7.

## Context
Cost modification is a multi-step process: start with mana cost or alternative cost, add additional costs and cost increases (including kicker, imposing, etc.), then subtract cost reductions. The total cost can't go below {0} for generic mana, but colored mana requirements can't be reduced below zero for that specific color. Cost increases and reductions are tracked independently and applied in the correct order.

### Comprehensive Rules Grounding
- **CR 118.7**: "The total cost to cast a spell is determined by starting with the mana cost or alternative cost (or the cost to cast a copy), adding all additional costs and cost increases, then subtracting all cost reductions."
- **CR 118.7a**: "Additional costs include kicker, buyback, and other optional costs that the player chooses to pay."
- **CR 118.7b**: "Cost increases apply after additional costs are added."
- **CR 118.7c**: "Cost reductions apply after cost increases. The total cost can't be reduced below {0} for generic mana."
- **CR 118.8**: "If a cost has a colored mana component, it can't be reduced to less than one mana of that color."
- **Example card**: Foundry Inspector — "Artifact spells you cast cost {1} less to cast."

## Acceptance Criteria
- [ ] `calculate_total_cost(gs, card, player, additional_costs)` implements CR 118.7 algorithm
- [ ] Starting point: mana cost or alternative cost (CR 118.7)
- [ ] Additional costs: optional costs like kicker, buyback, imprint costs are added
- [ ] Cost increases: effects that say "costs {N} more" are applied
- [ ] Cost reductions: effects that say "costs {N} less" are applied
- [ ] Generic mana reduction can't go below {0} (CR 118.7c)
- [ ] Colored mana reduction can't go below 1 mana of that color (CR 118.8)
- [ ] Cost reduction effects are persistent (tracked on GameState or battlefield)
- [ ] Cost increases and reductions from multiple sources stack
- [ ] Alternative costs (flashback, escape, mutate, bestow) replace the mana cost entirely
- [ ] Integration tests cover: simple reduction, multiple reductions, reduction + increase, colored reduction limit, alternative cost with reduction, kicker + reduction
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Mana Cost / Mana Value (CR 107.4, 202) — cost parsing and representation

## Priority: Medium

## Status: ❌ Not Implemented

### Gap Description
No general CR 118.7 cost calculation system exists. apply_keyword_cost_reductions() in mana.py handles keyword-specific reductions for Convoke, Delve, Improvise, Affinity, and Emerge, but there is no systematic cost modification layer with cost increases, cost decreases, colored mana reduction limits (CR 118.8), total-cost-can't-go-below-zero enforcement, or integration with the casting pipeline. The project has no calculate_total_cost() function.

## Estimated Effort: M

## Notes
- Cost modification is currently partially implemented (kicker, flashback, escape have alternative costs)
- The cost calculation function should be a pure function: `calc_cost(gs, card, player) -> ManaCost`
- Cost increases and decreases are tracked independently — increases are applied first (CR 118.7b), then decreases (CR 118.7c)
- "Costs {1} less to cast" effects typically apply to spells cast from any zone unless specified
- Some effects reduce "the cost to activate abilities" — these follow the same rules (CR 118.7 applies to abilities too)
- Tribal spells and hybrid mana have special cost considerations
- The mana cost model (ManaCost) needs to support cost calculations (adding/subtracting mana amounts)
