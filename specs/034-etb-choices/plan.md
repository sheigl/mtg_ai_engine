# ETB Choice Framework (034)

## Problem Statement

When certain cards enter the battlefield, they present the player with a choice. Currently the MTG engine either:
- Ignores the choice (shocklands enter tapped by default)
- Makes a conservative assumption (assumes "no" / worst case)

**This is incorrect.** All player types must be given the choice (or a reasonable decision).

## Player Type Requirements

### 1. Human Player (local UI)
- Show choice modal with clear options
- Display consequences of each choice ("Enter untapped" vs "Enter tapped")
- Human makes final decision via UI

### 2. AI Player (heuristic model)
- Evaluate board state using heuristic rules (see AI Heuristics below)
- Make "optimal" decision based on:
  - Life total
  - Opponent's removal/interaction
  - Board state advantage
  - Mana needs

### 3. Bot Player (networked AI via API)
- Same as AI - decision delegated to remote agent
- Engine sends pending choice to client
- Client returns decision
- Works for both single and hybrid games

## Examples of Affected Cards

### Shock Lands (pay life or enter tapped)
```
Steam Vents
Land — Island Mountain
({T}: Add {U} or {R}.)
As this land enters, you may pay 2 life. If you don't, it enters tapped.
```
- **Choice:** Pay 2 life → enter untapped | Don't pay → enter tapped
- **Default (correct):** Player decides

### Check Lands (enters tapped unless you control a land of that type)
```
Canopy Vista
Land — Forest Plains
({T}: Add {G} or {W}.)
Canopy Vista enters tapped unless you control a Forest or a Plains.
```
- **Choice:** Control such land → enter untapped | Don't → enter tapped
- **Default:** Must check battlefield

### Fetch Lands (enters tapped unless you control a basic land)
```
Polluted Delta
Land
{T}: Add {B}.
As Polluted Delta enters, you may pay 1 life and exile a land card from your graveyard. If you don't, Polluted Delta enters tapped.
```
- **Choice:** Pay 1 life + exile land → enter untapped | Don't → enter tapped
- **Default:** Must check graveyard + player decides

### Snow Duals (pay {1} or enter tapped)
```
Ice Tunnel
Land — Desert Snow
{T}: Add {C}.
As Ice Tunnel enters, you may pay 1 snow mana. If you don't, it enters tapped.
```
- **Choice:** Pay {1} → enter untapped | Don't → enter tapped
- **Default:** Player decides

### Creature Choice Effects (the one reported)
```
Stormchaser's Talent
Enchantment — Class
(Gain the next level as a sorcery to add its ability.)
When this Class enters, create a 1/1 blue and red Otter creature token with prowess.
```
- **Already working?** Token creation via replacement effect
- **Note:** Need to verify this is working

## Technical Approach

### Pattern Detection (ability_parser.py)
Add regex patterns to detect the choice type:

```python
# Pattern types
SHOCKLAND_RE = re.compile(
    r"As (?:this|~) enters?, you may pay (\d+) life\. "
    r"If you don'?t,? (?:it|~) enters tapped\.?",
    re.IGNORECASE
)

CHECKLAND_RE = re.compile(
    r"(\w+) enters tapped unless you control (?:a|an) (\w+)\.",
    re.IGNORECASE
)

FETCHLAND_RE = re.compile(
    r"As (?:this|~) enters?, you may pay (\d+) (?:life|snow mana) "
    r"and exile .+? If you don'?t,? (?:it|~) enters tapped\.?",
    re.IGNORECASE
)
```

### Game State (models/game.py)
Add new pending choice type:

```python
class ETBTappedChoice(GameState dict):
    choice_type: "etb_tapped" = "etb_tapped"
    card_id: str
    permanent_id: str
    player: str
    alternatives: list[ChoiceAlternative]  # e.g., "pay 2 life", "enter tapped"
```

### UI (frontend)
- Show modal when ETB choice is pending
- Choices should be presented as buttons like other pending choices (scry, surveil, etc.)
- Should show consequences ("Enter untapped" vs "Enter tapped")

### AI Decision
- For AI (heuristic model): Decide based on board state
  - If opponent has removal → enter untapped (can use immediately)
  - If ahead on board → could enter tapped (delays opponent)
  - If behind → enter untapped (need the mana)

## Implementation Phases

### Phase 1: Framework (this spec)
- Identify ALL card patterns that need ETB choices
- Create data models
- Update zones.py to detect and queue choices

### Phase 2: Data Model
- Add `etb_choices` list to GameState
- Add choice resolution in stack.py or turn_manager.py

### Phase 3: UI
- Add choice rendering in ActionPanel
- Test human decision flow

### Phase 4: AI Integration  
- Add heuristic rules for shocklands, checklands, fetches

## Research: All ETB Choice Patterns

### Known Patterns to Implement
1. **Shock** - "pay X life or enter tapped" (10 cards)
2. **Check** - "enters tapped unless you control X" (10 cards)
3. **Fetch** - "pay X and exile Y or enter tapped" (10 cards)
4. **Snow** - "pay {1} or enter tapped" (5 cards)
5. **Other** - various "as this enters, you may..."

### Card Lists (to be populated)
See `research.md` for identified cards by type.

## Testing

### Test Cases
1. [ ] Steam Vents (shock) - player choice works
2. [ ] Steam Vents (shock) - AI makes reasonable choice  
3. [ ] Canopy Vista (check) - enters tapped without Forest/Plains
4. [ ] Canopy Vista (check) - enters untapped with Forest/Plains
5. [ ] Polluted Delta (fetch) - prompts for choice
6. [ ] Ice Tunnel (snow) - prompts for choice

### Acceptance Criteria
- [ ] All 4 land types show choice when played
- [ ] AI decides within 3 seconds
- [ ] Human can override AI decision (in hybrid game)
- [ ] Game state correctly reflects choice result