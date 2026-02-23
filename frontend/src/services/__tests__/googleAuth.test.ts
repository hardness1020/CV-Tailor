/**
 * Unit tests for Google Authentication Service
 */

import { describe, it, expect, beforeEach, afterEach, vi, MockedFunction } from 'vitest'
import { GoogleAuthService, GoogleAuthError } from '../googleAuth'
import { apiClient } from '../apiClient'

// Mock the API client
vi.mock('../apiClient', () => ({
  apiClient: {
    post: vi.fn()
  }
}))

// Mock Google Identity Services
const mockGoogleAccounts = {
  id: {
    initialize: vi.fn(),
    prompt: vi.fn(),
    renderButton: vi.fn(),
    disableAutoSelect: vi.fn(),
    cancel: vi.fn(),
    storeCredential: vi.fn(),
    onGoogleLibraryLoad: vi.fn()
  }
}

// Mock DOM methods
Object.defineProperty(document, 'createElement', {
  value: vi.fn(() => ({
    src: '',
    async: false,
    defer: false,
    onload: null,
    onerror: null,
    addEventListener: vi.fn()
  }))
})

Object.defineProperty(document, 'querySelector', {
  value: vi.fn()
})

Object.defineProperty(document.head, 'appendChild', {
  value: vi.fn()
})

describe('GoogleAuthService', () => {
  let googleAuthService: GoogleAuthService
  const mockApiClient = apiClient as { post: MockedFunction<any> }

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks()

    // Setup environment variable mock
    import.meta.env.VITE_GOOGLE_CLIENT_ID = 'test-client-id'

    // Create new service instance
    googleAuthService = new GoogleAuthService('test-client-id')

    // Mock window.google
    Object.defineProperty(window, 'google', {
      value: { accounts: mockGoogleAccounts },
      writable: true,
      configurable: true
    })
  })

  afterEach(() => {
    // Clean up
    if ('google' in window) {
      Object.defineProperty(window, 'google', {
        value: undefined,
        writable: true,
        configurable: true
      })
    }
    vi.resetAllMocks()
  })

  describe('constructor', () => {
    it('should use provided client ID', () => {
      const service = new GoogleAuthService('custom-client-id')
      expect(service.getClientId()).toBe('custom-client-id')
    })

    it('should use environment variable when no client ID provided', () => {
      import.meta.env.VITE_GOOGLE_CLIENT_ID = 'env-client-id'
      const service = new GoogleAuthService()
      expect(service.getClientId()).toBe('env-client-id')
    })

    it('should warn when no client ID is available', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      import.meta.env.VITE_GOOGLE_CLIENT_ID = ''

      new GoogleAuthService()

      expect(consoleSpy).toHaveBeenCalledWith(
        'Google Client ID not found. Set VITE_GOOGLE_CLIENT_ID environment variable.'
      )

      consoleSpy.mockRestore()
    })
  })

  describe('initialize', () => {
    it('should initialize successfully when Google services are available', async () => {
      // Mock script loading
      const mockScript = {
        src: '',
        async: false,
        defer: false,
        onload: null,
        onerror: null,
        addEventListener: vi.fn()
      }

      vi.mocked(document.createElement).mockReturnValue(mockScript as any)
      vi.mocked(document.querySelector).mockReturnValue(null)

      // Initialize and trigger script load
      const initPromise = googleAuthService.initialize()

      // Simulate script loading
      if (mockScript.onload) {
        mockScript.onload(new Event('load'))
      }

      await expect(initPromise).resolves.toBeUndefined()
    })

    it('should throw error when client ID is missing', async () => {
      const serviceWithoutId = new GoogleAuthService('')

      await expect(serviceWithoutId.initialize()).rejects.toEqual(
        expect.objectContaining({
          type: 'INVALID_CONFIGURATION',
          message: 'Google Client ID is required',
          recoverable: false
        })
      )
    })

    it('should throw error when Google services fail to load', async () => {
      // Mock script loading failure
      const mockScript = {
        src: '',
        async: false,
        defer: false,
        onload: null,
        onerror: null,
        addEventListener: vi.fn()
      }

      vi.mocked(document.createElement).mockReturnValue(mockScript as any)
      vi.mocked(document.querySelector).mockReturnValue(null)

      // Remove Google from window after script "loads"
      Object.defineProperty(window, 'google', {
        value: undefined,
        writable: true,
        configurable: true
      })

      const initPromise = googleAuthService.initialize()

      // Simulate script loading but Google not available
      if (mockScript.onload) {
        mockScript.onload(new Event('load'))
      }

      await expect(initPromise).rejects.toThrow(GoogleAuthError)
      await expect(initPromise).rejects.toMatchObject({
        type: 'GOOGLE_UNAVAILABLE',
        message: 'Google Identity Services failed to load',
        recoverable: true
      })
    })

    it('should reuse initialization promise for concurrent calls', async () => {
      const mockScript = {
        src: '',
        onload: null,
        onerror: null,
        addEventListener: vi.fn()
      }

      vi.mocked(document.createElement).mockReturnValue(mockScript as any)
      vi.mocked(document.querySelector).mockReturnValue(null)

      // Start multiple initializations
      const init1 = googleAuthService.initialize()
      const init2 = googleAuthService.initialize()

      // Trigger script load
      if (mockScript.onload) {
        mockScript.onload(new Event('load'))
      }

      // Both should resolve
      await Promise.all([init1, init2])

      // createElement should only be called once
      expect(document.createElement).toHaveBeenCalledTimes(1)
    })
  })

  describe('signInWithOneTap', () => {
    beforeEach(async () => {
      // Mock successful initialization
      const mockScript = { onload: null, onerror: null, addEventListener: vi.fn() }
      vi.mocked(document.createElement).mockReturnValue(mockScript as any)
      vi.mocked(document.querySelector).mockReturnValue(null)

      const initPromise = googleAuthService.initialize()
      if (mockScript.onload) {
        mockScript.onload(new Event('load'))
      }
      await initPromise
    })

    it('should successfully sign in with One Tap', async () => {
      const mockResponse = {
        user: { id: 1, email: 'test@example.com', name: 'Test User' },
        access: 'access-token',
        refresh: 'refresh-token',
        created: false
      }

      mockApiClient.post.mockResolvedValue({ data: mockResponse })

      // Mock Google callback
      mockGoogleAccounts.id.initialize.mockImplementation((config) => {
        // Simulate successful credential response
        setTimeout(() => {
          config.callback({
            credential: 'fake-jwt-token',
            select_by: 'user'
          })
        }, 0)
      })

      mockGoogleAccounts.id.prompt.mockImplementation((callback) => {
        // Simulate successful display
        setTimeout(() => {
          callback({
            isDisplayMoment: () => true,
            isDisplayed: () => true,
            isNotDisplayed: () => false,
            isDismissedMoment: () => false,
            isSkippedMoment: () => false,
            getMomentType: () => 'display'
          })
        }, 0)
      })

      const result = await googleAuthService.signInWithOneTap()

      expect(result).toEqual(mockResponse)
      expect(mockGoogleAccounts.id.initialize).toHaveBeenCalledWith({
        client_id: 'test-client-id',
        callback: expect.any(Function),
        auto_select: false,
        cancel_on_tap_outside: true
      })
      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/google/', {
        credential: 'fake-jwt-token'
      })
    })

    it('should handle user cancellation', async () => {
      mockGoogleAccounts.id.initialize.mockImplementation(() => {
        // Do nothing - no callback
      })

      mockGoogleAccounts.id.prompt.mockImplementation((callback) => {
        setTimeout(() => {
          callback({
            isDisplayMoment: () => false,
            isDisplayed: () => false,
            isNotDisplayed: () => false,
            isDismissedMoment: () => true,
            isSkippedMoment: () => false,
            getDismissedReason: () => 'cancel_called',
            getMomentType: () => 'dismissed'
          })
        }, 0)
      })

      await expect(googleAuthService.signInWithOneTap()).rejects.toThrow(GoogleAuthError)
      await expect(googleAuthService.signInWithOneTap()).rejects.toMatchObject({
        type: 'USER_CANCELLED',
        message: 'User cancelled Google Sign-In',
        recoverable: true
      })
    })

    it('should handle Google services not available', async () => {
      // Remove Google from window
      Object.defineProperty(window, 'google', {
        value: undefined,
        writable: true,
        configurable: true
      })

      await expect(googleAuthService.signInWithOneTap()).rejects.toThrow(GoogleAuthError)
      await expect(googleAuthService.signInWithOneTap()).rejects.toMatchObject({
        type: 'GOOGLE_UNAVAILABLE',
        message: 'Google Identity Services not available',
        recoverable: true
      })
    })
  })

  describe('signInWithButton', () => {
    let mockElement: HTMLElement

    beforeEach(async () => {
      // Mock successful initialization
      const mockScript = { onload: null, onerror: null, addEventListener: vi.fn() }
      vi.mocked(document.createElement).mockReturnValue(mockScript as any)
      vi.mocked(document.querySelector).mockReturnValue(null)

      const initPromise = googleAuthService.initialize()
      if (mockScript.onload) {
        mockScript.onload(new Event('load'))
      }
      await initPromise

      mockElement = document.createElement('div')
    })

    it('should render Google Sign-In button with default options', async () => {
      await googleAuthService.signInWithButton(mockElement)

      expect(mockGoogleAccounts.id.renderButton).toHaveBeenCalledWith(
        mockElement,
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

    it('should render Google Sign-In button with custom options', async () => {
      const customOptions = {
        type: 'icon' as const,
        theme: 'filled_blue' as const,
        size: 'medium' as const,
        text: 'signup_with' as const
      }

      await googleAuthService.signInWithButton(mockElement, customOptions)

      expect(mockGoogleAccounts.id.renderButton).toHaveBeenCalledWith(
        mockElement,
        {
          type: 'icon',
          theme: 'filled_blue',
          size: 'medium',
          text: 'signup_with',
          shape: 'rectangular',
          logo_alignment: 'left',
          width: '100%'
        }
      )
    })

    it('should throw error when Google services not available', async () => {
      Object.defineProperty(window, 'google', {
        value: undefined,
        writable: true,
        configurable: true
      })

      await expect(googleAuthService.signInWithButton(mockElement)).rejects.toThrow(GoogleAuthError)
      await expect(googleAuthService.signInWithButton(mockElement)).rejects.toMatchObject({
        type: 'GOOGLE_UNAVAILABLE',
        message: 'Google Identity Services not available',
        recoverable: true
      })
    })
  })

  describe('exchangeCredentialForTokens', () => {
    it('should successfully exchange credential for tokens', async () => {
      const mockResponse = {
        user: { id: 1, email: 'test@example.com', name: 'Test User' },
        access: 'access-token',
        refresh: 'refresh-token',
        created: true
      }

      mockApiClient.post.mockResolvedValue({ data: mockResponse })

      const result = await googleAuthService.exchangeCredentialForTokens('fake-credential')

      expect(result).toEqual(mockResponse)
      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/google/', {
        credential: 'fake-credential'
      })
    })

    it('should handle invalid credential error', async () => {
      const mockError = {
        response: {
          status: 400,
          data: { message: 'Invalid Google credential' }
        }
      }

      mockApiClient.post.mockRejectedValue(mockError)

      await expect(googleAuthService.exchangeCredentialForTokens('invalid-credential'))
        .rejects.toThrow(GoogleAuthError)

      await expect(googleAuthService.exchangeCredentialForTokens('invalid-credential'))
        .rejects.toMatchObject({
          type: 'TOKEN_INVALID',
          message: 'Invalid Google credential',
          recoverable: true
        })
    })

    it('should handle network error', async () => {
      const mockError = new Error('Network error')
      mockApiClient.post.mockRejectedValue(mockError)

      await expect(googleAuthService.exchangeCredentialForTokens('fake-credential'))
        .rejects.toThrow(GoogleAuthError)

      await expect(googleAuthService.exchangeCredentialForTokens('fake-credential'))
        .rejects.toMatchObject({
          type: 'NETWORK_ERROR',
          message: 'Network error during authentication',
          recoverable: true
        })
    })

    it('should handle server error', async () => {
      const mockError = {
        response: {
          status: 500,
          data: { message: 'Internal server error' }
        }
      }

      mockApiClient.post.mockRejectedValue(mockError)

      await expect(googleAuthService.exchangeCredentialForTokens('fake-credential'))
        .rejects.toThrow(GoogleAuthError)

      await expect(googleAuthService.exchangeCredentialForTokens('fake-credential'))
        .rejects.toMatchObject({
          type: 'NETWORK_ERROR',
          message: 'Authentication service error',
          recoverable: false
        })
    })
  })

  describe('linkGoogleAccount', () => {
    it('should successfully link Google account', async () => {
      const mockResponse = {
        message: 'Google account linked successfully',
        linked_email: 'test@gmail.com'
      }

      mockApiClient.post.mockResolvedValue({ data: mockResponse })

      const result = await googleAuthService.linkGoogleAccount('fake-credential')

      expect(result).toEqual(mockResponse)
      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/google/link/', {
        credential: 'fake-credential'
      })
    })

    it('should handle account already linked error', async () => {
      const mockError = {
        response: {
          status: 400,
          data: { message: 'This Google account is already linked to another user' }
        }
      }

      mockApiClient.post.mockRejectedValue(mockError)

      await expect(googleAuthService.linkGoogleAccount('fake-credential'))
        .rejects.toThrow('This Google account is already linked to another user')
    })

    it('should handle network error during linking', async () => {
      const mockError = new Error('Network error')
      mockApiClient.post.mockRejectedValue(mockError)

      await expect(googleAuthService.linkGoogleAccount('fake-credential'))
        .rejects.toThrow('Network error during account linking')
    })
  })

  describe('unlinkGoogleAccount', () => {
    it('should successfully unlink Google account', async () => {
      const mockResponse = {
        message: 'Google account unlinked successfully'
      }

      mockApiClient.post.mockResolvedValue({ data: mockResponse })

      const result = await googleAuthService.unlinkGoogleAccount()

      expect(result).toEqual(mockResponse)
      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/google/unlink/')
    })

    it('should handle no Google account error', async () => {
      const mockError = {
        response: {
          status: 400,
          data: { message: 'No Google account linked to this user' }
        }
      }

      mockApiClient.post.mockRejectedValue(mockError)

      await expect(googleAuthService.unlinkGoogleAccount())
        .rejects.toThrow('No Google account linked to this user')
    })
  })

  describe('utility methods', () => {
    beforeEach(() => {
      // Set up window.google for these tests
      Object.defineProperty(window, 'google', {
        value: { accounts: mockGoogleAccounts },
        writable: true
      })
    })

    it('should disable auto select', () => {
      googleAuthService.disableAutoSelect()
      expect(mockGoogleAccounts.id.disableAutoSelect).toHaveBeenCalled()
    })

    it('should cancel ongoing flow', () => {
      googleAuthService.cancel()
      expect(mockGoogleAccounts.id.cancel).toHaveBeenCalled()
    })

    it('should check if Google is available', () => {
      expect(googleAuthService.isGoogleAvailable()).toBe(true)

      Object.defineProperty(window, 'google', {
        value: undefined,
        writable: true,
        configurable: true
      })
      expect(googleAuthService.isGoogleAvailable()).toBe(false)
    })

    it('should return client ID', () => {
      expect(googleAuthService.getClientId()).toBe('test-client-id')
    })

    it('should handle missing Google services gracefully in utility methods', () => {
      Object.defineProperty(window, 'google', {
        value: undefined,
        writable: true,
        configurable: true
      })

      // These should not throw errors
      expect(() => googleAuthService.disableAutoSelect()).not.toThrow()
      expect(() => googleAuthService.cancel()).not.toThrow()
      expect(googleAuthService.isGoogleAvailable()).toBe(false)
    })
  })

  describe('script loading', () => {
    it('should not load script if already exists', async () => {
      const existingScript = document.createElement('script')
      existingScript.src = 'https://accounts.google.com/gsi/client'

      vi.mocked(document.querySelector).mockReturnValue(existingScript)

      // Mock event listeners
      const addEventListenerSpy = vi.fn((event, handler) => {
        if (event === 'load') {
          setTimeout(handler, 0)
        }
      })
      existingScript.addEventListener = addEventListenerSpy

      await googleAuthService.initialize()

      expect(document.createElement).not.toHaveBeenCalled()
      expect(addEventListenerSpy).toHaveBeenCalledWith('load', expect.any(Function))
    })

    it('should handle script load error', async () => {
      const mockScript = {
        src: '',
        async: false,
        defer: false,
        onload: null,
        onerror: null,
        addEventListener: vi.fn()
      }

      vi.mocked(document.createElement).mockReturnValue(mockScript as any)
      vi.mocked(document.querySelector).mockReturnValue(null)

      const initPromise = googleAuthService.initialize()

      // Simulate script error
      setTimeout(() => {
        if (mockScript.onerror) {
          mockScript.onerror(new ErrorEvent('error'))
        }
      }, 0)

      await expect(initPromise).rejects.toThrow('Failed to load Google Identity Services')
    })
  })
})