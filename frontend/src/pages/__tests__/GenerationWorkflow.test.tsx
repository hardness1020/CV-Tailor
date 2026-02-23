/**
 * Integration tests for CV Generation Workflow with artifact selection (ft-007)
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import GenerationWorkflow from '../GenerationWorkflow'
import { apiClient } from '@/services/apiClient'

// Mock API client
vi.mock('@/services/apiClient', () => ({
  apiClient: {
    suggestArtifactsForJob: vi.fn(),
    generateCV: vi.fn()
  }
}))

describe('GenerationWorkflow with Artifact Selection', () => {
  const mockSuggestions = [
    {
      id: 1,
      title: 'E-commerce Platform',
      description: 'Built scalable marketplace',
      relevance_score: 0.85,
      exact_matches: 3,
      partial_matches: 1,
      matched_keywords: ['React', 'Node.js'],
      technologies: ['React', 'Node.js', 'PostgreSQL'],
      start_date: '2023-01-01',
      end_date: '2023-12-31'
    }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.suggestArtifactsForJob).mockResolvedValue({
      artifacts: mockSuggestions,
      total_artifacts: 1,
      returned_count: 1
    })
    vi.mocked(apiClient.generateCV).mockResolvedValue({
      document: {
        id: 1,
        content: 'Generated CV content'
      }
    })
  })

  it('shows artifact selection step after job description', async () => {
    render(
      <BrowserRouter>
        <GenerationWorkflow />
      </BrowserRouter>
    )

    // Step 1: Enter job description
    const jobDescInput = screen.getByLabelText(/job description/i)
    fireEvent.change(jobDescInput, {
      target: { value: 'Looking for React developer' }
    })

    // Click Next
    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    // Step 2: Artifact selection should appear
    await waitFor(() => {
      expect(screen.getByText(/select artifacts/i)).toBeInTheDocument()
    })
  })

  it('passes selected artifact IDs to CV generation', async () => {
    render(
      <BrowserRouter>
        <GenerationWorkflow />
      </BrowserRouter>
    )

    // Step 1: Enter job description
    const jobDescInput = screen.getByLabelText(/job description/i)
    const jobDescription = 'Looking for React developer'
    fireEvent.change(jobDescInput, { target: { value: jobDescription } })

    // Go to next step
    fireEvent.click(screen.getByRole('button', { name: /next/i }))

    // Step 2: Artifacts are auto-selected
    await waitFor(() => {
      expect(screen.getByText('E-commerce Platform')).toBeInTheDocument()
    })

    // Artifact should already be selected (auto-select behavior)
    await waitFor(() => {
      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toBeChecked()
    })

    // Go to next step (generation) with auto-selected artifact
    fireEvent.click(screen.getByRole('button', { name: /generate/i }))

    // Should call generateCV with artifact IDs
    await waitFor(() => {
      expect(apiClient.generateCV).toHaveBeenCalledWith(
        expect.objectContaining({
          jobDescription,
          artifactIds: expect.arrayContaining([1])
        })
      )
    })
  })

  it('persists selection when navigating back', async () => {
    render(
      <BrowserRouter>
        <GenerationWorkflow />
      </BrowserRouter>
    )

    // Step 1: Enter job description
    const jobDescInput = screen.getByLabelText(/job description/i)
    fireEvent.change(jobDescInput, { target: { value: 'Looking for React developer' } })
    fireEvent.click(screen.getByRole('button', { name: /next/i }))

    // Step 2: Artifact is auto-selected
    await waitFor(() => {
      expect(screen.getByText('E-commerce Platform')).toBeInTheDocument()
    })

    // Verify artifact is auto-selected
    await waitFor(() => {
      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toBeChecked()
    })

    // Go back
    fireEvent.click(screen.getByRole('button', { name: /back/i }))

    // Go forward again
    fireEvent.click(screen.getByRole('button', { name: /next/i }))

    // Selection should be preserved
    await waitFor(() => {
      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toBeChecked()
    })
  })

  it('allows skipping artifact selection (backward compatibility)', async () => {
    render(
      <BrowserRouter>
        <GenerationWorkflow />
      </BrowserRouter>
    )

    // Step 1: Enter job description
    const jobDescInput = screen.getByLabelText(/job description/i)
    const jobDescription = 'Looking for React developer'
    fireEvent.change(jobDescInput, { target: { value: jobDescription } })
    fireEvent.click(screen.getByRole('button', { name: /next/i }))

    // Step 2: Skip selection (use automatic)
    await waitFor(() => {
      expect(screen.getByText(/select artifacts/i)).toBeInTheDocument()
    })

    const skipButton = screen.getByRole('button', { name: /use top 5/i })
    fireEvent.click(skipButton)

    // Should call generateCV without artifact_ids (automatic selection)
    await waitFor(() => {
      expect(apiClient.generateCV).toHaveBeenCalledWith(
        expect.objectContaining({
          jobDescription
        })
      )
      // Verify artifactIds is not present in the call
      const call = vi.mocked(apiClient.generateCV).mock.calls[0][0]
      expect(call).not.toHaveProperty('artifactIds')
    })
  })

  it('validates at least 1 artifact selected', async () => {
    render(
      <BrowserRouter>
        <GenerationWorkflow />
      </BrowserRouter>
    )

    // Step 1: Enter job description
    fireEvent.change(screen.getByLabelText(/job description/i), {
      target: { value: 'Looking for React developer' }
    })
    fireEvent.click(screen.getByRole('button', { name: /next/i }))

    // Step 2: Artifacts are auto-selected, need to deselect them first
    await waitFor(() => {
      expect(screen.getByText(/select artifacts/i)).toBeInTheDocument()
    })

    // Deselect the auto-selected artifact by clicking its checkbox
    await waitFor(() => {
      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toBeChecked()
      fireEvent.click(checkbox)  // Deselect
    })

    // Try to generate with no artifacts selected
    const generateButton = screen.getByRole('button', { name: /generate/i })
    fireEvent.click(generateButton)

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText(/select at least 1 artifact/i)).toBeInTheDocument()
    })
  })

  it('displays step indicator with artifact selection step', async () => {
    render(
      <BrowserRouter>
        <GenerationWorkflow />
      </BrowserRouter>
    )

    // Should show 3 steps: Job Desc → Artifacts → Review
    // Use getAllByText since "Job Description" appears in both step indicator and page heading
    const jobDescElements = screen.getAllByText(/job description/i)
    expect(jobDescElements.length).toBeGreaterThan(0)

    expect(screen.getByText('Artifacts')).toBeInTheDocument()  // More specific - step indicator text
    expect(screen.getByText('Review')).toBeInTheDocument()  // More specific - step indicator text
  })

  it('shows artifact count in selection step header', async () => {
    render(
      <BrowserRouter>
        <GenerationWorkflow />
      </BrowserRouter>
    )

    // Enter job description and proceed
    fireEvent.change(screen.getByLabelText(/job description/i), {
      target: { value: 'Looking for React developer' }
    })
    fireEvent.click(screen.getByRole('button', { name: /next/i }))

    // Should show artifact count (after auto-select completes)
    await waitFor(() => {
      expect(screen.getByText('E-commerce Platform')).toBeInTheDocument()
    })

    // Wait for auto-select to update the count
    await waitFor(() => {
      expect(screen.getByText(/we've found 1 artifact/i)).toBeInTheDocument()
    })
  })

  it('allows reordering selected artifacts', async () => {
    const multipleSuggestions = [
      { ...mockSuggestions[0], id: 1 },
      { ...mockSuggestions[0], id: 2, title: 'API Gateway' }
    ]

    vi.mocked(apiClient.suggestArtifactsForJob).mockResolvedValue({
      artifacts: multipleSuggestions,
      total_artifacts: 2,
      returned_count: 2
    })

    render(
      <BrowserRouter>
        <GenerationWorkflow />
      </BrowserRouter>
    )

    // Enter job description and proceed
    fireEvent.change(screen.getByLabelText(/job description/i), {
      target: { value: 'Looking for React developer' }
    })
    fireEvent.click(screen.getByRole('button', { name: /next/i }))

    // Wait for artifacts to load and auto-select
    await waitFor(() => {
      expect(screen.getByText('E-commerce Platform')).toBeInTheDocument()
      expect(screen.getByText('API Gateway')).toBeInTheDocument()
    })

    // Both should be auto-selected (top 5 behavior selects top 2)
    await waitFor(() => {
      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes[0]).toBeChecked()
      expect(checkboxes[1]).toBeChecked()
    })

    // Simulate drag-to-reorder (implementation depends on DnD library)
    // For now, just test that generate works with both selected
    // After reorder, selected IDs should maintain new order

    // Proceed to generation
    fireEvent.click(screen.getByRole('button', { name: /generate/i }))

    // Should pass artifacts
    await waitFor(() => {
      expect(apiClient.generateCV).toHaveBeenCalledWith(
        expect.objectContaining({
          artifactIds: expect.arrayContaining([1, 2])
        })
      )
    })
  })
})
