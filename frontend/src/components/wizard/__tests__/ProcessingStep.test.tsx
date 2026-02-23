/**
 * Unit tests for ProcessingStep component (ft-045)
 * TDD Stage F - RED Phase: These tests will fail initially until implementation in Stage G
 *
 * Tests the blocking processing step that polls enrichment_status and auto-advances
 * to Evidence Review step when extraction completes.
 */

import { render, screen, waitFor } from '@/test/utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { act } from 'react-dom/test-utils'

// Import types (will be implemented in Stage G)
type ProcessingStepProps = {
  artifactId: string
  onProcessingComplete: () => void
  onError: (error: string) => void
}

// Mock component that will fail until implementation
const ProcessingStep: React.FC<ProcessingStepProps> = () => {
  throw new Error(
    'NotImplementedError: ProcessingStep component not yet implemented. ' +
    'Expected: Blocking processing screen with LoadingOverlay, polls enrichment_status every 3s, ' +
    'auto-advances on completion. ' +
    'See: docs/specs/spec-frontend.md (v3.0.0) Evidence Review & Acceptance Workflow'
  )
}

// Mock API client
const mockApiClient = {
  getArtifact: vi.fn()
}

vi.mock('@/lib/api', () => ({
  default: mockApiClient
}))

describe('ProcessingStep Component', () => {
  const mockOnComplete = vi.fn()
  const mockOnError = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  describe('AC 1: Polling Behavior', () => {
    it('should poll enrichment_status every 3 seconds', async () => {
      // Mock artifact with 'processing' status
      mockApiClient.getArtifact.mockResolvedValue({
        id: 123,
        enrichment_status: 'processing'
      })

      expect(() => {
        render(
          <ProcessingStep
            artifactId="123"
            onProcessingComplete={mockOnComplete}
            onError={mockOnError}
          />
        )
      }).toThrow(/NotImplementedError/)

      // After implementation:
      // - Should call getArtifact immediately on mount
      // - Should poll every 3000ms
      // - Should continue polling while status is 'processing'

      // Example assertion (will work after implementation):
      // expect(mockApiClient.getArtifact).toHaveBeenCalledTimes(1)
      //
      // act(() => {
      //   vi.advanceTimersByTime(3000) // 3 seconds
      // })
      //
      // await waitFor(() => {
      //   expect(mockApiClient.getArtifact).toHaveBeenCalledTimes(2)
      // })
    })

    it('should stop polling when enrichment_status is completed', async () => {
      // First call: processing, second call: completed
      mockApiClient.getArtifact
        .mockResolvedValueOnce({
          id: 123,
          enrichment_status: 'processing'
        })
        .mockResolvedValueOnce({
          id: 123,
          enrichment_status: 'completed'
        })

      expect(() => {
        render(
          <ProcessingStep
            artifactId="123"
            onProcessingComplete={mockOnComplete}
            onError={mockOnError}
          />
        )
      }).toThrow(/NotImplementedError/)

      // After implementation:
      // - Should stop polling after status becomes 'completed'
      // - Should not make additional API calls

      // Example assertion (will work after implementation):
      // act(() => {
      //   vi.advanceTimersByTime(3000)
      // })
      //
      // await waitFor(() => {
      //   expect(mockOnComplete).toHaveBeenCalledTimes(1)
      // })
      //
      // // No more polling
      // act(() => {
      //   vi.advanceTimersByTime(6000)
      // })
      //
      // // Still only 2 calls (initial + one poll)
      // expect(mockApiClient.getArtifact).toHaveBeenCalledTimes(2)
    })
  })

  describe('AC 2: Auto-advance on Completion', () => {
    it('should call onProcessingComplete when status becomes completed', async () => {
      mockApiClient.getArtifact.mockResolvedValue({
        id: 123,
        enrichment_status: 'completed'
      })

      expect(() => {
        render(
          <ProcessingStep
            artifactId="123"
            onProcessingComplete={mockOnComplete}
            onError={mockOnError}
          />
        )
      }).toThrow(/NotImplementedError/)

      // After implementation:
      // - Should call onProcessingComplete immediately if already completed
      // - Should trigger wizard to advance to Step 6 (Evidence Review)

      // Example assertion (will work after implementation):
      // await waitFor(() => {
      //   expect(mockOnComplete).toHaveBeenCalledTimes(1)
      // })
    })
  })

  describe('AC 3: Error Handling', () => {
    it('should call onError when enrichment_status is failed', async () => {
      mockApiClient.getArtifact.mockResolvedValue({
        id: 123,
        enrichment_status: 'failed',
        enrichment_error: 'GitHub API rate limit exceeded'
      })

      expect(() => {
        render(
          <ProcessingStep
            artifactId="123"
            onProcessingComplete={mockOnComplete}
            onError={mockOnError}
          />
        )
      }).toThrow(/NotImplementedError/)

      // After implementation:
      // - Should call onError with error message
      // - Should stop polling
      // - Should display error message to user

      // Example assertion (will work after implementation):
      // await waitFor(() => {
      //   expect(mockOnError).toHaveBeenCalledWith('GitHub API rate limit exceeded')
      // })
      //
      // expect(mockOnComplete).not.toHaveBeenCalled()
    })

    it('should handle network errors gracefully', async () => {
      mockApiClient.getArtifact.mockRejectedValue(new Error('Network error'))

      expect(() => {
        render(
          <ProcessingStep
            artifactId="123"
            onProcessingComplete={mockOnComplete}
            onError={mockOnError}
          />
        )
      }).toThrow(/NotImplementedError/)

      // After implementation:
      // - Should retry on network errors (exponential backoff)
      // - Should call onError after max retries
      // - Should display user-friendly error message
    })
  })

  describe('AC 4: UI Display', () => {
    it('should display LoadingOverlay with processing message', () => {
      mockApiClient.getArtifact.mockResolvedValue({
        id: 123,
        enrichment_status: 'processing'
      })

      expect(() => {
        render(
          <ProcessingStep
            artifactId="123"
            onProcessingComplete={mockOnComplete}
            onError={mockOnError}
          />
        )
      }).toThrow(/NotImplementedError/)

      // After implementation:
      // - Should render LoadingOverlay component
      // - Should display message: "Extracting content from your evidence sources..."
      // - Should show spinner animation
      // - Should be non-dismissible (blocking)

      // Example assertion (will work after implementation):
      // expect(screen.getByText(/Extracting content from your evidence/i)).toBeInTheDocument()
      // expect(screen.getByRole('status')).toBeInTheDocument() // Spinner
    })
  })

  describe('AC 5: Performance SLO', () => {
    it('should unblock within 30 seconds for typical artifacts', async () => {
      // Mock typical processing time (15 seconds)
      mockApiClient.getArtifact
        .mockResolvedValueOnce({ enrichment_status: 'processing' })
        .mockResolvedValueOnce({ enrichment_status: 'processing' })
        .mockResolvedValueOnce({ enrichment_status: 'processing' })
        .mockResolvedValueOnce({ enrichment_status: 'processing' })
        .mockResolvedValueOnce({ enrichment_status: 'completed' }) // After 15s

      expect(() => {
        render(
          <ProcessingStep
            artifactId="123"
            onProcessingComplete={mockOnComplete}
            onError={mockOnError}
          />
        )
      }).toThrow(/NotImplementedError/)

      // After implementation:
      // - Should complete in 15 seconds (5 polls × 3s)
      // - Performance SLO: <30 seconds for 95% of cases

      // Example assertion (will work after implementation):
      // for (let i = 0; i < 5; i++) {
      //   act(() => {
      //     vi.advanceTimersByTime(3000)
      //   })
      // }
      //
      // await waitFor(() => {
      //   expect(mockOnComplete).toHaveBeenCalled()
      // })
    })
  })

  describe('AC 6: Cleanup', () => {
    it('should cleanup polling interval on unmount', () => {
      mockApiClient.getArtifact.mockResolvedValue({
        enrichment_status: 'processing'
      })

      expect(() => {
        const { unmount } = render(
          <ProcessingStep
            artifactId="123"
            onProcessingComplete={mockOnComplete}
            onError={mockOnError}
          />
        )

        // After implementation:
        // unmount()
        //
        // act(() => {
        //   vi.advanceTimersByTime(10000)
        // })
        //
        // // Should not continue polling after unmount
        // expect(mockApiClient.getArtifact).toHaveBeenCalledTimes(1) // Only initial call
      }).toThrow(/NotImplementedError/)
    })
  })
})
