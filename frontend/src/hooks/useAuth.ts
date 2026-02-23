import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/stores/authStore'
import { apiClient } from '@/services/apiClient'
import type { RegisterData } from '@/types'

export function useAuth() {
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()
  const { setUser, setTokens, clearAuth } = useAuthStore()

  const login = async (email: string, password: string) => {
    setIsLoading(true)
    try {
      const response = await apiClient.login(email, password)
      setUser(response.user)
      setTokens(response.access, response.refresh)
      toast.success('Welcome back!')
      navigate('/dashboard', { replace: true })
    } catch (error) {
      console.error('Login error:', error)
      toast.error('Invalid email or password')
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (userData: RegisterData) => {
    setIsLoading(true)
    try {
      const response = await apiClient.register(userData)
      setUser(response.user)
      setTokens(response.access, response.refresh)
      toast.success('Account created successfully!')
      navigate('/dashboard', { replace: true })
    } catch (error) {
      console.error('Registration error:', error)
      toast.error('Failed to create account. Please try again.')
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    setIsLoading(true)
    try {
      await apiClient.logout()
      clearAuth()
      toast.success('Logged out successfully')
      navigate('/login', { replace: true })
    } catch (error) {
      console.error('Logout error:', error)
      clearAuth()
      navigate('/login', { replace: true })
    } finally {
      setIsLoading(false)
    }
  }

  return {
    login,
    register,
    logout,
    isLoading,
  }
}