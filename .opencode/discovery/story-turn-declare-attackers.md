# Story: Declare Attackers Step (CR 508)

## User Story
As a game engine developer, I want the declare attackers step to function correctly per CR 508, so that the active player chooses which creatures attack, which player/planeswalker each attacks, and taps them.

## Context
The declare attackers step is the second step of the combat phase (after beginning of combat). The active player chooses a set of creatures to attack, designates which defending player or planeswalker each creature is attacking, and taps the attacking creatures. Creatures with vigilance do not become tapped. Creatures with summoning sickness cannot attack unless they have haste. The current engine has attack declaration logic in `combat/core.py` via `declare_attackers()`. After attackers are declared, priority is granted to both players.

### Comprehensive Rules Grounding
- **CR 508.1**: "The active player declares attackers. The active player chooses which creatures that they control, if any, will attack. They choose which player or planeswalker each chosen creature is attacking. Then the active player taps the chosen creatures."
- **CR 508.3**: "Creatures with summoning sickness can't attack."
- **CR 508.4**: "A creature with vigilance doesn't become tapped when it attacks."
- **CR 508.5**: "A creature can't attack an opponent if that opponent is no longer in the game."
- **Purpose**: Initiate combat by selecting attackers and targets

## Acceptance Criteria
- [x] Active player selects which creatures attack
- [x] Active player designates each attacker's target (player or planeswalker)
- [x] Attacking creatures become tapped (unless they have vigilance)
- [x] Creatures with summoning sickness cannot attack (unless they have haste)
- [x] Creatures with defender cannot attack (unless they lose defender)
- [x] Player may choose not to attack (0 attackers)
- [x] "Attacks if able" restrictions are enforced
- [x] "Can't attack" restrictions are enforced
- [x] Priority is granted after attackers are declared
- [x] Full regression passes

## Dependencies
- story-turn-combat-phase.md (Combat Phase)

## Status: ✅ Complete

Implemented: `declare_attackers()` at `combat/core.py:233-277`. Validates creature can attack (untapped, no summoning sickness or haste, no defender). Taps attacking creatures unless vigilance. Creates `CombatState` with `AttackerInfo`. Legal actions in `_compute_legal_actions()` at `game.py:3287-3338`.

## Priority: High
