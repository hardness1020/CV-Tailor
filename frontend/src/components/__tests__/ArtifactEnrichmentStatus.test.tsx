import { render, screen, waitFor } from '@/test/utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { ArtifactEnrichmentStatus } from '../ArtifactEnrichmentStatus'
import { apiClient } from '@/services/apiClient'

// Mock apiClient
vi.mock('@/services/apiClient', () => ({
  apiClient: {
    get: vi.fn(),
  },
}))

const mockApiClient = vi.mocked(apiClient)

describe('ArtifactEnrichmentStatus', () => {
  const mockOnComplete = vi.fn()
  const mockOnError = vi.fn()
  let intervalSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    intervalSpy = vi.spyOn(global, 'setInterval')
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows loading state initially', () => {
    mockApiClient.get.mockImplementation(() => new Promise(() => {})) // Never resolves

    render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    )

    expect(screen.getByText('Loading enrichment status...')).toBeInTheDocument()
  })

  it('displays not started state', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        artifactId: 1,
        status: 'not_started',
        hasEnrichment: false,
        message: 'No enrichment has been performed yet',
      },
    })

    render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('No enrichment has been performed yet')).toBeInTheDocument()
    })
  })

  it('displays processing state with progress bar', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        artifactId: 1,
        status: 'processing',
        progressPercentage: 45,
        hasEnrichment: false,
      },
    })

    render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Enriching Artifact with AI...')).toBeInTheDocument()
      expect(screen.getByText('45%')).toBeInTheDocument()
      expect(screen.getByText('Progress')).toBeInTheDocument()
    })
  })

  it('displays completed state with enrichment metrics', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        artifactId: 1,
        status: 'completed',
        progressPercentage: 100,
        hasEnrichment: true,
        enrichment: {
          sourcesProcessed: 5,
          sourcesSuccessful: 4,
          processingConfidence: 0.85,
          totalCostUsd: 0.0523,
          processingTimeMs: 3500,
          technologiesCount: 8,
          achievementsCount: 3,
        },
      },
    })

    render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Enrichment Complete!')).toBeInTheDocument()
      expect(screen.getByText('4/5')).toBeInTheDocument() // Sources
      expect(screen.getByText('85%')).toBeInTheDocument() // Confidence
      expect(screen.getByText('8')).toBeInTheDocument() // Technologies count
      expect(screen.getByText('3')).toBeInTheDocument() // Achievements count
      expect(screen.getByText(/Processing time: 3.5s/)).toBeInTheDocument()
      expect(screen.getByText(/Cost: \$0.0523/)).toBeInTheDocument()
    })

    expect(mockOnComplete).toHaveBeenCalled()
  })

  it('displays failed state with error message', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        artifactId: 1,
        status: 'failed',
        progressPercentage: 30,
        hasEnrichment: false,
        errorMessage: 'LLM API rate limit exceeded',
      },
    })

    render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Enrichment Failed')).toBeInTheDocument()
      expect(screen.getByText('LLM API rate limit exceeded')).toBeInTheDocument()
    })

    expect(mockOnError).toHaveBeenCalledWith('LLM API rate limit exceeded')
  })

  it('polls for status updates at specified interval', async () => {
    let callCount = 0
    mockApiClient.get.mockImplementation(() => {
      callCount++
      return Promise.resolve({
        data: {
          artifactId: 1,
          status: callCount < 3 ? 'processing' : 'completed',
          progressPercentage: callCount * 30,
          hasEnrichment: callCount >= 3,
          enrichment: callCount >= 3 ? {
            sourcesProcessed: 2,
            sourcesSuccessful: 2,
            processingConfidence: 0.9,
            totalCostUsd: 0.03,
            processingTimeMs: 2000,
            technologiesCount: 5,
            achievementsCount: 2,
          } : undefined,
        },
      })
    })

    render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
        pollInterval={1000}
      />
    )

    // Initial fetch
    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledTimes(1)
    })

    // Advance time to trigger polling
    vi.advanceTimersByTime(1000)
    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledTimes(2)
    })

    vi.advanceTimersByTime(1000)
    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledTimes(3)
      expect(screen.getByText('Enrichment Complete!')).toBeInTheDocument()
    })

    // After completion, polling should stop
    vi.advanceTimersByTime(1000)
    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledTimes(3) // Should not increase
    })
  })

  it('stops polling when status is completed', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        artifactId: 1,
        status: 'completed',
        progressPercentage: 100,
        hasEnrichment: true,
        enrichment: {
          sourcesProcessed: 1,
          sourcesSuccessful: 1,
          processingConfidence: 0.8,
          totalCostUsd: 0.02,
          processingTimeMs: 1500,
          technologiesCount: 3,
          achievementsCount: 1,
        },
      },
    })

    render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
        pollInterval={1000}
      />
    )

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledTimes(1)
    })

    // Verify polling doesn't continue
    vi.advanceTimersByTime(3000)
    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledTimes(1) // Still only 1
    })
  })

  it('stops polling when status is failed', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        artifactId: 1,
        status: 'failed',
        progressPercentage: 50,
        hasEnrichment: false,
        errorMessage: 'Test error',
      },
    })

    render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
        pollInterval={1000}
      />
    )

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledTimes(1)
    })

    // Verify polling doesn't continue
    vi.advanceTimersByTime(3000)
    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledTimes(1)
    })
  })

  it('handles API errors gracefully', async () => {
    mockApiClient.get.mockRejectedValue(new Error('Network error'))

    render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    )

    await waitFor(() => {
      expect(mockOnError).toHaveBeenCalledWith('Failed to fetch enrichment status')
    })
  })

  it('calculates success rate correctly', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        artifactId: 1,
        status: 'completed',
        progressPercentage: 100,
        hasEnrichment: true,
        enrichment: {
          sourcesProcessed: 10,
          sourcesSuccessful: 7,
          processingConfidence: 0.7,
          totalCostUsd: 0.1,
          processingTimeMs: 5000,
          technologiesCount: 12,
          achievementsCount: 5,
        },
      },
    })

    render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('7/10')).toBeInTheDocument()
      expect(screen.getByText('70% success')).toBeInTheDocument()
    })
  })

  it('applies custom className', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        artifactId: 1,
        status: 'processing',
        progressPercentage: 50,
        hasEnrichment: false,
      },
    })

    const { container } = render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
        className="custom-class"
      />
    )

    await waitFor(() => {
      const element = container.querySelector('.custom-class')
      expect(element).toBeInTheDocument()
    })
  })

  it('cleans up interval on unmount', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        artifactId: 1,
        status: 'processing',
        progressPercentage: 50,
        hasEnrichment: false,
      },
    })

    const { unmount } = render(
      <ArtifactEnrichmentStatus
        artifactId={1}
        onComplete={mockOnComplete}
        onError={mockOnError}
      />
    )

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalled()
    })

    const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
    unmount()

    expect(clearIntervalSpy).toHaveBeenCalled()
  })
})
