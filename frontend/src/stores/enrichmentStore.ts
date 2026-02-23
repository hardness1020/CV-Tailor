import { create } from 'zustand'

interface EnrichmentState {
  activeEnrichmentId: number | null
  setActiveEnrichment: (id: number) => void
  clearActiveEnrichment: () => void
}

export const useEnrichmentStore = create<EnrichmentState>((set) => ({
  activeEnrichmentId: null,
  setActiveEnrichment: (id) => set({ activeEnrichmentId: id }),
  clearActiveEnrichment: () => set({ activeEnrichmentId: null }),
}))
