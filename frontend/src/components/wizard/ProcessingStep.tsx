/**
 * ProcessingStep component (ft-045)
 * Blocking processing screen that polls artifact.status every 10s
 * Auto-advances to Evidence Review step when status='review_pending'
 * No grace period needed - API sets status='processing' before task trigger
 */

import React, { useEffect, useRef } from 'react'
import apiClient from '@/services/apiClient'

export interface ProcessingStepProps {
  artifactId: string
  onProcessingComplete: () => void
  onError: (error: string) => void
}

export const ProcessingStep: React.FC<ProcessingStepProps> = ({
  artifactId,
  onProcessingComplete,
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

        if (status === 'review_pending') {
          // Phase 1 enrichment complete - stop polling and advance to Evidence Review (Step 6)
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
          console.log('[ProcessingStep] Artifact status=review_pending, advancing to Evidence Review')
          onProcessingComplete()
        } else if (status === 'draft') {
          // Processing failed - artifact reverted to draft status
          // No grace period needed since trigger_artifact_enrichment sets status='processing' before task trigger
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
          const errorMessage = 'Processing failed - please check your evidence sources and try again'
          console.error('[ProcessingStep] Artifact status=draft (processing failed)')
          onError(errorMessage)
        } else if (status === 'processing') {
          // Task is running - continue polling
          console.log('[ProcessingStep] Artifact processing in progress...')
        }
        // Otherwise unknown status - continue polling
      } catch (error: any) {
        // Network error - could retry with exponential backoff
        // For now, call error handler after first failure
        console.error('[ProcessingStep] Polling error:', error)
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        onError(error.message || 'Network error')
      }
    }

    // Poll immediately on mount
    pollStatus()

    // Then poll every 10 seconds
    intervalRef.current = setInterval(pollStatus, 10000)

    // Cleanup on unmount
    return () => {
      mountedRef.current = false
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [artifactId, onProcessingComplete, onError])

  return (
    <div role="status" className="flex flex-col items-center justify-center min-h-[400px] space-y-6">
      {/* Spinner animation */}
      <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-purple-600"></div>

      {/* Processing message */}
      <div className="text-center space-y-2">
        <p className="text-lg font-semibold text-gray-900">
          Extracting content from your evidence sources...
        </p>

        <p className="text-sm text-gray-500">
          This may take 1-3 minutes for repositories with extensive documentation
        </p>
      </div>

      {/* Auto-advance hint */}
      <div className="flex items-center gap-2 px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
          <p className="text-sm text-blue-700 font-medium">
            You'll be automatically taken to the next step when processing is complete
          </p>
        </div>
      </div>
    </div>
  )
}
