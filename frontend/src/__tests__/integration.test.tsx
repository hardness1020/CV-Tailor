import { describe, it, expect } from 'vitest'

describe('Integration Tests', () => {
  it('should have testing infrastructure setup', () => {
    // Basic test to verify testing infrastructure is working
    expect(true).toBe(true)
  })

  it('should import core modules without errors', async () => {
    // Test that core modules can be imported
    const { useAuthStore } = await import('@/stores/authStore')
    const { useArtifactStore } = await import('@/stores/artifactStore')
    const { apiClient } = await import('@/services/apiClient')

    expect(useAuthStore).toBeDefined()
    expect(useArtifactStore).toBeDefined()
    expect(apiClient).toBeDefined()
  })

  it('should have all required API client methods', async () => {
    const { apiClient } = await import('@/services/apiClient')

    // Authentication methods
    expect(typeof apiClient.login).toBe('function')
    expect(typeof apiClient.register).toBe('function')
    expect(typeof apiClient.logout).toBe('function')

    // Artifact methods
    expect(typeof apiClient.getArtifacts).toBe('function')
    expect(typeof apiClient.createArtifact).toBe('function')
    expect(typeof apiClient.deleteArtifact).toBe('function')

    // Generation methods
    expect(typeof apiClient.generateCV).toBe('function')
    expect(typeof apiClient.getGeneration).toBe('function')

    // Export methods
    expect(typeof apiClient.exportDocument).toBe('function')
    expect(typeof apiClient.getExportStatus).toBe('function')
  })

  it('should have store initial states', async () => {
    const { useAuthStore } = await import('@/stores/authStore')
    const { useArtifactStore } = await import('@/stores/artifactStore')

    const authState = useAuthStore.getState()
    const artifactState = useArtifactStore.getState()

    expect(authState.user).toBeNull()
    expect(authState.isAuthenticated).toBe(false)
    expect(Array.isArray(artifactState.artifacts)).toBe(true)
    expect(artifactState.isLoading).toBe(false)
  })
})