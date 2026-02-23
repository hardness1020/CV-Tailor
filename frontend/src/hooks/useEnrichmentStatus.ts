import { useState, useEffect, useRef } from 'react'
import { apiClient } from '@/services/apiClient'

export interface EnrichmentStatus {
  status: 'not_started' | 'pending' | 'processing' | 'completed' | 'failed'
  progressPercentage?: number
  sourcesProcessed?: number
  sourcesSuccessful?: number
  processingConfidence?: number
  totalCostUsd?: number
  processingTimeMs?: number
  technologiesCount?: number
  achievementsCount?: number
  errorMessage?: string
  hasEnrichment?: boolean
}

interface UseEnrichmentStatusOptions {
  artifactId: number
  enabled?: boolean
  pollingInterval?: number
  onComplete?: (status: EnrichmentStatus) => void
  onError?: (error: string) => void
}

/**
 * Hook to poll enrichment status for an artifact
 * Auto-starts/stops polling based on status
 * Uses React-recommended ignore flag pattern to prevent race conditions
 */
export function useEnrichmentStatus({
  artifactId,
  enabled = true,
  pollingInterval = 10000,
  onComplete,
  onError
}: UseEnrichmentStatusOptions) {
  const [status, setStatus] = useState<EnrichmentStatus>({ status: 'not_started' })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refetchCounter, setRefetchCounter] = useState(0)
  const previousStatusRef = useRef<string>('not_started')
  const onCompleteRef = useRef(onComplete)
  const onErrorRef = useRef(onError)

  // Keep callback refs updated
  useEffect(() => {
    onCompleteRef.current = onComplete
    onErrorRef.current = onError
  }, [onComplete, onError])

  // Fetch status effect - uses React's recommended ignore flag pattern
  useEffect(() => {
    if (!enabled) return

    let ignore = false // Local flag for THIS effect execution
    let intervalId: NodeJS.Timeout | undefined

    async function fetchStatus() {
      try {
        setIsLoading(true)
        setError(null)

        const response = await apiClient.getEnrichmentStatus(artifactId)

        // Check ignore flag BEFORE any state updates
        if (ignore) {
          return
        }

        const enrichmentStatus: EnrichmentStatus = {
          status: response.status || 'not_started',
          progressPercentage: response.progressPercentage,
          sourcesProcessed: response.enrichment?.sourcesProcessed,
          sourcesSuccessful: response.enrichment?.sourcesSuccessful,
          processingConfidence: response.enrichment?.processingConfidence,
          totalCostUsd: response.enrichment?.totalCostUsd,
          processingTimeMs: response.enrichment?.processingTimeMs,
          technologiesCount: response.enrichment?.technologiesCount,
          achievementsCount: response.enrichment?.achievementsCount,
          errorMessage: response.errorMessage,
          hasEnrichment: response.hasEnrichment
        }

        setStatus(enrichmentStatus)
        setIsLoading(false)

        // Handle status transitions and callbacks
        const previousStatus = previousStatusRef.current
        previousStatusRef.current = enrichmentStatus.status

        if (enrichmentStatus.status === 'completed' && previousStatus !== 'completed') {
          onCompleteRef.current?.(enrichmentStatus)
        } else if (enrichmentStatus.status === 'failed' && previousStatus !== 'failed') {
          onErrorRef.current?.(enrichmentStatus.errorMessage || 'Enrichment failed')
        }

        // Manage polling based on status
        if (enrichmentStatus.status === 'completed' || enrichmentStatus.status === 'failed') {
          // Stop polling for terminal states
          if (intervalId) {
            clearInterval(intervalId)
            intervalId = undefined
          }
        } else if (!intervalId) {
          // Start polling for non-terminal states
          intervalId = setInterval(() => fetchStatus(), pollingInterval)
        }
      } catch (err) {
        if (ignore) return

        console.error('[useEnrichmentStatus] Failed to fetch enrichment status:', err)
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch status'
        setError(errorMessage)
        setIsLoading(false)
        onErrorRef.current?.(errorMessage)
      }
    }

    // Initial fetch
    fetchStatus()

    // Cleanup function
    return () => {
      ignore = true // Prevent state updates from in-flight requests
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [enabled, artifactId, pollingInterval, refetchCounter])

  return {
    status,
    isLoading,
    error,
    refetch: () => {
      // Reset previous status to ensure onComplete fires for new enrichment
      previousStatusRef.current = 'not_started'
      setRefetchCounter(c => c + 1)
    }
  }
}
