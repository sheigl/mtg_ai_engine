# Known Engine Gaps and Bugs

This document tracks MTG engine gaps and bugs that need fixing or documenting for AI training.

## Gap: Duress-type Effects

### Card Examples
- **Duress**: "Target opponent reveals their hand. You choose a noncreature, nonland card from it. That player discards that card."
- **Thought Erasure**: "Target opponent reveals their hand. You choose a nonland, noncreature card from it. That player discards it. Draw a card."
- **Thoughtbite**: Similar pattern
- **Liliana of the Veil**: "-2: Each opponent discards a card."

### Problem
Current engine treats the spell as resolving without effect - the card goes to graveyard immediately after resolution without:
1. Revealing opponent's hand to controller
2. Queuing a choice for player to pick a card
3. Discarding the selected card

### Fix (In Progress)
Need to add pattern detection in stack.py `resolve_top()`:
1. Detect pattern `"target opponent reveals their hand. You choose...discard"`
2. Queue pending choice with opponent's hand as options
3. On choice, move selected card to graveyard

### Related Cards to Test
- [ ] Duress
- [ ] Thought Erasure
- [ ] Funeral Rites
- [ ] Coercion
- [ ] Death Speakers
- [ ] Chittering Skitter
- [ ] Gix's Caress
- [ ] Corrupt Court

---

## Gap: ETB Choices

### Status: FIXED (034)
Shocklands, checklands, fetchlands now properly detect choice patterns and either:
- Queue for human (modal UI)
- Auto-resolve for AI (heuristic)

### Verification
Play a shockland like Steam Vents - should work now.

---

## Bug: Regex in _detect_etb_choice

### Status: FIXED
Original regex required `it enters tapped` but some cards have `it enters tapped.` (with period)

### Fix Applied
Changed regex from strict to greedy match:
```python
r"as .*? enters.*? you may pay (\d+) life.*?enters tapped"
```

---

## Missing: Card-Specific ETB Effects

Some cards have unique ETB triggers not covered by generic patterns:
- Cards that create tokens with specific keywords
- Cards with "may" ETB triggers
- Leveler class cards

### Related
- Stormchaser's Talent - token with prowess (FIXED in 029)
- Level up abilities (need implementation)