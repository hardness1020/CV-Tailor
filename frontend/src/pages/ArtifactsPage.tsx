import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus,
  FileText,
  ExternalLink,
  Edit,
  Trash2,
  Github,
  Globe,
  Video,
  ArrowRight,
  FolderOpen,
  Play
} from 'lucide-react'
import { useArtifactStore } from '@/stores/artifactStore'
import { useArtifacts } from '@/hooks/useArtifacts'
import { useArtifactNavigation } from '@/hooks/useArtifactNavigation'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SelectionBar } from '@/components/ui/SelectionBar'
import { FilterBar } from '@/components/ui/FilterBar'
import { SelectableCard } from '@/components/ui/SelectableCard'
import { SelectableListItem } from '@/components/ui/SelectableListItem'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDateRange } from '@/utils/formatters'
import { artifactsTheme } from '@/utils/pageThemes'
import type { Artifact } from '@/types'

const evidenceTypeIcons = {
  github: Github,
  live_app: Globe,
  document: FileText,
  website: Globe,
  portfolio: ExternalLink,
  paper: FileText,
  video: Video,
  other: ExternalLink,
} as const

export default function ArtifactsPage() {
  const navigate = useNavigate()
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStatus, setSelectedStatus] = useState<'all' | 'active' | 'archived'>('all')

  const { selectedArtifacts, toggleSelection, clearSelection, artifacts } = useArtifactStore()
  const { isLoading, loadArtifacts, deleteArtifact, bulkDelete } = useArtifacts()
  const { navigateToArtifact } = useArtifactNavigation()

  // Memoize filters to prevent unnecessary re-renders
  const filters = useMemo(() => ({
    search: searchQuery || undefined,
    status: selectedStatus === 'all' ? undefined : selectedStatus,
  }), [searchQuery, selectedStatus])

  // Load artifacts on mount and when filters change
  useEffect(() => {
    loadArtifacts(filters)
  }, [filters]) // loadArtifacts is stable from Zustand, so we don't need it in dependencies

  const filteredArtifacts = artifacts.filter(artifact => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        artifact.title.toLowerCase().includes(query) ||
        artifact.description.toLowerCase().includes(query) ||
        (artifact.technologies || []).some(tech => tech.toLowerCase().includes(query))
      )
    }
    return true
  })

  const handleBulkDelete = async () => {
    if (selectedArtifacts.length === 0) return
    if (window.confirm(`Delete ${selectedArtifacts.length} selected artifacts?`)) {
      await bulkDelete(selectedArtifacts)
      clearSelection()
    }
  }

  const handleDelete = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this artifact?')) {
      await deleteArtifact(id)
    }
  }

  return (
    <>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        badgeIcon={FolderOpen}
        badgeText="Portfolio Management"
        title="Professional"
        titleHighlight="Artifacts"
        description="Manage your professional projects and documents with AI-powered insights."
        theme={artifactsTheme}
      >
        <Button
          onClick={() => navigate('/artifacts/upload')}
          className="group bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold px-6 py-3 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
        >
          <div className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            <span>Upload Artifact</span>
            <ArrowRight className="h-4 w-4 transform group-hover:translate-x-1 transition-transform duration-200" />
          </div>
        </Button>
      </PageHeader>

      {/* Filters and Search */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-300">
        <FilterBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          searchPlaceholder="Search by title, description, or technology..."
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          statusFilter={{
            value: selectedStatus,
            options: [
              { value: 'all', label: 'All Status' },
              { value: 'active', label: 'Active' },
              { value: 'archived', label: 'Archived' },
            ],
            onChange: (value) => setSelectedStatus(value as 'all' | 'active' | 'archived'),
          }}
          theme={artifactsTheme}
        />

        <SelectionBar
          selectedCount={selectedArtifacts.length}
          itemName="artifact"
          onClear={clearSelection}
          onDelete={handleBulkDelete}
          theme={artifactsTheme}
        />
      </div>

      {/* Artifacts Grid/List */}
      <div className="mt-6">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-sm text-gray-600">Loading artifacts...</p>
          </div>
        ) : filteredArtifacts.length > 0 ? (
          viewMode === 'grid' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
              {filteredArtifacts.map((artifact) => (
                <ArtifactCard
                  key={artifact.id}
                  artifact={artifact}
                  isSelected={selectedArtifacts.includes(artifact.id)}
                  onToggleSelect={() => toggleSelection(artifact.id)}
                  onDelete={() => handleDelete(artifact.id)}
                  onEdit={() => navigateToArtifact(artifact)}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {filteredArtifacts.map((artifact) => (
                <ArtifactListItem
                  key={artifact.id}
                  artifact={artifact}
                  isSelected={selectedArtifacts.includes(artifact.id)}
                  onToggleSelect={() => toggleSelection(artifact.id)}
                  onDelete={() => handleDelete(artifact.id)}
                  onEdit={() => navigateToArtifact(artifact)}
                />
              ))}
            </div>
          )
        ) : (
          <EmptyState
            title="No artifacts found"
            description={
              searchQuery || selectedStatus !== 'all'
                ? 'Try adjusting your search or filters to find what you\'re looking for.'
                : 'Get started by uploading your first project or document to build your portfolio.'
            }
            actionLabel={searchQuery || selectedStatus !== 'all' ? undefined : 'Upload First Artifact'}
            onAction={() => navigate('/artifacts/upload')}
            theme={artifactsTheme}
            showFiltered={searchQuery !== '' || selectedStatus !== 'all'}
          />
        )}
      </div>
      </div>
    </>
  )
}

interface ArtifactCardProps {
  artifact: Artifact
  isSelected: boolean
  onToggleSelect: () => void
  onDelete: () => void
  onEdit: () => void
}

function ArtifactCard({ artifact, isSelected, onToggleSelect, onEdit }: ArtifactCardProps) {
  return (
    <SelectableCard
      isSelected={isSelected}
      onToggleSelect={onToggleSelect}
      onClick={onEdit}
      icon={FileText}
      theme={artifactsTheme}
      header={
        <>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-gray-900 text-lg leading-6 truncate">{artifact.title}</h3>
            <StatusBadge status={artifact.status} size="sm" />
          </div>
          <p className="text-sm text-gray-500">{formatDateRange(artifact.startDate, artifact.endDate)}</p>
        </>
      }
      content={
        <>
          {/* Description */}
          <p className="text-sm text-gray-600 leading-relaxed line-clamp-2">{artifact.unifiedDescription}</p>

          {/* Technologies */}
          {(artifact.enrichedTechnologies?.length || 0) > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-4">
              {(artifact.enrichedTechnologies || []).slice(0, 4).map((tech) => (
                <span
                  key={tech}
                  className="inline-flex items-center px-2.5 py-1 bg-gray-100 text-xs font-medium text-gray-700 rounded-full"
                >
                  {tech}
                </span>
              ))}
              {(artifact.enrichedTechnologies?.length || 0) > 4 && (
                <span className="inline-flex items-center px-2.5 py-1 bg-gray-100 text-xs font-medium text-gray-500 rounded-full">
                  +{(artifact.enrichedTechnologies?.length || 0) - 4} more
                </span>
              )}
            </div>
          )}
        </>
      }
      footer={
        <div className="p-4 bg-gradient-to-br from-gray-50 to-purple-50/30 rounded-xl border border-purple-100">
          <div className="flex items-center justify-between">
            {/* Evidence Links */}
            <div className="flex items-center gap-2">
              {(artifact.evidenceLinks || []).slice(0, 4).map((link, index) => {
                const Icon = evidenceTypeIcons[link.evidenceType] || ExternalLink
                return (
                  <div
                    key={index}
                    className="p-1.5 bg-white hover:bg-gray-50 rounded-md transition-colors shadow-sm"
                    title={link.description}
                  >
                    <Icon className="h-3.5 w-3.5 text-gray-600" />
                  </div>
                )
              })}
              {(artifact.evidenceLinks?.length || 0) > 4 && (
                <span className="text-xs text-gray-500 font-medium ml-1">
                  +{(artifact.evidenceLinks?.length || 0) - 4}
                </span>
              )}
            </div>
          </div>
        </div>
      }
    />
  )
}

interface ArtifactListItemProps {
  artifact: Artifact
  isSelected: boolean
  onToggleSelect: () => void
  onDelete: () => void
  onEdit: () => void
}

function ArtifactListItem({ artifact, isSelected, onToggleSelect, onDelete, onEdit }: ArtifactListItemProps) {
  return (
    <SelectableListItem
      isSelected={isSelected}
      onToggleSelect={onToggleSelect}
      onClick={onEdit}
      icon={FileText}
      theme={artifactsTheme}
      header={
        <>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-gray-900 text-base leading-6 truncate">{artifact.title}</h3>
            <StatusBadge status={artifact.status} size="sm" />
          </div>
          <p className="text-sm text-gray-500">{formatDateRange(artifact.startDate, artifact.endDate)}</p>
        </>
      }
      content={
        <>
          {/* Description */}
          <p className="text-sm text-gray-600 leading-relaxed mb-4 line-clamp-2">{artifact.unifiedDescription}</p>

          {/* Footer */}
          <div className="flex items-center justify-between">
            {/* Technologies */}
            <div className="flex flex-wrap gap-1.5">
              {(artifact.enrichedTechnologies || []).slice(0, 5).map((tech) => (
                <span
                  key={tech}
                  className="inline-flex items-center px-2.5 py-1 bg-gray-100 text-xs font-medium text-gray-700 rounded-full"
                >
                  {tech}
                </span>
              ))}
              {(artifact.enrichedTechnologies?.length || 0) > 5 && (
                <span className="inline-flex items-center px-2.5 py-1 bg-gray-100 text-xs font-medium text-gray-500 rounded-full">
                  +{(artifact.enrichedTechnologies?.length || 0) - 5}
                </span>
              )}
            </div>

            {/* Metadata */}
            <div className="flex items-center gap-4 text-sm text-gray-500">
              {(artifact.evidenceLinks?.length || 0) > 0 && (
                <span className="flex items-center gap-1.5">
                  <ExternalLink className="h-3.5 w-3.5" />
                  <span className="font-medium">
                    {artifact.evidenceLinks?.length} link{artifact.evidenceLinks?.length !== 1 ? 's' : ''}
                  </span>
                </span>
              )}
            </div>
          </div>
        </>
      }
      actions={
        <>
          {artifact.status !== 'complete' && (
            <button
              className="p-2 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
              title="Resume wizard"
              onClick={(e) => {
                e.stopPropagation()
                onEdit()
              }}
            >
              <Play className="h-4 w-4" />
            </button>
          )}
          <button
            className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
            title={artifact.status === 'complete' ? 'Edit artifact' : 'Resume wizard'}
            onClick={(e) => {
              e.stopPropagation()
              onEdit()
            }}
          >
            <Edit className="h-4 w-4" />
          </button>
          <button
            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
            title="Delete artifact"
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
  )
}