import React, { useEffect } from 'react'
import { Loader2, Github, FileText, CheckCircle, AlertCircle, TrendingUp, ExternalLink, Trash2, Link as LinkIcon } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import {
  InlineEditableTextarea,
  InlineEditableTags,
  InlineEditableList
} from '@/components/ui/InlineEditableFields'
import type { EvidenceLink, EnhancedEvidenceResponse, AttributedTechnology, AttributedAchievement, AttributedPattern } from '@/types'

interface EvidenceContentViewerProps {
  evidence: EvidenceLink
  enhancedEvidence?: EnhancedEvidenceResponse
  isLoading: boolean
  onFetch: () => void
  onEdit?: () => void
  onDelete?: () => void
  onSaveEnrichedContent?: (evidenceId: string, content: any) => Promise<void>
}

const EvidenceTypeIcon: React.FC<{ type: string }> = ({ type }) => {
  switch (type) {
    case 'github':
      return <Github className="h-5 w-5 text-gray-600" />
    case 'document':
      return <FileText className="h-5 w-5 text-gray-600" />
    default:
      return <FileText className="h-5 w-5 text-gray-600" />
  }
}

const formatFileSize = (bytes?: number): string => {
  if (!bytes) return ''
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  const mb = kb / 1024
  return `${mb.toFixed(1)} MB`
}

const getEvidenceUrl = (evidence: EvidenceLink): string => {
  // For document type, check if URL is relative path (starts with /) and prefix with backend URL
  if (evidence.evidenceType === 'document' && evidence.url.startsWith('/')) {
    const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    return `${backendUrl}${evidence.url}`
  }
  return evidence.url
}

// ft-030: Helper functions to handle attributed items (backward compatible)
const getItemText = (item: string | AttributedTechnology | AttributedAchievement | AttributedPattern): string => {
  if (typeof item === 'string') {
    return item
  }
  // Check for name field (technologies, patterns)
  if ('name' in item) {
    return item.name
  }
  // Check for text field (achievements)
  if ('text' in item) {
    return item.text
  }
  return String(item)
}

export const EvidenceContentViewer: React.FC<EvidenceContentViewerProps> = ({
  evidence,
  enhancedEvidence,
  isLoading,
  onFetch,
  onEdit,
  onDelete,
  onSaveEnrichedContent,
}) => {
  // Auto-fetch enhanced evidence on mount
  useEffect(() => {
    if (!enhancedEvidence && !isLoading) {
      onFetch()
    }
  }, []) // Only run on mount

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this evidence link? This action cannot be undone.')) {
      onDelete?.()
    }
  }

  // Individual field save handlers for inline editing
  const handleSaveSummary = async (summary: string) => {
    if (!enhancedEvidence || !onSaveEnrichedContent) return
    await onSaveEnrichedContent(enhancedEvidence.id, {
      processedContent: {
        ...enhancedEvidence.processedContent,
        summary
      }
    })
  }

  const handleSaveTechnologies = async (technologies: string[]) => {
    if (!enhancedEvidence || !onSaveEnrichedContent) return
    await onSaveEnrichedContent(enhancedEvidence.id, {
      processedContent: {
        ...enhancedEvidence.processedContent,
        technologies
      }
    })
  }

  const handleSaveAchievements = async (achievements: string[]) => {
    if (!enhancedEvidence || !onSaveEnrichedContent) return
    await onSaveEnrichedContent(enhancedEvidence.id, {
      processedContent: {
        ...enhancedEvidence.processedContent,
        achievements
      }
    })
  }

  const handleSaveSkills = async (skills: string[]) => {
    if (!enhancedEvidence || !onSaveEnrichedContent) return
    await onSaveEnrichedContent(enhancedEvidence.id, {
      processedContent: {
        ...enhancedEvidence.processedContent,
        skills
      }
    })
  }

  return (
    <Card className="overflow-hidden">
      {/* Header Section - Always Visible */}
      <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-white border-b border-gray-200">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <EvidenceTypeIcon type={evidence.evidenceType} />
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-gray-900 mb-1">
                {evidence.description || 'Evidence'}
              </p>
              <a
                href={getEvidenceUrl(evidence)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-purple-600 hover:text-purple-800 underline flex items-center gap-1 mb-2 break-all"
              >
                {evidence.url}
                <ExternalLink className="h-3 w-3 flex-shrink-0" />
              </a>

              {/* Quick Info */}
              <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600">
                <span className="capitalize">{evidence.evidenceType}</span>
                {evidence.file_size && (
                  <>
                    <span className="text-gray-300">•</span>
                    <span>{formatFileSize(evidence.file_size)}</span>
                  </>
                )}
                {evidence.mime_type && (
                  <>
                    <span className="text-gray-300">•</span>
                    <span>{evidence.mime_type}</span>
                  </>
                )}
                <span className="text-gray-300">•</span>
                <div className="flex items-center gap-1.5">
                  {evidence.isAccessible ? (
                    <>
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      <span className="text-green-600 font-medium">Accessible</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-4 w-4 text-red-600" />
                      <span className="text-red-600 font-medium">Not accessible</span>
                    </>
                  )}
                </div>
                {/* Processing Confidence */}
                {enhancedEvidence && (
                  <>
                    <span className="text-gray-300">•</span>
                    <div className="inline-flex items-center gap-1.5 px-2 py-1 bg-gradient-to-r from-purple-50 to-pink-50 rounded border border-purple-200">
                      <TrendingUp className="h-3.5 w-3.5 text-purple-600" />
                      <span className="text-xs font-semibold text-purple-900">
                        {Math.round(enhancedEvidence.processingConfidence * 100)}% confidence
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Edit Evidence Link Button (optional) */}
            {onEdit && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => onEdit()}
                className="flex items-center gap-1.5"
              >
                <LinkIcon className="h-4 w-4" />
                Link
              </Button>
            )}

            {/* Delete Button */}
            {onDelete && (
              <Button
                size="sm"
                onClick={handleDelete}
                className="flex items-center gap-1.5 bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700 focus:ring-purple-500"
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Content Section - Always Visible */}
      <div className="p-6">
          {isLoading ? (
            <div className="py-8 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
              <span className="ml-3 text-gray-600">Loading evidence content...</span>
            </div>
          ) : enhancedEvidence ? (
          <div className="space-y-6">
            {/* Summary/Description */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-3">Summary</h4>
              <InlineEditableTextarea
                value={(enhancedEvidence.processedContent?.summary || enhancedEvidence.processedContent?.description) as string | undefined}
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
                tags={((enhancedEvidence.processedContent?.technologies || []) as any[]).map(tech =>
                  typeof tech === 'string' ? tech : getItemText(tech)
                )}
                onSave={handleSaveTechnologies}
                placeholder="Add technologies..."
              />
            </div>

            {/* Achievements */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-3">Achievements</h4>
              <InlineEditableList
                items={((enhancedEvidence.processedContent?.achievements || []) as any[]).map(achievement =>
                  typeof achievement === 'string' ? achievement : getItemText(achievement)
                )}
                onSave={handleSaveAchievements}
                placeholder="Add achievements..."
              />
            </div>

            {/* Skills */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-3">Skills</h4>
              <InlineEditableTags
                tags={(enhancedEvidence.processedContent?.skills as string[]) || []}
                onSave={handleSaveSkills}
                placeholder="Add skills..."
              />
            </div>

            {/* Empty State for Processed Content */}
            {(!enhancedEvidence.processedContent ||
              (!enhancedEvidence.processedContent.technologies?.length &&
                !enhancedEvidence.processedContent.achievements?.length &&
                !enhancedEvidence.processedContent.skills?.length &&
                !enhancedEvidence.processedContent.summary &&
                !enhancedEvidence.processedContent.description)) && (
                <div className="text-center py-6 text-gray-500">
                  <p className="text-sm mb-2">No structured content extracted yet</p>
                  <p className="text-xs text-gray-400">
                    Processing confidence: {Math.round(enhancedEvidence.processingConfidence * 100)}%
                  </p>
                </div>
              )}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <div className="max-w-md mx-auto">
              <AlertCircle className="h-12 w-12 text-gray-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-700 mb-2">Enhanced content not yet processed</p>
              <p className="text-xs text-gray-500 mb-4">
                This evidence hasn't been processed by the AI enrichment system yet.
                Run artifact enrichment to extract structured data from this evidence.
              </p>
              <button
                onClick={onFetch}
                className="text-sm text-purple-600 hover:text-purple-800 font-medium"
              >
                Check again
              </button>
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}
