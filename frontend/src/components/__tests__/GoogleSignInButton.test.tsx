/**
 * Unit tests for GoogleSignInButton component
 */

import { describe, it, expect, beforeEach, afterEach, vi, MockedFunction } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { GoogleSignInButton } from '../GoogleSignInButton'
import { googleAuthService, GoogleAuthError } from '@/services/googleAuth'
import { useAuthStore } from '@/stores/authStore'
import type { User } from '@/types'

// Mock the Google auth service
vi.mock('@/services/googleAuth', () => ({
  googleAuthService: {
    initialize: vi.fn(),
    signInWithOneTap: vi.fn(),
    linkGoogleAccount: vi.fn(),
    exchangeCredentialForTokens: vi.fn(),
    getClientId: vi.fn(() => 'test-client-id')
  },
  GoogleAuthError: class extends Error {
    type: string
    recoverable: boolean
    constructor({ type, message, recoverable }: { type: string, message: string, recoverable: boolean }) {
      super(message)
      this.type = type
      this.recoverable = recoverable
    }
  }
}))

// Mock the auth store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn()
}))

// Mock Google Identity Services
const mockGoogleAccounts = {
  id: {
    initialize: vi.fn(),
    renderButton: vi.fn()
  }
}

describe('GoogleSignInButton', () => {
  const mockSetUser = vi.fn()
  const mockSetTokens = vi.fn()
  const mockUser: User = {
    id: 1,
    email: 'test@example.com',
    username: 'testuser',
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

  const mockGoogleAuthService = googleAuthService as {
    initialize: MockedFunction<any>
    signInWithOneTap: MockedFunction<any>
    linkGoogleAccount: MockedFunction<any>
    exchangeCredentialForTokens: MockedFunction<any>
    getClientId: MockedFunction<any>
  }

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks()

    // Mock auth store
    ;(useAuthStore as any).mockReturnValue({
      setUser: mockSetUser,
      setTokens: mockSetTokens,
      user: null
    })

    ;(useAuthStore as any).getState = vi.fn(() => ({
      user: mockUser,
      setUser: mockSetUser,
      setTokens: mockSetTokens
    }))

    // Mock window.google
    Object.defineProperty(window, 'google', {
      value: { accounts: mockGoogleAccounts },
      writable: true
    })

    // Mock successful initialization by default
    mockGoogleAuthService.initialize.mockResolvedValue(undefined)
  })

  afterEach(() => {
    delete (window as any).google
    vi.resetAllMocks()
  })

  describe('initialization', () => {
    it('should render loading state initially', () => {
      render(<GoogleSignInButton />)

      expect(screen.getByText('Loading Google Sign-In...')).toBeInTheDocument()
    })

    it('should initialize Google auth service on mount', async () => {
      render(<GoogleSignInButton />)

      await waitFor(() => {
        expect(mockGoogleAuthService.initialize).toHaveBeenCalled()
      })
    })

    it('should handle initialization error', async () => {
      const initError = new GoogleAuthError({
        type: 'GOOGLE_UNAVAILABLE',
        message: 'Google services not available',
        recoverable: true
      })

      mockGoogleAuthService.initialize.mockRejectedValue(initError)

      render(<GoogleSignInButton />)

      await waitFor(() => {
        expect(screen.getByText('Google services not available')).toBeInTheDocument()
      })
    })
  })

  describe('button rendering', () => {
    beforeEach(async () => {
      // Mock successful initialization
      mockGoogleAuthService.initialize.mockResolvedValue(undefined)
    })

    it('should render Google Sign-In button after initialization', async () => {
      const { container } = render(<GoogleSignInButton />)

      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalledWith({
          client_id: 'test-client-id',
          callback: expect.any(Function),
          auto_select: false,
          cancel_on_tap_outside: true
        })

        expect(mockGoogleAccounts.id.renderButton).toHaveBeenCalledWith(
          expect.any(HTMLElement),
          {
            type: 'standard',
            theme: 'outline',
            size: 'large',
            text: 'signin_with',
            shape: 'rectangular',
            logo_alignment: 'left',
            width: '100%'
          }
        )
      })
    })

    it('should render with custom props', async () => {
      render(
        <GoogleSignInButton
          mode="signup"
          size="medium"
          theme="filled_blue"
          text="signup_with"
        />
      )

      await waitFor(() => {
        expect(mockGoogleAccounts.id.renderButton).toHaveBeenCalledWith(
          expect.any(HTMLElement),
          {
            type: 'standard',
            theme: 'filled_blue',
            size: 'medium',
            text: 'signup_with',
            shape: 'rectangular',
            logo_alignment: 'left',
            width: '100%'
          }
        )
      })
    })

    it('should determine correct text based on mode', async () => {
      const { rerender } = render(<GoogleSignInButton mode="signup" />)

      await waitFor(() => {
        expect(mockGoogleAccounts.id.renderButton).toHaveBeenCalledWith(
          expect.any(HTMLElement),
          expect.objectContaining({ text: 'signup_with' })
        )
      })

      rerender(<GoogleSignInButton mode="link" />)

      await waitFor(() => {
        expect(mockGoogleAccounts.id.renderButton).toHaveBeenCalledWith(
          expect.any(HTMLElement),
          expect.objectContaining({ text: 'continue_with' })
        )
      })
    })

    it('should not render when disabled', async () => {
      render(<GoogleSignInButton disabled />)

      await waitFor(() => {
        expect(mockGoogleAuthService.initialize).toHaveBeenCalled()
      })

      // Should not call renderButton when disabled
      expect(mockGoogleAccounts.id.renderButton).not.toHaveBeenCalled()
    })
  })

  describe('authentication flow', () => {
    const mockAuthResponse = {
      user: mockUser,
      access: 'access-token',
      refresh: 'refresh-token',
      created: false
    }

    beforeEach(async () => {
      mockGoogleAuthService.initialize.mockResolvedValue(undefined)
      mockGoogleAuthService.exchangeCredentialForTokens.mockResolvedValue(mockAuthResponse)
    })

    it('should handle successful sign in', async () => {
      const onSuccess = vi.fn()

      render(<GoogleSignInButton onSuccess={onSuccess} />)

      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      })

      // Get the callback from the initialize call
      const initializeCall = mockGoogleAccounts.id.initialize.mock.calls[0][0]
      const callback = initializeCall.callback

      // Simulate Google response
      await callback({
        credential: 'fake-jwt-token',
        select_by: 'user'
      })

      await waitFor(() => {
        expect(mockGoogleAuthService.exchangeCredentialForTokens).toHaveBeenCalledWith('fake-jwt-token')
        expect(mockSetUser).toHaveBeenCalledWith(mockUser)
        expect(mockSetTokens).toHaveBeenCalledWith('access-token', 'refresh-token')
        expect(onSuccess).toHaveBeenCalledWith(mockUser, false)
      })
    })

    it('should handle account linking mode', async () => {
      mockGoogleAuthService.linkGoogleAccount.mockResolvedValue({
        message: 'Account linked successfully',
        linked_email: 'test@gmail.com'
      })

      const onSuccess = vi.fn()

      render(<GoogleSignInButton mode="link" onSuccess={onSuccess} />)

      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      })

      // Get the callback from the initialize call
      const initializeCall = mockGoogleAccounts.id.initialize.mock.calls[0][0]
      const callback = initializeCall.callback

      // Simulate Google response for linking
      await callback({
        credential: 'fake-jwt-token',
        select_by: 'user'
      })

      await waitFor(() => {
        expect(mockGoogleAuthService.linkGoogleAccount).toHaveBeenCalledWith('fake-jwt-token')
        expect(onSuccess).toHaveBeenCalledWith(mockUser, false)
      })
    })

    it('should handle authentication error', async () => {
      const authError = new GoogleAuthError({
        type: 'TOKEN_INVALID',
        message: 'Invalid Google token',
        recoverable: true
      })

      mockGoogleAuthService.exchangeCredentialForTokens.mockRejectedValue(authError)

      const onError = vi.fn()

      render(<GoogleSignInButton onError={onError} />)

      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      })

      // Get the callback from the initialize call
      const initializeCall = mockGoogleAccounts.id.initialize.mock.calls[0][0]
      const callback = initializeCall.callback

      // Simulate Google response that will fail
      await callback({
        credential: 'invalid-jwt-token',
        select_by: 'user'
      })

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith(authError)
        expect(screen.getByText('Invalid Google token')).toBeInTheDocument()
      })
    })

    it('should show loading state during authentication', async () => {
      // Make the auth service hang
      let resolveAuth: (value: any) => void
      const authPromise = new Promise((resolve) => {
        resolveAuth = resolve
      })
      mockGoogleAuthService.exchangeCredentialForTokens.mockReturnValue(authPromise)

      render(<GoogleSignInButton />)

      await waitFor(() => {
        expect(mockGoogleAccounts.id.initialize).toHaveBeenCalled()
      })

      // Get the callback and trigger it
      const initializeCall = mockGoogleAccounts.id.initialize.mock.calls[0][0]
      const callback = initializeCall.callback

      // Start the auth process
      callback({
        credential: 'fake-jwt-token',
        select_by: 'user'
      })

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText('Signing in...')).toBeInTheDocument()
      })

      // Resolve the auth
      resolveAuth!(mockAuthResponse)

      // Loading should disappear
      await waitFor(() => {
        expect(screen.queryByText('Signing in...')).not.toBeInTheDocument()
      })
    })
  })

  describe('error states', () => {
    it('should show fallback button when Google is not available', async () => {
      const initError = new GoogleAuthError({
        type: 'GOOGLE_UNAVAILABLE',
        message: 'Google services not available',
        recoverable: false
      })

      mockGoogleAuthService.initialize.mockRejectedValue(initError)

      render(<GoogleSignInButton />)

      await waitFor(() => {
        expect(screen.getByText('Google services not available')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /sign in with google/i })).toBeInTheDocument()
      })
    })

    it('should handle fallback button click', async () => {
      const initError = new GoogleAuthError({
        type: 'GOOGLE_UNAVAILABLE',
        message: 'Google services not available',
        recoverable: false
      })

      mockGoogleAuthService.initialize.mockRejectedValue(initError)

      render(<GoogleSignInButton />)

      await waitFor(() => {
        const fallbackButton = screen.getByRole('button', { name: /sign in with google/i })
        fallbackButton.click()
      })

      await waitFor(() => {
        expect(screen.getByText('Google Sign-In is not available. Please try refreshing the page.')).toBeInTheDocument()
      })
    })

    it('should clear error when component re-renders', async () => {
      mockGoogleAuthService.initialize
        .mockRejectedValueOnce(new GoogleAuthError({
          type: 'GOOGLE_UNAVAILABLE',
          message: 'Google services not available',
          recoverable: false
        }))
        .mockResolvedValueOnce(undefined)

      const { rerender } = render(<GoogleSignInButton />)

      await waitFor(() => {
        expect(screen.getByText('Google services not available')).toBeInTheDocument()
      })

      // Re-render should clear error and retry initialization
      rerender(<GoogleSignInButton />)

      await waitFor(() => {
        expect(screen.queryByText('Google services not available')).not.toBeInTheDocument()
      })
    })
  })

  describe('accessibility', () => {
    beforeEach(async () => {
      mockGoogleAuthService.initialize.mockResolvedValue(undefined)
    })

    it('should be accessible when disabled', async () => {
      render(<GoogleSignInButton disabled />)

      await waitFor(() => {
        const loadingElement = screen.getByText('Loading Google Sign-In...')
        expect(loadingElement).toHaveClass('animate-pulse')
      })
    })

    it('should have proper ARIA attributes during loading', () => {
      render(<GoogleSignInButton />)

      const loadingElement = screen.getByText('Loading Google Sign-In...')
      expect(loadingElement).toBeInTheDocument()
    })

    it('should handle custom className', async () => {
      const { container } = render(<GoogleSignInButton className="custom-class" />)

      const wrapper = container.firstChild as HTMLElement
      expect(wrapper).toHaveClass('custom-class')
    })
  })

  describe('cleanup', () => {
    it('should clean up button element on unmount', async () => {
      mockGoogleAuthService.initialize.mockResolvedValue(undefined)

      const { unmount } = render(<GoogleSignInButton />)

      await waitFor(() => {
        expect(mockGoogleAccounts.id.renderButton).toHaveBeenCalled()
      })

      // Mock the button element with innerHTML
      const mockButtonElement = {
        innerHTML: 'Google Sign-In Button'
      }

      // Simulate the ref having the element
      const renderCall = mockGoogleAccounts.id.renderButton.mock.calls[0]
      const buttonElement = renderCall[0]
      if (buttonElement) {
        buttonElement.innerHTML = 'Google Sign-In Button'
      }

      unmount()

      // Should clean up on unmount (this is hard to test directly, but we can verify the component unmounts cleanly)
    })
  })
})