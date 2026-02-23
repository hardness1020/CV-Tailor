/**
 * Custom hook for polling generation status
 * ft-026: Unified Generation Status Polling (ADR-040)
 *
 * Provides automatic polling of generation status with configurable intervals,
 * terminal state detection, and race condition prevention.
 *
 * @example
 * ```tsx
 * const { status, isPolling, error, refetch } = useGenerationStatus({
 *   generationId: 'uuid-here',
 *   enabled: true,
 *   pollingInterval: 10000,
 *   onComplete: (status) => navigate('/generation/complete'),
 *   onError: (error) => toast.error(error)
 * })
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient } from '@/services/apiClient'
import type { GenerationStatus } from '@/types'

interface UseGenerationStatusOptions {
  generationId: string
  enabled?: boolean
  pollingInterval?: number
  onComplete?: (status: GenerationStatus) => void
  onError?: (error: string) => void
}

interface UseGenerationStatusReturn {
  status: GenerationStatus | null
  isPolling: boolean
  error: string | null
  refetch: () => Promise<void>
}

// Terminal states where polling should stop
// 'bullets_ready' is terminal because we wait for user action (approve/reject bullets)
const TERMINAL_STATES: GenerationStatus['status'][] = ['completed', 'failed', 'bullets_ready']

export function useGenerationStatus({
  generationId,
  enabled = true,
  pollingInterval = 10000,
  onComplete,
  onError,
}: UseGenerationStatusOptions): UseGenerationStatusReturn {
  const [status, setStatus] = useState<GenerationStatus | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Store callbacks in refs to avoid dependency issues (same pattern as useEnrichmentStatus)
  const onCompleteRef = useRef(onComplete)
  const onErrorRef = useRef(onError)

  // Keep callback refs updated
  useEffect(() => {
    onCompleteRef.current = onComplete
    onErrorRef.current = onError
  }, [onComplete, onError])

  const fetchStatus = useCallback(async () => {
    try {
      const statusData = await apiClient.getGenerationStatus(generationId)
      setStatus(statusData)
      setError(null)

      // Check for terminal states and trigger callbacks
      if (TERMINAL_STATES.includes(statusData.status)) {
        setIsPolling(false)

        if (statusData.status === 'completed') {
          onCompleteRef.current?.(statusData)
        } else if (statusData.status === 'failed') {
          const errorMessage = statusData.error_message || 'Generation failed'
          setError(errorMessage)
          onErrorRef.current?.(errorMessage)
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      onErrorRef.current?.(errorMessage)
    }
  }, [generationId])  // Removed onComplete/onError from deps (using refs instead)

  // Manual refetch capability
  const refetch = useCallback(async () => {
    await fetchStatus()
  }, [fetchStatus])

  // Auto-polling effect
  useEffect(() => {
    if (!enabled) {
      setIsPolling(false)
      return
    }

    let ignore = false
    let intervalId: NodeJS.Timeout | null = null

    const poll = async () => {
      if (ignore) return

      try {
        const statusData = await apiClient.getGenerationStatus(generationId)

        if (ignore) return // Check again after async operation

        setStatus(statusData)
        setError(null)

        // Check for terminal states and trigger callbacks
        if (TERMINAL_STATES.includes(statusData.status)) {
          setIsPolling(false)
          if (intervalId) {
            clearInterval(intervalId)
            intervalId = null
          }

          // Trigger appropriate callbacks
          if (statusData.status === 'completed') {
            onCompleteRef.current?.(statusData)
          } else if (statusData.status === 'failed') {
            const errorMessage = statusData.error_message || 'Generation failed'
            setError(errorMessage)
            onErrorRef.current?.(errorMessage)
          }
          // Note: 'bullets_ready' is terminal but has no callback (waits for user action)
        } else {
          // Continue polling for non-terminal states
          setIsPolling(true)
        }
      } catch (err) {
        if (ignore) return

        const errorMessage = err instanceof Error ? err.message : 'Unknown error'
        setError(errorMessage)
        onErrorRef.current?.(errorMessage)
      }
    }

    setIsPolling(true)

    // Initial fetch
    poll()

    // Set up polling interval
    intervalId = setInterval(poll, pollingInterval)

    return () => {
      ignore = true
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [generationId, enabled, pollingInterval])  // Removed onComplete/onError from deps (using refs instead)

  return {
    status,
    isPolling,
    error,
    refetch,
  }
}
