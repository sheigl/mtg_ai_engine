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
  aiBaseUrl: string
  aiModel: string
}

interface FieldErrors {
  humanName?: string
  opponentName?: string
  names?: string
  deck1?: string
  deck2?: string
  commander1?: string
  commander2?: string
  aiBaseUrl?: string
  aiModel?: string
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
    aiBaseUrl: 'http://localhost:8080/v1',
    aiModel: '',
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
    if (form.opponentType === 'ai') {
      if (!form.aiBaseUrl.trim() || (!form.aiBaseUrl.startsWith('http://') && !form.aiBaseUrl.startsWith('https://'))) {
        errors.aiBaseUrl = 'Valid http(s) URL required'
      }
      if (!form.aiModel.trim()) errors.aiModel = 'Model is required'
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

      const body: Record<string, unknown> = {
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

      if (form.opponentType === 'ai') {
        body.ai_base_url = form.aiBaseUrl.trim()
        body.ai_model = form.aiModel.trim()
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
    <div style={{ maxWidth: 640, margin: '0 auto', padding: 'var(--space-6) var(--space-4)' }}>
      <button
        className="btn btn--ghost btn--sm"
        onClick={() => navigate('/')}
        style={{ marginBottom: 'var(--space-4)' }}
      >
        ← Back to Games
      </button>

      <div style={{
        background: 'linear-gradient(135deg, var(--surface-elevated) 0%, var(--surface-hover) 100%)',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--border-subtle)',
        padding: 'var(--space-6)',
        marginBottom: 'var(--space-6)',
      }}>
        <h1 style={{
          fontSize: 'var(--text-2xl)',
          fontWeight: 800,
          marginBottom: 'var(--space-2)',
          letterSpacing: '-0.02em',
        }}>
          Play vs AI
        </h1>
        <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: 'var(--text-sm)' }}>
          Play MTG as a human against a bot opponent
        </p>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <div className="form-card">
          <div className="form-card-title">Opponent</div>
          <div className="form-row">
            <div className="form-field form-field--shrink">
              <label className="label">Opponent type</label>
              <select
                className="select"
                value={form.opponentType}
                onChange={e => setForm(f => ({ ...f, opponentType: e.target.value as PlayerType }))}
              >
                <option value="heuristic">Heuristic Bot (fast, no LLM)</option>
                <option value="ai">AI (requires LLM endpoint)</option>
              </select>
            </div>
            <div className="form-field">
              <label className="label">Opponent name</label>
              <input
                className="input"
                value={form.opponentName}
                onChange={e => setForm(f => ({ ...f, opponentName: e.target.value }))}
                placeholder="Bot"
              />
              {fieldErrors.opponentName && <span className="form-error">{fieldErrors.opponentName}</span>}
            </div>
          </div>
          {form.opponentType === 'ai' && (
            <div className="form-row" style={{ marginTop: 'var(--space-3)' }}>
              <div className="form-field">
                <label className="label">LLM Endpoint URL</label>
                <input
                  className="input"
                  value={form.aiBaseUrl}
                  onChange={e => setForm(f => ({ ...f, aiBaseUrl: e.target.value }))}
                  placeholder="http://localhost:8080/v1"
                />
                {fieldErrors.aiBaseUrl && <span className="form-error">{fieldErrors.aiBaseUrl}</span>}
              </div>
              <div className="form-field">
                <label className="label">Model</label>
                <input
                  className="input"
                  value={form.aiModel}
                  onChange={e => setForm(f => ({ ...f, aiModel: e.target.value }))}
                  placeholder="e.g. devstral"
                />
                {fieldErrors.aiModel && <span className="form-error">{fieldErrors.aiModel}</span>}
              </div>
            </div>
          )}
        </div>

        <div className="form-card">
          <div className="form-card-title">You</div>
          <div className="form-field">
            <label className="label">Your name</label>
            <input
              className="input"
              value={form.humanName}
              onChange={e => setForm(f => ({ ...f, humanName: e.target.value }))}
              placeholder="You"
            />
            {fieldErrors.humanName && <span className="form-error">{fieldErrors.humanName}</span>}
            {fieldErrors.names && <span className="form-error">{fieldErrors.names}</span>}
          </div>
        </div>

        <div className="form-card">
          <div className="form-card-title">Decks (optional — leave blank for default)</div>
          <div className="form-row">
            <div className="form-field">
              <label className="label">Your deck</label>
              <textarea
                className="textarea"
                value={form.deck1Text}
                onChange={e => { setFieldErrors(p => ({ ...p, deck1: undefined })); setForm(f => ({ ...f, deck1Text: e.target.value })) }}
                placeholder="Comma-separated card names or Archidekt URL"
              />
              {fieldErrors.deck1 && <span className="form-error">{fieldErrors.deck1}</span>}
            </div>
            <div className="form-field">
              <label className="label">Opponent deck</label>
              <textarea
                className="textarea"
                value={form.deck2Text}
                onChange={e => { setFieldErrors(p => ({ ...p, deck2: undefined })); setForm(f => ({ ...f, deck2Text: e.target.value })) }}
                placeholder="Comma-separated card names or Archidekt URL"
              />
              {fieldErrors.deck2 && <span className="form-error">{fieldErrors.deck2}</span>}
            </div>
          </div>
        </div>

        <div className="form-card">
          <div className="form-field form-field--shrink">
            <label className="label">Format</label>
            <select
              className="select"
              value={form.format}
              onChange={e => setForm(f => ({ ...f, format: e.target.value as 'standard' | 'commander' }))}
            >
              <option value="standard">Standard</option>
              <option value="commander">Commander</option>
            </select>
          </div>
          {form.format === 'commander' && (
            <div className="form-row" style={{ marginTop: 'var(--space-3)' }}>
              <div className="form-field">
                <label className="label">Your Commander</label>
                <input
                  className="input"
                  value={form.commander1}
                  onChange={e => { setFieldErrors(p => ({ ...p, commander1: undefined })); setForm(f => ({ ...f, commander1: e.target.value })) }}
                  placeholder="e.g. Atraxa, Praetors' Voice"
                />
                {fieldErrors.commander1 && <span className="form-error">{fieldErrors.commander1}</span>}
              </div>
              <div className="form-field">
                <label className="label">Opponent Commander</label>
                <input
                  className="input"
                  value={form.commander2}
                  onChange={e => { setFieldErrors(p => ({ ...p, commander2: undefined })); setForm(f => ({ ...f, commander2: e.target.value })) }}
                  placeholder="e.g. Atraxa, Praetors' Voice"
                />
                {fieldErrors.commander2 && <span className="form-error">{fieldErrors.commander2}</span>}
              </div>
            </div>
          )}
        </div>

        {serverError && <div className="cg-error">{serverError}</div>}

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button type="submit" disabled={isSubmitting} className="btn btn--primary btn--lg">
            {isSubmitting ? 'Starting…' : 'Start Game'}
          </button>
        </div>
      </form>
    </div>
  )
}
