/**
 * ConsolidatedReunificationStep component (6-step wizard consolidation)
 * Combines old Step 8 (Finalization) + Step 9 (Artifact Acceptance) into single step
 *
 * Flow:
 * 1. Show "Finalizing your artifact..." spinner (polls every 3s for status='review_finalized')
 * 2. Auto-transition to acceptance UI when status='review_finalized'
 * 3. User reviews unified_description, enriched_technologies, enriched_achievements
 * 4. User clicks "Accept Artifact" to set status='complete' and complete wizard
 */

import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import apiClient from '@/services/apiClient'
import { CheckCircle2, Sparkles, Code, Award, Loader2, Edit, Edit2, Save, X, Plus } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import type { Artifact } from '@/types'
import { toast } from 'react-hot-toast'

type ReunificationState = 'finalizing' | 'accepting'

export interface ConsolidatedReunificationStepProps {
  artifactId: string
  onAcceptComplete?: () => void // Called after artifact is accepted
  onError: (error: string) => void
}

export const ConsolidatedReunificationStep: React.FC<ConsolidatedReunificationStepProps> = ({
  artifactId,
  onAcceptComplete,
  onError
}) => {
  const navigate = useNavigate()
  const [reunificationState, setReunificationState] = useState<ReunificationState>('finalizing')
  const [artifact, setArtifact] = useState<Artifact | null>(null)
  const [isAccepting, setIsAccepting] = useState(false)

  // Per-section edit mode state
  const [editingSection, setEditingSection] = useState<'description' | 'technologies' | 'achievements' | null>(null)
  const [isSavingSection, setIsSavingSection] = useState<'description' | 'technologies' | 'achievements' | null>(null)
  const [editedDescription, setEditedDescription] = useState('')
  const [editedTechnologies, setEditedTechnologies] = useState<string[]>([])
  const [editedAchievements, setEditedAchievements] = useState<string[]>([])
  const [newTech, setNewTech] = useState('')
  const [newAchievement, setNewAchievement] = useState('')

  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const mountedRef = useRef(true)

  // Poll artifact status (for reunifying state)
  useEffect(() => {
    mountedRef.current = true

    const pollStatus = async () => {
      if (!mountedRef.current) return

      try {
        const fetchedArtifact = await apiClient.getArtifact(parseInt(artifactId))
        const status = (fetchedArtifact as any).status

        if (reunificationState === 'finalizing') {
          if (status === 'review_finalized') {
            // Finalization complete - transition to acceptance UI
            if (intervalRef.current) {
              clearInterval(intervalRef.current)
              intervalRef.current = null
            }
            console.log('[ConsolidatedReunificationStep] Finalization complete, showing acceptance UI')
            setArtifact(fetchedArtifact)
            setReunificationState('accepting')
          } else if (status === 'review_pending') {
            // Finalization failed - reverted to review_pending
            if (intervalRef.current) {
              clearInterval(intervalRef.current)
              intervalRef.current = null
            }
            console.error('[ConsolidatedReunificationStep] Finalization failed')
            onError('Finalization failed. Please go back and try again.')
          } else if (status === 'reunifying') {
            // Still finalizing - continue polling
            console.log('[ConsolidatedReunificationStep] Finalization in progress...')
          }
        }
      } catch (error: any) {
        console.error('[ConsolidatedReunificationStep] Polling error:', error)
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        onError(error.message || 'Network error during finalization')
      }
    }

    // Only poll if we're in finalizing state
    if (reunificationState === 'finalizing') {
      // Poll immediately on mount
      pollStatus()

      // Then poll every 3 seconds
      intervalRef.current = setInterval(pollStatus, 3000)
    }

    // Cleanup on unmount
    return () => {
      mountedRef.current = false
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [artifactId, reunificationState, onError])

  // Keyboard shortcuts for edit mode (per-section)
  useEffect(() => {
    if (editingSection === null) return

    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + S to save current section
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        if (isSavingSection === null) {
          handleSaveEdit(editingSection)
        }
      }
      // Escape to cancel current section
      if (e.key === 'Escape') {
        handleCancelEdit(editingSection)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [editingSection, isSavingSection])

  // Handle entering edit mode for a specific section
  const handleStartEdit = (section: 'description' | 'technologies' | 'achievements') => {
    if (!artifact) return

    // Populate edited state for the specific section
    if (section === 'description') {
      setEditedDescription(artifact.unifiedDescription || '')
    } else if (section === 'technologies') {
      setEditedTechnologies([...(artifact.enrichedTechnologies || [])])
    } else if (section === 'achievements') {
      setEditedAchievements([...(artifact.enrichedAchievements || [])])
    }

    setEditingSection(section)
  }

  // Handle canceling edits for a specific section
  const handleCancelEdit = (section: 'description' | 'technologies' | 'achievements') => {
    // Clear edited state for the specific section
    if (section === 'description') {
      setEditedDescription('')
    } else if (section === 'technologies') {
      setEditedTechnologies([])
      setNewTech('')
    } else if (section === 'achievements') {
      setEditedAchievements([])
      setNewAchievement('')
    }

    setEditingSection(null)
  }

  // Handle saving edits for a specific section
  const handleSaveEdit = async (section: 'description' | 'technologies' | 'achievements') => {
    if (!artifact) return

    setIsSavingSection(section)

    try {
      // Build update payload for only the edited section
      const updatePayload: any = {}

      if (section === 'description') {
        updatePayload.unifiedDescription = editedDescription
      } else if (section === 'technologies') {
        updatePayload.enrichedTechnologies = editedTechnologies
      } else if (section === 'achievements') {
        updatePayload.enrichedAchievements = editedAchievements
      }

      // Note: TypeScript type for updateArtifact expects ArtifactCreateData, but backend API
      // also accepts enriched fields (unifiedDescription, enrichedTechnologies, enrichedAchievements)
      await apiClient.updateArtifact(artifact.id, updatePayload)

      // Refresh artifact data
      const updatedArtifact = await apiClient.getArtifact(artifact.id)
      setArtifact(updatedArtifact)

      // Exit edit mode for this section
      setEditingSection(null)

      // Show section-specific success message
      const sectionName = section.charAt(0).toUpperCase() + section.slice(1)
      toast.success(`${sectionName} saved successfully`, {
        duration: 3000,
        icon: '✅',
        style: {
          background: 'linear-gradient(to right, #10b981, #059669)',
          color: '#fff',
          fontWeight: '600'
        }
      })
    } catch (error: any) {
      console.error(`[ConsolidatedReunificationStep] Failed to save ${section}:`, error)
      const sectionName = section.charAt(0).toUpperCase() + section.slice(1)
      const errorMessage = `Failed to save ${sectionName}. Please try again.`
      toast.error(errorMessage, {
        duration: 4000,
        icon: '❌'
      })
    } finally {
      setIsSavingSection(null)
    }
  }

  // Handle artifact acceptance
  const handleAcceptArtifact = async () => {
    setIsAccepting(true)
    try {
      await apiClient.acceptArtifact(parseInt(artifactId))
      console.log('[ConsolidatedReunificationStep] Artifact accepted, navigating to detail page')

      if (onAcceptComplete) {
        onAcceptComplete()
      } else {
        navigate(`/artifacts/${artifactId}`)
      }
    } catch (error: any) {
      console.error('[ConsolidatedReunificationStep] Failed to accept artifact:', error)
      onError(error.response?.data?.error || error.message || 'Failed to accept artifact')
      setIsAccepting(false)
    }
  }

  // Render finalizing spinner
  if (reunificationState === 'finalizing') {
    return (
      <div role="status" className="flex flex-col items-center justify-center min-h-[400px] space-y-6">
        <div className="relative">
          <Sparkles className="h-16 w-16 text-purple-600 animate-pulse" />
        </div>

        <div className="text-center space-y-2">
          <p className="text-lg font-semibold text-gray-900">
            Finalizing your artifact...
          </p>
          <p className="text-sm text-gray-500">
            This usually takes 30-45 seconds
          </p>
        </div>

        <div className="flex items-center gap-2 px-4 py-3 bg-purple-50 border border-purple-200 rounded-lg">
          <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></div>
          <p className="text-sm text-purple-700 font-medium">
            You'll review and accept your artifact shortly
          </p>
        </div>
      </div>
    )
  }

  // Render acceptance UI (reunificationState === 'accepting')
  if (!artifact) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600 mb-4" />
        <p className="text-sm text-gray-600">Loading artifact data...</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-gradient-to-br from-green-100 to-emerald-100 rounded-2xl">
            <CheckCircle2 className="h-8 w-8 text-green-600" />
          </div>
          <div>
            <h2 className="text-3xl font-bold text-gray-900">Review Your Artifact</h2>
            <p className="text-sm text-gray-600 mt-1">
              Edit sections individually, then accept when ready
            </p>
          </div>
        </div>

        {/* Active editing indicator */}
        {editingSection && (
          <div className="mt-4 flex items-center gap-2 px-4 py-2 bg-purple-50 border border-purple-200 rounded-lg text-sm text-purple-700">
            <Edit className="h-4 w-4" />
            <span>Editing: {editingSection.charAt(0).toUpperCase() + editingSection.slice(1)}</span>
            <kbd className="ml-auto px-2 py-1 bg-white border border-purple-300 rounded shadow-sm font-mono text-xs">
              ⌘/Ctrl+S
            </kbd>
            <span className="text-xs">to save</span>
            <kbd className="px-2 py-1 bg-white border border-purple-300 rounded shadow-sm font-mono text-xs">
              Esc
            </kbd>
            <span className="text-xs">to cancel</span>
          </div>
        )}
      </div>

      {/* Unified Description */}
      {(artifact.unifiedDescription || editingSection === 'description') && (
        <div className={`mb-6 bg-white rounded-xl border shadow-sm overflow-hidden transition-all duration-300 ${
          editingSection === 'description'
            ? 'border-purple-300 border-2 shadow-xl shadow-purple-200/50 ring-4 ring-purple-100/50'
            : 'border-gray-200'
        }`}>
          <div className="bg-gradient-to-r from-purple-50 to-pink-50 px-6 py-4 border-b border-purple-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-purple-600" />
                <h3 className="font-semibold text-gray-900">AI-Generated Description</h3>
              </div>

              {/* Per-section Edit/Save/Cancel */}
              <div className="flex gap-2">
                {editingSection === 'description' ? (
                  <>
                    <button
                      type="button"
                      onClick={() => handleCancelEdit('description')}
                      disabled={isSavingSection === 'description'}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                    >
                      <X className="h-4 w-4" />
                      <span>Cancel</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSaveEdit('description')}
                      disabled={isSavingSection === 'description'}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 shadow-sm hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSavingSection === 'description' ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                          <span className="font-medium">Saving...</span>
                        </>
                      ) : (
                        <>
                          <Save className="h-4 w-4" />
                          <span className="font-medium">Save</span>
                        </>
                      )}
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleStartEdit('description')}
                    disabled={editingSection !== null}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-purple-700 bg-white border border-purple-200 rounded-lg hover:bg-purple-50 hover:border-purple-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                    title={editingSection !== null ? `Finish editing ${editingSection} first` : 'Edit description'}
                  >
                    <Edit2 className="h-4 w-4" />
                    <span className="font-medium">Edit</span>
                  </button>
                )}
              </div>
            </div>

            {/* Editing indicator badge */}
            {editingSection === 'description' && (
              <div className="mt-2 flex items-center gap-2 px-3 py-1 bg-purple-600 text-white text-xs font-medium rounded-full shadow-sm w-fit">
                <Edit className="h-3 w-3 animate-pulse" />
                <span>Editing</span>
              </div>
            )}
          </div>
          <div className="p-6">
            {editingSection === 'description' ? (
              <textarea
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                className="w-full min-h-[300px] p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent focus:shadow-lg focus:shadow-purple-200/50 resize-y transition-all duration-200"
                placeholder="Enter unified description..."
                rows={12}
              />
            ) : (
              <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">
                {artifact.unifiedDescription}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Enriched Technologies */}
      {((artifact.enrichedTechnologies && artifact.enrichedTechnologies.length > 0) || editingSection === 'technologies') && (
        <div className={`mb-6 bg-white rounded-xl border shadow-sm overflow-hidden transition-all duration-300 ${
          editingSection === 'technologies'
            ? 'border-purple-300 border-2 shadow-xl shadow-purple-200/50 ring-4 ring-purple-100/50'
            : 'border-gray-200'
        }`}>
          <div className="bg-gradient-to-r from-blue-50 to-cyan-50 px-6 py-4 border-b border-blue-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Code className="h-5 w-5 text-blue-600" />
                <h3 className="font-semibold text-gray-900">
                  Technologies ({editingSection === 'technologies' ? editedTechnologies.length : artifact.enrichedTechnologies?.length || 0})
                </h3>
              </div>

              {/* Per-section Edit/Save/Cancel */}
              <div className="flex gap-2">
                {editingSection === 'technologies' ? (
                  <>
                    <button
                      type="button"
                      onClick={() => handleCancelEdit('technologies')}
                      disabled={isSavingSection === 'technologies'}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                    >
                      <X className="h-4 w-4" />
                      <span>Cancel</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSaveEdit('technologies')}
                      disabled={isSavingSection === 'technologies'}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg hover:from-purple-700 hover:to-blue-700 shadow-sm hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSavingSection === 'technologies' ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                          <span className="font-medium">Saving...</span>
                        </>
                      ) : (
                        <>
                          <Save className="h-4 w-4" />
                          <span className="font-medium">Save</span>
                        </>
                      )}
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleStartEdit('technologies')}
                    disabled={editingSection !== null}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-purple-700 bg-white border border-purple-200 rounded-lg hover:bg-purple-50 hover:border-purple-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                    title={editingSection !== null ? `Finish editing ${editingSection} first` : 'Edit technologies'}
                  >
                    <Edit2 className="h-4 w-4" />
                    <span className="font-medium">Edit</span>
                  </button>
                )}
              </div>
            </div>

            {/* Editing indicator badge */}
            {editingSection === 'technologies' && (
              <div className="mt-2 flex items-center gap-2 px-3 py-1 bg-purple-600 text-white text-xs font-medium rounded-full shadow-sm w-fit">
                <Edit className="h-3 w-3 animate-pulse" />
                <span>Editing</span>
              </div>
            )}
          </div>
          <div className="p-6">
            {editingSection === 'technologies' ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2 mb-3">
                  {editedTechnologies.map((tech, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-100 text-blue-800 text-sm font-medium rounded-full border border-blue-200"
                    >
                      {tech}
                      <button
                        type="button"
                        onClick={() => setEditedTechnologies(editedTechnologies.filter((_, i) => i !== index))}
                        className="ml-1 text-blue-600 hover:text-blue-800 hover:bg-blue-200 rounded-full p-0.5 transition-all duration-150 transform hover:scale-110"
                        title="Remove technology"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newTech}
                    onChange={(e) => setNewTech(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && newTech.trim()) {
                        setEditedTechnologies([...editedTechnologies, newTech.trim()])
                        setNewTech('')
                      }
                    }}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent focus:shadow-lg focus:shadow-purple-200/50 transition-all duration-200"
                    placeholder="Add technology (press Enter)"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (newTech.trim()) {
                        setEditedTechnologies([...editedTechnologies, newTech.trim()])
                        setNewTech('')
                      }
                    }}
                    disabled={!newTech.trim()}
                    className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg hover:from-purple-700 hover:to-blue-700 shadow-sm hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-[1.02]"
                  >
                    <Plus className="h-4 w-4" />
                    <span className="font-medium">Add</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {artifact.enrichedTechnologies?.map((tech, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-3 py-1.5 bg-blue-100 text-blue-800 text-sm font-medium rounded-full border border-blue-200"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Enriched Achievements */}
      {((artifact.enrichedAchievements && artifact.enrichedAchievements.length > 0) || editingSection === 'achievements') && (
        <div className={`mb-6 bg-white rounded-xl border shadow-sm overflow-hidden transition-all duration-300 ${
          editingSection === 'achievements'
            ? 'border-purple-300 border-2 shadow-xl shadow-purple-200/50 ring-4 ring-purple-100/50'
            : 'border-gray-200'
        }`}>
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 px-6 py-4 border-b border-amber-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Award className="h-5 w-5 text-amber-600" />
                <h3 className="font-semibold text-gray-900">
                  Key Achievements ({editingSection === 'achievements' ? editedAchievements.length : artifact.enrichedAchievements?.length || 0})
                </h3>
              </div>

              {/* Per-section Edit/Save/Cancel */}
              <div className="flex gap-2">
                {editingSection === 'achievements' ? (
                  <>
                    <button
                      type="button"
                      onClick={() => handleCancelEdit('achievements')}
                      disabled={isSavingSection === 'achievements'}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                    >
                      <X className="h-4 w-4" />
                      <span>Cancel</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSaveEdit('achievements')}
                      disabled={isSavingSection === 'achievements'}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-gradient-to-r from-amber-500 to-orange-500 rounded-lg hover:from-amber-600 hover:to-orange-600 shadow-sm hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSavingSection === 'achievements' ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                          <span className="font-medium">Saving...</span>
                        </>
                      ) : (
                        <>
                          <Save className="h-4 w-4" />
                          <span className="font-medium">Save</span>
                        </>
                      )}
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleStartEdit('achievements')}
                    disabled={editingSection !== null}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-purple-700 bg-white border border-purple-200 rounded-lg hover:bg-purple-50 hover:border-purple-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                    title={editingSection !== null ? `Finish editing ${editingSection} first` : 'Edit achievements'}
                  >
                    <Edit2 className="h-4 w-4" />
                    <span className="font-medium">Edit</span>
                  </button>
                )}
              </div>
            </div>

            {/* Editing indicator badge */}
            {editingSection === 'achievements' && (
              <div className="mt-2 flex items-center gap-2 px-3 py-1 bg-purple-600 text-white text-xs font-medium rounded-full shadow-sm w-fit">
                <Edit className="h-3 w-3 animate-pulse" />
                <span>Editing</span>
              </div>
            )}
          </div>
          <div className="p-6">
            {editingSection === 'achievements' ? (
              <div className="space-y-3">
                <ul className="space-y-3 mb-4">
                  {editedAchievements.map((achievement, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-amber-500 to-orange-500 text-white text-xs font-bold flex items-center justify-center mt-2 shadow-sm">
                        {index + 1}
                      </span>
                      <input
                        type="text"
                        value={achievement}
                        onChange={(e) => {
                          const updated = [...editedAchievements]
                          updated[index] = e.target.value
                          setEditedAchievements(updated)
                        }}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent focus:shadow-lg focus:shadow-purple-200/50 transition-all duration-200"
                      />
                      <button
                        type="button"
                        onClick={() => setEditedAchievements(editedAchievements.filter((_, i) => i !== index))}
                        className="flex-shrink-0 p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-all duration-150 transform hover:scale-110"
                        title="Remove achievement"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </li>
                  ))}
                </ul>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newAchievement}
                    onChange={(e) => setNewAchievement(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && newAchievement.trim()) {
                        setEditedAchievements([...editedAchievements, newAchievement.trim()])
                        setNewAchievement('')
                      }
                    }}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent focus:shadow-lg focus:shadow-purple-200/50 transition-all duration-200"
                    placeholder="Add achievement (press Enter)"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (newAchievement.trim()) {
                        setEditedAchievements([...editedAchievements, newAchievement.trim()])
                        setNewAchievement('')
                      }
                    }}
                    disabled={!newAchievement.trim()}
                    className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg hover:from-amber-600 hover:to-orange-600 shadow-sm hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-[1.02]"
                  >
                    <Plus className="h-4 w-4" />
                    <span className="font-medium">Add</span>
                  </button>
                </div>
              </div>
            ) : (
              <ul className="space-y-3">
                {artifact.enrichedAchievements?.map((achievement, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 text-xs font-semibold flex items-center justify-center mt-0.5">
                      {index + 1}
                    </span>
                    <span className="text-gray-800 leading-relaxed">{achievement}</span>
                  </li>
                ))}
              </ul>
            )}
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
        <div className="relative">
          <Button
            onClick={handleAcceptArtifact}
            disabled={isAccepting || editingSection !== null}
            className="group bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            title={editingSection !== null ? `Finish editing ${editingSection} before accepting` : ''}
          >
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5" />
              <span className="text-lg">
                {isAccepting ? 'Accepting...' : 'Accept Artifact'}
              </span>
            </div>
          </Button>
          {editingSection !== null && (
            <p className="mt-2 text-sm text-amber-600 text-center">
              Finish editing {editingSection} before accepting
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
