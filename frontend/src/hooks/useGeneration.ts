import { useEffect } from 'react'
import toast from 'react-hot-toast'
import { useGenerationStore } from '@/stores/generationStore'
import { apiClient } from '@/services/apiClient'
import type { GenerationRequest } from '@/types'

export function useGeneration() {
  const {
    activeGenerations,
    completedDocuments,
    selectedDocuments,
    isGenerating,
    startGeneration,
    updateGeneration,
    completeGeneration,
    removeGeneration,
    toggleSelection,
    clearSelection,
    deleteDocument: deleteDocumentFromStore,
    bulkDelete: bulkDeleteFromStore,
  } = useGenerationStore()

  // Note: Polling is now handled by useGenerationStatus hook (consolidated pattern)

  const createGeneration = async (request: GenerationRequest) => {
    try {
      const response = await apiClient.createGeneration(request)
      const generationId = response.generationId

      // Start tracking the generation
      startGeneration(generationId, 'cv')

      // Note: Polling is now handled by useGenerationStatus hook in the calling component

      toast.success('Generation started!')
      return generationId
    } catch (error) {
      console.error('Failed to start generation:', error)
      toast.error('Failed to start generation')
      throw error
    }
  }

  const generateCoverLetter = async (request: Omit<GenerationRequest, 'templateId'>) => {
    try {
      const response = await apiClient.generateCoverLetter(request)
      const generationId = response.generationId

      // Start tracking the generation
      startGeneration(generationId, 'cover_letter')

      // Note: Polling is now handled by useGenerationStatus hook in the calling component

      toast.success('Cover letter generation started!')
      return generationId
    } catch (error) {
      console.error('Failed to start cover letter generation:', error)
      toast.error('Failed to start cover letter generation')
      throw error
    }
  }

  const cancelGeneration = (generationId: string) => {
    // Remove from store
    removeGeneration(generationId)
    toast.success('Generation cancelled')
  }

  const rateGeneration = async (generationId: string, rating: number, feedback?: string) => {
    try {
      await apiClient.rateGeneration(generationId, rating, feedback)
      toast.success('Thank you for your feedback!')
    } catch (error) {
      console.error('Failed to rate generation:', error)
      toast.error('Failed to submit rating')
      throw error
    }
  }

  // Two-phase workflow methods (ft-009)
  const getBullets = async (generationId: string) => {
    try {
      const bullets = await apiClient.getGenerationBullets(generationId)
      return bullets
    } catch (error) {
      console.error('Failed to get bullets:', error)
      toast.error('Failed to load bullets')
      throw error
    }
  }

  const editBullet = async (generationId: string, bulletId: number, text: string) => {
    try {
      const result = await apiClient.editGenerationBullet(generationId, bulletId, text)
      return result.bullet
    } catch (error) {
      console.error('Failed to edit bullet:', error)
      toast.error('Failed to edit bullet')
      throw error
    }
  }

  const approveBullets = async (generationId: string) => {
    try {
      const result = await apiClient.approveGenerationBullets(generationId)
      toast.success('Bullets approved! Assembling your document...')

      // Note: Calling component should resume polling via useGenerationStatus

      return result
    } catch (error) {
      console.error('Failed to approve bullets:', error)
      toast.error('Failed to approve bullets')
      throw error
    }
  }

  const assembleFinalGeneration = async (generationId: string) => {
    try {
      const result = await apiClient.assembleGeneration(generationId)
      toast.success('Document assembly started!')

      // Note: Calling component should handle polling via useGenerationStatus

      return result
    } catch (error) {
      console.error('Failed to assemble document:', error)
      toast.error('Failed to assemble document')
      throw error
    }
  }

  const loadUserGenerations = async () => {
    try {
      const generations = await apiClient.getUserGenerations()
      // Add generations to store
      generations.forEach(generation => {
        if (generation.status === 'completed') {
          completeGeneration(generation.id, generation)
        } else {
          // Add to store, polling handled by individual pages via useGenerationStatus
          updateGeneration(generation.id, generation)
        }
      })
    } catch (error) {
      console.error('Failed to load user generations:', error)
    }
  }

  // Note: Polling cleanup is now handled by useGenerationStatus hook

  // Load user generations on mount
  useEffect(() => {
    loadUserGenerations()
  }, [])

  const deleteDocument = async (id: string) => {
    try {
      await apiClient.deleteGeneration(id)
      deleteDocumentFromStore(id)
      toast.success('Document deleted successfully')
    } catch (error) {
      console.error('Failed to delete document:', error)
      toast.error('Failed to delete document')
      throw error
    }
  }

  const bulkDeleteDocuments = async (ids: string[]) => {
    try {
      await apiClient.bulkDeleteGenerations(ids)
      bulkDeleteFromStore(ids)
      toast.success(`${ids.length} document${ids.length > 1 ? 's' : ''} deleted successfully`)
    } catch (error) {
      console.error('Failed to bulk delete documents:', error)
      toast.error('Failed to delete documents')
      throw error
    }
  }

  const updateGenerationMetadata = async (
    id: string,
    updates: {
      templateId?: number;
      customSections?: Record<string, any>;
      generationPreferences?: {
        tone?: 'professional' | 'technical' | 'creative';
        length?: 'concise' | 'detailed';
      };
    }
  ) => {
    try {
      const updatedDocument = await apiClient.updateGeneration(id, updates)

      // Update in store
      updateGeneration(id, updatedDocument)

      toast.success('Generation updated successfully')
      return updatedDocument
    } catch (error) {
      console.error('Failed to update generation:', error)
      toast.error('Failed to update generation')
      throw error
    }
  }

  return {
    activeGenerations: Array.from(activeGenerations.values()),
    completedDocuments,
    selectedDocuments,
    isGenerating,
    createGeneration,
    generateCoverLetter,
    cancelGeneration,
    rateGeneration,
    loadUserGenerations,
    // Two-phase workflow methods
    getBullets,
    editBullet,
    approveBullets,
    assembleFinalGeneration,
    // Selection and delete methods
    toggleSelection,
    clearSelection,
    deleteDocument,
    bulkDeleteDocuments,
    // Update method
    updateGenerationMetadata,
  }
}