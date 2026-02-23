import { create } from 'zustand'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/apiClient'
import type { Artifact, ArtifactFilters } from '@/types'

interface ArtifactState {
  artifacts: Artifact[]
  selectedArtifacts: number[]
  filters: ArtifactFilters
  isLoading: boolean
  error: string | null

  // Actions
  setArtifacts: (artifacts: Artifact[]) => void
  addArtifact: (artifact: Artifact) => void
  updateArtifact: (id: number, updates: Partial<Artifact>) => void
  deleteArtifact: (id: number) => void
  setFilters: (filters: ArtifactFilters) => void
  toggleSelection: (id: number) => void
  clearSelection: () => void
  selectAll: () => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  loadArtifacts: (customFilters?: ArtifactFilters) => Promise<void>
}

export const useArtifactStore = create<ArtifactState>((set, get) => ({
  artifacts: [],
  selectedArtifacts: [],
  filters: {},
  isLoading: false,
  error: null,

  setArtifacts: (artifacts: Artifact[]) => {
    set({ artifacts })
  },

  addArtifact: (artifact: Artifact) => {
    set((state) => ({
      artifacts: [artifact, ...state.artifacts]
    }))
  },

  updateArtifact: (id: number, updates: Partial<Artifact>) => {
    set((state) => ({
      artifacts: state.artifacts.map((artifact) =>
        artifact.id === id ? { ...artifact, ...updates } : artifact
      )
    }))
  },

  deleteArtifact: (id: number) => {
    set((state) => ({
      artifacts: state.artifacts.filter((artifact) => artifact.id !== id),
      selectedArtifacts: state.selectedArtifacts.filter((selectedId) => selectedId !== id)
    }))
  },

  setFilters: (filters: ArtifactFilters) => {
    set({ filters })
  },

  toggleSelection: (id: number) => {
    set((state) => {
      const isSelected = state.selectedArtifacts.includes(id)
      return {
        selectedArtifacts: isSelected
          ? state.selectedArtifacts.filter((selectedId) => selectedId !== id)
          : [...state.selectedArtifacts, id]
      }
    })
  },

  clearSelection: () => {
    set({ selectedArtifacts: [] })
  },

  selectAll: () => {
    const { artifacts } = get()
    set({ selectedArtifacts: artifacts.map((artifact) => artifact.id) })
  },

  setLoading: (loading: boolean) => {
    set({ isLoading: loading })
  },

  setError: (error: string | null) => {
    set({ error })
  },

  loadArtifacts: async (customFilters: ArtifactFilters = {}) => {
    try {
      set({ isLoading: true, error: null })
      const response = await apiClient.getArtifacts(customFilters)
      set({ artifacts: response.results })
    } catch (error) {
      console.error('Failed to load artifacts:', error)
      set({ error: 'Failed to load artifacts' })
      toast.error('Failed to load artifacts')
    } finally {
      set({ isLoading: false })
    }
  },
}))