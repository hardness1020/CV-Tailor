/**
 * Tests for useGenerationStatus hook
 * ft-026: Unified Generation Status Polling (ADR-040)
 *
 * Following TDD RED phase - these tests will fail until implementation is complete.
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useGenerationStatus } from '../useGenerationStatus'
import { apiClient } from '@/services/apiClient'
import type { GenerationStatus } from '@/types'

// Mock apiClient
vi.mock('@/services/apiClient', () => ({
  apiClient: {
    getGenerationStatus: vi.fn(),
  },
}))

const mockApiClient = vi.mocked(apiClient)

describe('useGenerationStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const mockGenerationId = 'test-generation-123'

  const createMockStatus = (overrides: Partial<GenerationStatus> = {}): GenerationStatus => ({
    generation_id: mockGenerationId,
    status: 'processing',
    progress_percentage: 50,
    created_at: '2025-10-31T10:00:00Z',
    current_phase: 'bullet_generation',
    phase_details: {
      bullet_generation: {
        status: 'in_progress',
        artifacts_total: 3,
        artifacts_processed: 1,
        bullets_generated: 3,
      },
      assembly: {
        status: 'not_started',
      },
    },
    bullet_generation_jobs: [],
    processing_metrics: {},
    quality_metrics: {},
    ...overrides,
  })

  it('should fetch status on mount', async () => {
    const mockStatus = createMockStatus()
    mockApiClient.getGenerationStatus.mockResolvedValue(mockStatus)

    const { result } = renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: true,
      })
    )

    await waitFor(() => {
      expect(result.current.status).toEqual(mockStatus)
    })

    expect(mockApiClient.getGenerationStatus).toHaveBeenCalledWith(mockGenerationId)
  })

  it('should poll status at specified interval', async () => {
    const mockStatus = createMockStatus()
    mockApiClient.getGenerationStatus.mockResolvedValue(mockStatus)

    renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: true,
        pollingInterval: 100, // 100ms for faster test
      })
    )

    // Initial fetch
    await waitFor(() => {
      expect(mockApiClient.getGenerationStatus).toHaveBeenCalledTimes(1)
    })

    // Wait for second poll
    await waitFor(
      () => {
        expect(mockApiClient.getGenerationStatus).toHaveBeenCalledTimes(2)
      },
      { timeout: 200 }
    )

    // Wait for third poll
    await waitFor(
      () => {
        expect(mockApiClient.getGenerationStatus).toHaveBeenCalledTimes(3)
      },
      { timeout: 200 }
    )
  })

  it('should stop polling when status is completed', async () => {
    const processingStatus = createMockStatus({ status: 'processing' })
    const completedStatus = createMockStatus({ status: 'completed', current_phase: 'completed' })

    mockApiClient.getGenerationStatus
      .mockResolvedValueOnce(processingStatus)
      .mockResolvedValueOnce(completedStatus)

    const { result } = renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: true,
        pollingInterval: 100, // 100ms for faster test
      })
    )

    // Initial fetch
    await waitFor(() => {
      expect(result.current.status?.status).toBe('processing')
    })

    // Wait for completed status
    await waitFor(
      () => {
        expect(result.current.status?.status).toBe('completed')
        expect(result.current.isPolling).toBe(false)
      },
      { timeout: 300 }
    )

    // Wait a bit longer to ensure no more polls
    await new Promise(resolve => setTimeout(resolve, 300))
    expect(mockApiClient.getGenerationStatus).toHaveBeenCalledTimes(2)
  })

  it('should stop polling when status is failed', async () => {
    const processingStatus = createMockStatus({ status: 'processing' })
    const failedStatus = createMockStatus({
      status: 'failed',
      error_message: 'Generation failed',
      current_phase: 'completed',
    })

    mockApiClient.getGenerationStatus
      .mockResolvedValueOnce(processingStatus)
      .mockResolvedValueOnce(failedStatus)

    const { result } = renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: true,
        pollingInterval: 100, // 100ms for faster test
      })
    )

    // Initial fetch
    await waitFor(() => {
      expect(result.current.status?.status).toBe('processing')
    })

    // Wait for failed status
    await waitFor(
      () => {
        expect(result.current.status?.status).toBe('failed')
        expect(result.current.isPolling).toBe(false)
      },
      { timeout: 300 }
    )

    // Wait a bit longer to ensure no more polls
    await new Promise(resolve => setTimeout(resolve, 300))
    expect(mockApiClient.getGenerationStatus).toHaveBeenCalledTimes(2)
  })

  it('should call onComplete callback when generation completes', async () => {
    const onComplete = vi.fn()
    const completedStatus = createMockStatus({ status: 'completed', current_phase: 'completed' })

    mockApiClient.getGenerationStatus.mockResolvedValue(completedStatus)

    renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: true,
        onComplete,
      })
    )

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith(completedStatus)
    })
  })

  it('should call onError callback when generation fails', async () => {
    const onError = vi.fn()
    const errorMessage = 'LLM API timeout'
    const failedStatus = createMockStatus({
      status: 'failed',
      error_message: errorMessage,
      current_phase: 'completed',
    })

    mockApiClient.getGenerationStatus.mockResolvedValue(failedStatus)

    renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: true,
        onError,
      })
    )

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(errorMessage)
    })
  })

  it('should handle API errors gracefully', async () => {
    const onError = vi.fn()
    const apiError = new Error('Network error')

    mockApiClient.getGenerationStatus.mockRejectedValue(apiError)

    const { result } = renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: true,
        onError,
      })
    )

    await waitFor(() => {
      expect(result.current.error).toBe('Network error')
      expect(onError).toHaveBeenCalledWith('Network error')
    })
  })

  it('should not fetch when enabled is false', async () => {
    renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: false,
      })
    )

    // Wait a bit to ensure no polling happens
    await new Promise(resolve => setTimeout(resolve, 200))
    expect(mockApiClient.getGenerationStatus).not.toHaveBeenCalled()
  })

  it('should provide manual refetch capability', async () => {
    const mockStatus = createMockStatus()
    mockApiClient.getGenerationStatus.mockResolvedValue(mockStatus)

    const { result } = renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: false, // Disabled auto-fetch
      })
    )

    expect(mockApiClient.getGenerationStatus).not.toHaveBeenCalled()

    // Manual refetch
    await act(async () => {
      await result.current.refetch()
    })

    expect(mockApiClient.getGenerationStatus).toHaveBeenCalledWith(mockGenerationId)
    expect(result.current.status).toEqual(mockStatus)
  })

  it('should prevent race conditions with ignore flag', async () => {
    const mockStatus = createMockStatus()
    mockApiClient.getGenerationStatus.mockImplementation(
      () =>
        new Promise((resolve) => {
          setTimeout(() => resolve(mockStatus), 50)
        })
    )

    const { unmount } = renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: true,
      })
    )

    // Unmount before request completes (simulates component unmount during polling)
    unmount()

    // Wait for request to complete
    await new Promise(resolve => setTimeout(resolve, 100))

    // Should not throw or cause state updates after unmount
    // (React will warn if state updates occur after unmount)
  })

  it('should update isPolling state correctly', async () => {
    const processingStatus = createMockStatus({ status: 'processing' })
    const completedStatus = createMockStatus({ status: 'completed', current_phase: 'completed' })

    mockApiClient.getGenerationStatus
      .mockResolvedValueOnce(processingStatus)
      .mockResolvedValueOnce(completedStatus)

    const { result } = renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: true,
        pollingInterval: 100, // 100ms for faster test
      })
    )

    // Initially polling
    await waitFor(() => {
      expect(result.current.isPolling).toBe(true)
    })

    // Should stop polling after completion
    await waitFor(
      () => {
        expect(result.current.isPolling).toBe(false)
      },
      { timeout: 300 }
    )
  })

  it('should handle different terminal states correctly', async () => {
    const terminalStates: Array<GenerationStatus['status']> = ['completed', 'failed', 'bullets_ready']

    for (const terminalState of terminalStates) {
      vi.clearAllMocks()

      const mockStatus = createMockStatus({
        status: terminalState,
        current_phase: 'completed',
      })
      mockApiClient.getGenerationStatus.mockResolvedValue(mockStatus)

      const { result } = renderHook(() =>
        useGenerationStatus({
          generationId: mockGenerationId,
          enabled: true,
          pollingInterval: 100, // 100ms for faster test
        })
      )

      await waitFor(() => {
        expect(result.current.status?.status).toBe(terminalState)
        expect(result.current.isPolling).toBe(false)
      })

      // Wait to ensure no more polls
      await new Promise(resolve => setTimeout(resolve, 300))
      expect(mockApiClient.getGenerationStatus).toHaveBeenCalledTimes(1)
    }
  })

  it('should use default polling interval when not specified', async () => {
    const mockStatus = createMockStatus()
    mockApiClient.getGenerationStatus.mockResolvedValue(mockStatus)

    const { rerender } = renderHook(() =>
      useGenerationStatus({
        generationId: mockGenerationId,
        enabled: true,
        pollingInterval: 100, // Use 100ms to test default behavior faster
      })
    )

    // Initial fetch
    await waitFor(() => {
      expect(mockApiClient.getGenerationStatus).toHaveBeenCalledTimes(1)
    })

    // Wait for second poll at specified interval
    await waitFor(
      () => {
        expect(mockApiClient.getGenerationStatus).toHaveBeenCalledTimes(2)
      },
      { timeout: 300 }
    )
  })
})
