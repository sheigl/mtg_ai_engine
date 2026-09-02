# Story Guidelines

Every keyword, game mechanic, trigger pattern, and API feature MUST have its own individual story file.

## File Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Keyword | `story-kw-{slug}.md` | `story-kw-crew.md` |
| Trigger | `story-trg-{slug}.md` | `story-trg-sacrifice.md` |
| Game Mechanic | `story-gm-{slug}.md` | `story-gm-commander.md` |
| API Feature | `story-api-{slug}.md` | `story-api-card-search.md` |
| Architecture | `story-arch-{slug}.md` | `story-arch-keyword-wiring.md` |

## Story Template

```markdown
# Story: {Title}

## User Story
As a {user type}, I want {feature}, so that {benefit}

## Context
{Why this matters, how it works in MTG, relevant background}

### Comprehensive Rules Grounding
- **CR {number}**: "{exact or paraphrased rule text}"
- **Rule source**: {what the rule governs}
- **Example card**: {card name} — "{ability text that demonstrates the mechanic}"

## Acceptance Criteria
- [ ] {testable criterion 1}
- [ ] {testable criterion 2}
- [ ] {testable criterion 3}

## Dependencies
- {list of prerequisite story file paths, or "None"}

## Priority: {High / Medium / Low}

## Estimated Effort: {S / M / L / XL}

## Notes
{Implementation considerations, edge cases, cross-references to Forge implementation if applicable}
```

## Priority Definitions

| Priority | Meaning | When to Use |
|----------|---------|-------------|
| P0 / High | Blocks gameplay — cards with this keyword silently fail | Most common mechanics, critical triggers |
| P1 / Medium-High | Common in current Standard/modern sets | Appears in 10+ cards in recent sets |
| P2 / Medium | Moderate frequency or needed for set coverage | Several cards per set |
| P3 / Medium-Low | Niche mechanics, old keywords | Rare or rotating mechanics |
| P4 / Low | Very rare, corner cases | Could leave for last |

## Status Definitions

| Status | Meaning |
|--------|---------|
| ✅ Complete | Discovery → Planning → Implement → Code Review → Test → Document all done |
| 🔄 In Progress | Currently being worked on |
| ⏳ Planned | Discovery done, ready for Technical Planning |
| 🚫 Blocked | Waiting on dependency |
| 📋 Backlog | Not yet prioritized |

## Key Rules
- ONE story file per keyword or trigger — NO bundling
- EVERY story MUST include a CR reference from the MTG Comprehensive Rules
- Always include an example card that demonstrates the mechanic
- Acceptance criteria must be testable (can verify with a passing/failing test)
- Cross-reference Forge's implementation when relevant
