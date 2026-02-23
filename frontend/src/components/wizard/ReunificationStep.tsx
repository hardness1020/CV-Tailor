/**
 * ReunificationStep component (ft-045, ft-046)
 * Blocking reunification screen that polls artifact status every 3s
 * Auto-advances to Step 9 (Artifact Acceptance) when reunification completes
 */

import React, { useEffect, useRef } from 'react'
import apiClient from '@/services/apiClient'
import { Sparkles } from 'lucide-react'

export interface ReunificationStepProps {
  artifactId: string
  onReunificationComplete?: () => void
  onError: (error: string) => void
}

export const ReunificationStep: React.FC<ReunificationStepProps> = ({
  artifactId,
  onReunificationComplete,
  onError
}) => {
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true

    const pollStatus = async () => {
      if (!mountedRef.current) return

      try {
        const artifact = await apiClient.getArtifact(parseInt(artifactId))

        // Check artifact status field (ft-045 workflow)
        const status = (artifact as any).status

        if (status === 'review_finalized') {
          // Reunification complete - stop polling and advance to Step 9 (Artifact Acceptance)
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
          console.log('[ReunificationStep] Reunification complete (status=review_finalized), advancing to Step 9')

          if (onReunificationComplete) {
            onReunificationComplete()
          }
        } else if (status === 'review_pending') {
          // Task failed - reverted to review_pending
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
          console.error('[ReunificationStep] Reunification failed')
          onError('Reunification failed. Please go back and try again.')
        } else if (status === 'reunifying') {
          // Task is running - continue polling
          console.log('[ReunificationStep] Reunification in progress...')
        }
      } catch (error: any) {
        console.error('[ReunificationStep] Polling error:', error)
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        onError(error.message || 'Network error during reunification')
      }
    }

    // Poll immediately on mount
    pollStatus()

    // Then poll every 3 seconds
    intervalRef.current = setInterval(pollStatus, 3000)

    // Cleanup on unmount
    return () => {
      mountedRef.current = false
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [artifactId, onReunificationComplete, onError])

  return (
    <div role="status" className="flex flex-col items-center justify-center min-h-[400px] space-y-6">
      {/* Animated sparkles icon */}
      <div className="relative">
        <Sparkles className="h-16 w-16 text-purple-600 animate-pulse" />
      </div>

      {/* Reunification message */}
      <div className="text-center space-y-2">
        <p className="text-lg font-semibold text-gray-900">
          Combining reviewed evidence into your artifact...
        </p>

        <p className="text-sm text-gray-500">
          This usually takes 30-45 seconds
        </p>
      </div>

      {/* Progress indicator */}
      <div className="flex items-center gap-2 px-4 py-3 bg-purple-50 border border-purple-200 rounded-lg">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></div>
          <p className="text-sm text-purple-700 font-medium">
            You'll review and accept your artifact in the next step
          </p>
        </div>
      </div>
    </div>
  )
}
