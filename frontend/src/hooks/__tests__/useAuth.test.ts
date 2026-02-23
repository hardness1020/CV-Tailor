import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { useAuth } from '../useAuth'
import { apiClient } from '@/services/apiClient'
import { useAuthStore } from '@/stores/authStore'

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}))

// Mock stores
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

const mockUseAuthStore = vi.mocked(useAuthStore)
const mockApiClient = vi.mocked(apiClient)

describe('useAuth', () => {
  const mockSetUser = vi.fn()
  const mockSetTokens = vi.fn()
  const mockClearAuth = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuthStore.mockReturnValue({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      setUser: mockSetUser,
      setTokens: mockSetTokens,
      clearAuth: mockClearAuth,
    })
  })

  it('should handle successful login', async () => {
    const mockResponse = {
      user: { id: 1, email: 'test@example.com', firstName: 'Test', lastName: 'User' },
      access: 'access-token',
      refresh: 'refresh-token',
    }

    mockApiClient.login.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useAuth())

    await act(async () => {
      await result.current.login('test@example.com', 'password')
    })

    expect(mockApiClient.login).toHaveBeenCalledWith('test@example.com', 'password')
    expect(mockSetUser).toHaveBeenCalledWith(mockResponse.user)
    expect(mockSetTokens).toHaveBeenCalledWith(mockResponse.access, mockResponse.refresh)
  })

  it('should handle login error', async () => {
    const mockError = new Error('Invalid credentials')
    mockApiClient.login.mockRejectedValue(mockError)

    const { result } = renderHook(() => useAuth())

    await expect(act(async () => {
      await result.current.login('test@example.com', 'wrong-password')
    })).rejects.toThrow('Invalid credentials')

    expect(mockSetUser).not.toHaveBeenCalled()
    expect(mockSetTokens).not.toHaveBeenCalled()
  })

  it('should handle successful registration', async () => {
    const mockResponse = {
      user: { id: 1, email: 'test@example.com', firstName: 'Test', lastName: 'User' },
      access: 'access-token',
      refresh: 'refresh-token',
    }

    mockApiClient.register.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useAuth())

    await act(async () => {
      await result.current.register({
        email: 'test@example.com',
        password: 'password',
        firstName: 'Test',
        lastName: 'User',
      })
    })

    expect(mockApiClient.register).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password',
      firstName: 'Test',
      lastName: 'User',
    })
    expect(mockSetUser).toHaveBeenCalledWith(mockResponse.user)
    expect(mockSetTokens).toHaveBeenCalledWith(mockResponse.access, mockResponse.refresh)
  })

  it('should handle logout', async () => {
    mockApiClient.logout.mockResolvedValue(undefined)

    const { result } = renderHook(() => useAuth())

    await act(async () => {
      await result.current.logout()
    })

    expect(mockApiClient.logout).toHaveBeenCalled()
    expect(mockClearAuth).toHaveBeenCalled()
  })
})