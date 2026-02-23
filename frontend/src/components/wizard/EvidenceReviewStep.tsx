/**
 * EvidenceReviewStep component (ft-045)
 * Main evidence review container with cards, progress counter, finalize button
 */

import React, { useEffect, useState } from 'react'
import apiClient from '@/services/apiClient'
import { EnhancedEvidenceResponse } from '@/types'
import { EvidenceCard } from './EvidenceCard'

export interface EvidenceReviewStepProps {
  artifactId: string
  onFinalize: () => void
  onBack: () => void
}

export const EvidenceReviewStep: React.FC<EvidenceReviewStepProps> = ({
  artifactId,
  onFinalize,
  onBack
}) => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [canFinalize, setCanFinalize] = useState(false)
  const [totalEvidence, setTotalEvidence] = useState(0)
  const [acceptedCount, setAcceptedCount] = useState(0)
  const [evidence, setEvidence] = useState<EnhancedEvidenceResponse[]>([])
  const [finalizing, setFinalizing] = useState(false)

  const fetchAcceptanceStatus = async () => {
    try {
      const status = await apiClient.getEvidenceAcceptanceStatus(parseInt(artifactId))

      setCanFinalize(status.canFinalize)
      setTotalEvidence(status.totalEvidence)
      setAcceptedCount(status.accepted)
      setEvidence(status.evidenceDetails || [])
      setError(null) // Clear any previous errors
      setLoading(false)
    } catch (error) {
      console.error('Failed to fetch evidence acceptance status:', error)
      setError('Failed to load evidence data. Please try again.')
      setEvidence([]) // Ensure evidence is at least an empty array
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAcceptanceStatus()
  }, [artifactId])

  const handleAccept = async (evidenceId: string, reviewNotes?: string) => {
    try {
      await apiClient.acceptEvidence(parseInt(artifactId), evidenceId, reviewNotes)
      // Refresh status
      await fetchAcceptanceStatus()
    } catch (error) {
      console.error('Failed to accept evidence:', error)
    }
  }

  const handleReject = async (evidenceId: string) => {
    try {
      await apiClient.rejectEvidence(parseInt(artifactId), evidenceId)
      // Refresh status
      await fetchAcceptanceStatus()
    } catch (error) {
      console.error('Failed to reject evidence:', error)
    }
  }

  const handleEdit = async (evidenceId: string, content: any) => {
    try {
      await apiClient.editEvidenceContent(parseInt(artifactId), evidenceId, content)
      // Refresh status
      await fetchAcceptanceStatus()
    } catch (error) {
      console.error('Failed to edit evidence:', error)
    }
  }

  const handleFinalize = async () => {
    if (!canFinalize) return

    setFinalizing(true)
    try {
      // Trigger async reunification task
      await apiClient.finalizeEvidenceReview(parseInt(artifactId))

      // Advance to Step 8 (Reunification Progress)
      // Parent wizard will show ReunificationStep component which handles polling
      console.log('[EvidenceReviewStep] Reunification task triggered, advancing to Step 8')
      onFinalize()
    } catch (error) {
      console.error('Failed to finalize evidence review:', error)
      setError('Failed to start reunification. Please try again.')
      setFinalizing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading evidence...</p>
        </div>
      </div>
    )
  }

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
            <p className="text-gray-600 text-sm mb-1">
              No evidence is available for this artifact yet.
            </p>
            <p className="text-gray-500 text-sm">
              Evidence may still be processing. Try going back to the processing step or refresh this page.
            </p>
          </div>
          <div className="mt-4 space-x-3">
            <button
              onClick={onBack}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Go Back
            </button>
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
      {/* Progress Counter */}
      <div className="flex items-center justify-between pb-4 border-b">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Review Evidence</h2>
          <p className="text-sm text-gray-600 mt-1">
            Accept all evidence to continue to the next step
          </p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-purple-600">
            {acceptedCount}/{totalEvidence}
          </div>
          <div className="text-sm text-gray-600">accepted</div>
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

      {/* Action Buttons */}
      <div className="flex justify-between pt-6 border-t">
        <button
          type="button"
          onClick={onBack}
          className="px-6 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Back
        </button>

        <button
          type="button"
          onClick={handleFinalize}
          disabled={!canFinalize || finalizing}
          className={`px-8 py-2 rounded-lg font-medium ${
            canFinalize && !finalizing
              ? 'bg-purple-600 text-white hover:bg-purple-700'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
          title={!canFinalize ? 'Accept all evidence to continue' : ''}
        >
          {finalizing ? 'Reunifying Evidence...' : 'Finalize & Continue'}
        </button>
      </div>
    </div>
  )
}
