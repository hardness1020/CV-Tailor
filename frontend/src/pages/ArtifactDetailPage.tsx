import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Trash2,
  FileText,
  Lock,
  Sparkles,
  ChevronDown,
  Clock,
  RefreshCw
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { ConfirmationModal } from '@/components/ui/ConfirmationModal'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { ErrorState } from '@/components/ui/ErrorState'
import { Tooltip } from '@/components/ui/Tooltip'
import { ArtifactDetailSkeleton } from '@/components/ArtifactDetailSkeleton'
import { EnrichedContentEditor, type EnrichedContentUpdate } from '@/components/EnrichedContentEditor'
import { EvidenceContentViewer } from '@/components/EvidenceContentViewer'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  InlineEditableText,
  InlineEditableTextarea,
  InlineEditableSelect,
  InlineEditableDateRange,
  InlineEditableTags,
  InlineEditableList
} from '@/components/ui/InlineEditableFields'
import { useEnrichmentStatus } from '@/hooks/useEnrichmentStatus'
import { useArtifactStore } from '@/stores/artifactStore'
import { apiClient } from '@/services/apiClient'
import { formatRelativeOrAbsolute } from '@/utils/formatters'
import toast from 'react-hot-toast'
import type { Artifact, ArtifactCreateData, EnhancedEvidenceResponse } from '@/types'

export default function ArtifactDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { updateArtifact, deleteArtifact } = useArtifactStore()

  const [artifact, setArtifact] = useState<Artifact | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showEnrichedEditor, setShowEnrichedEditor] = useState(false)
  const [enhancedEvidenceCache, setEnhancedEvidenceCache] = useState<Record<number, EnhancedEvidenceResponse>>({})
  const [loadingEvidence, setLoadingEvidence] = useState<Record<number, boolean>>({})
  const [isSubmittingEnrichment, setIsSubmittingEnrichment] = useState(false)

  // Confirmation modal states
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  // Poll enrichment status to detect when enrichment is in progress
  const { status: enrichmentStatus } = useEnrichmentStatus({
    artifactId: artifact?.id || 0,
    enabled: !!artifact?.id,
    pollingInterval: 3000,
    onComplete: (status) => {
      // Refresh artifact when enrichment completes
      if (artifact?.id) {
        const artifactId = artifact.id // Capture ID to avoid closure issues

        apiClient.getArtifact(artifactId)
          .then(updatedArtifact => {
            setArtifact(updatedArtifact)
            updateArtifact(artifactId, updatedArtifact)

            // Show success toast with enrichment summary
            const techCount = status.technologiesCount || 0
            const achievementCount = status.achievementsCount || 0
            toast.success(
              `Enrichment complete! Extracted ${techCount} technologies and ${achievementCount} achievements.`
            )
          })
          .catch(error => {
            console.error('=== FAILED TO REFRESH ARTIFACT ===')
            console.error('Error:', error)
            toast.error('Enrichment completed but failed to load updated content. Please refresh the page.')
          })
      }
    },
    onError: (error) => {
      // Show error toast with retry option
      toast.error(
        <div>
          <p className="font-semibold">Enrichment failed</p>
          <p className="text-sm">{error}</p>
        </div>,
        { duration: 5000 }
      )
    }
  })

  // Derive isEnriching from backend polled status AND local submission state
  // isSubmittingEnrichment provides immediate UI feedback while waiting for backend polling to detect the new status
  const isEnriching = isSubmittingEnrichment || enrichmentStatus.status === 'processing' || enrichmentStatus.status === 'pending'

  // Clear submission state when backend polling detects the enrichment has started
  useEffect(() => {
    if (isSubmittingEnrichment && (enrichmentStatus.status === 'processing' || enrichmentStatus.status === 'pending')) {
      setIsSubmittingEnrichment(false)
    }
  }, [isSubmittingEnrichment, enrichmentStatus.status])

  // Load artifact data
  useEffect(() => {
    if (!id) {
      setError('Artifact ID is required')
      setIsLoading(false)
      return
    }

    const loadArtifact = async () => {
      try {
        setIsLoading(true)
        setError(null) // Clear any previous errors
        const artifactData = await apiClient.getArtifact(parseInt(id))
        setArtifact(artifactData)
      } catch (error) {
        console.error('Failed to load artifact:', error)
        setError('Failed to load artifact')
        toast.error('Failed to load artifact')
      } finally {
        setIsLoading(false)
      }
    }

    loadArtifact()
  }, [id])


  const handleEdit = async (updates: Partial<ArtifactCreateData>) => {
    if (!artifact) {
      console.error('No artifact to update')
      return
    }

    try {
      const updatedArtifact = await apiClient.updateArtifact(artifact.id, updates)

      // Ensure the updated artifact has all required fields
      if (!updatedArtifact || !updatedArtifact.id) {
        throw new Error('Invalid response from server')
      }

      // Merge updated data with existing artifact to preserve all fields
      const mergedArtifact = { ...artifact, ...updatedArtifact }
      setArtifact(mergedArtifact)

      // Update global store with merged data
      updateArtifact(artifact.id, mergedArtifact)

      // Clear any error state first to ensure clean state
      setError(null)

      toast.success('Artifact updated successfully!')
    } catch (error) {
      console.error('Failed to update artifact:', error)
      toast.error('Failed to update artifact')
      throw error
    }
  }

  const handleDelete = async () => {
    if (!artifact) return
    try {
      await apiClient.deleteArtifact(artifact.id)
      deleteArtifact(artifact.id)
      toast.success('Artifact deleted successfully')
      navigate('/artifacts')
    } catch (error) {
      console.error('Failed to delete artifact:', error)
      toast.error('Failed to delete artifact')
    }
  }

  // ft-046: Navigate to wizard for re-enrichment (6-step wizard)
  const handleReEnrichEvidence = () => {
    if (!artifact) return
    // Jump to Step 3 (Evidence) for full re-enrichment with evidence changes
    navigate(`/artifacts/upload?artifactId=${artifact.id}&startStep=3`)
  }

  const handleReEnrichArtifact = () => {
    if (!artifact) return
    // Jump to Step 5 (Processing & Evidence Review) for fast content refresh without evidence changes
    navigate(`/artifacts/upload?artifactId=${artifact.id}&startStep=5`)
  }

  const handleUpdateEnrichedContent = async (data: EnrichedContentUpdate) => {
    if (!artifact) return

    try {
      await apiClient.updateEnrichedContent(artifact.id, data)

      // Refresh artifact to get updated enriched content
      const updatedArtifact = await apiClient.getArtifact(artifact.id)
      setArtifact(updatedArtifact)
      updateArtifact(artifact.id, updatedArtifact)

      setShowEnrichedEditor(false)
      toast.success('Enriched content updated successfully!')
    } catch (error) {
      console.error('Failed to update enriched content:', error)
      toast.error('Failed to update enriched content')
      throw error
    }
  }

  const fetchEnhancedEvidence = async (evidenceId: number) => {
    // Check if already cached or loading
    if (enhancedEvidenceCache[evidenceId] || loadingEvidence[evidenceId]) {
      return
    }

    try {
      setLoadingEvidence(prev => ({ ...prev, [evidenceId]: true }))

      const enhancedEvidence = await apiClient.getEnhancedEvidence(evidenceId)
      setEnhancedEvidenceCache(prev => ({ ...prev, [evidenceId]: enhancedEvidence }))
    } catch (error: any) {
      console.error('Failed to fetch enhanced evidence:', error)

      // 404 is expected when evidence hasn't been processed yet - don't show error toast
      if (error?.response?.status !== 404) {
        // For other errors, show error toast
        console.error('Error details:', error?.response?.data || error.message)
        toast.error(`Failed to load evidence content: ${error?.response?.data?.detail || error.message}`)
      }
    } finally {
      setLoadingEvidence(prev => ({ ...prev, [evidenceId]: false }))
    }
  }

  const handleSaveEnrichedEvidence = async (
    enhancedEvidenceId: string,
    data: {
      processedContent: {
        summary?: string
        description?: string
        technologies?: string[]
        achievements?: string[]
        skills?: string[]
      }
    }
  ) => {
    try {
      const updated = await apiClient.updateEnhancedEvidence(enhancedEvidenceId, data)

      // Update cache with new data
      const evidenceId = updated.evidenceId
      if (evidenceId) {
        setEnhancedEvidenceCache(prev => ({
          ...prev,
          [evidenceId]: updated
        }))
      }

      toast.success('Enriched content updated successfully')
    } catch (error) {
      console.error('Failed to update enriched evidence:', error)
      toast.error('Failed to update enriched content')
      throw error
    }
  }

  // Artifact type options for select dropdown
  const artifactTypeOptions = [
    { value: 'project', label: 'Project' },
    { value: 'role', label: 'Role' },
    { value: 'certification', label: 'Certification' },
    { value: 'publication', label: 'Publication' },
    { value: 'award', label: 'Award' },
    { value: 'other', label: 'Other' }
  ]

  // Inline editing save handlers
  const handleSaveTitle = async (title: string) => {
    await handleEdit({ title })
  }

  const handleSaveArtifactType = async (artifactType: string) => {
    await handleEdit({ artifactType: artifactType as any })
  }

  const handleSaveDateRange = async (startDate: string, endDate: string | null) => {
    await handleEdit({ startDate, endDate: endDate ?? undefined })
  }

  const handleSaveUserContext = async (userContext: string) => {
    await handleEdit({ userContext })
  }

  const handleSaveDescription = async (unifiedDescription: string) => {
    await handleUpdateEnrichedContent({ unifiedDescription })
  }

  const handleSaveTechnologies = async (enrichedTechnologies: string[]) => {
    await handleUpdateEnrichedContent({ enrichedTechnologies })
  }

  const handleSaveAchievements = async (enrichedAchievements: string[]) => {
    await handleUpdateEnrichedContent({ enrichedAchievements })
  }


  if (isLoading) {
    return <ArtifactDetailSkeleton />
  }

  if (error || !artifact) {
    const errorType = error?.includes('network') || error?.includes('connection') ? 'network'
      : !artifact ? 'notFound'
      : 'generic'

    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <ErrorState
          type={errorType}
          title={!artifact ? 'Artifact Not Found' : undefined}
          message={error || (!artifact ? 'The artifact you\'re looking for doesn\'t exist or has been removed.' : undefined)}
          onRetry={error ? () => window.location.reload() : undefined}
          onGoBack={() => navigate('/artifacts')}
        />
      </div>
    )
  }

  return (
    <div key={`${artifact?.id}-${artifact?.updatedAt}`} className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between min-w-0 gap-4">
        <div className="flex items-center space-x-4 flex-1 min-w-0">
          <Button
            variant="outline"
            onClick={() => navigate('/artifacts')}
            className="flex-shrink-0"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <InlineEditableText
                value={artifact.title}
                onSave={handleSaveTitle}
                className="text-2xl font-bold text-gray-900 break-words"
                inputClassName="text-2xl font-bold"
                maxLength={200}
              />
              <StatusBadge status={artifact.status} />
            </div>
            <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
              <InlineEditableSelect
                value={artifact.artifactType}
                options={artifactTypeOptions}
                onSave={handleSaveArtifactType}
                className="capitalize font-medium"
              />
              <span className="text-gray-300">•</span>
              <InlineEditableDateRange
                startDate={artifact.startDate}
                endDate={artifact.endDate ?? null}
                onSave={handleSaveDateRange}
              />
              <span className="text-gray-300">•</span>
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                Created {formatRelativeOrAbsolute(artifact.createdAt)}
              </span>
              <span className="text-gray-300">•</span>
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                Updated {formatRelativeOrAbsolute(artifact.updatedAt)}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3 flex-shrink-0">
          {/* Re-enrich Dropdown (ft-046) */}
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <Button
                variant="outline"
                disabled={isEnriching}
                className="inline-flex items-center gap-2"
              >
                <RefreshCw className={`h-4 w-4 ${isEnriching ? 'animate-spin' : ''}`} />
                Re-enrich
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                className="min-w-[220px] bg-white rounded-lg shadow-lg border border-gray-200 p-1 z-50"
                sideOffset={5}
              >
                <DropdownMenu.Item
                  className="flex items-start gap-3 px-3 py-2 text-sm text-gray-700 rounded-md hover:bg-gray-100 focus:bg-gray-100 outline-none cursor-pointer"
                  onSelect={handleReEnrichEvidence}
                >
                  <FileText className="h-4 w-4 mt-0.5 text-purple-600 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">Re-enrich Evidence</div>
                    <div className="text-xs text-gray-500">Update evidence sources</div>
                  </div>
                </DropdownMenu.Item>
                <DropdownMenu.Item
                  className="flex items-start gap-3 px-3 py-2 text-sm text-gray-700 rounded-md hover:bg-gray-100 focus:bg-gray-100 outline-none cursor-pointer"
                  onSelect={handleReEnrichArtifact}
                >
                  <Sparkles className="h-4 w-4 mt-0.5 text-purple-600 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">Re-enrich Artifact</div>
                    <div className="text-xs text-gray-500">Refresh content only</div>
                  </div>
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>

          <Tooltip
            content={isEnriching ? "Can't delete while enrichment is in progress" : "Delete this artifact"}
            disabled={!isEnriching}
            position="bottom"
          >
            <Button
              onClick={() => setShowDeleteConfirm(true)}
              disabled={isEnriching}
              className="bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </Tooltip>
        </div>
      </div>

      {/* Artifact Details (ft-046: Tabs removed, single-page view) */}
      <div className="mt-6 space-y-6">
            {/* Your Context - Clean Highlight */}
            <Card className="relative bg-purple-50/30 border-l-4 border-purple-500">
              <div className="p-6">
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                    <Lock className="h-5 w-5 text-purple-600" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold text-gray-900">Your Context</h2>
                    <p className="text-xs text-gray-600">Private notes preserved during enrichment</p>
                  </div>
                </div>
                <div className="p-4 bg-white rounded-lg border border-gray-200">
                  <InlineEditableTextarea
                    value={artifact.userContext || ''}
                    onSave={handleSaveUserContext}
                    placeholder="Add private context notes..."
                    rows={3}
                    maxLength={1000}
                  />
                </div>
              </div>
            </Card>

            {/* Main Content - Full Width */}
            <div className="space-y-6">
              {/* Description */}
              <Card className="p-6">
                <h3 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <FileText className="h-5 w-5 text-gray-600" />
                  Description
                </h3>
                <InlineEditableTextarea
                  value={artifact.unifiedDescription}
                  onSave={handleSaveDescription}
                  placeholder="Add a description..."
                  rows={6}
                  maxLength={1000}
                />
              </Card>

              {/* Technologies */}
              <Card className="p-6">
                <h3 className="text-base font-semibold text-gray-900 mb-4">Technologies</h3>
                <InlineEditableTags
                  tags={artifact.enrichedTechnologies || []}
                  onSave={handleSaveTechnologies}
                  placeholder="Add technologies..."
                />
              </Card>

              {/* Achievements */}
              <Card className="p-6">
                <h3 className="text-base font-semibold text-gray-900 mb-4">Key Achievements</h3>
                <InlineEditableList
                  items={artifact.enrichedAchievements || []}
                  onSave={handleSaveAchievements}
                  placeholder="Add achievements..."
                />
              </Card>

              {/* Evidence Sources */}
              {artifact.evidenceLinks && artifact.evidenceLinks.length > 0 && (
                <Card className="p-6">
                  <h3 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    Evidence Sources
                    <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-gray-200 text-gray-700 text-xs font-semibold rounded-full">
                      {artifact.evidenceLinks.length}
                    </span>
                  </h3>
                  <div className="space-y-3">
                    {artifact.evidenceLinks.map((evidence) => {
                      const enhancedEvidence = enhancedEvidenceCache[evidence.id]
                      const isLoadingEnhanced = loadingEvidence[evidence.id]

                      return (
                        <EvidenceContentViewer
                          key={evidence.id}
                          evidence={evidence}
                          enhancedEvidence={enhancedEvidence}
                          isLoading={isLoadingEnhanced}
                          onFetch={() => fetchEnhancedEvidence(evidence.id)}
                          onSaveEnrichedContent={handleSaveEnrichedEvidence}
                        />
                      )
                    })}
                  </div>
                </Card>
              )}
            </div>
      </div>

      {/* Enriched Content Editor */}
      <EnrichedContentEditor
        artifact={artifact}
        isOpen={showEnrichedEditor}
        onClose={() => setShowEnrichedEditor(false)}
        onSave={handleUpdateEnrichedContent}
      />

      {/* Confirmation Modals */}
      <ConfirmationModal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={handleDelete}
        title="Delete Artifact"
        message="Are you sure you want to delete this artifact? This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
      />
    </div>
  )
}