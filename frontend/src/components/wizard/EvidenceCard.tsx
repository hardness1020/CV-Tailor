/**
 * EvidenceCard component (ft-045)
 * Individual evidence card with inline editing, accept/reject actions, confidence badge
 * Using InlineEditableFields components for consistent editing UX
 */

import React from 'react'
import { Check, X, FileText, Github, Globe, User, LucideIcon } from 'lucide-react'
import {
  InlineEditableTextarea,
  InlineEditableTags,
  InlineEditableList
} from '@/components/ui/InlineEditableFields'
import { EnhancedEvidenceResponse } from '@/types'

export interface EvidenceCardProps {
  evidence: EnhancedEvidenceResponse
  onAccept: (evidenceId: string, reviewNotes?: string) => Promise<void>
  onReject: (evidenceId: string) => Promise<void>
  onEdit: (evidenceId: string, content: any) => Promise<void>
}

// Evidence content type icon mapping
const contentTypeIcons: Record<string, LucideIcon> = {
  pdf: FileText,
  github: Github,
  linkedin: User,
  web_profile: Globe,
  markdown: FileText,
  text: FileText,
}

const ConfidenceBadge: React.FC<{ confidence: number }> = ({ confidence }) => {
  const percentage = Math.round(confidence * 100)

  let colorClass = 'bg-red-100 text-red-800 shadow-sm shadow-red-200/50'
  let tooltip = 'This content may need significant review'

  if (confidence >= 0.8) {
    colorClass = 'bg-green-100 text-green-800 shadow-sm shadow-green-200/50'
    tooltip = 'This content appears accurate'
  } else if (confidence >= 0.5) {
    colorClass = 'bg-yellow-100 text-yellow-800 shadow-sm shadow-yellow-200/50'
    tooltip = 'This content may need minor corrections'
  }

  return (
    <span
      data-testid="confidence-badge"
      className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${colorClass}`}
      title={tooltip}
    >
      {percentage}%
    </span>
  )
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({
  evidence,
  onAccept,
  onReject,
  onEdit
}) => {
  const accepted = (evidence as any).accepted || false

  // Individual field save handlers for inline editing
  const handleSaveSummary = async (summary: string) => {
    await onEdit(evidence.id, {
      ...evidence.processedContent,
      summary
    })
  }

  const handleSaveTechnologies = async (technologies: string[]) => {
    await onEdit(evidence.id, {
      ...evidence.processedContent,
      technologies
    })
  }

  const handleSaveAchievements = async (achievements: string[]) => {
    await onEdit(evidence.id, {
      ...evidence.processedContent,
      achievements
    })
  }

  return (
    <div
      className={`bg-white rounded-xl border overflow-hidden shadow-sm transition-all duration-300 ${
        accepted
          ? 'border-green-300 border-2 shadow-xl shadow-green-200/50'
          : 'border-gray-200'
      }`}
    >
      {/* Header with gradient background */}
      <div className="bg-gradient-to-r from-purple-50 to-pink-50 px-6 py-4 border-b border-purple-100">
        <div className="flex items-center gap-2 flex-1">
          {React.createElement(
            contentTypeIcons[evidence.contentType] || FileText,
            { className: 'h-5 w-5 text-purple-600' }
          )}
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-gray-900">{evidence.title}</h3>
            <span className="text-xs text-purple-600 capitalize">
              {evidence.contentType.replace('_', ' ')}
            </span>
            <ConfidenceBadge confidence={(evidence as any).processing_confidence || 0} />
          </div>
        </div>
      </div>

      {/* Content - Inline Editing */}
      <div className="p-6">
        <div className="space-y-6">
          {/* Summary */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Summary</h4>
            <InlineEditableTextarea
              value={(evidence.processedContent?.summary as string | undefined)}
              onSave={handleSaveSummary}
              placeholder="Add summary..."
              rows={5}
              maxLength={500}
            />
          </div>

          {/* Technologies */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Technologies</h4>
            <InlineEditableTags
              tags={(evidence.processedContent?.technologies as string[]) || []}
              onSave={handleSaveTechnologies}
              placeholder="Add technologies..."
            />
          </div>

          {/* Achievements */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Achievements</h4>
            <InlineEditableList
              items={(evidence.processedContent?.achievements as string[]) || []}
              onSave={handleSaveAchievements}
              placeholder="Add achievements..."
            />
          </div>
        </div>
      </div>

      {/* Accept/Reject Actions */}
      <div className="px-6 pb-6 flex justify-end gap-2">
        {accepted ? (
          <button
            type="button"
            onClick={() => onReject(evidence.id)}
            className="flex items-center gap-2 px-4 py-2 text-sm text-red-700 bg-white border border-red-300 rounded-lg hover:bg-red-50"
          >
            <X className="w-4 h-4" />
            Reject
          </button>
        ) : (
          <button
            type="button"
            onClick={() => onAccept(evidence.id)}
            className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg hover:from-green-700 hover:to-emerald-700 shadow-sm hover:shadow-md transition-all"
          >
            <Check className="w-4 h-4" />
            Accept
          </button>
        )}
      </div>

      {/* Accepted Indicator */}
      {accepted && (
        <div className="px-6 pb-6 pt-4 border-t border-green-200 flex items-center gap-2 text-sm">
          <div className="flex items-center gap-2 px-3 py-2 bg-green-100 rounded-lg">
            <Check className="w-5 h-5 text-green-700" />
            <span className="font-semibold text-green-800">Accepted</span>
          </div>
          {(evidence as any).accepted_at && (
            <span className="text-gray-600 text-xs">
              {new Date((evidence as any).accepted_at).toLocaleDateString()}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
