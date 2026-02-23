import { useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'
import { Info } from 'lucide-react'

interface BulletRegenerationModalProps {
  isOpen: boolean
  onClose: () => void
  onRegenerate: (refinementPrompt?: string) => void
  artifactCount: number
  isLoading?: boolean
}

const QUICK_SUGGESTIONS = [
  { label: 'Add more metrics', prompt: 'Add specific metrics and quantifiable achievements' },
  { label: 'Focus on leadership', prompt: 'Focus more on leadership and team management' },
  { label: 'More technical detail', prompt: 'Emphasize technical depth over business impact' },
  { label: 'Use action verbs', prompt: 'Use more action verbs and reduce generic language' },
]

export function BulletRegenerationModal({
  isOpen,
  onClose,
  onRegenerate,
  artifactCount,
  isLoading = false
}: BulletRegenerationModalProps) {
  const [refinementPrompt, setRefinementPrompt] = useState('')
  const [selectedSuggestion, setSelectedSuggestion] = useState<string | null>(null)

  const handleSuggestionClick = (prompt: string) => {
    setRefinementPrompt(prompt)
    setSelectedSuggestion(prompt)
  }

  const handleSubmit = () => {
    onRegenerate(refinementPrompt || undefined)
    // Reset state
    setRefinementPrompt('')
    setSelectedSuggestion(null)
  }

  const handleClose = () => {
    onClose()
    // Reset state on close
    setRefinementPrompt('')
    setSelectedSuggestion(null)
  }

  const bulletsToRegenerate = artifactCount * 3

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Regenerate Bullets" size="lg">
      <div className="space-y-4">
        {/* Description */}
        <p className="text-sm text-gray-600">
          Provide hints to improve your bullet points. This prompt is temporary and won't be saved.
        </p>

        {/* Info Alert */}
        <div className="flex items-start gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900">
            <p className="font-medium mb-1">Temporary Refinement</p>
            <p>Refinement prompts are temporary and only apply to this generation. To permanently improve bullets, edit your artifact context.</p>
          </div>
        </div>

        {/* Quick Suggestions */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Quick Suggestions</label>
          <div className="flex flex-wrap gap-2">
            {QUICK_SUGGESTIONS.map((suggestion) => (
              <Button
                key={suggestion.label}
                variant={selectedSuggestion === suggestion.prompt ? 'primary' : 'outline'}
                size="sm"
                onClick={() => handleSuggestionClick(suggestion.prompt)}
                type="button"
                disabled={isLoading}
              >
                {suggestion.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Custom Prompt */}
        <div className="space-y-2">
          <label htmlFor="refinement" className="block text-sm font-medium text-gray-700">
            Custom Refinement Prompt (Optional)
          </label>
          <Textarea
            id="refinement"
            value={refinementPrompt}
            onChange={(e) => {
              setRefinementPrompt(e.target.value)
              setSelectedSuggestion(null)
            }}
            placeholder="Describe how to improve these bullets..."
            rows={4}
            maxLength={500}
            className="resize-none"
            disabled={isLoading}
          />
          <p className="text-sm text-gray-500">
            {refinementPrompt.length}/500 characters
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Regenerating...' : `Regenerate ${bulletsToRegenerate} Bullets`}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
