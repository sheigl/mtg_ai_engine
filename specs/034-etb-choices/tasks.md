# ETB Choice Tasks (034)

## Tasks

### Phase 1: Foundation
- [ ] 1.1 Add ETB choice detection regex to ability_parser.py
- [ ] 1.2 Create `detect_etb_choice(oracle_text)` function
- [ ] 1.3 Test detection on known card set

### Phase 2: Game State
- [ ] 2.1 Add ETBChoice model to models/game.py
- [ ] 2.2 Add etb_choices field to GameState
- [ ] 2.3 Add _resolve_etb_choice function

### Phase 3: Engine Integration
- [ ] 3.1 Update zones.py put_permanent_onto_battlefield to check ETB
- [ ] 3.2 Queue pending choice when detected
- [ ] 3.3 Apply choice result (tap/untap permanent)

### Phase 4: API Integration
- [ ] 4.1 Add ETB choice to legal_actions endpoint
- [ ] 4.2 Handle choice submission
- [ ] 4.3 Add submit_choice handler

### Phase 5: UI (Human Player)
- [ ] 5.1 Add ETB choice to action panel
- [ ] 5.2 Style as choice (not spell/activation)
- [ ] 5.3 Test human choice flow

### Phase 6: AI Player
- [ ] 6.1 Add AI heuristic for shocklands
- [ ] 6.2 Add AI heuristic for checklands  
- [ ] 6.3 Add AI heuristic for fetchlands
- [ ] 6.4 Add AI heuristic for snow duals
- [ ] 6.5 Test AI decision making

### Phase 7: Bot Player (Networked AI)
- [ ] 7.1 Verify pending choice is sent to AI client
- [ ] 7.2 AI client handles choice submission
- [ ] 7.3 Test bot choice flow

## Player Type Testing
- [ ] Human: choice UI appears, decision works
- [ ] AI: heuristic makes reasonable choice  
- [ ] Bot: decision delegated to remote agent