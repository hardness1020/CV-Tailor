/**
 * ArtifactAcceptanceStep component (Step 9 of wizard, ft-045)
 * Displays final artifact content for user acceptance after reunification
 * User can review unified_description, enriched_technologies, enriched_achievements
 * Clicking "Accept Artifact" sets status='complete' and navigates to detail page
 */

import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import apiClient from '@/services/apiClient'
import { CheckCircle2, Sparkles, Code, Award } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import type { Artifact } from '@/types'

export interface ArtifactAcceptanceStepProps {
  artifact: Artifact
  onAcceptComplete?: () => void
  onError: (error: string) => void
}

export const ArtifactAcceptanceStep: React.FC<ArtifactAcceptanceStepProps> = ({
  artifact,
  onAcceptComplete,
  onError
}) => {
  const navigate = useNavigate()
  const [isAccepting, setIsAccepting] = useState(false)

  const handleAcceptArtifact = async () => {
    setIsAccepting(true)
    try {
      await apiClient.acceptArtifact(artifact.id)
      console.log('[ArtifactAcceptanceStep] Artifact accepted, navigating to detail page')

      if (onAcceptComplete) {
        onAcceptComplete()
      } else {
        navigate(`/artifacts/${artifact.id}`)
      }
    } catch (error: any) {
      console.error('[ArtifactAcceptanceStep] Failed to accept artifact:', error)
      onError(error.response?.data?.error || error.message || 'Failed to accept artifact')
      setIsAccepting(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="p-3 bg-gradient-to-br from-green-100 to-emerald-100 rounded-2xl">
            <CheckCircle2 className="h-8 w-8 text-green-600" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900">
            Review Your Artifact
          </h2>
        </div>
      </div>

      {/* Unified Description */}
      {artifact.unifiedDescription && (
        <div className="mb-6 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="bg-gradient-to-r from-purple-50 to-pink-50 px-6 py-4 border-b border-purple-100">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-purple-600" />
              <h3 className="font-semibold text-gray-900">AI-Generated Description</h3>
            </div>
          </div>
          <div className="p-6">
            <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">
              {artifact.unifiedDescription}
            </p>
          </div>
        </div>
      )}

      {/* Enriched Technologies */}
      {artifact.enrichedTechnologies && artifact.enrichedTechnologies.length > 0 && (
        <div className="mb-6 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="bg-gradient-to-r from-blue-50 to-cyan-50 px-6 py-4 border-b border-blue-100">
            <div className="flex items-center gap-2">
              <Code className="h-5 w-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900">
                Technologies ({artifact.enrichedTechnologies.length})
              </h3>
            </div>
          </div>
          <div className="p-6">
            <div className="flex flex-wrap gap-2">
              {artifact.enrichedTechnologies.map((tech, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-3 py-1.5 bg-blue-100 text-blue-800 text-sm font-medium rounded-full border border-blue-200"
                >
                  {tech}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Enriched Achievements */}
      {artifact.enrichedAchievements && artifact.enrichedAchievements.length > 0 && (
        <div className="mb-6 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 px-6 py-4 border-b border-amber-100">
            <div className="flex items-center gap-2">
              <Award className="h-5 w-5 text-amber-600" />
              <h3 className="font-semibold text-gray-900">
                Key Achievements ({artifact.enrichedAchievements.length})
              </h3>
            </div>
          </div>
          <div className="p-6">
            <ul className="space-y-3">
              {artifact.enrichedAchievements.map((achievement, index) => (
                <li key={index} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 text-xs font-semibold flex items-center justify-center mt-0.5">
                    {index + 1}
                  </span>
                  <span className="text-gray-800 leading-relaxed">{achievement}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Info Banner */}
      <div className="mb-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> After accepting, you can still edit your artifact details or re-enrich content from the artifact detail page.
        </p>
      </div>

      {/* Accept Button */}
      <div className="flex justify-center">
        <Button
          onClick={handleAcceptArtifact}
          disabled={isAccepting}
          className="group bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
        >
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5" />
            <span className="text-lg">
              {isAccepting ? 'Accepting...' : 'Accept Artifact'}
            </span>
          </div>
        </Button>
      </div>
    </div>
  )
}
