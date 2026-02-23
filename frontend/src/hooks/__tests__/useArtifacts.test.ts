import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { useArtifacts } from '../useArtifacts'
import { apiClient } from '@/services/apiClient'
import { useArtifactStore } from '@/stores/artifactStore'

// Mock stores
vi.mock('@/stores/artifactStore', () => ({
  useArtifactStore: vi.fn(),
}))

const mockUseArtifactStore = vi.mocked(useArtifactStore)
const mockApiClient = vi.mocked(apiClient)

describe('useArtifacts', () => {
  const mockSetArtifacts = vi.fn()
  const mockAddArtifact = vi.fn()
  const mockUpdateArtifact = vi.fn()
  const mockDeleteArtifact = vi.fn()
  const mockSetLoading = vi.fn()
  const mockSetError = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseArtifactStore.mockReturnValue({
      artifacts: [],
      selectedArtifacts: [],
      filters: {},
      isLoading: false,
      error: null,
      setArtifacts: mockSetArtifacts,
      addArtifact: mockAddArtifact,
      updateArtifact: mockUpdateArtifact,
      deleteArtifact: mockDeleteArtifact,
      setLoading: mockSetLoading,
      setError: mockSetError,
      toggleSelection: vi.fn(),
      clearSelection: vi.fn(),
      setFilters: vi.fn(),
    })
  })

  it('should load artifacts successfully', async () => {
    const mockArtifacts = [
      {
        id: 1,
        title: 'Test Artifact',
        description: 'Test Description',
        technologies: ['React', 'TypeScript'],
        startDate: '2023-01-01',
        endDate: '2023-12-31',
        status: 'active' as const,
        evidenceLinks: [],
        labels: [],
      },
    ]

    mockApiClient.getArtifacts.mockResolvedValue({
      results: mockArtifacts,
      count: 1,
      next: null,
      previous: null,
    })

    const { result } = renderHook(() => useArtifacts())

    await act(async () => {
      await result.current.loadArtifacts()
    })

    expect(mockSetLoading).toHaveBeenCalledWith(true)
    expect(mockApiClient.getArtifacts).toHaveBeenCalled()
    expect(mockSetArtifacts).toHaveBeenCalledWith(mockArtifacts)
    expect(mockSetLoading).toHaveBeenCalledWith(false)
  })

  it('should create artifact successfully', async () => {
    const mockArtifact = {
      id: 1,
      title: 'New Artifact',
      description: 'New Description',
      technologies: ['React'],
      startDate: '2023-01-01',
      endDate: '2023-12-31',
      status: 'active' as const,
      evidenceLinks: [],
      labels: [],
    }

    const createData = {
      title: 'New Artifact',
      description: 'New Description',
      technologies: ['React'],
      startDate: '2023-01-01',
      endDate: '2023-12-31',
      evidenceLinks: [],
      labelIds: [],
    }

    mockApiClient.createArtifact.mockResolvedValue(mockArtifact)

    const { result } = renderHook(() => useArtifacts())

    await act(async () => {
      await result.current.createArtifact(createData)
    })

    expect(mockApiClient.createArtifact).toHaveBeenCalledWith(createData)
    expect(mockAddArtifact).toHaveBeenCalledWith(mockArtifact)
  })

  it('should delete artifact successfully', async () => {
    mockApiClient.deleteArtifact.mockResolvedValue(undefined)

    const { result } = renderHook(() => useArtifacts())

    await act(async () => {
      await result.current.deleteArtifact(1)
    })

    expect(mockApiClient.deleteArtifact).toHaveBeenCalledWith(1)
    expect(mockDeleteArtifact).toHaveBeenCalledWith(1)
  })

  it('should handle bulk delete', async () => {
    mockApiClient.deleteArtifact.mockResolvedValue(undefined)

    const { result } = renderHook(() => useArtifacts())

    await act(async () => {
      await result.current.bulkDelete([1, 2, 3])
    })

    expect(mockApiClient.deleteArtifact).toHaveBeenCalledTimes(3)
    expect(mockDeleteArtifact).toHaveBeenCalledWith(1)
    expect(mockDeleteArtifact).toHaveBeenCalledWith(2)
    expect(mockDeleteArtifact).toHaveBeenCalledWith(3)
  })

  it('should handle API errors', async () => {
    const mockError = new Error('API Error')
    mockApiClient.getArtifacts.mockRejectedValue(mockError)

    const { result } = renderHook(() => useArtifacts())

    await act(async () => {
      await result.current.loadArtifacts()
    })

    expect(mockSetError).toHaveBeenCalledWith(mockError.message)
    expect(mockSetLoading).toHaveBeenCalledWith(false)
  })
})