import { useState, useEffect } from 'react'

interface ETBChoiceModalProps {
  permanentName: string
  choiceType: string
  costAmount: number
  costType: string
  onChoice: (pay: boolean) => void
}

export function ETBChoiceModal({
  permanentName,
  choiceType,
  costAmount,
  costType,
  onChoice,
}: ETBChoiceModalProps) {
  const [selected, setSelected] = useState<boolean | null>(null)

  // Auto-close after selection
  useEffect(() => {
    if (selected !== null) {
      onChoice(selected)
    }
  }, [selected, onChoice])

  // Format the cost display
  const costDisplay = costType === 'life' 
    ? `${costAmount} life` 
    : costType === 'snow'
    ? `${costAmount} snow mana`
    : `${costAmount} ${costType}`

  // Get choice description
  const choiceDescription = choiceType === 'shockland'
    ? `Pay ${costDisplay} to enter untapped`
    : `Enter tapped (don't pay)`

  return (
    <div className="modal-overlay">
      <div className="modal" style={{ maxWidth: 400 }}>
        <div className="modal-header">
          <h3 className="modal-title">ETB Choice: {permanentName}</h3>
        </div>
        
        <div className="modal-body">
          <p style={{ marginBottom: 'var(--space-4)', color: 'var(--text-secondary)' }}>
            How should {permanentName} enter the battlefield?
          </p>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <button
              onClick={() => setSelected(true)}
              className="btn btn--primary"
              style={{ padding: 'var(--space-4)', textAlign: 'left' }}
            >
              <div style={{ fontWeight: 600 }}>
                Pay {costDisplay}
              </div>
              <div style={{ fontSize: 'var(--text-sm)', opacity: 0.8, marginTop: 4 }}>
                {permanentName} enters untapped (ready to use)
              </div>
            </button>
            
            <button
              onClick={() => setSelected(false)}
              className="btn btn--secondary"
              style={{ padding: 'var(--space-4)', textAlign: 'left' }}
            >
              <div style={{ fontWeight: 600 }}>
                Don't pay
              </div>
              <div style={{ fontSize: 'var(--text-sm)', opacity: 0.8, marginTop: 4 }}>
                {permanentName} enters tapped
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}