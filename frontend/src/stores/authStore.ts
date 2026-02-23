import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  googleLinked: boolean

  // Actions
  setUser: (user: User) => void
  setTokens: (access: string, refresh: string) => void
  clearAuth: () => void
  setLoading: (loading: boolean) => void
  setGoogleLinked: (linked: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      googleLinked: false,

      setUser: (user: User) => {
        set({ user, isAuthenticated: true })
      },

      setTokens: (access: string, refresh: string) => {
        set({
          accessToken: access,
          refreshToken: refresh,
          isAuthenticated: true
        })
      },

      clearAuth: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          googleLinked: false
        })
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },

      setGoogleLinked: (linked: boolean) => {
        set({ googleLinked: linked })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        googleLinked: state.googleLinked,
      }),
    }
  )
)