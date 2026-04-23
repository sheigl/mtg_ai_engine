import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMetagameDecks, fetchCachedDeck } from '../hooks/useMetagameDecks'
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
  enableDebug: boolean
  observerUrl: string
  observerModel: string
  seriesCount: number
  // Deck source selection (033-deck-randomizer)
  deck1Source: 'random' | 'cached' | 'custom'
  deck2Source: 'random' | 'cached' | 'custom'
  deck1Cached: string
  deck2Cached: string
  randomizeDecksPerGame: boolean
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
    enableDebug: false,
    observerUrl: '',
    observerModel: '',
    seriesCount: 1,
    deck1Source: 'random',
    deck2Source: 'random',
    deck1Cached: '',
    deck2Cached: '',
    randomizeDecksPerGame: false,
  })
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const metagameDecks = useMetagameDecks(form.format)

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
      let deck1: string[] = []
      let deck2: string[] = []
      let detectedCommander1: string | undefined
      let detectedCommander2: string | undefined

      // Parse deck1 based on source
      if (form.deck1Source === 'custom') {
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
      } else if (form.deck1Source === 'cached' && form.deck1Cached) {
        try {
          const r = await fetchCachedDeck(form.format, form.deck1Cached)
          deck1 = r.cards
          if (r.commander) detectedCommander1 = r.commander
        } catch {
          setFieldErrors(prev => ({ ...prev, deck1: 'Failed to load cached deck' }))
          return
        }
      }

      // Parse deck2 based on source
      if (form.deck2Source === 'custom') {
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
      } else if (form.deck2Source === 'cached' && form.deck2Cached) {
        try {
          const r = await fetchCachedDeck(form.format, form.deck2Cached)
          deck2 = r.cards
          if (r.commander) detectedCommander2 = r.commander
        } catch {
          setFieldErrors(prev => ({ ...prev, deck2: 'Failed to load cached deck' }))
          return
        }
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
        debug: form.enableDebug,
        series_count: form.seriesCount,
        randomize_decks_per_game: form.randomizeDecksPerGame,
        ...(form.format === 'commander' && {
          commander1,
          commander2,
        }),
      }

      if (form.opponentType === 'ai') {
        body.ai_base_url = form.aiBaseUrl.trim()
        body.ai_model = form.aiModel.trim()
        // If observer fields are filled, send them too
        if (form.observerUrl.trim()) {
          body.observer_url = form.observerUrl.trim()
        }
        if (form.observerModel.trim()) {
          body.observer_model = form.observerModel.trim()
        }
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
          <div className="form-card-title">Decks</div>
          {(['Your', 'Opponent'] as const).map((label, i) => {
            const pn = i + 1
            const source = pn === 1 ? form.deck1Source : form.deck2Source
            const setSource = (v: 'custom' | 'random' | 'cached') =>
              setForm(f => ({ ...f, [pn === 1 ? 'deck1Source' : 'deck2Source']: v }))
            const cached = pn === 1 ? form.deck1Cached : form.deck2Cached
            const setCached = (v: string) =>
              setForm(f => ({ ...f, [pn === 1 ? 'deck1Cached' : 'deck2Cached']: v }))
            const deckText = pn === 1 ? form.deck1Text : form.deck2Text
            const setDeckText = (v: string) =>
              setForm(f => ({ ...f, [pn === 1 ? 'deck1Text' : 'deck2Text']: v }))
            const deckError = pn === 1 ? fieldErrors.deck1 : fieldErrors.deck2
            const clearDeckError = () =>
              setFieldErrors(prev => ({ ...prev, [pn === 1 ? 'deck1' : 'deck2']: undefined }))
            return (
              <div key={pn} style={{ marginBottom: 'var(--space-3)' }}>
                <div className="form-row">
                  <div className="form-field form-field--shrink">
                    <label className="label">{label} deck</label>
                    <select
                      className="select"
                      value={source}
                      onChange={e => setSource(e.target.value as 'custom' | 'random' | 'cached')}
                    >
                      <option value="random">Random metagame deck</option>
                      <option value="cached">Choose from metagame</option>
                      <option value="custom">Custom deck list</option>
                    </select>
                  </div>
                  {source === 'cached' && (
                    <div className="form-field">
                      <label className="label">Select deck</label>
                      {metagameDecks.isLoading ? (
                        <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>Loading decks…</span>
                      ) : metagameDecks.isError ? (
                        <span style={{ fontSize: 'var(--text-sm)', color: 'var(--danger)' }}>Failed to load decks</span>
                      ) : (
                        <select
                          className="select"
                          value={cached}
                          onChange={e => setCached(e.target.value)}
                        >
                          <option value="">— pick a deck —</option>
                          {(metagameDecks.data ?? []).map(d => (
                            <option key={d.name} value={d.name}>{d.name} ({d.card_count} cards)</option>
                          ))}
                        </select>
                      )}
                    </div>
                  )}
                </div>
                {source === 'custom' && (
                  <textarea
                    className="textarea"
                    value={deckText}
                    onChange={e => { clearDeckError(); setDeckText(e.target.value) }}
                    placeholder="Comma-separated card names or Archidekt URL"
                    style={{ marginTop: 'var(--space-2)' }}
                  />
                )}
                {source === 'random' && (
                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>
                    A random competitive deck will be assigned from MTGGoldfish.
                  </div>
                )}
                {source === 'cached' && !cached && (
                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--warning)', marginTop: 'var(--space-1)' }}>
                    Select a deck from the dropdown above.
                  </div>
                )}
                {deckError && <span className="form-error">{deckError}</span>}
              </div>
            )
          })}
          {form.seriesCount > 1 && (
            <label className="cg-check-row" style={{ marginTop: 'var(--space-2)' }}>
              <input
                type="checkbox"
                checked={form.randomizeDecksPerGame}
                onChange={e => setForm(f => ({ ...f, randomizeDecksPerGame: e.target.checked }))}
              />
              Randomize decks per game in series
            </label>
          )}
        </div>

        <div className="form-card">
          <div className="form-row">
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
            <div className="form-field form-field--shrink">
              <label className="label">Series count</label>
              <input
                className="input"
                type="number"
                min={1}
                max={100}
                value={form.seriesCount}
                onChange={e => setForm(f => ({ ...f, seriesCount: Math.max(1, parseInt(e.target.value, 10) || 1) }))}
                style={{ width: 80 }}
              />
            </div>
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

        <div className="form-card">
          <div className="form-card-title">AI Commentary</div>
          <label className="cg-check-row">
            <input
              type="checkbox"
              checked={form.enableDebug}
              onChange={e => setForm(f => ({ ...f, enableDebug: e.target.checked }))}
            />
            Enable AI commentary panel (shows prompts, responses, and move analysis)
          </label>
          {form.enableDebug && (
            <div className="form-row" style={{ marginTop: 'var(--space-3)' }}>
              <div className="form-field">
                <label className="label">Observer endpoint URL (optional)</label>
                <input
                  className="input"
                  value={form.observerUrl}
                  onChange={e => setForm(f => ({ ...f, observerUrl: e.target.value }))}
                  placeholder={form.aiBaseUrl || 'http://localhost:8080/v1'}
                />
              </div>
              <div className="form-field">
                <label className="label">Observer model (optional)</label>
                <input
                  className="input"
                  value={form.observerModel}
                  onChange={e => setForm(f => ({ ...f, observerModel: e.target.value }))}
                  placeholder={form.aiModel || 'e.g. devstral'}
                />
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
