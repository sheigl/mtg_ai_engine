# ETB Choice Research (034)

## Player Type Considerations

### Human Players
- Show UI choice (like scry/surveil)
- Decision made via action panel

### AI Players (heuristic model)
- Uses built-in heuristics below
- Decision computed locally in engine

### Bot Players (networked AI)
- Decision delegated to remote agent
- Agent receives choice context and responds
- Works seamlessly with existing AI client protocol

## Implementation Pattern for All Player Types
```python
def _resolve_etb_choice(gs: GameState, player: str, choice_type: str) -> GameState:
    if player_is_human(player):
        # Queue for UI
        return gs_with_pending_choice(gs)
    elif player_is_ai(player):
        # Use heuristic
        return apply_ai_heuristic(gs, player, choice_type)
    elif player_is_bot(player):
        # Same as AI - bot client will decide
        return gs_with_pending_choice(gs)  
```

## Shock Lands (10 cards)
Pay 2 life or enter tapped.

| Card | Set | Type |
|------|-----|------|
| Overgrown Tomb | GRN | BG |
| Breeding Pool | RNA | GU |
| Stomping Ground | RNA | GR |
| Temple Garden | RNA | GW |
| Hallowed Fountain | RNA | UW |
| Watery Grave | RNA | UB |
| Blood Crypt | RNA | BR |
| Godless Shrine | RNA | WB |
| Sacred Foundry | RNA | WR |
| Steam Vents | RNA | UR |

**AI Heuristic:**
- If AI has <= 3 life: pay (can't afford to lose 2)
- If opponent has instant-speed interaction: pay (need to use immediately)
- If AI has high life (>= 10): could enter tapped (preserve life buffer)

## Check Lands (10 cards)
Enters tapped unless you control [type] land.

| Card | Set | Requires |
|------|-----|----------|
| Canopy Vista | BFZ | Forest OR Plains |
| Cinder Glade | BFZ | Mountain OR Forest |
| Harbor Mist | BFZ | Island OR Swamp |
| Lumbering Falls | BFZ | Mountain OR Forest |
| Moss Kat | BFZ | Forest OR Island |
| Evolving Wilds | XLN | Basic land type |
| Irrigated Farmland | XLN | Island OR Plains |
| Scattered Groves | XLN | Forest OR Plains |
| Shimmering Grotto | XLN | Any two colors |
| Smoldering Ef | XLN | Mountain OR Swamp |

**AI Heuristic:**
- Check battlefield for required type
- If required type present: enter untapped (free!)
- If not: enter tapped

## Fetch Lands (10 cards)
Pay 1 life and exile land OR enter tapped.

| Card | Set | Requires |
|------|-----|----------|
| Polluted Delta | ONS | Land in graveyard |
| Flooded Strand | ONS | Land in graveyard |
| Windswept Heath | ONS | Land in graveyard |
| Bloodstained Mire | ONS | Land in graveyard |
| Wooded Foothills | ONS | Land in graveyard |
| Arid Mesa | ZEN | Land in graveyard |
| Misty Rainforest | ZEN | Land in graveyard |
| Scalding Tarn | ZEN | Land in graveyard |
| Verdant Catacomb | ZEN | Land in graveyard |
| Raging Ravine (no choice, just enters tapped) | -- | N/A |

**AI Heuristic:**
- If graveyard has land & life > 3: pay + exile
- Otherwise: enter tapped
- Note: Exile also relevant for cards like Crucible of Worlds

## Snow Duals (5 cards)
Pay {1} snow mana or enter tapped.

| Card | Set | 
|------|-----|
| Ice Tunnel | CLB |
| Snowfield | CLB |
| Snow-Covered | CLB |
| Rimewood Falls | CLB |
| Glacier | CLB |

**AI Heuristic:**
- If snow mana available: pay (can tap for {C} anyway)
- Otherwise: enter tapped

## Other ETB Choice Cards

### Choices that create tokens (already implemented?)
- Stormchaser's Talent: "create token" - replaced by token creation pattern
- Check if this needs fixing (one of the original issues)

### Modal Double-Faced Cards (MDFC)
```text
Turn into a Tree
Instant // Land — Treefolk
...
// Back
{T}: Add {G}
```
- MDFCs enter on the non-land side by default
- Need to check if choice is needed

### Class Cards
```text
Stormchaser's Talent
Enchantment — Class
(Gain the next level as a sorcery to add its ability.)
When this Class enters, create a 1/1 blue and red Otter creature token with prowess.
```
- Not an ETB choice, just ETB token creation
- Token pattern should handle this (see spec 029 token patterns)

### Cards with "may"
Many cards have "may" triggers - need to determine which ones require choice:

1. **Optional ETB triggers** (usually handled by pending_triggers)
   - "When ~ enters, you may..." 
   - Creates PendingTrigger in triggers.py ✓ working

2. **Replacement effects** (need new handling)
   - "As ~ enters, you may pay X. If you don't, Y."
   - Requires pending choice in zones.py

## Pattern Regexes to Implement

```python
# Shockland pattern
pattern = r"As (?:this|~) enters?, you may pay (\d+) life\.? If you don'?t?,? (?:it|~) enters tapped\.?"

# Checkland pattern  
pattern = r"([\w\s]+) enters tapped unless you control (?:a|an) ([\w\s]+)"

# Fetchland pattern
pattern = r"As (?:this|~) enters?, you may pay (\d+) (?:life|snow mana) and exile .+? If you don'?t?,? (?:it|~) enters tapped\.?"

# Snow dual pattern
pattern = r"As (?:this|~) enters?, you may pay (\d+) snow mana\.? If you don'?t?,? (?:it|~) enters tapped\.?"
```

## Files to Modify

1. **mtg_engine/card_data/ability_parser.py**
   - Add ETB choice detection patterns
   - May need new function: `detect_etb_choice(oracle_text) -> ETBChoice`

2. **mtg_engine/engine/zones.py**
   - Update `put_permanent_onto_battlefield()`
   - Queue ETB choice as pending choice

3. **mtg_engine/models/game.py**  
   - Add ETBChoice model
   - Add etb_choices: list[ETBChoice] to GameState

4. **mtg_engine/api/routers/game.py**
   - Add ETB choice to legal_actions (like scry/surveil)

5. **frontend/src/components/ActionPanel.tsx**
   - Add ETB choice rendering
   - Similar to scry/surveil handling

6. **ai_client/hybrid_game_loop.py** or AI decision logic
   - Add AI heuristic for each choice type