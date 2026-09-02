# Story: Additional Costs (CR 118.9)

## User Story
As a game engine developer, I want the additional cost system to function correctly per the Comprehensive Rules, so that cards with mandatory additional costs (such as "As an additional cost to cast this spell, sacrifice a creature") are properly enforced during casting.

## Context
Additional costs are costs that must be paid IN ADDITION TO a spell's mana cost. They are mandatory unless specified otherwise (CR 118.9). The total cost of a spell = mana cost + all additional costs + cost increases - cost reductions (with alternative cost optionally replacing the mana cost).

Key types of additional costs:
- **Card-defining additional costs**: Written directly on the card, e.g., "As an additional cost to cast this spell, sacrifice a creature."
- **Keyword-based additional costs**: E.g., Kicker ("You may pay an additional {2}"), Buyback, Escalate — these are OPTIONAL additional costs (handled by CR 118.10)
- **Effect-imposed additional costs**: Another effect may say "Spells your opponents cast cost {1} more to cast" — this is a cost increase, not an additional cost

Important distinction: CR 118.9 covers MANDATORY additional costs. OPTIONAL additional costs (like Kicker) are covered by CR 118.10. Cost increases (like Thalia's "Noncreature spells cost {1} more to cast") are covered by a different rule.

Additional costs stack — if a spell has multiple additional costs, all must be paid. Unlike alternative costs, they are not mutually exclusive.

### Comprehensive Rules Grounding
- **CR 118.9**: "Some spells and abilities have additional costs."
- **CR 118.9a**: "If a spell has multiple additional costs, the player may pay them in any order."
- **CR 118.9b**: "Additional costs are mandatory unless the cost is phrased as an option."
- **CR 118.9c**: "Some cards have additional costs that consist of removing counters from a permanent they refer to as 'this permanent.'"
- **CR 118.9d**: "Some additional costs are 'as an additional cost to cast this spell,' which must be paid during the casting process."
- **Example card**: Fling — "As an additional cost to cast this spell, sacrifice a creature."
- **Example card**: Tragic Lesson — "As an additional cost to cast this spell, discard a card."

## Acceptance Criteria
- [ ] `parse_additional_cost(oracle_text: str) -> list[AdditionalCost]` detects and parses mandatory additional cost patterns ("As an additional cost to cast this spell, ...")
- [ ] `get_mandatory_additional_costs(gs, card_id, player_name) -> list[AdditionalCost]` returns all mandatory additional costs for a card
- [ ] Additional costs are integrated into total cost calculation in step 601.2c of casting process
- [ ] Enforcement: player cannot cast the spell if they cannot fulfill all mandatory additional costs (CR 601.3 — illegal action rollback)
- [ ] Multiple additional costs can be paid in any order (CR 118.9a)
- [ ] Additional costs support: sacrifice, discard, pay life, exile, remove counters, tap, and other actions
- [ ] Cost increases from external effects (e.g., Thalia, Sphere of Resistance) are tracked separately from additional costs
- [ ] AI auto-resolution: bot evaluates whether it can and should pay additional costs before beginning to cast
- [ ] Human path: queues `pending_additional_cost_choices` for multi-choice additional costs if applicable
- [ ] Full regression passes

## Dependencies
- story-ab-spell-abilities.md (additional costs integrate into the casting process)
- story-ab-alternative-costs.md (distinct from but complementary to alternative costs)

## Status: 🔄 Partial

Implemented per-keyword: Kicker (pending_kicker_choice, kicker_paid flag), Entwine (parse_entwine_cost), Buyback (buyback_paid flag), Replicate (replicate_count), Ward (pending_ward_payment), Evoke sacrifice queue. Cost type classes in cost.py (SacrificeCost, ExileCost, DiscardCost, LifeCost).

**Gap**: No unified additional-cost framework. Each keyword has its own mechanism (boolean flags, pending fields, separate endpoints). Entwine is parsed but NOT wired into legal actions or mode selection. Escalate and Conspire have NO modules.

## Priority: High

## Notes
- The key distinction from alternative costs: additional costs ADD to the total cost (they don't replace the mana cost).
- The key distinction from optional costs (CR 118.10): additional costs are MANDATORY.
- Kicker, Buyback, Escalate, etc. are OPTIONAL additional costs governed by CR 118.10, NOT CR 118.9.
- Cost increases (e.g., "costs {1} more to cast") are also distinct — they are governed by CR 601.2c and apply automatically.
- Forge reference: `AdditionalCost` class / cost payment during `SpellAbility.cast()`.
