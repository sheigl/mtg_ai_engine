import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import '../styles/create-game.css'

// ── Types ─────────────────────────────────────────────────────────────────────

interface PlayerFormState {
  name: string
  playerType: 'llm' | 'heuristic'
  baseUrl: string
  model: string
}

interface FormState {
  player1: PlayerFormState
  player2: PlayerFormState
  deck1Text: string
  deck2Text: string
  format: 'standard' | 'commander'
  commander1: string
  commander2: string
  verbose: boolean
  maxTurns: string
  debug: boolean
  observerUrl: string
  observerModel: string
}

interface FieldErrors {
  player1Name?: string
  player1Url?: string
  player1Model?: string
  player2Name?: string
  player2Url?: string
  player2Model?: string
  commander1?: string
  commander2?: string
  observerModel?: string
  names?: string
  deck1?: string
  deck2?: string
}

interface Props {
  onClose: () => void
}

// ── Defaults ──────────────────────────────────────────────────────────────────

const defaultPlayer = (name: string): PlayerFormState => ({
  name,
  playerType: 'heuristic',
  baseUrl: 'http://localhost:8080/v1',
  model: '',
})

const defaultForm = (): FormState => ({
  player1: defaultPlayer('Player 1'),
  player2: defaultPlayer('Player 2'),
  deck1Text: '',
  deck2Text: '',
  format: 'standard',
  commander1: '',
  commander2: '',
  verbose: false,
  maxTurns: '200',
  debug: false,
  observerUrl: 'http://localhost:8080/v1',
  observerModel: '',
})

// ── Helpers ───────────────────────────────────────────────────────────────────

function parseDeck(raw: string): string[] {
  return raw.split(',').map(s => s.trim()).filter(Boolean)
}

function isArchidektUrl(raw: string): boolean {
  const t = raw.trim()
  return t.startsWith('https://archidekt.com') || t.startsWith('http://archidekt.com')
}

async function resolveArchidektDeck(url: string): Promise<string[]> {
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
  // Expand each card by quantity into flat name list
  return cards.flatMap(c => Array(c.quantity).fill(c.name))
}

function validateForm(form: FormState): FieldErrors {
  const errors: FieldErrors = {}

  if (!form.player1.name.trim()) errors.player1Name = 'Name is required'
  if (!form.player2.name.trim()) errors.player2Name = 'Name is required'
  if (
    form.player1.name.trim() &&
    form.player2.name.trim() &&
    form.player1.name.trim() === form.player2.name.trim()
  ) {
    errors.names = 'Player names must be different'
  }

  if (form.player1.playerType === 'llm') {
    if (!form.player1.baseUrl.trim() || (!form.player1.baseUrl.startsWith('http://') && !form.player1.baseUrl.startsWith('https://'))) {
      errors.player1Url = 'Valid http(s) URL required for LLM player'
    }
    if (!form.player1.model.trim()) errors.player1Model = 'Model is required for LLM player'
  }

  if (form.player2.playerType === 'llm') {
    if (!form.player2.baseUrl.trim() || (!form.player2.baseUrl.startsWith('http://') && !form.player2.baseUrl.startsWith('https://'))) {
      errors.player2Url = 'Valid http(s) URL required for LLM player'
    }
    if (!form.player2.model.trim()) errors.player2Model = 'Model is required for LLM player'
  }

  if (form.format === 'commander') {
    if (!form.commander1.trim()) errors.commander1 = 'Commander name required'
    if (!form.commander2.trim()) errors.commander2 = 'Commander name required'
  }

  if (form.observerUrl.trim() && !form.observerModel.trim()) {
    errors.observerModel = 'Observer model is required when observer URL is set'
  }

  return errors
}

function hasErrors(errors: FieldErrors): boolean {
  return Object.keys(errors).length > 0
}

// ── Sub-component: player config card ────────────────────────────────────────

function PlayerCard({
  label,
  state,
  onChange,
  errors,
}: {
  label: string
  state: PlayerFormState
  onChange: (patch: Partial<PlayerFormState>) => void
  errors: { name?: string; url?: string; model?: string; names?: string }
}) {
  return (
    <div className="cg-player-card">
      <div className="cg-player-title">{label}</div>
      <div className="cg-row">
        <div className="cg-field">
          <label>Name</label>
          <input
            value={state.name}
            onChange={e => onChange({ name: e.target.value })}
            placeholder="Player name"
          />
          {errors.name && <span className="cg-field-error">{errors.name}</span>}
          {errors.names && <span className="cg-field-error">{errors.names}</span>}
        </div>
        <div className="cg-field cg-field--shrink">
          <label>Type</label>
          <select
            value={state.playerType}
            onChange={e => onChange({ playerType: e.target.value as 'llm' | 'heuristic' })}
          >
            <option value="heuristic">Heuristic</option>
            <option value="llm">LLM</option>
          </select>
        </div>
      </div>
      {state.playerType === 'llm' && (
        <div className="cg-row">
          <div className="cg-field">
            <label>LLM Endpoint URL</label>
            <input
              value={state.baseUrl}
              onChange={e => onChange({ baseUrl: e.target.value })}
              placeholder="http://localhost:8080/v1"
            />
            {errors.url && <span className="cg-field-error">{errors.url}</span>}
          </div>
          <div className="cg-field">
            <label>Model</label>
            <input
              value={state.model}
              onChange={e => onChange({ model: e.target.value })}
              placeholder="devstral"
            />
            {errors.model && <span className="cg-field-error">{errors.model}</span>}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function CreateGameForm({ onClose }: Props) {
  const navigate = useNavigate()
  const [form, setForm] = useState<FormState>(defaultForm)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const setPlayer1 = (patch: Partial<PlayerFormState>) =>
    setForm(f => ({ ...f, player1: { ...f.player1, ...patch } }))
  const setPlayer2 = (patch: Partial<PlayerFormState>) =>
    setForm(f => ({ ...f, player2: { ...f.player2, ...patch } }))

  // Warn when debug is on but no LLM and no observer URL
  const showObserverWarning =
    form.debug &&
    form.player1.playerType === 'heuristic' &&
    form.player2.playerType === 'heuristic' &&
    !form.observerUrl.trim()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setServerError(null)

    const errors = validateForm(form)
    setFieldErrors(errors)
    if (hasErrors(errors)) return

    setIsSubmitting(true)
    try {
      // Resolve Archidekt URLs before building the body
      let deck1: string[]
      let deck2: string[]
      try {
        deck1 = isArchidektUrl(form.deck1Text)
          ? await resolveArchidektDeck(form.deck1Text)
          : parseDeck(form.deck1Text)
      } catch (err) {
        setFieldErrors(prev => ({ ...prev, deck1: (err as Error).message }))
        return
      }
      try {
        deck2 = isArchidektUrl(form.deck2Text)
          ? await resolveArchidektDeck(form.deck2Text)
          : parseDeck(form.deck2Text)
      } catch (err) {
        setFieldErrors(prev => ({ ...prev, deck2: (err as Error).message }))
        return
      }

      const body = {
        player1: {
          name: form.player1.name.trim(),
          player_type: form.player1.playerType,
          base_url: form.player1.baseUrl.trim(),
          model: form.player1.model.trim(),
        },
        player2: {
          name: form.player2.name.trim(),
          player_type: form.player2.playerType,
          base_url: form.player2.baseUrl.trim(),
          model: form.player2.model.trim(),
        },
        deck1,
        deck2,
        format: form.format,
        commander1: form.format === 'commander' ? form.commander1.trim() : null,
        commander2: form.format === 'commander' ? form.commander2.trim() : null,
        verbose: form.verbose,
        max_turns: parseInt(form.maxTurns, 10) || 200,
        debug: form.debug,
        observer_url: form.observerUrl.trim() || null,
        observer_model: form.observerModel.trim() || null,
      }

      const res = await fetch('/ai-game', {
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
      if (gameId) {
        onClose()
        navigate(`/game/${gameId}`)
      }
    } catch {
      setServerError('Could not reach the engine. Is it running?')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="cg-overlay" onClick={onClose}>
      <div className="cg-modal" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="cg-header">
          <h2>New AI Game</h2>
          <button className="cg-close-btn" onClick={onClose} title="Close">✕</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="cg-body">

            {/* Players */}
            <div>
              <div className="cg-section-label">Players</div>
              <div className="cg-players">
                <PlayerCard
                  label="Player 1"
                  state={form.player1}
                  onChange={setPlayer1}
                  errors={{
                    name: fieldErrors.player1Name,
                    url: fieldErrors.player1Url,
                    model: fieldErrors.player1Model,
                    names: fieldErrors.names,
                  }}
                />
                <PlayerCard
                  label="Player 2"
                  state={form.player2}
                  onChange={setPlayer2}
                  errors={{
                    name: fieldErrors.player2Name,
                    url: fieldErrors.player2Url,
                    model: fieldErrors.player2Model,
                  }}
                />
              </div>
            </div>

            <div className="cg-divider" />

            {/* Decks */}
            <div>
              <div className="cg-section-label">Decks (optional)</div>
              <div className="cg-row">
                <div className="cg-field">
                  <label>Player 1 deck</label>
                  <textarea
                    value={form.deck1Text}
                    onChange={e => {
                      setFieldErrors(prev => ({ ...prev, deck1: undefined }))
                      setForm(f => ({ ...f, deck1Text: e.target.value }))
                    }}
                    placeholder="Leave blank for default deck — paste comma-separated card names or an Archidekt URL"
                  />
                  {fieldErrors.deck1 && <span className="cg-field-error">{fieldErrors.deck1}</span>}
                </div>
                <div className="cg-field">
                  <label>Player 2 deck</label>
                  <textarea
                    value={form.deck2Text}
                    onChange={e => {
                      setFieldErrors(prev => ({ ...prev, deck2: undefined }))
                      setForm(f => ({ ...f, deck2Text: e.target.value }))
                    }}
                    placeholder="Leave blank for default deck — paste comma-separated card names or an Archidekt URL"
                  />
                  {fieldErrors.deck2 && <span className="cg-field-error">{fieldErrors.deck2}</span>}
                </div>
              </div>
            </div>

            <div className="cg-divider" />

            {/* Format */}
            <div>
              <div className="cg-section-label">Format</div>
              <div className="cg-row">
                <div className="cg-field cg-field--shrink">
                  <label>Game format</label>
                  <select
                    value={form.format}
                    onChange={e => setForm(f => ({ ...f, format: e.target.value as 'standard' | 'commander' }))}
                  >
                    <option value="standard">Standard</option>
                    <option value="commander">Commander</option>
                  </select>
                </div>
              </div>
              {form.format === 'commander' && (
                <div className="cg-row">
                  <div className="cg-field">
                    <label>Commander (Player 1)</label>
                    <input
                      value={form.commander1}
                      onChange={e => setForm(f => ({ ...f, commander1: e.target.value }))}
                      placeholder="e.g. Ghalta, Primal Hunger"
                    />
                    {fieldErrors.commander1 && (
                      <span className="cg-field-error">{fieldErrors.commander1}</span>
                    )}
                  </div>
                  <div className="cg-field">
                    <label>Commander (Player 2)</label>
                    <input
                      value={form.commander2}
                      onChange={e => setForm(f => ({ ...f, commander2: e.target.value }))}
                      placeholder="e.g. Multani, Maro-Sorcerer"
                    />
                    {fieldErrors.commander2 && (
                      <span className="cg-field-error">{fieldErrors.commander2}</span>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="cg-divider" />

            {/* Debug / Observer */}
            <div>
              <div className="cg-section-label">Debug &amp; Observer</div>
              <label className="cg-check-row">
                <input
                  type="checkbox"
                  checked={form.debug}
                  onChange={e => setForm(f => ({ ...f, debug: e.target.checked }))}
                />
                Enable debug panel (captures AI prompts &amp; commentary)
              </label>
              {form.debug && (
                <div className="cg-row" style={{ marginTop: '0.6rem' }}>
                  <div className="cg-field">
                    <label>Observer endpoint URL (optional)</label>
                    <input
                      value={form.observerUrl}
                      onChange={e => setForm(f => ({ ...f, observerUrl: e.target.value }))}
                      placeholder="http://localhost:8080/v1"
                    />
                  </div>
                  <div className="cg-field">
                    <label>Observer model (optional)</label>
                    <input
                      value={form.observerModel}
                      onChange={e => setForm(f => ({ ...f, observerModel: e.target.value }))}
                      placeholder="e.g. devstral"
                    />
                    {fieldErrors.observerModel && (
                      <span className="cg-field-error">{fieldErrors.observerModel}</span>
                    )}
                  </div>
                </div>
              )}
              {showObserverWarning && (
                <div className="cg-warning" style={{ marginTop: '0.5rem' }}>
                  All players are heuristic and no observer URL is set — no AI commentary will be available. The debug panel will still capture game events.
                </div>
              )}
            </div>

            <div className="cg-divider" />

            {/* Advanced */}
            <div>
              <button
                type="button"
                className="cg-advanced-toggle"
                onClick={() => setShowAdvanced(v => !v)}
              >
                {showAdvanced ? '▼' : '▶'} Advanced options
              </button>
              {showAdvanced && (
                <div className="cg-advanced-section" style={{ marginTop: '0.6rem' }}>
                  <div className="cg-row">
                    <div className="cg-field cg-field--shrink">
                      <label>Max turns (0 = unlimited)</label>
                      <input
                        type="number"
                        min={0}
                        value={form.maxTurns}
                        onChange={e => setForm(f => ({ ...f, maxTurns: e.target.value }))}
                        style={{ width: '100px' }}
                      />
                    </div>
                  </div>
                  <label className="cg-check-row">
                    <input
                      type="checkbox"
                      checked={form.verbose}
                      onChange={e => setForm(f => ({ ...f, verbose: e.target.checked }))}
                    />
                    Verbose play-by-play logging
                  </label>
                </div>
              )}
            </div>

            {/* Server error */}
            {serverError && (
              <div className="cg-error">{serverError}</div>
            )}

          </div>

          {/* Footer */}
          <div className="cg-footer">
            <button type="button" className="cg-btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="cg-btn-start" disabled={isSubmitting}>
              {isSubmitting ? 'Starting…' : 'Start Game'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
