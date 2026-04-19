import { useQuery } from '@tanstack/react-query'
import type { Step } from '../types/game'

export interface LegalAction {
  action_type: string
  description: string
  card_id?: string
  permanent_id?: string
  valid_targets?: string[]
  mana_options?: { mana_cost: string }[]
  x_value?: number | null
  face_index?: number
  modes_chosen?: number[]
  alternative_cost?: string
  from_graveyard?: boolean
}

interface LegalActionsResponse {
  priority_player: string
  phase: string
  step: Step
  legal_actions: LegalAction[]
  is_paused: boolean
  is_game_over: boolean
  winner: string | null
}

interface UseLegalActionsResult {
  isMyTurn: boolean
  legalActions: LegalAction[]
  legalActionsByCard: Map<string, LegalAction[]>
  hasPendingChoice: boolean
  step: Step | null
  phase: string | null
  isGameOver: boolean
  winner: string | null
}

export function useLegalActions(
  gameId: string | undefined,
  humanPlayerName: string,
): UseLegalActionsResult {
  const { data } = useQuery<LegalActionsResponse>({
    queryKey: ['legalActions', gameId],
    queryFn: async () => {
      const res = await fetch(`/game/${gameId}/legal-actions`)
      if (!res.ok) throw new Error('FETCH_ERROR')
      const json = await res.json()
      return json.data as LegalActionsResponse
    },
    enabled: !!gameId,
    refetchInterval: 750,
    refetchIntervalInBackground: false,
  })

  if (!data) {
    return {
      isMyTurn: false,
      legalActions: [],
      legalActionsByCard: new Map(),
      hasPendingChoice: false,
      step: null,
      phase: null,
      isGameOver: false,
      winner: null,
    }
  }

  const isMyTurn = data.priority_player === humanPlayerName
  const legalActions = data.legal_actions ?? []

  // Build card_id → actions map for fast lookup
  const legalActionsByCard = new Map<string, LegalAction[]>()
  for (const action of legalActions) {
    if (action.card_id) {
      const existing = legalActionsByCard.get(action.card_id) ?? []
      existing.push(action)
      legalActionsByCard.set(action.card_id, existing)
    }
    if (action.permanent_id) {
      const existing = legalActionsByCard.get(action.permanent_id) ?? []
      existing.push(action)
      legalActionsByCard.set(action.permanent_id, existing)
    }
  }

  // A pending choice is detected when legalActions only contains choice-type actions
  const choiceTypes = new Set(['scry_choice', 'surveil_choice', 'discard', 'mulligan', 'cascade_choice', 'choice'])
  const hasPendingChoice = legalActions.length > 0 && legalActions.every(a => choiceTypes.has(a.action_type))

  return {
    isMyTurn,
    legalActions,
    legalActionsByCard,
    hasPendingChoice,
    step: data.step,
    phase: data.phase,
    isGameOver: data.is_game_over,
    winner: data.winner,
  }
}
