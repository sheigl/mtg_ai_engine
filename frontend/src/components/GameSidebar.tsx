import { useState, useEffect, useRef } from 'react'
import { useTranscript } from '../hooks/useTranscript'
import { useDebugLog } from '../hooks/useDebugLog'
import { PromptResponseBlock } from './PromptResponseBlock'
import { CommentaryBlock } from './CommentaryBlock'
import type { DebugEntry } from '../types/debug'

interface GameSidebarProps {
  gameId: string
  isGameOver: boolean
}

const VISIBLE_EVENTS = new Set([
  'cast', 'resolve', 'zone_change', 'damage', 'attack', 'block',
  'life_change', 'game_end', 'trigger', 'activate', 'draw',
])

const EVENT_COLORS: Record<string, string> = {
  cast: 'var(--accent)',
  resolve: 'var(--success)',
  damage: 'var(--danger)',
  life_change: 'var(--warning)',
  attack: 'var(--mtg-red)',
  block: 'var(--mtg-white)',
  game_end: 'var(--success)',
  zone_change: 'var(--text-secondary)',
  trigger: '#c9a0ff',
  activate: 'var(--mtg-blue)',
  draw: 'var(--text-muted)',
}

const PAGE_SIZE = 10

export function GameSidebar({ gameId, isGameOver }: GameSidebarProps) {
  const [activeTab, setActiveTab] = useState<'log' | 'ai'>('log')

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'var(--surface-elevated)',
      borderRadius: 'var(--radius-lg)',
      border: '1px solid var(--border-subtle)',
      overflow: 'hidden',
    }}>
      {/* Tab bar */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid var(--border-subtle)',
        flexShrink: 0,
      }}>
        <TabButton label="Action Log" isActive={activeTab === 'log'} onClick={() => setActiveTab('log')} />
        <TabButton label="AI" isActive={activeTab === 'ai'} onClick={() => setActiveTab('ai')} />
      </div>

      {/* Content */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {activeTab === 'log' ? (
          <ActionLogContent gameId={gameId} />
        ) : (
          <DebugLogContent gameId={gameId} isGameOver={isGameOver} />
        )}
      </div>
    </div>
  )
}

function TabButton({ label, isActive, onClick }: { label: string; isActive: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        padding: 'var(--space-3) var(--space-4)',
        background: isActive ? 'var(--surface-hover)' : 'transparent',
        color: isActive ? 'var(--text-primary)' : 'var(--text-tertiary)',
        border: 'none',
        borderBottom: `2px solid ${isActive ? 'var(--accent)' : 'transparent'}`,
        fontSize: 'var(--text-sm)',
        fontWeight: isActive ? 700 : 500,
        cursor: 'pointer',
        transition: 'all var(--transition-fast)',
      }}
    >
      {label}
    </button>
  )
}

function ActionLogContent({ gameId }: { gameId: string }) {
  const { entries } = useTranscript(gameId)
  const scrollRef = useRef<HTMLDivElement>(null)

  const filtered = entries.filter(e => VISIBLE_EVENTS.has(e.event_type))

  const byTurn: { turn: number; entries: typeof filtered }[] = []
  for (const entry of filtered) {
    const last = byTurn[byTurn.length - 1]
    if (last && last.turn === entry.turn) {
      last.entries.push(entry)
    } else {
      byTurn.push({ turn: entry.turn, entries: [entry] })
    }
  }

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [filtered.length])

  return (
    <div
      ref={scrollRef}
      style={{
        height: '100%',
        overflowY: 'auto',
        padding: 'var(--space-2)',
      }}
    >
      {filtered.length === 0 && (
        <div style={{
          color: 'var(--text-muted)',
          fontSize: 'var(--text-sm)',
          textAlign: 'center',
          padding: 'var(--space-8) var(--space-4)',
        }}>
          Waiting for game actions...
        </div>
      )}
      {byTurn.map(({ turn, entries: turnEntries }) => (
        <div key={turn}>
          <div style={{
            fontSize: 'var(--text-xs)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: 'var(--text-muted)',
            padding: 'var(--space-2) var(--space-2) var(--space-1)',
            borderBottom: '1px solid var(--border-subtle)',
            marginBottom: 'var(--space-1)',
          }}>
            Turn {turn}
          </div>
          {turnEntries.map((entry) => (
            <div
              key={entry.seq}
              style={{
                padding: 'var(--space-1) var(--space-2)',
                fontSize: 'var(--text-xs)',
                lineHeight: 'var(--leading-normal)',
                borderLeft: `2px solid ${EVENT_COLORS[entry.event_type] || 'var(--border-subtle)'}`,
                marginBottom: 'var(--space-1)',
                color: 'var(--text-primary)',
                borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
              }}
            >
              {entry.description}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

function DebugLogContent({ gameId, isGameOver }: { gameId: string; isGameOver: boolean }) {
  const [showAll, setShowAll] = useState(false)
  const [paused, setPaused] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const { entries, isLoading } = useDebugLog(gameId, true, isGameOver)

  const allSources = Array.from(
    new Set(entries.filter(e => e.source !== 'Observer AI').map(e => e.source))
  )

  const [frozenEntries, setFrozenEntries] = useState<DebugEntry[]>([])
  useEffect(() => {
    if (!paused) setFrozenEntries([])
  }, [paused])

  const displayedAll = paused && frozenEntries.length > 0 ? frozenEntries : entries
  const visibleEntries = showAll ? displayedAll : displayedAll.slice(-PAGE_SIZE)
  const hiddenCount = displayedAll.length - visibleEntries.length

  useEffect(() => {
    if (!paused && !showAll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [entries.length, paused, showAll])

  const togglePause = async () => {
    const next = !paused
    if (next) setFrozenEntries(entries)
    setPaused(next)
    await fetch(`/game/${gameId}/${next ? 'pause' : 'resume'}`, { method: 'POST' })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Debug controls */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 'var(--space-2) var(--space-3)',
        borderBottom: '1px solid var(--border-subtle)',
        flexShrink: 0,
      }}>
        <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-tertiary)' }}>
          AI Commentary
        </span>
        {!isGameOver && (
          <button
            className="btn btn--ghost btn--sm"
            onClick={togglePause}
            title={paused ? 'Resume game' : 'Pause game'}
          >
            {paused ? '▶ Resume' : '⏸ Pause'}
          </button>
        )}
      </div>

      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-2)' }}>
        {isLoading ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 'var(--space-8)' }}>
            Loading…
          </div>
        ) : entries.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 'var(--space-8)', fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-relaxed)' }}>
            No AI entries yet.
            <br />
            <small style={{ color: 'var(--text-tertiary)' }}>
              Heuristic players don't generate LLM entries.
              Add an observer URL when creating the game to see move commentary.
            </small>
          </div>
        ) : (
          <>
            {hiddenCount > 0 && (
              <button
                className="btn btn--ghost btn--sm"
                style={{ width: '100%', marginBottom: 'var(--space-2)' }}
                onClick={() => setShowAll(true)}
              >
                ↑ Show {hiddenCount} earlier {hiddenCount === 1 ? 'entry' : 'entries'}
              </button>
            )}
            {showAll && (
              <button
                className="btn btn--ghost btn--sm"
                style={{ width: '100%', marginBottom: 'var(--space-2)' }}
                onClick={() => setShowAll(false)}
              >
                ↑ Show latest {PAGE_SIZE} only
              </button>
            )}
            {visibleEntries.map((entry: DebugEntry) =>
              entry.entry_type === 'commentary' ? (
                <CommentaryBlock key={entry.entry_id} entry={entry} gameId={gameId} />
              ) : (
                <PromptResponseBlock key={entry.entry_id} entry={entry} allSources={allSources} gameId={gameId} />
              )
            )}
          </>
        )}
      </div>
    </div>
  )
}
