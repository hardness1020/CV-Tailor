/**
 * ConsolidatedProcessingStep component (6-step wizard consolidation)
 * Combines old Step 6 (Processing) + Step 7 (Evidence Review) into single step
 *
 * Flow:
 * 1. Show "Extracting content..." spinner (polls every 10s for status='review_pending')
 * 2. Auto-transition to evidence review UI when status='review_pending'
 * 3. User accepts/rejects evidence and clicks "Finalize & Continue"
 * 4. Show "Combining evidence..." spinner (polls for status='reunifying')
 * 5. Auto-advance to Step 6 when status='reunifying' detected
 */

import React, { useEffect, useRef, useState } from 'react'
import apiClient from '@/services/apiClient'
import { EnhancedEvidenceResponse } from '@/types'
import { EvidenceCard } from './EvidenceCard'
import { Loader2, ClipboardCheck, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/Button'

type ProcessingState = 'processing' | 'reviewing' | 'finalizing'

export interface ConsolidatedProcessingStepProps {
  artifactId: string
  onComplete: () => void // Called when status='reunifying' detected
  onError: (error: string) => void
}

export const ConsolidatedProcessingStep: React.FC<ConsolidatedProcessingStepProps> = ({
  artifactId,
  onComplete,
  onError
}) => {
  const [processingState, setProcessingState] = useState<ProcessingState>('processing')
  const [evidence, setEvidence] = useState<EnhancedEvidenceResponse[]>([])
  const [canFinalize, setCanFinalize] = useState(false)
  const [totalEvidence, setTotalEvidence] = useState(0)
  const [acceptedCount, setAcceptedCount] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [finalizing, setFinalizing] = useState(false)

  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const mountedRef = useRef(true)
  const startTimeRef = useRef<number>(Date.now()) // Track when processing started

  // Fetch evidence acceptance status (for review state)
  const fetchAcceptanceStatus = async () => {
    try {
      const status = await apiClient.getEvidenceAcceptanceStatus(parseInt(artifactId))
      setCanFinalize(status.canFinalize)
      setTotalEvidence(status.totalEvidence)
      setAcceptedCount(status.accepted)
      setEvidence(status.evidenceDetails || [])
      setError(null)
    } catch (error) {
      console.error('[ConsolidatedProcessingStep] Failed to fetch evidence:', error)
      setError('Failed to load evidence data. Please try again.')
      setEvidence([])
    }
  }

  // Poll artifact status (for processing & finalizing states)
  useEffect(() => {
    mountedRef.current = true

    const pollStatus = async () => {
      if (!mountedRef.current) return

      try {
        const artifact = await apiClient.getArtifact(parseInt(artifactId))
        const status = (artifact as any).status

        if (processingState === 'processing') {
          // Waiting for enrichment to complete
          if (status === 'review_pending') {
            // Phase 1 enrichment complete - transition to evidence review
            if (intervalRef.current) {
              clearInterval(intervalRef.current)
              intervalRef.current = null
            }
            console.log('[ConsolidatedProcessingStep] Enrichment complete, showing evidence review')
            setProcessingState('reviewing')
            await fetchAcceptanceStatus()
          } else if (status === 'draft') {
            // Check if stuck in 'draft' state (timeout-based failure detection)
            const elapsedMs = Date.now() - startTimeRef.current
            const TIMEOUT_MS = 30000 // 30 seconds

            if (elapsedMs > TIMEOUT_MS) {
              // Processing failed - stuck in draft for too long
              if (intervalRef.current) {
                clearInterval(intervalRef.current)
                intervalRef.current = null
              }
              console.error(`[ConsolidatedProcessingStep] Processing failed (stuck in draft for ${elapsedMs}ms)`)
              onError('Processing failed - please check your evidence sources and try again')
            } else {
              // Still in initial state - continue polling
              console.log(`[ConsolidatedProcessingStep] Waiting for enrichment to start (${elapsedMs}ms elapsed)`)
            }
          } else if (status === 'processing') {
            // Still processing - continue polling
            console.log('[ConsolidatedProcessingStep] Enrichment in progress...')
          }
        } else if (processingState === 'finalizing') {
          // Waiting for reunification to start
          if (status === 'reunifying') {
            // Reunification started - advance to Step 6
            if (intervalRef.current) {
              clearInterval(intervalRef.current)
              intervalRef.current = null
            }
            console.log('[ConsolidatedProcessingStep] Reunification started, advancing to Step 6')
            onComplete()
          } else if (status === 'review_pending') {
            // Still finalizing - continue polling
            console.log('[ConsolidatedProcessingStep] Finalizing in progress...')
          }
        }
      } catch (error: any) {
        console.error('[ConsolidatedProcessingStep] Polling error:', error)
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        onError(error.message || 'Network error')
      }
    }

    // Only poll if we're in processing or finalizing state
    if (processingState === 'processing' || processingState === 'finalizing') {
      // Poll immediately on mount or state change
      pollStatus()

      // Then poll every 10 seconds
      intervalRef.current = setInterval(pollStatus, 10000)
    }

    // Cleanup on unmount
    return () => {
      mountedRef.current = false
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [artifactId, processingState, onComplete, onError])

  // Evidence action handlers
  const handleAccept = async (evidenceId: string, reviewNotes?: string) => {
    try {
      await apiClient.acceptEvidence(parseInt(artifactId), evidenceId, reviewNotes)
      await fetchAcceptanceStatus()
    } catch (error) {
      console.error('[ConsolidatedProcessingStep] Failed to accept evidence:', error)
    }
  }

  const handleReject = async (evidenceId: string) => {
    try {
      await apiClient.rejectEvidence(parseInt(artifactId), evidenceId)
      await fetchAcceptanceStatus()
    } catch (error) {
      console.error('[ConsolidatedProcessingStep] Failed to reject evidence:', error)
    }
  }

  const handleEdit = async (evidenceId: string, content: any) => {
    try {
      await apiClient.editEvidenceContent(parseInt(artifactId), evidenceId, content)
      await fetchAcceptanceStatus()
    } catch (error) {
      console.error('[ConsolidatedProcessingStep] Failed to edit evidence:', error)
    }
  }

  const handleFinalize = async () => {
    if (!canFinalize) return

    setFinalizing(true)
    try {
      // Trigger async reunification task
      await apiClient.finalizeEvidenceReview(parseInt(artifactId))
      console.log('[ConsolidatedProcessingStep] Reunification triggered, transitioning to finalizing state')

      // Transition to finalizing state (will start polling for status='reunifying')
      setProcessingState('finalizing')
    } catch (error) {
      console.error('[ConsolidatedProcessingStep] Failed to finalize:', error)
      setError('Failed to start reunification. Please try again.')
      setFinalizing(false)
    }
  }

  // Render processing spinner
  if (processingState === 'processing') {
    return (
      <div role="status" className="flex flex-col items-center justify-center min-h-[400px] space-y-6">
        <div className="relative">
          <Loader2 className="h-16 w-16 text-purple-600 animate-spin" />
        </div>

        <div className="text-center space-y-2">
          <p className="text-lg font-semibold text-gray-900">
            Extracting content from your evidence sources...
          </p>
          <p className="text-sm text-gray-500">
            This may take 1-3 minutes for repositories with extensive documentation
          </p>
        </div>

        <div className="flex items-center gap-2 px-4 py-3 bg-purple-50 border border-purple-200 rounded-lg">
          <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></div>
          <p className="text-sm text-purple-700 font-medium">
            You'll be able to review evidence shortly
          </p>
        </div>
      </div>
    )
  }

  // Render finalizing spinner
  if (processingState === 'finalizing') {
    return (
      <div role="status" className="flex flex-col items-center justify-center min-h-[400px] space-y-6">
        <div className="relative">
          <Loader2 className="h-16 w-16 text-purple-600 animate-spin" />
        </div>

        <div className="text-center space-y-2">
          <p className="text-lg font-semibold text-gray-900">
            Finalizing content preparation...
          </p>
          <p className="text-sm text-gray-500">
            Preparing your artifact for final review
          </p>
        </div>

        <div className="flex items-center gap-2 px-4 py-3 bg-purple-50 border border-purple-200 rounded-lg">
          <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></div>
          <p className="text-sm text-purple-700 font-medium">
            You'll review your final artifact in the next step
          </p>
        </div>
      </div>
    )
  }

  // Render evidence review UI (processingState === 'reviewing')
  if (error) {
    return (
      <div className="text-center p-8">
        <div className="max-w-md mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-4">
            <svg className="h-12 w-12 text-red-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-red-800 font-medium mb-2">Error Loading Evidence</p>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
          <button
            onClick={fetchAcceptanceStatus}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!evidence || evidence.length === 0) {
    return (
      <div className="text-center p-8">
        <div className="max-w-md mx-auto">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
            <svg className="h-12 w-12 text-gray-400 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-gray-700 font-medium mb-2">No Evidence Found</p>
            <p className="text-gray-600 text-sm">
              No evidence is available for this artifact yet. Evidence may still be processing.
            </p>
          </div>
          <div className="mt-4">
            <button
              onClick={fetchAcceptanceStatus}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with Icon */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-2xl">
            <ClipboardCheck className="h-8 w-8 text-purple-600" />
          </div>
          <div>
            <h2 className="text-3xl font-bold text-gray-900">Review Evidence</h2>
            <p className="text-sm text-gray-600 mt-1">
              Accept all evidence to continue ({acceptedCount}/{totalEvidence} accepted)
            </p>
          </div>
        </div>
      </div>

      {/* Evidence Cards */}
      <div className="space-y-4">
        {evidence.map((ev) => (
          <EvidenceCard
            key={ev.id}
            evidence={ev}
            onAccept={handleAccept}
            onReject={handleReject}
            onEdit={handleEdit}
          />
        ))}
      </div>

      {/* Finalize Button */}
      <div className="flex justify-center pt-6 border-t">
        <Button
          onClick={handleFinalize}
          disabled={!canFinalize || finalizing}
          className="group bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-semibold px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          title={!canFinalize ? 'Accept all evidence to continue' : ''}
        >
          <div className="flex items-center gap-3">
            {finalizing ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-lg">Starting reunification...</span>
              </>
            ) : (
              <>
                <ArrowRight className="h-5 w-5" />
                <span className="text-lg">Finalize & Continue</span>
              </>
            )}
          </div>
        </Button>
      </div>
    </div>
  )
}
