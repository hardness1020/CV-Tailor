import { useEffect, useCallback } from 'react'
import { X } from 'lucide-react'
import { useEnrichmentStore } from '@/stores/enrichmentStore'
import { ArtifactEnrichmentStatus } from '@/components/ArtifactEnrichmentStatus'

export function EnrichmentModal() {
  const { activeEnrichmentId, clearActiveEnrichment } = useEnrichmentStore()

  const handleDismiss = useCallback(() => {
    clearActiveEnrichment()
  }, [clearActiveEnrichment])

  const handleComplete = useCallback(() => {
    // Success state reached - user can manually close via X button, Dismiss button, backdrop, or ESC key
  }, [clearActiveEnrichment])

  const handleError = useCallback((error: string) => {
    console.error('[EnrichmentModal] Enrichment error:', error)
    // Don't auto-dismiss on error - let user manually close
  }, [])

  const handleBackdropClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      handleDismiss()
    }
  }, [handleDismiss])

  const handleEscKey = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      handleDismiss()
    }
  }, [handleDismiss])

  useEffect(() => {
    document.addEventListener('keydown', handleEscKey)
    return () => {
      document.removeEventListener('keydown', handleEscKey)
    }
  }, [handleEscKey])

  // Don't render if no active enrichment
  if (!activeEnrichmentId) {
    return null
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 transition-opacity duration-300 ease-out"
      onClick={handleBackdropClick}
      aria-hidden="true"
    >
      <div
        role="dialog"
        aria-labelledby="enrichment-modal-title"
        aria-modal="true"
        className="bg-white rounded-xl shadow-2xl p-6 max-w-2xl w-full transform transition-all duration-300 ease-out scale-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with close button */}
        <div className="flex items-center justify-between mb-4">
          <h2
            id="enrichment-modal-title"
            className="text-xl font-semibold text-gray-900"
          >
            Artifact Processing
          </h2>
          <button
            type="button"
            onClick={handleDismiss}
            className="text-gray-400 hover:text-gray-600 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 rounded-lg p-1"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Enrichment Status Component */}
        <ArtifactEnrichmentStatus
          artifactId={activeEnrichmentId}
          onComplete={handleComplete}
          onError={handleError}
          pollInterval={2000}
        />

        {/* Dismiss Button */}
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={handleDismiss}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  )
}
