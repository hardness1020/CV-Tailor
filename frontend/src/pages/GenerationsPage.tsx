import { useState, useMemo, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, FileText, Download, ArrowRight, Sparkles, Trash2, Edit, Loader2 } from 'lucide-react'
import ExportDialog from '@/components/ExportDialog'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SelectionBar } from '@/components/ui/SelectionBar'
import { FilterBar } from '@/components/ui/FilterBar'
import { SelectableCard } from '@/components/ui/SelectableCard'
import { SelectableListItem } from '@/components/ui/SelectableListItem'
import { GenerationStatusBadge } from '@/components/GenerationStatusBadge'
import { useGeneration } from '@/hooks/useGeneration'
import { formatDate } from '@/utils/formatters'
import { cn } from '@/utils/cn'
import { cvsTheme } from '@/utils/pageThemes'
import type { GeneratedDocument } from '@/types'

// Helper to get phase display text (ft-026)
function getPhaseDisplayText(phase?: string): string {
  switch (phase) {
    case 'bullet_generation':
      return 'Generating Bullets'
    case 'bullet_review':
      return 'Ready for Review'
    case 'assembly':
      return 'Assembling Document'
    case 'completed':
      return 'Completed'
    default:
      return 'Processing'
  }
}

// Helper to get generation title with job info
function getGenerationTitle(document: GeneratedDocument): string {
  const { jobTitle, companyName, type } = document

  // If we have both job title and company, show "Job Title @ Company"
  if (jobTitle && companyName) {
    return `${jobTitle} @ ${companyName}`
  }

  // If we have only job title
  if (jobTitle) {
    return jobTitle
  }

  // If we have only company name
  if (companyName) {
    return companyName
  }

  // Fallback to generic title
  return type === 'cv' ? 'CV Generation' : 'Cover Letter'
}

// Check if generation is in progress (ft-026)
function isInProgress(status: string): boolean {
  return ['pending', 'processing', 'bullets_approved', 'assembling'].includes(status)
}

export default function GenerationsPage() {
  const navigate = useNavigate()
  const {
    completedDocuments,
    activeGenerations,
    selectedDocuments,
    toggleSelection,
    clearSelection,
    deleteDocument,
    bulkDeleteDocuments,
  } = useGeneration()

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStatus, setSelectedStatus] = useState<'all' | 'in_progress' | 'completed' | 'failed'>('all')
  const [isLoading, setIsLoading] = useState(true)

  // Simulate initial loading state
  useEffect(() => {
    // Allow time for data to load from hook
    const timer = setTimeout(() => {
      setIsLoading(false)
    }, 500)
    return () => clearTimeout(timer)
  }, [])

  // Combine all generations (active + completed) into one list
  const allDocuments = useMemo(() => {
    return [...activeGenerations, ...completedDocuments]
  }, [activeGenerations, completedDocuments])

  // Filter documents
  const filteredDocuments = useMemo(() => {
    return allDocuments.filter(document => {
      // Status filter
      if (selectedStatus === 'in_progress') {
        return ['pending', 'processing', 'bullets_ready', 'bullets_approved', 'assembling'].includes(document.status)
      } else if (selectedStatus !== 'all' && document.status !== selectedStatus) {
        return false
      }

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const matchesType = document.type?.toLowerCase().includes(query)
        const matchesHash = document.jobDescriptionHash?.toLowerCase().includes(query)
        const matchesMetadata = document.metadata?.modelUsed?.toLowerCase().includes(query)

        return matchesType || matchesHash || matchesMetadata
      }

      return true
    })
  }, [allDocuments, selectedStatus, searchQuery])

  const handleBulkDelete = async () => {
    if (selectedDocuments.length === 0) return
    if (window.confirm(`Delete ${selectedDocuments.length} selected document${selectedDocuments.length > 1 ? 's' : ''}?`)) {
      await bulkDeleteDocuments(selectedDocuments)
    }
  }

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this document?')) {
      await deleteDocument(id)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        badgeIcon={Sparkles}
        badgeText="AI-Powered Generation"
        title="Your"
        titleHighlight="Generations"
        description="View and manage your AI-generated documents tailored for specific job descriptions."
        theme={cvsTheme}
      >
        <Link to="/generations/create">
          <Button
            className="group bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold px-6 py-3 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
          >
            <div className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              <span>Generate CV</span>
              <ArrowRight className="h-4 w-4 transform group-hover:translate-x-1 transition-transform duration-200" />
            </div>
          </Button>
        </Link>
      </PageHeader>

      {/* Filters and Search */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-300">
        <FilterBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          searchPlaceholder="Search by type, job description, or model..."
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          statusFilter={{
            value: selectedStatus,
            options: [
              { value: 'all', label: 'All Status' },
              { value: 'in_progress', label: 'In Progress' },
              { value: 'completed', label: 'Completed' },
              { value: 'failed', label: 'Failed' },
            ],
            onChange: (value) => setSelectedStatus(value as 'all' | 'in_progress' | 'completed' | 'failed'),
          }}
          theme={cvsTheme}
        />

        <SelectionBar
          selectedCount={selectedDocuments.length}
          itemName="CV"
          onClear={clearSelection}
          onDelete={handleBulkDelete}
          theme={cvsTheme}
        />
      </div>

      {/* Recent CVs Grid/List */}
      <div className="mt-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Loading CVs...</span>
          </div>
        ) : filteredDocuments.length > 0 ? (
          viewMode === 'grid' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredDocuments.map((document) => (
                <GenerationCard
                  key={document.id}
                  document={document}
                  isSelected={selectedDocuments.includes(document.id)}
                  onToggleSelect={() => toggleSelection(document.id)}
                  onDelete={() => handleDelete(document.id)}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {filteredDocuments.map((document) => (
                <GenerationListItem
                  key={document.id}
                  document={document}
                  isSelected={selectedDocuments.includes(document.id)}
                  onToggleSelect={() => toggleSelection(document.id)}
                  onDelete={() => handleDelete(document.id)}
                />
              ))}
            </div>
          )
        ) : (
          <EmptyState
            title={searchQuery || selectedStatus !== 'all' ? 'No CVs found' : 'Ready to create your first CV?'}
            description={
              searchQuery || selectedStatus !== 'all'
                ? 'Try adjusting your search or filters to find what you\'re looking for.'
                : 'Our AI will analyze job descriptions and intelligently match them with your professional artifacts to create targeted, ATS-optimized resumes that stand out.'
            }
            actionLabel={searchQuery || selectedStatus !== 'all' ? undefined : 'Generate Your First CV'}
            onAction={() => navigate('/generations/create')}
            theme={cvsTheme}
            showFiltered={searchQuery !== '' || selectedStatus !== 'all'}
          />
        )}
      </div>
    </div>
  )
}

interface GenerationCardProps {
  document: GeneratedDocument
  isSelected: boolean
  onToggleSelect: () => void
  onDelete: () => void
}

function GenerationCard({ document, isSelected, onToggleSelect, onDelete }: GenerationCardProps) {
  const [showExportDialog, setShowExportDialog] = useState(false)
  const navigate = useNavigate()

  return (
    <>
      <SelectableCard
        isSelected={isSelected}
        onToggleSelect={onToggleSelect}
        onClick={() => navigate(`/generations/${document.id}`)}
        icon={FileText}
        theme={cvsTheme}
        header={
          <>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-bold text-gray-900 text-lg truncate">
                {getGenerationTitle(document)}
              </h3>
              <GenerationStatusBadge document={document} />
            </div>
            <p className="text-sm text-gray-500 flex items-center gap-2">
              <span>{formatDate(document.createdAt)}</span>
            </p>
          </>
        }
        content={
          <>
            {/* Progress Indicator for In-Progress Generations (ft-026) */}
            {isInProgress(document.status) && (
              <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-3 w-3 text-blue-600 animate-spin" />
                    <span className="text-xs font-semibold text-blue-900">
                      {getPhaseDisplayText(document.currentPhase)}
                    </span>
                  </div>
                  <span className="text-xs font-bold text-blue-900">
                    {document.progressPercentage}%
                  </span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-1.5">
                  <div
                    className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${document.progressPercentage}%` }}
                  />
                </div>
                {document.phaseDetails?.bullet_generation && (
                  <p className="text-xs text-blue-700 mt-2">
                    {document.phaseDetails.bullet_generation.artifacts_processed} of{' '}
                    {document.phaseDetails.bullet_generation.artifacts_total} artifacts processed
                  </p>
                )}
              </div>
            )}

            {/* Metadata Section */}
            {document.metadata && document.metadata.artifactsUsed && (
              <div className="space-y-4 p-4 bg-gradient-to-br from-gray-50 to-gray-100/50 rounded-xl border border-gray-100">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-700">Match Score</span>
                    <div className="flex items-center gap-3">
                      <div className="w-20 h-3 bg-gray-200 rounded-full overflow-hidden shadow-inner">
                        <div
                          className={cn(
                            'h-full rounded-full transition-all duration-500 relative',
                            document.metadata.skillMatchScore >= 80
                              ? 'bg-gradient-to-r from-green-500 to-emerald-500'
                              : document.metadata.skillMatchScore >= 60
                              ? 'bg-gradient-to-r from-yellow-500 to-amber-500'
                              : 'bg-gradient-to-r from-red-500 to-rose-500'
                          )}
                          style={{ width: `${document.metadata.skillMatchScore}%` }}
                        >
                          <div className="absolute inset-0 bg-white/20 rounded-full" />
                        </div>
                      </div>
                      <span className="text-sm font-bold text-gray-900 min-w-[40px] text-right">
                        {document.metadata.skillMatchScore}%
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-700">Artifacts</span>
                    <span className="inline-flex items-center px-3 py-1.5 bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-800 text-xs font-bold rounded-full border border-blue-200">
                      {document.metadata.artifactsUsed.length} items
                    </span>
                  </div>
                </div>
              </div>
            )}
          </>
        }
        actions={
          <>
            <button
              className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
              title="Edit CV"
              onClick={(e) => {
                e.stopPropagation()
                navigate(`/generations/${document.id}`)
              }}
            >
              <Edit className="h-4 w-4" />
            </button>
            <button
              className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
              title="Export CV"
              onClick={(e) => {
                e.stopPropagation()
                setShowExportDialog(true)
              }}
            >
              <Download className="h-4 w-4" />
            </button>
            <button
              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
              title="Delete CV"
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
              }}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </>
        }
      />

      {showExportDialog && (
        <ExportDialog
          generationId={document.id}
          isOpen={showExportDialog}
          onClose={() => setShowExportDialog(false)}
          onExportComplete={() => setShowExportDialog(false)}
        />
      )}
    </>
  )
}

interface GenerationListItemProps {
  document: GeneratedDocument
  isSelected: boolean
  onToggleSelect: () => void
  onDelete: () => void
}

function GenerationListItem({ document, isSelected, onToggleSelect, onDelete }: GenerationListItemProps) {
  const [showExportDialog, setShowExportDialog] = useState(false)
  const navigate = useNavigate()

  return (
    <>
      <SelectableListItem
        isSelected={isSelected}
        onToggleSelect={onToggleSelect}
        onClick={() => navigate(`/generations/${document.id}`)}
        icon={FileText}
        theme={cvsTheme}
        header={
          <>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-gray-900 text-base leading-6">
                {getGenerationTitle(document)}
              </h3>
              <GenerationStatusBadge document={document} />
            </div>
            <p className="text-sm text-gray-500">{formatDate(document.createdAt)}</p>
          </>
        }
        content={
          <div className="space-y-3">
            {/* Progress Indicator for In-Progress Generations (ft-026) */}
            {isInProgress(document.status) && (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 min-w-[140px]">
                  <Loader2 className="h-3 w-3 text-blue-600 animate-spin flex-shrink-0" />
                  <span className="text-xs font-semibold text-blue-900">
                    {getPhaseDisplayText(document.currentPhase)}
                  </span>
                </div>
                <div className="flex-1 flex items-center gap-3">
                  <div className="flex-1 bg-blue-200 rounded-full h-1.5">
                    <div
                      className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${document.progressPercentage}%` }}
                    />
                  </div>
                  <span className="text-xs font-bold text-blue-900 min-w-[35px]">
                    {document.progressPercentage}%
                  </span>
                </div>
                {document.phaseDetails?.bullet_generation && (
                  <span className="text-xs text-blue-700 whitespace-nowrap">
                    {document.phaseDetails.bullet_generation.artifacts_processed} /{' '}
                    {document.phaseDetails.bullet_generation.artifacts_total} artifacts
                  </span>
                )}
              </div>
            )}

            {/* Metadata Section */}
            {document.metadata && document.metadata.artifactsUsed && (
              <div className="flex items-center gap-6 text-sm text-gray-600">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-700">Match:</span>
                  <span className="font-bold text-gray-900">{document.metadata.skillMatchScore}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-700">Artifacts:</span>
                  <span className="font-bold text-gray-900">{document.metadata.artifactsUsed.length}</span>
                </div>
                {document.metadata.modelUsed && (
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-700">Model:</span>
                    <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                      {document.metadata.modelUsed}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        }
        actions={
          <>
            <button
              className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
              title="Edit CV"
              onClick={(e) => {
                e.stopPropagation()
                navigate(`/generations/${document.id}`)
              }}
            >
              <Edit className="h-4 w-4" />
            </button>
            <button
              className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
              title="Export CV"
              onClick={(e) => {
                e.stopPropagation()
                setShowExportDialog(true)
              }}
            >
              <Download className="h-4 w-4" />
            </button>
            <button
              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
              title="Delete CV"
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
              }}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </>
        }
      />

      {showExportDialog && (
        <ExportDialog
          generationId={document.id}
          isOpen={showExportDialog}
          onClose={() => setShowExportDialog(false)}
          onExportComplete={() => setShowExportDialog(false)}
        />
      )}
    </>
  )
}
