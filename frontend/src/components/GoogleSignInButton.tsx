import React, { useRef, useEffect, useState } from 'react'
import { googleAuthService, GoogleAuthError, GoogleAuthResponse } from '@/services/googleAuth'
import { useAuthStore } from '@/stores/authStore'
import type { User } from '@/types'

interface GoogleSignInButtonProps {
  mode?: 'signin' | 'signup' | 'link'
  onSuccess?: (user: User, created: boolean) => void
  onError?: (error: GoogleAuthError) => void
  disabled?: boolean
  className?: string
  size?: 'large' | 'medium' | 'small'
  theme?: 'outline' | 'filled_blue' | 'filled_black'
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin'
}

export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
  mode = 'signin',
  onSuccess,
  onError,
  disabled = false,
  className = '',
  size = 'large',
  theme = 'outline',
  text
}) => {
  const buttonRef = useRef<HTMLDivElement>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialized, setIsInitialized] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { setUser, setTokens } = useAuthStore()

  // Determine button text based on mode
  const getButtonText = () => {
    if (text) return text

    switch (mode) {
      case 'signup':
        return 'signup_with'
      case 'link':
        return 'continue_with'
      default:
        return 'signin_with'
    }
  }

  useEffect(() => {
    const initializeGoogleAuth = async () => {
      try {
        await googleAuthService.initialize()
        setIsInitialized(true)
        setError(null)
      } catch (err) {
        const googleError = err as GoogleAuthError
        setError(googleError.message)
        console.error('Failed to initialize Google Auth:', googleError)
      }
    }

    initializeGoogleAuth()
  }, [])

  useEffect(() => {
    if (!isInitialized || !buttonRef.current || disabled) {
      return
    }

    const handleGoogleResponse = async (response: any) => {
      setIsLoading(true)
      setError(null)

      try {
        const credential = response.credential
        let authResponse: GoogleAuthResponse

        if (mode === 'link') {
          // Handle account linking
          await googleAuthService.linkGoogleAccount(credential)
          // For link mode, we don't get user data back, so we'll need to handle this differently
          // For now, we'll just call the success callback with current user
          const currentUser = useAuthStore.getState().user
          if (currentUser && onSuccess) {
            onSuccess(currentUser, false)
          }
          return
        } else {
          // Handle sign in/sign up
          authResponse = await googleAuthService.exchangeCredentialForTokens(credential)
        }

        // Update auth store
        setUser(authResponse.user)
        setTokens(authResponse.access, authResponse.refresh)

        // Call success callback
        if (onSuccess) {
          onSuccess(authResponse.user, authResponse.created)
        }

      } catch (err) {
        const googleError = err as GoogleAuthError
        setError(googleError.message)

        if (onError) {
          onError(googleError)
        }

        console.error('Google authentication error:', googleError)
      } finally {
        setIsLoading(false)
      }
    }

    // Configure Google Sign-In
    if (window.google?.accounts?.id) {
      window.google.accounts.id.initialize({
        client_id: googleAuthService.getClientId(),
        callback: handleGoogleResponse,
        auto_select: false,
        cancel_on_tap_outside: true,
      })

      // Render the button
      window.google.accounts.id.renderButton(buttonRef.current, {
        type: 'standard',
        theme,
        size,
        text: getButtonText(),
        shape: 'rectangular',
        logo_alignment: 'left',
        width: '100%',
      })
    }

    // Cleanup function
    return () => {
      if (buttonRef.current) {
        buttonRef.current.innerHTML = ''
      }
    }
  }, [isInitialized, disabled, mode, size, theme, text, onSuccess, onError])

  // Fallback button for when Google Services aren't available
  const FallbackButton = () => (
    <button
      type="button"
      disabled={disabled || isLoading}
      className={`flex items-center justify-center w-full px-4 py-3 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${className}`}
      onClick={() => {
        setError('Google Sign-In is not available. Please try refreshing the page.')
      }}
    >
      <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
        <path
          fill="currentColor"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="currentColor"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        />
        <path
          fill="currentColor"
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        />
        <path
          fill="currentColor"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        />
      </svg>
      {isLoading ? 'Signing in...' : `${mode === 'signup' ? 'Sign up' : mode === 'link' ? 'Link account' : 'Sign in'} with Google`}
    </button>
  )

  // Show error message
  if (error && !isInitialized) {
    return (
      <div className={className}>
        <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg">
          {error}
        </div>
        <div className="mt-2">
          <FallbackButton />
        </div>
      </div>
    )
  }

  // Show loading state while initializing
  if (!isInitialized) {
    return (
      <div className={`flex items-center justify-center w-full px-4 py-3 text-sm text-gray-500 bg-gray-100 border border-gray-200 rounded-lg animate-pulse ${className}`}>
        <svg className="w-5 h-5 mr-3 animate-spin" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        Loading Google Sign-In...
      </div>
    )
  }

  return (
    <div className={className}>
      {error && (
        <div className="mb-3 p-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded">
          {error}
        </div>
      )}
      <div
        ref={buttonRef}
        className={isLoading ? 'opacity-50 pointer-events-none' : ''}
      />
      {isLoading && (
        <div className="mt-2 text-center text-sm text-gray-500">
          Signing in...
        </div>
      )}
    </div>
  )
}