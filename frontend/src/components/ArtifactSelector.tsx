import React, { useState, useEffect, useMemo } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { apiClient } from '@/services/apiClient'
import { Search, AlertCircle } from 'lucide-react'
import { cn } from '@/utils/cn'

interface ArtifactSuggestion {
  id: number
  title: string
  description: string
  technologies: string[]
  enriched_technologies: string[]
  relevance_score: number
  exact_matches: number
  partial_matches: number
  fuzzy_matches: number
  matched_keywords: string[]
  start_date?: string
  end_date?: string
  artifact_type: string
}

interface ArtifactSelectorProps {
  jobDescription: string
  onSelectionChange: (artifactIds: number[]) => void
  initialSelection?: number[]
}

export const ArtifactSelector: React.FC<ArtifactSelectorProps> = ({
  jobDescription,
  onSelectionChange,
  initialSelection = []
}) => {
  const [artifacts, setArtifacts] = useState<ArtifactSuggestion[]>([])
  const [selectedIds, setSelectedIds] = useState<number[]>(initialSelection)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'relevance' | 'date' | 'title'>('relevance')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch artifacts on mount
  useEffect(() => {
    const fetchArtifacts = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await apiClient.suggestArtifactsForJob(jobDescription, 10)

        setArtifacts(response.artifacts)

        // Auto-select top 5 artifacts if no initial selection provided
        if (initialSelection.length === 0 && response.artifacts.length > 0) {
          const topFive = response.artifacts.slice(0, 5).map(a => a.id)
          setSelectedIds(topFive)
          onSelectionChange(topFive)
        } else if (initialSelection.length > 0) {
          setSelectedIds(initialSelection)
        }
      } catch (err) {
        setError('Failed to fetch artifact suggestions. Please try again.')
        console.error('Error fetching artifacts:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchArtifacts()
  }, [jobDescription]) // Note: onSelectionChange and initialSelection are intentionally not in deps

  // Filter and sort artifacts
  const filteredAndSortedArtifacts = useMemo(() => {
    let result = [...artifacts]

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        artifact =>
          artifact.title.toLowerCase().includes(query) ||
          artifact.description.toLowerCase().includes(query) ||
          artifact.technologies.some(tech => tech.toLowerCase().includes(query))
      )
    }

    // Apply sorting
    result.sort((a, b) => {
      switch (sortBy) {
        case 'relevance':
          return b.relevance_score - a.relevance_score
        case 'date':
          const dateA = a.end_date || a.start_date || '0000-00-00'
          const dateB = b.end_date || b.start_date || '0000-00-00'
          return dateB.localeCompare(dateA)
        case 'title':
          return a.title.localeCompare(b.title)
        default:
          return 0
      }
    })

    return result
  }, [artifacts, searchQuery, sortBy])

  // Handle selection toggle
  const handleToggleSelection = (artifactId: number) => {
    const newSelection = selectedIds.includes(artifactId)
      ? selectedIds.filter(id => id !== artifactId)
      : [...selectedIds, artifactId]

    setSelectedIds(newSelection)
    onSelectionChange(newSelection)
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-600">Loading artifact suggestions...</p>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <Card className="p-6 border-red-200 bg-red-50">
        <div className="flex items-center space-x-3 mb-4">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <h3 className="font-semibold text-red-900">Error Loading Artifacts</h3>
        </div>
        <p className="text-red-800 mb-4">{error}</p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => window.location.reload()}
        >
          Retry
        </Button>
      </Card>
    )
  }

  // Empty state
  if (artifacts.length === 0) {
    return (
      <Card className="p-8 text-center">
        <div className="flex flex-col items-center space-y-3">
          <AlertCircle className="h-12 w-12 text-gray-400" />
          <h3 className="text-lg font-medium text-gray-900">No Matches Found</h3>
          <p className="text-gray-600 max-w-md">
            No artifacts match this job description. Try uploading more work experiences
            or projects to get better suggestions.
          </p>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header with search and sort */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search artifacts by title or technology..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
              />
            </div>
          </div>

          {/* Sort */}
          <div className="sm:w-48">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'relevance' | 'date' | 'title')}
              aria-label="Sort by"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
            >
              <option value="relevance">Sort by Relevance</option>
              <option value="date">Sort by Date</option>
              <option value="title">Sort by Title</option>
            </select>
          </div>
        </div>

        {/* Selection count */}
        <div className="mt-3 text-sm text-gray-600">
          {selectedIds.length} artifact{selectedIds.length !== 1 ? 's' : ''} selected
        </div>
      </Card>

      {/* Artifact list */}
      <div className="space-y-3">
        {filteredAndSortedArtifacts.map((artifact) => {
          const isSelected = selectedIds.includes(artifact.id)
          const relevancePercent = Math.round(artifact.relevance_score * 100)

          return (
            <Card
              key={artifact.id}
              className={cn(
                'p-4 cursor-pointer transition-all hover:shadow-md',
                isSelected && 'ring-2 ring-purple-500 bg-purple-50'
              )}
              onClick={() => handleToggleSelection(artifact.id)}
            >
              <div className="flex items-start space-x-4">
                {/* Checkbox */}
                <div className="flex-shrink-0 pt-1">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleToggleSelection(artifact.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="h-5 w-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 cursor-pointer"
                  />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <h3 className="font-semibold text-gray-900">{artifact.title}</h3>
                      <p className="text-sm text-gray-600 mt-1">{artifact.description}</p>
                    </div>
                    {/* Relevance score badge */}
                    <div className="flex-shrink-0">
                      <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                        {relevancePercent}% match
                      </div>
                    </div>
                  </div>

                  {/* Matched keywords */}
                  {artifact.matched_keywords && artifact.matched_keywords.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {artifact.matched_keywords.map((keyword, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Technologies (excluding matched keywords to avoid duplication) */}
                  {artifact.technologies && artifact.technologies.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {artifact.technologies
                        .filter(tech => !artifact.matched_keywords?.includes(tech))
                        .map((tech, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700"
                          >
                            {tech}
                          </span>
                        ))}
                    </div>
                  )}

                  {/* Match details */}
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    {artifact.exact_matches > 0 && (
                      <span>{artifact.exact_matches} exact match{artifact.exact_matches !== 1 ? 'es' : ''}</span>
                    )}
                    {artifact.partial_matches > 0 && (
                      <span>{artifact.partial_matches} partial match{artifact.partial_matches !== 1 ? 'es' : ''}</span>
                    )}
                    {artifact.fuzzy_matches > 0 && (
                      <span>{artifact.fuzzy_matches} fuzzy match{artifact.fuzzy_matches !== 1 ? 'es' : ''}</span>
                    )}
                    {artifact.start_date && (
                      <span>
                        {new Date(artifact.start_date).getFullYear()}
                        {artifact.end_date && ` - ${new Date(artifact.end_date).getFullYear()}`}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* No results message for filtered list */}
      {filteredAndSortedArtifacts.length === 0 && artifacts.length > 0 && (
        <Card className="p-6 text-center">
          <p className="text-gray-600">
            No artifacts match your search. Try a different search term.
          </p>
        </Card>
      )}
    </div>
  )
}
