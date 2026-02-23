import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '../authStore'

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.getState().clearAuth()
  })

  it('should have initial state', () => {
    const state = useAuthStore.getState()

    expect(state.user).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.refreshToken).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it('should set user', () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      firstName: 'Test',
      lastName: 'User',
    }

    useAuthStore.getState().setUser(mockUser)

    const state = useAuthStore.getState()
    expect(state.user).toEqual(mockUser)
  })

  it('should set tokens', () => {
    const accessToken = 'access-token'
    const refreshToken = 'refresh-token'

    useAuthStore.getState().setTokens(accessToken, refreshToken)

    const state = useAuthStore.getState()
    expect(state.accessToken).toBe(accessToken)
    expect(state.refreshToken).toBe(refreshToken)
  })

  it('should clear auth state', () => {
    // First set some state
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      firstName: 'Test',
      lastName: 'User',
    }

    useAuthStore.getState().setUser(mockUser)
    useAuthStore.getState().setTokens('access', 'refresh')

    // Then clear it
    useAuthStore.getState().clearAuth()

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.refreshToken).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it('should compute isAuthenticated correctly', () => {
    const state = useAuthStore.getState()

    // Initially not authenticated
    expect(state.isAuthenticated).toBe(false)

    // Set user but no tokens
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      firstName: 'Test',
      lastName: 'User',
    }
    useAuthStore.getState().setUser(mockUser)
    expect(useAuthStore.getState().isAuthenticated).toBe(false)

    // Set tokens but no user
    useAuthStore.getState().clearAuth()
    useAuthStore.getState().setTokens('access', 'refresh')
    expect(useAuthStore.getState().isAuthenticated).toBe(false)

    // Set both user and tokens
    useAuthStore.getState().setUser(mockUser)
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
  })
})