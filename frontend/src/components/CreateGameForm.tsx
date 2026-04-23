import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import '../styles/create-game.css'

interface PlayerFormState {
  name: string
  playerType: 'llm' | 'heuristic' | 'human'
  baseUrl: string
  model: string
  enableThinking: 'auto' | 'on' | 'off'
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
  seriesCount: number
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
  humanConflict?: string
  deck1?: string
  deck2?: string
}

interface Props {
  onClose: () => void
}

const defaultPlayer = (name: string): PlayerFormState => ({
  name,
  playerType: 'heuristic',
  baseUrl: 'http://localhost:8080/v1',
  model: '',
  enableThinking: 'auto',
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
  maxTurns: '0',
  debug: false,
  observerUrl: 'http://localhost:8080/v1',
  observerModel: '',
  seriesCount: 1,
})

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

  if (form.player1.playerType === 'human' && form.player2.playerType === 'human') {
    errors.humanConflict = 'Both players cannot be Human'
  }

  if (form.player1.playerType === 'llm') {
    if (!form.player1.baseUrl.trim() || (!form.player1.baseUrl.startsWith('http://') && !form.player1.baseUrl.startsWith('https://'))) {
      errors.player1Url = 'Valid http(s) URL required'
    }
    if (!form.player1.model.trim()) errors.player1Model = 'Model is required'
  }

  if (form.player2.playerType === 'llm') {
    if (!form.player2.baseUrl.trim() || (!form.player2.baseUrl.startsWith('http://') && !form.player2.baseUrl.startsWith('https://'))) {
      errors.player2Url = 'Valid http(s) URL required'
    }
    if (!form.player2.model.trim()) errors.player2Model = 'Model is required'
  }

  if (form.format === 'commander') {
    if (!form.commander1.trim() && !isArchidektUrl(form.deck1Text))
      errors.commander1 = 'Commander name required'
    if (!form.commander2.trim() && !isArchidektUrl(form.deck2Text))
      errors.commander2 = 'Commander name required'
  }

  if (form.debug && form.observerUrl.trim() && !form.observerModel.trim()) {
    errors.observerModel = 'Observer model is required when observer URL is set'
  }

  return errors
}

function hasErrors(errors: FieldErrors): boolean {
  return Object.keys(errors).length > 0
}

function thinkingValue(v: 'auto' | 'on' | 'off'): boolean | null {
  if (v === 'on') return true
  if (v === 'off') return false
  return null
}

function PlayerCard({
  label,
  state,
  onChange,
  errors,
}: {
  label: string
  state: PlayerFormState
  onChange: (patch: Partial<PlayerFormState>) => void
  errors: { name?: string; url?: string; model?: string; names?: string; humanConflict?: string }
}) {
  return (
    <div className="form-card">
      <div className="form-card-title">{label}</div>
      <div className="form-row">
        <div className="form-field">
          <label className="label">Name</label>
          <input
            className="input"
            value={state.name}
            onChange={e => onChange({ name: e.target.value })}
            placeholder="Player name"
          />
          {errors.name && <span className="form-error">{errors.name}</span>}
          {errors.names && <span className="form-error">{errors.names}</span>}
          {errors.humanConflict && <span className="form-error">{errors.humanConflict}</span>}
        </div>
        <div className="form-field form-field--shrink">
          <label className="label">Type</label>
          <select
            className="select"
            value={state.playerType}
            onChange={e => onChange({ playerType: e.target.value as PlayerFormState['playerType'] })}
          >
            <option value="heuristic">Heuristic Bot</option>
            <option value="llm">LLM (AI)</option>
            <option value="human">Human (You)</option>
          </select>
        </div>
      </div>
      {state.playerType === 'llm' && (
        <>
          <div className="form-row">
            <div className="form-field">
              <label className="label">LLM Endpoint URL</label>
              <input
                className="input"
                value={state.baseUrl}
                onChange={e => onChange({ baseUrl: e.target.value })}
                placeholder="http://localhost:8080/v1"
              />
              {errors.url && <span className="form-error">{errors.url}</span>}
            </div>
            <div className="form-field">
              <label className="label">Model</label>
              <input
                className="input"
                value={state.model}
                onChange={e => onChange({ model: e.target.value })}
                placeholder="devstral"
              />
              {errors.model && <span className="form-error">{errors.model}</span>}
            </div>
          </div>
          <div className="form-row" style={{ marginTop: 'var(--space-3)' }}>
            <div className="form-field form-field--shrink">
              <label className="label">Thinking</label>
              <select
                className="select"
                value={state.enableThinking}
                onChange={e => onChange({ enableThinking: e.target.value as PlayerFormState['enableThinking'] })}
              >
                <option value="auto">Auto (model default)</option>
                <option value="on">Enabled</option>
                <option value="off">Disabled</option>
              </select>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

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

  const hasHumanPlayer = form.player1.playerType === 'human' || form.player2.playerType === 'human'

  const showObserverWarning =
    form.debug &&
    form.player1.playerType !== 'llm' &&
    form.player2.playerType !== 'llm' &&
    !form.observerUrl.trim()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setServerError(null)

    const errors = validateForm(form)
    setFieldErrors(errors)
    if (hasErrors(errors)) return

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

      const resolvedCommander1 = form.commander1.trim() || detectedCommander1 || ''
      const resolvedCommander2 = form.commander2.trim() || detectedCommander2 || ''

      if (hasHumanPlayer) {
        const aiPlayer = form.player1.playerType !== 'human' ? form.player1 : form.player2
        const body = {
          player1_type: form.player1.playerType,
          player2_type: form.player2.playerType,
          player1_name: form.player1.name.trim(),
          player2_name: form.player2.name.trim(),
          player1_deck: deck1,
          player2_deck: deck2,
          format: form.format,
          ...(form.format === 'commander' && {
            commander1: resolvedCommander1,
            commander2: resolvedCommander2,
          }),
          ai_model: aiPlayer.model.trim(),
          ai_base_url: aiPlayer.baseUrl.trim(),
          ai_enable_thinking: thinkingValue(aiPlayer.enableThinking),
          observer_enabled: form.debug,
          observer_url: form.debug ? (form.observerUrl.trim() || null) : null,
          observer_model: form.debug ? (form.observerModel.trim() || null) : null,
          verbose: form.verbose,
          max_turns: parseInt(form.maxTurns, 10) || 0,
          debug: form.debug,
          series_count: form.seriesCount,
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
          onClose()
          navigate(`/human-game/${gameId}`, { state: { humanPlayerName } })
        }
      } else {
        const body = {
          player1: {
            name: form.player1.name.trim(),
            player_type: form.player1.playerType,
            base_url: form.player1.baseUrl.trim(),
            model: form.player1.model.trim(),
            enable_thinking: thinkingValue(form.player1.enableThinking),
          },
          player2: {
            name: form.player2.name.trim(),
            player_type: form.player2.playerType,
            base_url: form.player2.baseUrl.trim(),
            model: form.player2.model.trim(),
            enable_thinking: thinkingValue(form.player2.enableThinking),
          },
          deck1,
          deck2,
          format: form.format,
          commander1: form.format === 'commander' ? resolvedCommander1 : null,
          commander2: form.format === 'commander' ? resolvedCommander2 : null,
          verbose: form.verbose,
          max_turns: parseInt(form.maxTurns, 10) || 0,
          debug: form.debug,
          observer_url: form.debug ? (form.observerUrl.trim() || null) : null,
          observer_model: form.debug ? (form.observerModel.trim() || null) : null,
          series_count: form.seriesCount,
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
      }
    } catch {
      setServerError('Could not reach the engine. Is it running?')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="cg-modal" onClick={e => e.stopPropagation()}>
      <div className="cg-header">
        <h2>New Game</h2>
        <button className="btn btn--ghost btn--icon" onClick={onClose} title="Close" style={{ width: 32, height: 32 }}>
          ✕
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="cg-body">
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
                  humanConflict: fieldErrors.humanConflict,
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

          <hr className="divider" />

          <div>
            <div className="cg-section-label">Decks (optional)</div>
            <div className="form-row">
              <div className="form-field">
                <label className="label">Player 1 deck</label>
                <textarea
                  className="textarea"
                  value={form.deck1Text}
                  onChange={e => {
                    setFieldErrors(prev => ({ ...prev, deck1: undefined }))
                    setForm(f => ({ ...f, deck1Text: e.target.value }))
                  }}
                  placeholder="Leave blank for default deck — paste comma-separated card names or an Archidekt URL"
                />
                {fieldErrors.deck1 && <span className="form-error">{fieldErrors.deck1}</span>}
              </div>
              <div className="form-field">
                <label className="label">Player 2 deck</label>
                <textarea
                  className="textarea"
                  value={form.deck2Text}
                  onChange={e => {
                    setFieldErrors(prev => ({ ...prev, deck2: undefined }))
                    setForm(f => ({ ...f, deck2Text: e.target.value }))
                  }}
                  placeholder="Leave blank for default deck — paste comma-separated card names or an Archidekt URL"
                />
                {fieldErrors.deck2 && <span className="form-error">{fieldErrors.deck2}</span>}
              </div>
            </div>
          </div>

          <hr className="divider" />

          <div>
            <div className="cg-section-label">Format</div>
            <div className="form-row">
              <div className="form-field form-field--shrink">
                <label className="label">Game format</label>
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
              <div className="form-row">
                <div className="form-field">
                  <label className="label">Commander (Player 1)</label>
                  <input
                    className="input"
                    value={form.commander1}
                    onChange={e => setForm(f => ({ ...f, commander1: e.target.value }))}
                    placeholder="e.g. Ghalta, Primal Hunger"
                  />
                  {fieldErrors.commander1 && <span className="form-error">{fieldErrors.commander1}</span>}
                </div>
                <div className="form-field">
                  <label className="label">Commander (Player 2)</label>
                  <input
                    className="input"
                    value={form.commander2}
                    onChange={e => setForm(f => ({ ...f, commander2: e.target.value }))}
                    placeholder="e.g. Multani, Maro-Sorcerer"
                  />
                  {fieldErrors.commander2 && <span className="form-error">{fieldErrors.commander2}</span>}
                </div>
              </div>
            )}
          </div>

          <hr className="divider" />

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
              <div className="form-row" style={{ marginTop: 'var(--space-3)' }}>
                <div className="form-field">
                  <label className="label">Observer endpoint URL (optional)</label>
                  <input
                    className="input"
                    value={form.observerUrl}
                    onChange={e => setForm(f => ({ ...f, observerUrl: e.target.value }))}
                    placeholder="http://localhost:8080/v1"
                  />
                </div>
                <div className="form-field">
                  <label className="label">Observer model (optional)</label>
                  <input
                    className="input"
                    value={form.observerModel}
                    onChange={e => setForm(f => ({ ...f, observerModel: e.target.value }))}
                    placeholder="e.g. devstral"
                  />
                  {fieldErrors.observerModel && <span className="form-error">{fieldErrors.observerModel}</span>}
                </div>
              </div>
            )}
            {showObserverWarning && (
              <div className="cg-warning">
                No LLM players and no observer URL — no AI commentary will be available. The debug panel will still capture game events.
              </div>
            )}
          </div>

          <hr className="divider" />

          <div>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => setShowAdvanced(v => !v)}
              style={{ padding: 0, background: 'transparent', border: 'none' }}
            >
              {showAdvanced ? '▼' : '▶'} Advanced options
            </button>
            {showAdvanced && (
              <div className="form-card" style={{ marginTop: 'var(--space-3)' }}>
                <div className="form-row">
                  <div className="form-field form-field--shrink">
                    <label className="label">Max turns (0 = unlimited)</label>
                    <input
                      className="input"
                      type="number"
                      min={0}
                      value={form.maxTurns}
                      onChange={e => setForm(f => ({ ...f, maxTurns: e.target.value }))}
                      style={{ width: 100 }}
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

          {serverError && (
            <div className="cg-error">{serverError}</div>
          )}
        </div>

        <div className="cg-footer">
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn--primary" disabled={isSubmitting}>
            {isSubmitting ? 'Starting…' : hasHumanPlayer ? 'Start Game' : 'Start AI Game'}
          </button>
        </div>
      </form>
    </div>
  )
}
