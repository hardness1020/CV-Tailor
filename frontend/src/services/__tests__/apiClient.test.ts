import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import axios from 'axios'
import { apiClient } from '../apiClient'

// Mock axios
vi.mock('axios')
const mockedAxios = vi.mocked(axios)

// Mock auth store
const mockSetTokens = vi.fn()
const mockClearAuth = vi.fn()
const mockGetState = vi.fn(() => ({
  accessToken: 'test-token',
  refreshToken: 'test-refresh-token',
  setTokens: mockSetTokens,
  clearAuth: mockClearAuth,
}))

vi.mock('@/stores/authStore', () => ({
  useAuthStore: {
    getState: mockGetState,
  },
}))

// Mock toast
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('ApiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Setup default axios create mock
    mockedAxios.create = vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      post: vi.fn(),
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    })) as any
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should have correct base configuration', () => {
    expect(apiClient).toBeDefined()
  })

  describe('Authentication methods', () => {
    it('should have login method', () => {
      expect(typeof apiClient.login).toBe('function')
    })

    it('should have register method', () => {
      expect(typeof apiClient.register).toBe('function')
    })

    it('should have logout method', () => {
      expect(typeof apiClient.logout).toBe('function')
    })

    it('should have getCurrentUser method', () => {
      expect(typeof apiClient.getCurrentUser).toBe('function')
    })
  })

  describe('Artifact methods', () => {
    it('should have getArtifacts method', () => {
      expect(typeof apiClient.getArtifacts).toBe('function')
    })

    it('should have createArtifact method', () => {
      expect(typeof apiClient.createArtifact).toBe('function')
    })

    it('should have updateArtifact method', () => {
      expect(typeof apiClient.updateArtifact).toBe('function')
    })

    it('should have deleteArtifact method', () => {
      expect(typeof apiClient.deleteArtifact).toBe('function')
    })

    it('should have getArtifact method', () => {
      expect(typeof apiClient.getArtifact).toBe('function')
    })

    it('should have uploadArtifactFiles method', () => {
      expect(typeof apiClient.uploadArtifactFiles).toBe('function')
    })
  })

  describe('Generation methods', () => {
    it('should have generateCV method', () => {
      expect(typeof apiClient.generateCV).toBe('function')
    })

    it('should have getGeneration method', () => {
      expect(typeof apiClient.getGeneration).toBe('function')
    })

    it('should have generateCoverLetter method', () => {
      expect(typeof apiClient.generateCoverLetter).toBe('function')
    })

    it('should have getUserGenerations method', () => {
      expect(typeof apiClient.getUserGenerations).toBe('function')
    })

    it('should have rateGeneration method', () => {
      expect(typeof apiClient.rateGeneration).toBe('function')
    })

    it('should have getCVTemplates method', () => {
      expect(typeof apiClient.getCVTemplates).toBe('function')
    })
  })

  describe('Export methods', () => {
    it('should have exportDocument method', () => {
      expect(typeof apiClient.exportDocument).toBe('function')
    })

    it('should have getExportStatus method', () => {
      expect(typeof apiClient.getExportStatus).toBe('function')
    })

    it('should have downloadExport method', () => {
      expect(typeof apiClient.downloadExport).toBe('function')
    })

    it('should have getUserExports method', () => {
      expect(typeof apiClient.getUserExports).toBe('function')
    })

    it('should have getExportTemplates method', () => {
      expect(typeof apiClient.getExportTemplates).toBe('function')
    })
  })

  describe('Labels and metadata methods', () => {
    it('should have getLabels method', () => {
      expect(typeof apiClient.getLabels).toBe('function')
    })

    it('should have createLabel method', () => {
      expect(typeof apiClient.createLabel).toBe('function')
    })

    it('should have suggestSkills method', () => {
      expect(typeof apiClient.suggestSkills).toBe('function')
    })
  })
})

describe('ApiClient Authentication Integration', () => {
  let mockAxiosInstance: any

  beforeEach(() => {
    vi.clearAllMocks()

    mockAxiosInstance = {
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      post: vi.fn(),
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    }

    mockedAxios.create = vi.fn(() => mockAxiosInstance)
  })

  describe('Login Integration', () => {
    it('should login successfully with valid credentials', async () => {
      const mockResponse = {
        data: {
          user: {
            id: 1,
            email: 'test@example.com',
            username: 'testuser',
            first_name: 'Test',
            last_name: 'User',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
          access: 'access-token',
          refresh: 'refresh-token',
        },
      }

      mockAxiosInstance.post.mockResolvedValue(mockResponse)

      const result = await apiClient.login('test@example.com', 'password123')

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/v1/auth/login/', {
        email: 'test@example.com',
        password: 'password123',
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle login failure', async () => {
      const mockError = {
        response: {
          status: 400,
          data: { error: 'Invalid credentials' },
        },
      }

      mockAxiosInstance.post.mockRejectedValue(mockError)

      await expect(apiClient.login('test@example.com', 'wrongpassword')).rejects.toThrow()
    })
  })

  describe('Registration Integration', () => {
    it('should register successfully with valid data', async () => {
      const mockResponse = {
        data: {
          user: {
            id: 2,
            email: 'newuser@example.com',
            username: 'newuser',
            first_name: 'New',
            last_name: 'User',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
          access: 'new-access-token',
          refresh: 'new-refresh-token',
        },
      }

      const registerData = {
        email: 'newuser@example.com',
        username: 'newuser',
        password: 'password123',
        password_confirm: 'password123',
        first_name: 'New',
        last_name: 'User',
      }

      mockAxiosInstance.post.mockResolvedValue(mockResponse)

      const result = await apiClient.register(registerData)

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/v1/auth/register/', registerData)
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle registration failure with password mismatch', async () => {
      const mockError = {
        response: {
          status: 400,
          data: { password: ["Passwords don't match."] },
        },
      }

      const registerData = {
        email: 'newuser@example.com',
        username: 'newuser',
        password: 'password123',
        password_confirm: 'differentpassword',
        first_name: 'New',
        last_name: 'User',
      }

      mockAxiosInstance.post.mockRejectedValue(mockError)

      await expect(apiClient.register(registerData)).rejects.toThrow()
    })
  })

  describe('Token Refresh Integration', () => {
    it('should refresh token successfully', async () => {
      const mockResponse = {
        data: {
          access: 'new-access-token',
          refresh: 'new-refresh-token',
        },
      }

      mockAxiosInstance.post.mockResolvedValue(mockResponse)

      const result = await apiClient.refreshToken()

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/v1/auth/token/refresh/', {
        refresh: 'test-refresh-token',
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle token refresh failure', async () => {
      const mockError = {
        response: {
          status: 401,
          data: { detail: 'Token is invalid or expired' },
        },
      }

      mockAxiosInstance.post.mockRejectedValue(mockError)

      await expect(apiClient.refreshToken()).rejects.toThrow()
    })
  })

  describe('User Profile Integration', () => {
    it('should get current user successfully', async () => {
      const mockResponse = {
        data: {
          id: 1,
          email: 'test@example.com',
          username: 'testuser',
          first_name: 'Test',
          last_name: 'User',
          bio: 'Test bio',
          location: 'Test City',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      }

      mockAxiosInstance.get.mockResolvedValue(mockResponse)

      const result = await apiClient.getCurrentUser()

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/v1/auth/profile/')
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle unauthorized access to profile', async () => {
      const mockError = {
        response: {
          status: 401,
          data: { detail: 'Authentication credentials were not provided.' },
        },
      }

      mockAxiosInstance.get.mockRejectedValue(mockError)

      await expect(apiClient.getCurrentUser()).rejects.toThrow()
    })
  })

  describe('Logout Integration', () => {
    it('should logout successfully', async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: { message: 'Successfully logged out' } })

      await apiClient.logout()

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/v1/auth/logout/', {
        refresh: 'test-refresh-token',
      })
    })

    it('should handle logout failure gracefully', async () => {
      const mockError = {
        response: {
          status: 400,
          data: { error: 'Invalid token' },
        },
      }

      mockAxiosInstance.post.mockRejectedValue(mockError)

      // Should not throw error, just log warning
      await expect(apiClient.logout()).resolves.toBeUndefined()
    })
  })

  describe('Authentication Flow Integration', () => {
    it('should handle complete authentication flow', async () => {
      // Step 1: Login
      const loginResponse = {
        data: {
          user: {
            id: 1,
            email: 'test@example.com',
            username: 'testuser',
            first_name: 'Test',
            last_name: 'User',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
          access: 'access-token',
          refresh: 'refresh-token',
        },
      }

      // Step 2: Get profile
      const profileResponse = {
        data: {
          id: 1,
          email: 'test@example.com',
          username: 'testuser',
          first_name: 'Test',
          last_name: 'User',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      }

      // Step 3: Logout
      const logoutResponse = {
        data: { message: 'Successfully logged out' },
      }

      mockAxiosInstance.post
        .mockResolvedValueOnce(loginResponse) // Login
        .mockResolvedValueOnce(logoutResponse) // Logout

      mockAxiosInstance.get.mockResolvedValue(profileResponse) // Get profile

      // Execute flow
      const loginResult = await apiClient.login('test@example.com', 'password123')
      expect(loginResult).toEqual(loginResponse.data)

      const profileResult = await apiClient.getCurrentUser()
      expect(profileResult).toEqual(profileResponse.data)

      await apiClient.logout()

      expect(mockAxiosInstance.post).toHaveBeenCalledTimes(2) // Login + Logout
      expect(mockAxiosInstance.get).toHaveBeenCalledTimes(1) // Get profile
    })
  })
})

describe('ApiClient Error Handling', () => {
  let mockAxiosInstance: any

  beforeEach(() => {
    vi.clearAllMocks()

    mockAxiosInstance = {
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      post: vi.fn(),
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    }

    mockedAxios.create = vi.fn(() => mockAxiosInstance)
  })

  it('should handle network errors', async () => {
    const networkError = new Error('Network Error')
    mockAxiosInstance.post.mockRejectedValue(networkError)

    await expect(apiClient.login('test@example.com', 'password123')).rejects.toThrow('Network Error')
  })

  it('should handle server errors (500)', async () => {
    const serverError = {
      response: {
        status: 500,
        data: { error: 'Internal Server Error' },
      },
    }

    mockAxiosInstance.post.mockRejectedValue(serverError)

    await expect(apiClient.login('test@example.com', 'password123')).rejects.toThrow()
  })

  it('should handle validation errors (400)', async () => {
    const validationError = {
      response: {
        status: 400,
        data: {
          email: ['This field is required.'],
          password: ['This field is required.'],
        },
      },
    }

    mockAxiosInstance.post.mockRejectedValue(validationError)

    await expect(apiClient.register({
      email: '',
      username: 'test',
      password: '',
      password_confirm: '',
      first_name: 'Test',
      last_name: 'User',
    })).rejects.toThrow()
  })
})

describe('ApiClient Additional Authentication Features', () => {
  let mockAxiosInstance: any

  beforeEach(() => {
    vi.clearAllMocks()

    mockAxiosInstance = {
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      post: vi.fn(),
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    }

    mockedAxios.create = vi.fn(() => mockAxiosInstance)
  })

  describe('Profile Management', () => {
    it('should update user profile successfully', async () => {
      const mockResponse = {
        data: {
          id: 1,
          email: 'test@example.com',
          username: 'testuser',
          first_name: 'Updated',
          last_name: 'Name',
          bio: 'Updated bio',
          location: 'New York',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      }

      const updateData = {
        first_name: 'Updated',
        last_name: 'Name',
        bio: 'Updated bio',
        location: 'New York',
      }

      mockAxiosInstance.patch.mockResolvedValue(mockResponse)

      const result = await apiClient.updateProfile(updateData)

      expect(mockAxiosInstance.patch).toHaveBeenCalledWith('/v1/auth/profile/', updateData)
      expect(result).toEqual(mockResponse.data)
    })

    it('should change password successfully', async () => {
      const passwordData = {
        current_password: 'oldpass123',
        new_password: 'newpass123',
        new_password_confirm: 'newpass123',
      }

      mockAxiosInstance.post.mockResolvedValue({ data: { message: 'Password changed successfully' } })

      await apiClient.changePassword(passwordData)

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/v1/auth/change-password/', passwordData)
    })

    it('should request password reset successfully', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { message: 'If this email exists, a password reset link has been sent' },
      })

      await apiClient.requestPasswordReset('test@example.com')

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/v1/auth/password-reset/', {
        email: 'test@example.com',
      })
    })
  })

  describe('Security and Validation', () => {
    it('should handle password strength validation', async () => {
      const weakPasswordData = {
        email: 'test@example.com',
        username: 'testuser',
        password: '123',
        password_confirm: '123',
        first_name: 'Test',
        last_name: 'User',
      }

      const mockError = {
        response: {
          status: 400,
          data: {
            password: [
              'This password is too short. It must contain at least 8 characters.',
              'This password is too common.',
            ],
          },
        },
      }

      mockAxiosInstance.post.mockRejectedValue(mockError)

      await expect(apiClient.register(weakPasswordData)).rejects.toThrow()
    })

    it('should handle registration with existing email', async () => {
      const mockError = {
        response: {
          status: 400,
          data: { email: ['A user with this email already exists.'] },
        },
      }

      const registerData = {
        email: 'existing@example.com',
        username: 'newuser',
        password: 'password123',
        password_confirm: 'password123',
        first_name: 'New',
        last_name: 'User',
      }

      mockAxiosInstance.post.mockRejectedValue(mockError)

      await expect(apiClient.register(registerData)).rejects.toThrow()
    })
  })
})