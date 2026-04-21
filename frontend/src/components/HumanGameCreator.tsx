import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import '../styles/create-game.css'

type PlayerType = 'heuristic' | 'ai'

interface FormState {
  opponentType: PlayerType
  humanName: string
  opponentName: string
  deck1Text: string
  deck2Text: string
  format: 'standard' | 'commander'
  commander1: string
  commander2: string
}

interface FieldErrors {
  humanName?: string
  opponentName?: string
  names?: string
  deck1?: string
  deck2?: string
  commander1?: string
  commander2?: string
}

function parseDeck(raw: string): string[] {
  return raw.split(',').map(s => s.trim()).filter(Boolean)
}

function isArchidektUrl(raw: string): boolean {
  const t = raw.trim()
  return t.startsWith('https://archidekt.com') || t.startsWith('http://archidekt.com')
}

async function resolveArchidektDeck(url: string): Promise<{ cards: string[]; commander?: string }> {
  const res = await fetch('/deck/import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ archidekt_url: url.trim() }),
  })
  const json = await res.json()
  if (!res.ok) {
    const detail = json?.detail
    const msg = typeof detail === 'object' ? detail?.error : String(detail ?? 'Archidekt import failed')
    throw new Error(msg)
  }
  const cards: { name: string; quantity: number }[] = json.data?.main_deck ?? []
  return {
    cards: cards.flatMap(c => Array(c.quantity).fill(c.name)),
    commander: json.data?.commander ?? undefined,
  }
}

export function HumanGameCreator() {
  const navigate = useNavigate()
  const [form, setForm] = useState<FormState>({
    opponentType: 'heuristic',
    humanName: 'You',
    opponentName: 'Bot',
    deck1Text: '',
    deck2Text: '',
    format: 'standard',
    commander1: '',
    commander2: '',
  })
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  function validate(): FieldErrors {
    const errors: FieldErrors = {}
    if (!form.humanName.trim()) errors.humanName = 'Name required'
    if (!form.opponentName.trim()) errors.opponentName = 'Name required'
    if (form.humanName.trim() && form.opponentName.trim() && form.humanName.trim() === form.opponentName.trim()) {
      errors.names = 'Names must be different'
    }
    if (form.format === 'commander') {
      if (!form.commander1.trim() && !isArchidektUrl(form.deck1Text))
        errors.commander1 = 'Your commander name required'
      if (!form.commander2.trim() && !isArchidektUrl(form.deck2Text))
        errors.commander2 = 'Opponent commander name required'
    }
    return errors
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setServerError(null)
    const errors = validate()
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setIsSubmitting(true)
    try {
      let deck1: string[]
      let deck2: string[]
      let detectedCommander1: string | undefined
      let detectedCommander2: string | undefined
      try {
        if (isArchidektUrl(form.deck1Text)) {
          const r = await resolveArchidektDeck(form.deck1Text)
          deck1 = r.cards
          detectedCommander1 = r.commander
        } else {
          deck1 = parseDeck(form.deck1Text)
        }
      } catch (err) {
        setFieldErrors(prev => ({ ...prev, deck1: (err as Error).message }))
        return
      }
      try {
        if (isArchidektUrl(form.deck2Text)) {
          const r = await resolveArchidektDeck(form.deck2Text)
          deck2 = r.cards
          detectedCommander2 = r.commander
        } else {
          deck2 = parseDeck(form.deck2Text)
        }
      } catch (err) {
        setFieldErrors(prev => ({ ...prev, deck2: (err as Error).message }))
        return
      }

      const commander1 = form.commander1.trim() || detectedCommander1 || ''
      const commander2 = form.commander2.trim() || detectedCommander2 || ''

      const body = {
        player1_type: 'human',
        player2_type: form.opponentType,
        player1_name: form.humanName.trim(),
        player2_name: form.opponentName.trim(),
        player1_deck: deck1,
        player2_deck: deck2,
        format: form.format,
        ...(form.format === 'commander' && {
          commander1,
          commander2,
        }),
      }

      const res = await fetch('/human-game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const json = await res.json()
      if (!res.ok) {
        const detail = json?.detail
        const msg = typeof detail === 'object' ? detail?.error : String(detail ?? 'Unknown error')
        setServerError(msg)
        return
      }
      const gameId: string = json.data?.game_id
      const humanPlayerName: string = json.data?.human_player_name
      if (gameId) {
        navigate(`/human-game/${gameId}`, { state: { humanPlayerName } })
      }
    } catch {
      setServerError('Could not reach the engine. Is it running?')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: '2rem 1rem' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <button
          onClick={() => navigate('/')}
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.85rem', padding: 0 }}
        >
          ← Back
        </button>
        <h1 style={{ margin: '0.5rem 0 0.25rem', fontSize: '1.5rem' }}>Play vs AI</h1>
        <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.85rem' }}>
          Play MTG as a human against a bot opponent
        </p>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Opponent type */}
        <div className="cg-player-card">
          <div className="cg-player-title">Opponent</div>
          <div className="cg-row">
            <div className="cg-field cg-field--shrink">
              <label>Opponent type</label>
              <select
                value={form.opponentType}
                onChange={e => setForm(f => ({ ...f, opponentType: e.target.value as PlayerType }))}
              >
                <option value="heuristic">Heuristic Bot (fast, no LLM)</option>
                <option value="ai">AI (requires LLM endpoint)</option>
              </select>
            </div>
            <div className="cg-field">
              <label>Opponent name</label>
              <input
                value={form.opponentName}
                onChange={e => setForm(f => ({ ...f, opponentName: e.target.value }))}
                placeholder="Bot"
              />
              {fieldErrors.opponentName && <span className="cg-field-error">{fieldErrors.opponentName}</span>}
            </div>
          </div>
        </div>

        {/* Human player */}
        <div className="cg-player-card">
          <div className="cg-player-title">You</div>
          <div className="cg-field">
            <label>Your name</label>
            <input
              value={form.humanName}
              onChange={e => setForm(f => ({ ...f, humanName: e.target.value }))}
              placeholder="You"
            />
            {fieldErrors.humanName && <span className="cg-field-error">{fieldErrors.humanName}</span>}
            {fieldErrors.names && <span className="cg-field-error">{fieldErrors.names}</span>}
          </div>
        </div>

        {/* Decks */}
        <div className="cg-player-card">
          <div className="cg-player-title">Decks (optional — leave blank for default)</div>
          <div className="cg-row">
            <div className="cg-field">
              <label>Your deck</label>
              <textarea
                value={form.deck1Text}
                onChange={e => { setFieldErrors(p => ({ ...p, deck1: undefined })); setForm(f => ({ ...f, deck1Text: e.target.value })) }}
                placeholder="Comma-separated card names or Archidekt URL"
              />
              {fieldErrors.deck1 && <span className="cg-field-error">{fieldErrors.deck1}</span>}
            </div>
            <div className="cg-field">
              <label>Opponent deck</label>
              <textarea
                value={form.deck2Text}
                onChange={e => { setFieldErrors(p => ({ ...p, deck2: undefined })); setForm(f => ({ ...f, deck2Text: e.target.value })) }}
                placeholder="Comma-separated card names or Archidekt URL"
              />
              {fieldErrors.deck2 && <span className="cg-field-error">{fieldErrors.deck2}</span>}
            </div>
          </div>
        </div>

        {/* Format */}
        <div className="cg-player-card">
          <div className="cg-field cg-field--shrink">
            <label>Format</label>
            <select
              value={form.format}
              onChange={e => setForm(f => ({ ...f, format: e.target.value as 'standard' | 'commander' }))}
            >
              <option value="standard">Standard</option>
              <option value="commander">Commander</option>
            </select>
          </div>
          {form.format === 'commander' && (
            <div className="cg-row" style={{ marginTop: '0.75rem' }}>
              <div className="cg-field">
                <label>Your Commander</label>
                <input
                  value={form.commander1}
                  onChange={e => { setFieldErrors(p => ({ ...p, commander1: undefined })); setForm(f => ({ ...f, commander1: e.target.value })) }}
                  placeholder="e.g. Atraxa, Praetors' Voice"
                />
                {fieldErrors.commander1 && <span className="cg-field-error">{fieldErrors.commander1}</span>}
              </div>
              <div className="cg-field">
                <label>Opponent Commander</label>
                <input
                  value={form.commander2}
                  onChange={e => { setFieldErrors(p => ({ ...p, commander2: undefined })); setForm(f => ({ ...f, commander2: e.target.value })) }}
                  placeholder="e.g. Atraxa, Praetors' Voice"
                />
                {fieldErrors.commander2 && <span className="cg-field-error">{fieldErrors.commander2}</span>}
              </div>
            </div>
          )}
        </div>

        {serverError && <div className="cg-error">{serverError}</div>}

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="submit"
            disabled={isSubmitting}
            className="cg-btn-start"
            style={{ padding: '0.6rem 2rem' }}
          >
            {isSubmitting ? 'Starting…' : 'Start Game'}
          </button>
        </div>
      </form>
    </div>
  )
}
