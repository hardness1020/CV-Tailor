/**
 * Integration tests for Google authentication flow
 */

import { describe, it, expect, beforeEach, afterEach, vi, MockedFunction } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import LoginPage from '@/pages/LoginPage'
import { apiClient } from '@/services/apiClient'
import { useAuthStore } from '@/stores/authStore'
import type { User } from '@/types'

// Mock the API client
vi.mock('@/services/apiClient', () => ({
  apiClient: {
    post: vi.fn(),
    login: vi.fn()
  }
}))

// Mock the auth store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn()
}))

// Mock react-router-dom navigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: null })
  }
})

// Mock Google Identity Services
const mockGoogleAccounts = {
  id: {
    initialize: vi.fn(),
    renderButton: vi.fn(),
    prompt: vi.fn()
  }
}

// Test wrapper component
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    {children}
    <Toaster />
  </BrowserRouter>
)

describe('Google Authentication Integration', () => {
  const mockSetUser = vi.fn()
  const mockSetTokens = vi.fn()
  const mockApiClient = apiClient as {
    post: MockedFunction<any>
    login: MockedFunction<any>
  }

  const mockUser: User = {
    id: 1,
    email: 'test@gmail.com',
    username: 'test@gmail.com',
    first_name: 'Test',
    last_name: 'User',
    profile_image: null,
    phone: '',
    linkedin_url: '',
    github_url: '',
    website_url: '',
    bio: '',
    location: '',
    preferred_cv_template: 1,
    email_notifications: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  }

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks()

    // Mock environment variables
    import.meta.env.VITE_GOOGLE_CLIENT_ID = 'test-client-id'

    // Mock auth store
    ;(useAuthStore as any).mockReturnValue({
      setUser: mockSetUser,
      setTokens: mockSetTokens,
      user: null,
      isAuthenticated: false,
      isLoading: false
    })

    // Mock window.google
    Object.defineProperty(window, 'google', {
      value: { accounts: mockGoogleAccounts },
      writable: true
    })

    // Mock DOM methods for Google script loading
    const mockScript = {
      src: '',
      async: false,
      defer: false,
      onload: null,
      onerror: null,
      addEventListener: vi.fn()
    }

    vi.spyOn(document, 'createElement').mockReturnValue(mockScript as any)
    vi.spyOn(document, 'querySelector').mockReturnValue(null)
    vi.spyOn(document.head, 'appendChild').mockImplementation(() => {
      // Simulate script loading
      if (mockScript.onload) {
        setTimeout(() => mockScript.onload!(new Event('load')), 0)
      }
      return mockScript as any
    })
  })

  afterEach(() => {
    delete (window as any).google
    vi.resetAllMocks()
    vi.restoreAllMocks()
  })

  describe('LoginPage Google Integration', () => {
    it('should render Google Sign-In button on login page', async () => {
      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      // Wait for Google services to load
      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      }, { timeout: 3000 })

      // Should render the button
      expect(mockGoogleAccounts.id.renderButton).toHaveBeenCalledWith(
        expect.any(HTMLElement),
        expect.objectContaining({
          type: 'standard',
          theme: 'outline',
          size: 'large',
          text: 'signin_with'
        })
      )
    })

    it('should complete successful Google sign-in flow for new user', async () => {
      const mockGoogleResponse = {
        user: mockUser,
        access: 'access-token',
        refresh: 'refresh-token',
        created: true
      }

      mockApiClient.post.mockResolvedValue({ data: mockGoogleResponse })

      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      // Wait for initialization
      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      })

      // Get the Google callback function
      const initCall = mockGoogleAccounts.id.initialize.mock.calls[0][0]
      const googleCallback = initCall.callback

      // Simulate Google authentication response
      await googleCallback({
        credential: 'fake-google-jwt-token',
        select_by: 'user'
      })

      // Verify API call was made
      await waitFor(() => {
        expect(mockApiClient.post).toHaveBeenCalledWith('/auth/google/', {
          credential: 'fake-google-jwt-token'
        })
      })

      // Verify auth store was updated
      expect(mockSetUser).toHaveBeenCalledWith(mockUser)
      expect(mockSetTokens).toHaveBeenCalledWith('access-token', 'refresh-token')

      // Verify navigation
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
    })

    it('should complete successful Google sign-in flow for existing user', async () => {
      const mockGoogleResponse = {
        user: mockUser,
        access: 'access-token',
        refresh: 'refresh-token',
        created: false
      }

      mockApiClient.post.mockResolvedValue({ data: mockGoogleResponse })

      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      // Wait for initialization
      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      })

      // Simulate successful Google authentication
      const initCall = mockGoogleAccounts.id.initialize.mock.calls[0][0]
      const googleCallback = initCall.callback

      await googleCallback({
        credential: 'fake-google-jwt-token',
        select_by: 'user'
      })

      // Verify the flow completed successfully
      await waitFor(() => {
        expect(mockSetUser).toHaveBeenCalledWith(mockUser)
        expect(mockSetTokens).toHaveBeenCalledWith('access-token', 'refresh-token')
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
      })
    })

    it('should handle Google authentication error', async () => {
      const mockError = {
        response: {
          status: 400,
          data: {
            error: 'google_auth_failed',
            message: 'Invalid Google credential',
            recoverable: true
          }
        }
      }

      mockApiClient.post.mockRejectedValue(mockError)

      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      // Wait for initialization
      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      })

      // Simulate Google authentication with invalid token
      const initCall = mockGoogleAccounts.id.initialize.mock.calls[0][0]
      const googleCallback = initCall.callback

      await googleCallback({
        credential: 'invalid-google-jwt-token',
        select_by: 'user'
      })

      // Should show error message and not navigate
      await waitFor(() => {
        expect(screen.getByText('Invalid Google credential')).toBeInTheDocument()
      })

      expect(mockNavigate).not.toHaveBeenCalled()
      expect(mockSetUser).not.toHaveBeenCalled()
      expect(mockSetTokens).not.toHaveBeenCalled()
    })

    it('should handle network error during Google authentication', async () => {
      mockApiClient.post.mockRejectedValue(new Error('Network error'))

      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      })

      // Simulate Google authentication
      const initCall = mockGoogleAccounts.id.initialize.mock.calls[0][0]
      const googleCallback = initCall.callback

      await googleCallback({
        credential: 'fake-google-jwt-token',
        select_by: 'user'
      })

      // Should show network error
      await waitFor(() => {
        expect(screen.getByText('Network error during authentication')).toBeInTheDocument()
      })
    })

    it('should show loading state during Google authentication', async () => {
      // Create a promise that we can control
      let resolveAuth: (value: any) => void
      const authPromise = new Promise((resolve) => {
        resolveAuth = resolve
      })
      mockApiClient.post.mockReturnValue(authPromise)

      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      })

      // Trigger Google authentication
      const initCall = mockGoogleAccounts.id.initialize.mock.calls[0][0]
      const googleCallback = initCall.callback

      googleCallback({
        credential: 'fake-google-jwt-token',
        select_by: 'user'
      })

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText('Signing in...')).toBeInTheDocument()
      })

      // Resolve the authentication
      resolveAuth!({
        data: {
          user: mockUser,
          access: 'access-token',
          refresh: 'refresh-token',
          created: false
        }
      })

      // Loading should disappear
      await waitFor(() => {
        expect(screen.queryByText('Signing in...')).not.toBeInTheDocument()
      })
    })
  })

  describe('Google Services Fallback', () => {
    it('should show fallback when Google services are unavailable', async () => {
      // Remove Google from window
      delete (window as any).google

      // Mock script loading failure
      vi.spyOn(document.head, 'appendChild').mockImplementation((script: any) => {
        if (script.onerror) {
          setTimeout(() => script.onerror(new ErrorEvent('error')), 0)
        }
        return script
      })

      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      // Should show fallback UI
      await waitFor(() => {
        expect(screen.getByText(/Google Sign-In is not available/)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Sign in with Google/ })).toBeInTheDocument()
      })
    })

    it('should allow traditional email/password login when Google fails', async () => {
      // Remove Google services
      delete (window as any).google

      const mockLoginResponse = {
        user: mockUser,
        access: 'access-token',
        refresh: 'refresh-token'
      }

      mockApiClient.login.mockResolvedValue(mockLoginResponse)

      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      // Fill in email/password form
      const emailInput = screen.getByPlaceholderText('Enter your email')
      const passwordInput = screen.getByPlaceholderText('Enter your password')
      const submitButton = screen.getByRole('button', { name: 'Sign in' })

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.click(submitButton)

      // Should complete traditional login flow
      await waitFor(() => {
        expect(mockApiClient.login).toHaveBeenCalledWith('test@example.com', 'password123')
        expect(mockSetUser).toHaveBeenCalledWith(mockUser)
        expect(mockSetTokens).toHaveBeenCalledWith('access-token', 'refresh-token')
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
      })
    })
  })

  describe('Error Recovery', () => {
    it('should allow retry after Google authentication error', async () => {
      mockApiClient.post
        .mockRejectedValueOnce({
          response: {
            status: 400,
            data: { message: 'Invalid credential' }
          }
        })
        .mockResolvedValueOnce({
          data: {
            user: mockUser,
            access: 'access-token',
            refresh: 'refresh-token',
            created: false
          }
        })

      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      })

      const initCall = mockGoogleAccounts.id.initialize.mock.calls[0][0]
      const googleCallback = initCall.callback

      // First attempt should fail
      await googleCallback({
        credential: 'invalid-token',
        select_by: 'user'
      })

      await waitFor(() => {
        expect(screen.getByText('Invalid credential')).toBeInTheDocument()
      })

      // Second attempt should succeed
      await googleCallback({
        credential: 'valid-token',
        select_by: 'user'
      })

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
      })
    })
  })

  describe('Accessibility and UX', () => {
    it('should have proper focus management', async () => {
      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      // Wait for page to load
      await waitFor(() => {
        expect(screen.getByText('Sign in to CV Tailor')).toBeInTheDocument()
      })

      // Check that form elements are focusable
      const emailInput = screen.getByPlaceholderText('Enter your email')
      const passwordInput = screen.getByPlaceholderText('Enter your password')

      expect(emailInput).toBeInTheDocument()
      expect(passwordInput).toBeInTheDocument()

      // Elements should be focusable
      emailInput.focus()
      expect(document.activeElement).toBe(emailInput)

      passwordInput.focus()
      expect(document.activeElement).toBe(passwordInput)
    })

    it('should have proper ARIA labels and structure', async () => {
      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      // Check for proper form structure
      const emailLabel = screen.getByText('Email address')
      const passwordLabel = screen.getByText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign in' })

      expect(emailLabel).toBeInTheDocument()
      expect(passwordLabel).toBeInTheDocument()
      expect(submitButton).toBeInTheDocument()
    })

    it('should show appropriate loading states', async () => {
      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      )

      // Should show loading for Google Sign-In initially
      expect(screen.getByText('Loading Google Sign-In...')).toBeInTheDocument()

      // Wait for Google to load
      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      })

      // Loading should be replaced with button
      await waitFor(() => {
        expect(screen.queryByText('Loading Google Sign-In...')).not.toBeInTheDocument()
      })
    })
  })
})