import { create } from 'zustand'
import type { GeneratedDocument } from '@/types'

interface GenerationState {
  activeGenerations: Map<string, GeneratedDocument>
  completedDocuments: GeneratedDocument[]
  selectedDocuments: string[]
  isGenerating: boolean

  // Actions
  startGeneration: (id: string, type: 'cv' | 'cover_letter') => void
  updateGeneration: (id: string, updates: Partial<GeneratedDocument>) => void
  completeGeneration: (id: string, document: GeneratedDocument) => void
  removeGeneration: (id: string) => void
  clearCompleted: () => void
  toggleSelection: (id: string) => void
  clearSelection: () => void
  deleteDocument: (id: string) => void
  bulkDelete: (ids: string[]) => void
}

export const useGenerationStore = create<GenerationState>((set) => ({
  activeGenerations: new Map(),
  completedDocuments: [],
  selectedDocuments: [],
  isGenerating: false,

  startGeneration: (id: string, type: 'cv' | 'cover_letter') => {
    const newGeneration: GeneratedDocument = {
      id,
      type,
      status: 'processing',
      progressPercentage: 0,
      createdAt: new Date().toISOString(),
      jobDescriptionHash: '',
    }

    set((state) => {
      const newActiveGenerations = new Map(state.activeGenerations)
      newActiveGenerations.set(id, newGeneration)
      return {
        activeGenerations: newActiveGenerations,
        isGenerating: true,
      }
    })
  },

  updateGeneration: (id: string, updates: Partial<GeneratedDocument>) => {
    set((state) => {
      const newActiveGenerations = new Map(state.activeGenerations)
      const existing = newActiveGenerations.get(id)
      if (existing) {
        // Merge updates with existing generation to preserve all fields (ft-026)
        newActiveGenerations.set(id, { ...existing, ...updates })
      }
      return {
        activeGenerations: newActiveGenerations,
      }
    })
  },

  completeGeneration: (id: string, document: GeneratedDocument) => {
    set((state) => {
      const newActiveGenerations = new Map(state.activeGenerations)
      newActiveGenerations.delete(id)

      return {
        activeGenerations: newActiveGenerations,
        completedDocuments: [document, ...state.completedDocuments],
        isGenerating: newActiveGenerations.size > 0,
      }
    })
  },

  removeGeneration: (id: string) => {
    set((state) => {
      const newActiveGenerations = new Map(state.activeGenerations)
      newActiveGenerations.delete(id)

      return {
        activeGenerations: newActiveGenerations,
        isGenerating: newActiveGenerations.size > 0,
      }
    })
  },

  clearCompleted: () => {
    set({ completedDocuments: [] })
  },

  toggleSelection: (id: string) => {
    set((state) => {
      const isSelected = state.selectedDocuments.includes(id)
      return {
        selectedDocuments: isSelected
          ? state.selectedDocuments.filter((selectedId) => selectedId !== id)
          : [...state.selectedDocuments, id]
      }
    })
  },

  clearSelection: () => {
    set({ selectedDocuments: [] })
  },

  deleteDocument: (id: string) => {
    set((state) => ({
      completedDocuments: state.completedDocuments.filter((doc) => doc.id !== id),
      selectedDocuments: state.selectedDocuments.filter((selectedId) => selectedId !== id)
    }))
  },

  bulkDelete: (ids: string[]) => {
    set((state) => ({
      completedDocuments: state.completedDocuments.filter((doc) => !ids.includes(doc.id)),
      selectedDocuments: []
    }))
  },
}))