/**
 * Google Authentication Service
 *
 * This service handles Google Sign-In integration using Google Identity Services.
 * It provides methods for initializing Google Sign-In, handling authentication,
 * and managing the OAuth flow with our backend API.
 */

import { apiClient } from './apiClient'
import type { User } from '@/types'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: GoogleIdConfiguration) => void
          prompt: (callback?: (notification: PromptMomentNotification) => void) => void
          renderButton: (parent: HTMLElement, options: GsiButtonConfiguration) => void
          disableAutoSelect: () => void
          storeCredential: (credentials: any, callback?: () => void) => void
          cancel: () => void
          onGoogleLibraryLoad: () => void
        }
      }
    }
  }
}

interface GoogleIdConfiguration {
  client_id: string
  callback: (response: CredentialResponse) => void
  auto_select?: boolean
  cancel_on_tap_outside?: boolean
  context?: 'signin' | 'signup' | 'use'
  ux_mode?: 'popup' | 'redirect'
  login_uri?: string
  native_callback?: (response: any) => void
  intermediate_iframe_close_callback?: () => void
  itp_support?: boolean
  state_cookie_domain?: string
  allowed_parent_origin?: string | string[]
  native_login_uri?: string
  hd?: string
}

interface CredentialResponse {
  credential: string
  select_by: string
  client_id?: string
}

interface PromptMomentNotification {
  isDisplayMoment: () => boolean
  isDisplayed: () => boolean
  isNotDisplayed: () => boolean
  isSkippedMoment: () => boolean
  isDismissedMoment: () => boolean
  getDismissedReason: () => 'credential_returned' | 'cancel_called' | 'flow_restarted' | 'tap_outside'
  getMomentType: () => 'display' | 'skipped' | 'dismissed'
  getNotDisplayedReason: () => 'browser_not_supported' | 'invalid_client' | 'missing_client_id' | 'opt_out_or_no_session' | 'secure_http_required' | 'suppressed_by_user' | 'unregistered_origin' | 'unknown_reason'
  getSkippedReason: () => 'auto_cancel' | 'user_cancel' | 'tap_outside' | 'issuing_failed'
}

interface GsiButtonConfiguration {
  type?: 'standard' | 'icon'
  theme?: 'outline' | 'filled_blue' | 'filled_black'
  size?: 'large' | 'medium' | 'small'
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin'
  shape?: 'rectangular' | 'pill' | 'circle' | 'square'
  logo_alignment?: 'left' | 'center'
  width?: string | number
  locale?: string
  click_listener?: () => void
}

export interface GoogleAuthErrorType {
  type: 'GOOGLE_UNAVAILABLE' | 'TOKEN_INVALID' | 'USER_CANCELLED' | 'NETWORK_ERROR' | 'INVALID_CONFIGURATION'
  message: string
  recoverable: boolean
}

export interface GoogleAuthResponse {
  user: User
  access: string
  refresh: string
  created: boolean
}

export class GoogleAuthService {
  private clientId: string
  private isInitialized = false
  private initializationPromise: Promise<void> | null = null

  constructor(clientId?: string) {
    this.clientId = clientId || import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

    if (!this.clientId) {
      console.warn('Google Client ID not found. Set VITE_GOOGLE_CLIENT_ID environment variable.')
    }
  }

  /**
   * Initialize Google Identity Services
   * This method loads the Google Identity Services library and initializes it
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      return
    }

    if (this.initializationPromise) {
      return this.initializationPromise
    }

    this.initializationPromise = this._initialize()
    return this.initializationPromise
  }

  private async _initialize(): Promise<void> {
    if (!this.clientId) {
      throw new GoogleAuthError({
        type: 'INVALID_CONFIGURATION',
        message: 'Google Client ID is required',
        recoverable: false
      })
    }

    // Load Google Identity Services script
    await this.loadGoogleScript()

    // Wait for Google library to be available
    if (!window.google?.accounts?.id) {
      throw new GoogleAuthError({
        type: 'GOOGLE_UNAVAILABLE',
        message: 'Google Identity Services failed to load',
        recoverable: true
      })
    }

    this.isInitialized = true
  }

  /**
   * Load Google Identity Services script dynamically
   */
  private loadGoogleScript(): Promise<void> {
    return new Promise((resolve, reject) => {
      // Check if script is already loaded
      if (window.google?.accounts?.id) {
        resolve()
        return
      }

      // Check if script element already exists
      const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]')
      if (existingScript) {
        existingScript.addEventListener('load', () => resolve())
        existingScript.addEventListener('error', () => reject(new Error('Failed to load Google Identity Services')))
        return
      }

      // Create and load script
      const script = document.createElement('script')
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.defer = true

      script.onload = () => resolve()
      script.onerror = () => reject(new Error('Failed to load Google Identity Services'))

      document.head.appendChild(script)
    })
  }

  /**
   * Sign in with Google using the One Tap prompt
   */
  async signInWithOneTap(): Promise<GoogleAuthResponse> {
    await this.initialize()

    return new Promise((resolve, reject) => {
      if (!window.google?.accounts?.id) {
        reject(new GoogleAuthError({
          type: 'GOOGLE_UNAVAILABLE',
          message: 'Google Identity Services not available',
          recoverable: true
        }))
        return
      }

      window.google.accounts.id.initialize({
        client_id: this.clientId,
        callback: async (response: CredentialResponse) => {
          try {
            const authResponse = await this.exchangeCredentialForTokens(response.credential)
            resolve(authResponse)
          } catch (error) {
            reject(error)
          }
        },
        auto_select: false,
        cancel_on_tap_outside: true,
      })

      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed()) {
          reject(new GoogleAuthError({
            type: 'GOOGLE_UNAVAILABLE',
            message: `Google Sign-In not available: ${notification.getNotDisplayedReason()}`,
            recoverable: false
          }))
        } else if (notification.isDismissedMoment()) {
          const reason = notification.getDismissedReason()
          if (reason === 'cancel_called' || reason === 'tap_outside') {
            reject(new GoogleAuthError({
              type: 'USER_CANCELLED',
              message: 'User cancelled Google Sign-In',
              recoverable: true
            }))
          }
        }
      })
    })
  }

  /**
   * Sign in with Google using a button
   * This method should be called when a user clicks a Google Sign-In button
   */
  async signInWithButton(buttonElement: HTMLElement, options?: GsiButtonConfiguration): Promise<void> {
    await this.initialize()

    if (!window.google?.accounts?.id) {
      throw new GoogleAuthError({
        type: 'GOOGLE_UNAVAILABLE',
        message: 'Google Identity Services not available',
        recoverable: true
      })
    }

    const defaultOptions: GsiButtonConfiguration = {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      text: 'signin_with',
      shape: 'rectangular',
      logo_alignment: 'left',
      width: '100%',
    }

    window.google.accounts.id.renderButton(buttonElement, {
      ...defaultOptions,
      ...options
    })
  }

  /**
   * Exchange Google credential for our app's JWT tokens
   */
  async exchangeCredentialForTokens(credential: string): Promise<GoogleAuthResponse> {
    try {
      const response = await apiClient.client.post('/v1/auth/google/', {
        credential
      })

      return response.data
    } catch (error: any) {
      if (error.response?.status === 400) {
        throw new GoogleAuthError({
          type: 'TOKEN_INVALID',
          message: error.response.data?.message || 'Invalid Google credential',
          recoverable: true
        })
      } else if (!error.response) {
        throw new GoogleAuthError({
          type: 'NETWORK_ERROR',
          message: 'Network error during authentication',
          recoverable: true
        })
      } else {
        throw new GoogleAuthError({
          type: 'NETWORK_ERROR',
          message: 'Authentication service error',
          recoverable: false
        })
      }
    }
  }

  /**
   * Link Google account to existing user account
   */
  async linkGoogleAccount(credential: string): Promise<{ message: string; linked_email: string }> {
    try {
      const response = await apiClient.client.post('/v1/auth/google/link/', {
        credential
      })

      return response.data
    } catch (error: any) {
      if (error.response?.status === 400) {
        throw new Error(error.response.data?.message || 'Failed to link Google account')
      } else {
        throw new Error('Network error during account linking')
      }
    }
  }

  /**
   * Unlink Google account from user account
   */
  async unlinkGoogleAccount(): Promise<{ message: string }> {
    try {
      const response = await apiClient.client.post('/v1/auth/google/unlink/')
      return response.data
    } catch (error: any) {
      if (error.response?.status === 400) {
        throw new Error(error.response.data?.message || 'Failed to unlink Google account')
      } else {
        throw new Error('Network error during account unlinking')
      }
    }
  }

  /**
   * Disable auto-select for Google Sign-In
   */
  disableAutoSelect(): void {
    if (window.google?.accounts?.id) {
      window.google.accounts.id.disableAutoSelect()
    }
  }

  /**
   * Cancel any ongoing Google Sign-In flow
   */
  cancel(): void {
    if (window.google?.accounts?.id) {
      window.google.accounts.id.cancel()
    }
  }

  /**
   * Check if Google Identity Services is available
   */
  isGoogleAvailable(): boolean {
    return !!(window.google?.accounts?.id)
  }

  /**
   * Get the configured client ID
   */
  getClientId(): string {
    return this.clientId
  }
}

// Custom error class for Google authentication errors
class GoogleAuthError extends Error {
  public type: GoogleAuthErrorType['type']
  public recoverable: boolean

  constructor({ type, message, recoverable }: { type: GoogleAuthErrorType['type'], message: string, recoverable: boolean }) {
    super(message)
    this.name = 'GoogleAuthError'
    this.type = type
    this.recoverable = recoverable
  }
}

// Export singleton instance
export const googleAuthService = new GoogleAuthService()

// Export error class for type checking
export { GoogleAuthError }