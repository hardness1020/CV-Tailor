import { useEffect, useState, useRef } from 'react'
import { Loader2, CheckCircle, XCircle, Sparkles, TrendingUp, AlertCircle } from 'lucide-react'
import { apiClient } from '@/services/apiClient'
import { cn } from '@/utils/cn'

interface EnrichmentStatus {
  artifactId: number
  status: 'not_started' | 'pending' | 'processing' | 'completed' | 'failed'
  progressPercentage: number
  errorMessage?: string
  hasEnrichment: boolean
  enrichment?: {
    sourcesProcessed: number
    sourcesSuccessful: number
    processingConfidence: number
    totalCostUsd: number
    processingTimeMs: number
    technologiesCount: number
    achievementsCount: number
    qualityWarnings?: string[]  // NEW: Quality validation warnings
  }
}

interface ArtifactEnrichmentStatusProps {
  artifactId: number
  onComplete?: () => void
  onError?: (error: string) => void
  pollInterval?: number // ms
  className?: string
}

export function ArtifactEnrichmentStatus({
  artifactId,
  onComplete,
  onError,
  pollInterval = 10000,
  className
}: ArtifactEnrichmentStatusProps) {
  const [status, setStatus] = useState<EnrichmentStatus | null>(null)
  const [isPolling, setIsPolling] = useState(true)

  // Use refs to track callbacks and prevent re-triggering on callback changes
  const onCompleteRef = useRef(onComplete)
  const onErrorRef = useRef(onError)
  const hasCompletedRef = useRef(false)
  const hasErroredRef = useRef(false)

  // Update refs when callbacks change
  useEffect(() => {
    onCompleteRef.current = onComplete
    onErrorRef.current = onError
  }, [onComplete, onError])

  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null

    const fetchStatus = async () => {
      try {
        console.log('[ArtifactEnrichmentStatus] Fetching status for artifact:', artifactId)
        const data = await apiClient.getEnrichmentStatus(artifactId)
        console.log('[ArtifactEnrichmentStatus] Received status data:', data)

        setStatus(data)

        // Stop polling if completed or failed
        // Continue polling for 15 seconds after initial "completed" to catch late quality validation failures
        if (data.status === 'completed' || data.status === 'failed') {
          if (data.status === 'completed' && !hasCompletedRef.current) {
            console.log('[ArtifactEnrichmentStatus] Enrichment completed, continuing to poll for 15s to catch late failures')
            hasCompletedRef.current = true

            // Continue polling for 15 more seconds to catch quality validation failures
            setTimeout(() => {
              console.log('[ArtifactEnrichmentStatus] Stopping polling after 15s delay')
              setIsPolling(false)
            }, 15000)

            onCompleteRef.current?.()
          } else if (data.status === 'failed') {
            setIsPolling(false)

            if (data.errorMessage && !hasErroredRef.current) {
              console.log('[ArtifactEnrichmentStatus] Enrichment failed:', data.errorMessage)
              hasErroredRef.current = true
              onErrorRef.current?.(data.errorMessage)
            }
          }
        }
      } catch (error) {
        console.error('[ArtifactEnrichmentStatus] API error:', error)
        if (!hasErroredRef.current) {
          hasErroredRef.current = true
          onErrorRef.current?.('Failed to fetch enrichment status')
        }
      }
    }

    // Initial fetch
    fetchStatus()

    // Start polling if needed
    if (isPolling) {
      intervalId = setInterval(fetchStatus, pollInterval)
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [artifactId, isPolling, pollInterval])

  if (!status) {
    console.log('[ArtifactEnrichmentStatus] Rendering loading state')
    return (
      <div className={cn('p-4 bg-gray-50 rounded-lg', className)}>
        <div className="flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
          <span className="text-sm text-gray-600">Loading enrichment status...</span>
        </div>
      </div>
    )
  }

  if (status.status === 'not_started') {
    console.log('[ArtifactEnrichmentStatus] Rendering not_started state')
    return (
      <div className={cn('p-4 bg-blue-50 border border-blue-200 rounded-lg', className)}>
        <div className="flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-blue-600" />
          <span className="text-sm text-blue-900">No enrichment has been performed yet</span>
        </div>
      </div>
    )
  }

  if (status.status === 'failed') {
    console.log('[ArtifactEnrichmentStatus] Rendering failed state')
    return (
      <div className={cn('p-4 bg-red-50 border border-red-200 rounded-lg', className)}>
        <div className="flex items-start gap-3">
          <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-red-900 mb-1">Enrichment Failed</h4>
            {status.errorMessage && (
              <div className="space-y-2">
                <p className="text-sm text-red-700 font-medium">{status.errorMessage}</p>

                {/* NEW: Show quality warnings if available */}
                {status.enrichment?.qualityWarnings && status.enrichment.qualityWarnings.length > 0 && (
                  <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
                    <p className="text-xs font-medium text-yellow-800 mb-1">Quality Warnings:</p>
                    <ul className="list-disc list-inside text-xs text-yellow-700">
                      {status.enrichment.qualityWarnings.map((warning, idx) => (
                        <li key={idx}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* NEW: Retry button */}
                <button
                  onClick={() => window.location.reload()}
                  className="mt-2 text-sm text-red-700 underline hover:text-red-900"
                >
                  Retry Enrichment
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (status.status === 'completed' && status.enrichment) {
    console.log('[ArtifactEnrichmentStatus] Rendering completed state')
    const { enrichment } = status
    const successRate = enrichment.sourcesProcessed > 0
      ? (enrichment.sourcesSuccessful / enrichment.sourcesProcessed) * 100
      : 0

    return (
      <div className={cn('p-4 bg-green-50 border border-green-200 rounded-lg', className)}>
        <div className="flex items-start gap-3 mb-3">
          <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-green-900 mb-1">Enrichment Complete!</h4>
            <p className="text-sm text-green-700">
              AI-powered content generation finished successfully
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <div className="bg-white rounded-lg p-3 border border-green-100">
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="h-4 w-4 text-green-600" />
              <span className="text-xs font-medium text-gray-600">Sources</span>
            </div>
            <p className="text-lg font-bold text-gray-900">
              {enrichment.sourcesSuccessful}/{enrichment.sourcesProcessed}
            </p>
            <p className="text-xs text-gray-500">{successRate.toFixed(0)}% success</p>
          </div>

          <div className="bg-white rounded-lg p-3 border border-green-100">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-green-600" />
              <span className="text-xs font-medium text-gray-600">Confidence</span>
            </div>
            <p className="text-lg font-bold text-gray-900">
              {(enrichment.processingConfidence * 100).toFixed(0)}%
            </p>
            <p className="text-xs text-gray-500">Quality score</p>
          </div>

          <div className="bg-white rounded-lg p-3 border border-green-100">
            <span className="text-xs font-medium text-gray-600 block mb-1">Technologies</span>
            <p className="text-lg font-bold text-gray-900">{enrichment.technologiesCount}</p>
            <p className="text-xs text-gray-500">Extracted</p>
          </div>

          <div className="bg-white rounded-lg p-3 border border-green-100">
            <span className="text-xs font-medium text-gray-600 block mb-1">Achievements</span>
            <p className="text-lg font-bold text-gray-900">{enrichment.achievementsCount}</p>
            <p className="text-xs text-gray-500">Identified</p>
          </div>
        </div>

        {/* NEW: Show warnings if present */}
        {enrichment.qualityWarnings && enrichment.qualityWarnings.length > 0 && (
          <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5" />
              <div className="flex-1">
                <p className="text-xs font-medium text-yellow-800 mb-1">Quality Warnings:</p>
                <ul className="list-disc list-inside text-xs text-yellow-700">
                  {enrichment.qualityWarnings.map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        <div className="mt-3 pt-3 border-t border-green-100">
          <div className="flex items-center justify-between text-xs text-green-700">
            <span>Processing time: {(enrichment.processingTimeMs / 1000).toFixed(1)}s</span>
            <span>Cost: ${enrichment.totalCostUsd.toFixed(4)}</span>
          </div>
        </div>
      </div>
    )
  }

  // Processing state
  console.log('[ArtifactEnrichmentStatus] Rendering processing state, progress:', status.progressPercentage)
  return (
    <div className={cn('p-4 bg-blue-50 border border-blue-200 rounded-lg', className)}>
      <div className="flex items-start gap-3 mb-3">
        <Loader2 className="h-5 w-5 animate-spin text-blue-600 mt-0.5" />
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-blue-900 mb-1">
            Enriching Artifact with AI...
          </h4>
          <p className="text-sm text-blue-700">
            Analyzing evidence sources and generating enhanced content
          </p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mt-4">
        <div className="flex items-center justify-between text-xs text-blue-700 mb-2">
          <span>Progress</span>
          <span>{status.progressPercentage}%</span>
        </div>
        <div className="w-full bg-blue-100 rounded-full h-2 overflow-hidden">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${status.progressPercentage}%` }}
          />
        </div>
      </div>
    </div>
  )
}
