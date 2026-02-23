import { useState } from 'react'
import { Sparkles, RefreshCw, Check, Edit, ArrowRight, Loader2, FileText } from 'lucide-react'
import { cn } from '@/utils/cn'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Tooltip } from '@/components/ui/Tooltip'
import { EvidenceContentViewer } from '@/components/EvidenceContentViewer'
import { AddEvidenceLinkForm, EditEvidenceLinkModal, type LinkFormData } from '@/components/EvidenceLinkManager'
import type { Artifact, EvidenceLink, EnhancedEvidenceResponse, AttributedTechnology, AttributedAchievement, AttributedPattern } from '@/types'

// ft-030: Helper functions to handle attributed items (backward compatible)
// const isAttributedItem = (item: any): item is { source_attribution: any } => {
//   return typeof item === 'object' && item !== null && 'source_attribution' in item
// }

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

interface EnrichedContentViewerProps {
  artifact: Artifact
  onReEnrich: () => void
  onEdit: () => void
  onAcceptAll: () => void
  isEnriching?: boolean
  className?: string
  // Evidence props
  evidenceLinks?: EvidenceLink[]
  enhancedEvidenceCache?: Record<number, EnhancedEvidenceResponse>
  loadingEvidence?: Record<number, boolean>
  onFetchEnhancedEvidence?: (evidenceId: number) => void
  onEditEnrichedContent?: (evidence: EnhancedEvidenceResponse) => void
  onSaveEnrichedEvidence?: (evidenceId: string, content: any) => Promise<void>
  onAddEvidence?: (data: LinkFormData) => Promise<void>
  onEditEvidence?: (linkId: number, data: Partial<LinkFormData>) => Promise<void>
  onDeleteEvidence?: (linkId: number) => Promise<void>
  onUploadEvidence?: (files: File[]) => Promise<void>
}

export function EnrichedContentViewer({
  artifact,
  onReEnrich,
  onEdit,
  onAcceptAll,
  isEnriching = false,
  className,
  evidenceLinks = [],
  enhancedEvidenceCache = {},
  loadingEvidence = {},
  onFetchEnhancedEvidence,
  onSaveEnrichedEvidence,
  onAddEvidence,
  onEditEvidence,
  onDeleteEvidence,
  onUploadEvidence
}: EnrichedContentViewerProps) {
  const [activeTab, setActiveTab] = useState<'description' | 'technologies' | 'achievements' | 'evidence'>('description')
  const [isAddingEvidence, setIsAddingEvidence] = useState(false)
  const [editingEvidence, setEditingEvidence] = useState<EvidenceLink | null>(null)

  const hasEnrichment = Boolean(
    artifact.unifiedDescription ||
    artifact.enrichedTechnologies?.length ||
    artifact.enrichedAchievements?.length
  )

  if (!hasEnrichment) {
    return (
      <div className={cn('bg-gray-50 border border-gray-200 rounded-xl p-8 text-center', className)}>
        <div className="w-16 h-16 rounded-full bg-gradient-to-r from-purple-50 to-pink-50 flex items-center justify-center mx-auto mb-4">
          <Sparkles className="h-8 w-8 text-purple-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No Enriched Content Yet</h3>
        <p className="text-gray-600 mb-6 max-w-md mx-auto">
          AI-powered content enrichment will analyze your evidence sources to generate enhanced descriptions, extract technologies, and identify achievements.
        </p>
        <Button
          onClick={onReEnrich}
          disabled={isEnriching}
          className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white"
        >
          {isEnriching ? (
            <>
              <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              Enriching...
            </>
          ) : (
            <>
              <Sparkles className="h-5 w-5 mr-2" />
              Enrich with AI
            </>
          )}
        </Button>
      </div>
    )
  }

  return (
    <div className={cn('bg-white border border-gray-200 rounded-xl shadow-sm', className)}>
      {/* Header - Simple and clean */}
      <div className="bg-white border-b border-gray-200 p-6 overflow-visible">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Subtle AI indicator */}
            <div className="w-10 h-10 rounded-lg bg-gradient-to-r from-purple-50 to-pink-50 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">AI-Enriched Content</h3>
              <p className="text-sm text-gray-600">
                Enhanced by artificial intelligence
                {artifact.processingConfidence !== undefined && (
                  <span className="ml-2 text-xs text-gray-500">
                    • {(artifact.processingConfidence * 100).toFixed(0)}% confidence
                  </span>
                )}
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <Tooltip
              content={isEnriching ? "Can't edit while enrichment is in progress" : "Edit AI-enriched content"}
              position="bottom"
            >
              <Button
                onClick={onEdit}
                disabled={isEnriching}
                variant="outline"
                size="sm"
              >
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
            </Tooltip>
            <Tooltip
              content={isEnriching ? "Enrichment is currently running" : "Re-run AI enrichment with latest evidence"}
              position="bottom"
            >
              <Button
                onClick={onReEnrich}
                disabled={isEnriching}
                variant="outline"
                size="sm"
              >
                <RefreshCw className={cn("h-4 w-4 mr-2", isEnriching && "animate-spin")} />
                {isEnriching ? 'Enriching...' : 'Re-enrich'}
              </Button>
            </Tooltip>
            <Tooltip
              content={isEnriching ? "Can't accept while enrichment is in progress" : "Apply all AI suggestions to your artifact"}
              position="bottom"
            >
              <Button
                onClick={onAcceptAll}
                disabled={isEnriching}
                size="sm"
                className="bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700 focus:ring-purple-500"
              >
                <Check className="h-4 w-4 mr-2" />
                Accept All
              </Button>
            </Tooltip>
          </div>
        </div>
      </div>

      {/* Tabs - Clean and simple */}
      <div className="border-b border-gray-200 bg-gray-50">
        <div className="flex px-2">
          <button
            onClick={() => setActiveTab('description')}
            className={cn(
              'relative px-6 py-3 text-sm font-medium transition-colors border-b-2',
              activeTab === 'description'
                ? 'border-purple-600 text-purple-700 bg-white'
                : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            )}
          >
            Description
          </button>
          <button
            onClick={() => setActiveTab('technologies')}
            className={cn(
              'relative px-6 py-3 text-sm font-medium transition-colors border-b-2',
              activeTab === 'technologies'
                ? 'border-purple-600 text-purple-700 bg-white'
                : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            )}
          >
            <span className="flex items-center gap-2">
              Technologies
              {(artifact.enrichedTechnologies?.length ?? 0) > 0 && (
                <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 text-xs font-semibold rounded-full border border-purple-200">
                  {artifact.enrichedTechnologies?.length}
                </span>
              )}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('achievements')}
            className={cn(
              'relative px-6 py-3 text-sm font-medium transition-colors border-b-2',
              activeTab === 'achievements'
                ? 'border-purple-600 text-purple-700 bg-white'
                : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            )}
          >
            <span className="flex items-center gap-2">
              Achievements
              {(artifact.enrichedAchievements?.length ?? 0) > 0 && (
                <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 text-xs font-semibold rounded-full border border-purple-200">
                  {artifact.enrichedAchievements?.length}
                </span>
              )}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('evidence')}
            className={cn(
              'relative px-6 py-3 text-sm font-medium transition-colors border-b-2',
              activeTab === 'evidence'
                ? 'border-purple-600 text-purple-700 bg-white'
                : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            )}
          >
            <span className="flex items-center gap-2">
              Evidence Sources
              {(evidenceLinks?.length ?? 0) > 0 && (
                <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 text-xs font-semibold rounded-full border border-purple-200">
                  {evidenceLinks.length}
                </span>
              )}
            </span>
          </button>
        </div>
      </div>

      {/* Content - Improved spacing and typography */}
      <div className="p-6 relative">
        {/* Loading overlay when enriching */}
        {isEnriching && (
          <div className="absolute inset-0 bg-white/90 backdrop-blur-sm z-10 flex items-center justify-center rounded-b-xl">
            <div className="text-center px-6 py-8 bg-white rounded-xl shadow-lg border border-gray-200">
              <Loader2 className="h-10 w-10 animate-spin text-purple-600 mx-auto mb-4" />
              <p className="text-base font-semibold text-gray-900">AI is enriching your artifact...</p>
              <p className="text-sm text-gray-600 mt-2">This may take a few moments</p>
            </div>
          </div>
        )}

        {activeTab === 'description' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Original */}
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-gray-700">Original Description</h4>
              <div className="bg-gray-50 rounded-lg p-5 border border-gray-200 min-h-[200px]">
                <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                  {artifact.description}
                </p>
              </div>
            </div>

            {/* Enriched */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-semibold text-gray-700">AI-Enhanced Description</h4>
                <ArrowRight className="h-4 w-4 text-purple-600" />
              </div>
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-5 border-2 border-purple-200 min-h-[200px]">
                <p className="text-sm text-gray-900 whitespace-pre-wrap leading-relaxed">
                  {artifact.unifiedDescription || 'No enriched description available'}
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'technologies' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Original */}
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-gray-700">Original Technologies</h4>
              <div className="flex flex-wrap gap-2">
                {artifact.technologies?.map((tech, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-3 py-1.5 bg-white text-gray-800 text-sm font-medium rounded-lg border border-gray-300"
                  >
                    {tech}
                  </span>
                ))}
                {!artifact.technologies?.length && (
                  <p className="text-sm text-gray-500 py-4">No technologies listed</p>
                )}
              </div>
            </div>

            {/* Enriched */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-semibold text-gray-700">AI-Extracted Technologies</h4>
                <ArrowRight className="h-4 w-4 text-purple-600" />
              </div>
              <div className="flex flex-wrap gap-2">
                {artifact.enrichedTechnologies?.map((tech, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-3 py-1.5 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-900 text-sm font-semibold rounded-lg border border-purple-300"
                  >
                    {getItemText(tech)}
                  </span>
                ))}
                {!artifact.enrichedTechnologies?.length && (
                  <p className="text-sm text-gray-500 py-4">No enriched technologies available</p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'achievements' && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-gray-700">AI-Identified Achievements</h4>
              <ArrowRight className="h-4 w-4 text-purple-600" />
            </div>
            <div className="space-y-3">
              {artifact.enrichedAchievements?.map((achievement, index) => (
                <div
                  key={index}
                  className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 text-white flex items-center justify-center text-xs font-semibold">
                      {index + 1}
                    </div>
                    <p className="text-sm text-gray-900 leading-relaxed flex-1 pt-0.5">{getItemText(achievement)}</p>
                  </div>
                </div>
              ))}
              {!artifact.enrichedAchievements?.length && (
                <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
                  <p className="text-sm text-gray-500">No achievements identified yet</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'evidence' && (
          <div className="space-y-4">
            {/* Evidence List */}
            {evidenceLinks.length === 0 && !isAddingEvidence ? (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No Evidence Sources
                </h3>
                <p className="text-gray-600 mb-4">
                  Add evidence links to repositories, live applications, and supporting documents
                </p>
                {onAddEvidence && (
                  <Button
                    onClick={() => setIsAddingEvidence(true)}
                    size="sm"
                  >
                    + Add Evidence Link
                  </Button>
                )}
              </div>
            ) : (
              <>
                {/* Evidence Items - Always Visible */}
                {evidenceLinks.map((evidence) => (
                  <EvidenceContentViewer
                    key={evidence.id}
                    evidence={evidence}
                    enhancedEvidence={enhancedEvidenceCache[evidence.id]}
                    isLoading={loadingEvidence[evidence.id] || false}
                    onFetch={() => {
                      if (onFetchEnhancedEvidence) {
                        onFetchEnhancedEvidence(evidence.id)
                      }
                    }}
                    onEdit={onEditEvidence ? () => setEditingEvidence(evidence) : undefined}
                    onDelete={onDeleteEvidence ? () => onDeleteEvidence(evidence.id) : undefined}
                    onSaveEnrichedContent={onSaveEnrichedEvidence}
                  />
                ))}

                {/* Add Evidence Button/Form at Bottom */}
                {!isAddingEvidence && onAddEvidence ? (
                  <div className="flex justify-center pt-2">
                    <Button
                      onClick={() => setIsAddingEvidence(true)}
                      variant="outline"
                      size="sm"
                    >
                      + Add Evidence Link
                    </Button>
                  </div>
                ) : isAddingEvidence && onAddEvidence && (
                  <Card className="p-6">
                    <h4 className="font-medium text-gray-900 mb-4">Add Evidence</h4>
                    <AddEvidenceLinkForm
                      onSave={async (data) => {
                        await onAddEvidence(data)
                        setIsAddingEvidence(false)
                      }}
                      onUpload={async (files) => {
                        if (onUploadEvidence) {
                          await onUploadEvidence(files)
                          setIsAddingEvidence(false)
                        }
                      }}
                      onCancel={() => setIsAddingEvidence(false)}
                    />
                  </Card>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Edit Evidence Modal */}
      {editingEvidence && onEditEvidence && (
        <EditEvidenceLinkModal
          link={editingEvidence}
          isOpen={!!editingEvidence}
          onClose={() => setEditingEvidence(null)}
          onSave={async (linkId, data) => {
            await onEditEvidence(linkId, data)
            setEditingEvidence(null)
          }}
        />
      )}
    </div>
  )
}
