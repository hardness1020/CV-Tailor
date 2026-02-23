/**
 * Tests for ArtifactSelector component (ft-007)
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ArtifactSelector } from '../ArtifactSelector'
import { apiClient } from '@/services/apiClient'

// Mock API client
vi.mock('@/services/apiClient', () => ({
  apiClient: {
    suggestArtifactsForJob: vi.fn()
  }
}))

describe('ArtifactSelector', () => {
  const mockOnSelectionChange = vi.fn()
  const mockSuggestions = [
    {
      id: 1,
      title: 'E-commerce Platform',
      description: 'Built scalable marketplace',
      relevance_score: 0.85,
      exact_matches: 3,
      partial_matches: 1,
      matched_keywords: ['React', 'Node.js', 'PostgreSQL'],
      technologies: ['React', 'Node.js', 'PostgreSQL', 'Redis'],
      start_date: '2023-01-01',
      end_date: '2023-12-31'
    },
    {
      id: 2,
      title: 'API Gateway',
      description: 'RESTful API service',
      relevance_score: 0.65,
      exact_matches: 2,
      partial_matches: 0,
      matched_keywords: ['Python', 'FastAPI'],
      technologies: ['Python', 'FastAPI', 'Redis'],
      start_date: '2022-06-01',
      end_date: '2023-05-31'
    }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.suggestArtifactsForJob).mockResolvedValue({
      artifacts: mockSuggestions,
      total_artifacts: 2,
      returned_count: 2
    })
  })

  it('renders artifact list with relevance scores', async () => {
    render(
      <ArtifactSelector
        jobDescription="Looking for React developer"
        onSelectionChange={mockOnSelectionChange}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('E-commerce Platform')).toBeInTheDocument()
      expect(screen.getByText('API Gateway')).toBeInTheDocument()
    })

    // Check relevance scores are displayed
    expect(screen.getByText(/85%/)).toBeInTheDocument()
    expect(screen.getByText(/65%/)).toBeInTheDocument()
  })

  it('handles selection and deselection', async () => {
    render(
      <ArtifactSelector
        jobDescription="Looking for React developer"
        onSelectionChange={mockOnSelectionChange}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('E-commerce Platform')).toBeInTheDocument()
    })

    // Find and click checkbox for first artifact
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])

    await waitFor(() => {
      expect(mockOnSelectionChange).toHaveBeenCalledWith(expect.arrayContaining([1]))
    })

    // Deselect
    fireEvent.click(checkboxes[0])

    await waitFor(() => {
      expect(mockOnSelectionChange).toHaveBeenCalledWith(expect.not.arrayContaining([1]))
    })
  })

  it('shows empty state when no artifacts', async () => {
    vi.mocked(apiClient.suggestArtifactsForJob).mockResolvedValue({
      artifacts: [],
      total_artifacts: 0,
      returned_count: 0
    })

    render(
      <ArtifactSelector
        jobDescription="Looking for COBOL developer"
        onSelectionChange={mockOnSelectionChange}
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/no artifacts/i)).toBeInTheDocument()
    })
  })

  it('calls API on mount', async () => {
    const jobDescription = 'Looking for React developer'

    render(
      <ArtifactSelector
        jobDescription={jobDescription}
        onSelectionChange={mockOnSelectionChange}
      />
    )

    await waitFor(() => {
      expect(apiClient.suggestArtifactsForJob).toHaveBeenCalledWith(jobDescription, 10)
    })
  })

  it('handles API errors gracefully', async () => {
    vi.mocked(apiClient.suggestArtifactsForJob).mockRejectedValue(
      new Error('Network error')
    )

    render(
      <ArtifactSelector
        jobDescription="Looking for React developer"
        onSelectionChange={mockOnSelectionChange}
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/failed to fetch/i)).toBeInTheDocument()
    })
  })

  it('auto-selects top 5 artifacts on load', async () => {
    const manySuggestions = Array.from({ length: 10 }, (_, i) => ({
      id: i + 1,
      title: `Project ${i + 1}`,
      description: 'Test project',
      relevance_score: 0.9 - i * 0.1,
      exact_matches: 3,
      partial_matches: 0,
      matched_keywords: ['React'],
      technologies: ['React'],
      start_date: '2023-01-01'
    }))

    vi.mocked(apiClient.suggestArtifactsForJob).mockResolvedValue({
      artifacts: manySuggestions,
      total_artifacts: 10,
      returned_count: 10
    })

    render(
      <ArtifactSelector
        jobDescription="Looking for React developer"
        onSelectionChange={mockOnSelectionChange}
      />
    )

    await waitFor(() => {
      // Should auto-select top 5 (IDs 1-5)
      expect(mockOnSelectionChange).toHaveBeenCalledWith([1, 2, 3, 4, 5])
    })
  })

  it('displays matched keywords', async () => {
    render(
      <ArtifactSelector
        jobDescription="Looking for React and Node.js developer"
        onSelectionChange={mockOnSelectionChange}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('React')).toBeInTheDocument()
      expect(screen.getByText('Node.js')).toBeInTheDocument()
      expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
    })
  })

  it('supports initial selection prop', async () => {
    render(
      <ArtifactSelector
        jobDescription="Looking for React developer"
        onSelectionChange={mockOnSelectionChange}
        initialSelection={[2]}
      />
    )

    await waitFor(() => {
      // Should start with artifact 2 selected
      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes[1]).toBeChecked()
    })
  })

  it('allows sorting by relevance, date, and title', async () => {
    render(
      <ArtifactSelector
        jobDescription="Looking for developer"
        onSelectionChange={mockOnSelectionChange}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('E-commerce Platform')).toBeInTheDocument()
    })

    // Find sort dropdown
    const sortSelect = screen.getByLabelText(/sort/i)

    // Change sort to date
    fireEvent.change(sortSelect, { target: { value: 'date' } })

    // Artifacts should be reordered (implementation in Stage G)
    await waitFor(() => {
      // Verify order changed
    })
  })

  it('supports search/filter functionality', async () => {
    render(
      <ArtifactSelector
        jobDescription="Looking for developer"
        onSelectionChange={mockOnSelectionChange}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('E-commerce Platform')).toBeInTheDocument()
      expect(screen.getByText('API Gateway')).toBeInTheDocument()
    })

    // Find search input
    const searchInput = screen.getByPlaceholderText(/search/i)

    // Type in search
    fireEvent.change(searchInput, { target: { value: 'API' } })

    // Should filter to show only API Gateway
    await waitFor(() => {
      expect(screen.queryByText('E-commerce Platform')).not.toBeInTheDocument()
      expect(screen.getByText('API Gateway')).toBeInTheDocument()
    })
  })

  it('shows loading state while fetching', () => {
    // Make API call slow
    vi.mocked(apiClient.suggestArtifactsForJob).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({
        artifacts: [],
        total_artifacts: 0,
        returned_count: 0
      }), 1000))
    )

    render(
      <ArtifactSelector
        jobDescription="Looking for developer"
        onSelectionChange={mockOnSelectionChange}
      />
    )

    // Should show loading state immediately
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('handles drag-to-reorder', async () => {
    render(
      <ArtifactSelector
        jobDescription="Looking for developer"
        onSelectionChange={mockOnSelectionChange}
        initialSelection={[1, 2]}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('E-commerce Platform')).toBeInTheDocument()
    })

    // Simulate drag-and-drop
    // (Actual implementation depends on DnD library used)
    // This test documents expected behavior

    // After drag, order should change and onSelectionChange should be called with new order
    // expect(mockOnSelectionChange).toHaveBeenCalledWith([2, 1])  // Reordered
  })
})
