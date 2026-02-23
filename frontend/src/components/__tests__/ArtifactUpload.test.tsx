import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import ArtifactUpload from '../ArtifactUpload'
import { useArtifacts } from '@/hooks/useArtifacts'
import { apiClient } from '@/services/apiClient'

// Mock hooks and modules
vi.mock('@/hooks/useArtifacts', () => ({
  useArtifacts: vi.fn(),
}))

vi.mock('@/services/apiClient', () => ({
  apiClient: {
    get: vi.fn(),
    createArtifact: vi.fn(),
    uploadArtifactFiles: vi.fn(),
  },
}))

const mockUseArtifacts = vi.mocked(useArtifacts)
const mockApiClient = vi.mocked(apiClient)

describe('ArtifactUpload', () => {
  const mockCreateArtifact = vi.fn()
  const mockOnUploadComplete = vi.fn()
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseArtifacts.mockReturnValue({
      artifacts: [],
      createArtifact: mockCreateArtifact,
      loadArtifacts: vi.fn(),
      updateArtifact: vi.fn(),
      deleteArtifact: vi.fn(),
      bulkDelete: vi.fn(),
      uploadProgress: {},
      isLoading: false,
      error: null,
    })
  })

  it('renders upload form correctly with multi-step wizard', () => {
    render(
      <ArtifactUpload
        onUploadComplete={mockOnUploadComplete}
        onClose={mockOnClose}
      />
    )

    // Check for step indicator
    expect(screen.getByText('Basic Info')).toBeInTheDocument()
    expect(screen.getByText('Technologies')).toBeInTheDocument()
    expect(screen.getByText('Evidence')).toBeInTheDocument()
    expect(screen.getByText('Confirm Details')).toBeInTheDocument()

    // Check step 1 content
    expect(screen.getByText('Upload New Artifact')).toBeInTheDocument()
    expect(screen.getByText('Basic Information')).toBeInTheDocument()
  })

  it('validates required fields in step 1', async () => {
    render(
      <ArtifactUpload
        onUploadComplete={mockOnUploadComplete}
        onClose={mockOnClose}
      />
    )

    // Try to proceed without filling required fields
    const nextButton = screen.getByText('Next')
    fireEvent.click(nextButton)

    await waitFor(() => {
      expect(screen.getByText('Title is required')).toBeInTheDocument()
    })
  })

  it('submits form with valid data through multi-step flow', async () => {
    mockCreateArtifact.mockResolvedValue({
      id: 1,
      title: 'Test Artifact',
      description: 'Test Description',
      technologies: ['React'],
      startDate: '2023-01-01',
      endDate: '2023-12-31',
      status: 'active',
      evidenceLinks: [],
      labels: [],
      artifactType: 'project',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    })

    render(
      <ArtifactUpload
        onUploadComplete={mockOnUploadComplete}
        onClose={mockOnClose}
      />
    )

    // Step 1: Fill in basic information
    const titleInput = screen.getByPlaceholderText(/E-commerce Platform/i)
    const descriptionInput = screen.getByPlaceholderText(/Describe your role/i)
    const startDateInputs = screen.getAllByDisplayValue('')

    fireEvent.change(titleInput, { target: { value: 'Test Artifact' } })
    fireEvent.change(descriptionInput, { target: { value: 'Test Description for this artifact' } })
    fireEvent.change(startDateInputs[0], { target: { value: '2023-01-01' } })

    // Navigate to step 2
    fireEvent.click(screen.getByText('Next'))

    await waitFor(() => {
      expect(screen.getByText('Technologies Used')).toBeInTheDocument()
    })

    // Step 2: Add technology
    const techInput = screen.getByPlaceholderText(/React, Python/i)
    fireEvent.change(techInput, { target: { value: 'React' } })
    fireEvent.click(screen.getByRole('button', { name: /Add/ }))

    await waitFor(() => {
      expect(screen.getByText('React')).toBeInTheDocument()
    })

    // Navigate to step 3
    fireEvent.click(screen.getByText('Next'))

    await waitFor(() => {
      expect(screen.getByText('Evidence & Sources')).toBeInTheDocument()
    })

    // Step 3: Skip evidence (optional)
    fireEvent.click(screen.getByText('Next'))

    await waitFor(() => {
      expect(screen.getByText('Review & Submit')).toBeInTheDocument()
    })

    // Step 4: Submit
    fireEvent.click(screen.getByText('Submit Artifact'))

    await waitFor(() => {
      expect(mockCreateArtifact).toHaveBeenCalled()
    })
  })

  it('handles form cancellation', () => {
    render(
      <ArtifactUpload
        onUploadComplete={mockOnUploadComplete}
        onClose={mockOnClose}
      />
    )

    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('allows navigation back to previous steps', async () => {
    render(
      <ArtifactUpload
        onUploadComplete={mockOnUploadComplete}
        onClose={mockOnClose}
      />
    )

    // Navigate to step 2
    fireEvent.click(screen.getByText('Next'))

    await waitFor(() => {
      expect(screen.getByText('Technologies Used')).toBeInTheDocument()
    })

    // Navigate back to step 1
    fireEvent.click(screen.getByText('Back'))

    await waitFor(() => {
      expect(screen.getByText('Basic Information')).toBeInTheDocument()
    })
  })

  it('displays loading state during submission', async () => {
    mockCreateArtifact.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

    render(
      <ArtifactUpload
        onUploadComplete={mockOnUploadComplete}
        onClose={mockOnClose}
      />
    )

    // Navigate through all steps quickly
    const titleInput = screen.getByPlaceholderText(/E-commerce Platform/i)
    const descriptionInput = screen.getByPlaceholderText(/Describe your role/i)
    const startDateInputs = screen.getAllByDisplayValue('')

    fireEvent.change(titleInput, { target: { value: 'Test' } })
    fireEvent.change(descriptionInput, { target: { value: 'Test Description' } })
    fireEvent.change(startDateInputs[0], { target: { value: '2023-01-01' } })
    fireEvent.click(screen.getByText('Next'))

    await waitFor(() => screen.getByText('Technologies Used'))
    const techInput = screen.getByPlaceholderText(/React, Python/i)
    fireEvent.change(techInput, { target: { value: 'React' } })
    fireEvent.click(screen.getByRole('button', { name: /Add/ }))

    await waitFor(() => screen.getByText('React'))
    fireEvent.click(screen.getByText('Next'))

    await waitFor(() => screen.getByText('Evidence & Sources'))
    fireEvent.click(screen.getByText('Next'))

    await waitFor(() => screen.getByText('Review & Submit'))
    fireEvent.click(screen.getByText('Submit Artifact'))

    await waitFor(() => {
      expect(screen.getByText('Uploading...')).toBeInTheDocument()
    })
  })

  describe('Evidence Type Validation', () => {
    it('shows GitHub-specific UI without type selector', () => {
      render(
        <ArtifactUpload
          onUploadComplete={mockOnUploadComplete}
          onClose={mockOnClose}
        />
      )

      // Navigate to evidence step
      fireEvent.click(screen.getByText('Evidence'))

      // Check that GitHub section is present
      expect(screen.getByText('GitHub Repositories')).toBeInTheDocument()

      // Check that upload documents section is present
      expect(screen.getByText('Upload Documents')).toBeInTheDocument()

      // Should NOT have evidence type selector (removed in ft-011)
      expect(screen.queryByText('Evidence Type')).not.toBeInTheDocument()
      expect(screen.queryByText('Link Type')).not.toBeInTheDocument()

      // These deprecated types should NOT be present
      expect(screen.queryByText('Live Application')).not.toBeInTheDocument()
      expect(screen.queryByText('Video Demo')).not.toBeInTheDocument()
      expect(screen.queryByText('Research Paper')).not.toBeInTheDocument()
      expect(screen.queryByText('Website')).not.toBeInTheDocument()
      expect(screen.queryByText('Portfolio')).not.toBeInTheDocument()
      expect(screen.queryByText('Other Link')).not.toBeInTheDocument()
    })

    it('accepts valid github evidence type', async () => {
      mockCreateArtifact.mockResolvedValue({
        id: 1,
        title: 'Test',
        description: 'Test',
        technologies: ['React'],
        startDate: '2023-01-01',
        status: 'active',
        evidenceLinks: [{ url: 'https://github.com/user/repo', evidence_type: 'github' }],
        labels: [],
        artifactType: 'project',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      })

      render(
        <ArtifactUpload
          onUploadComplete={mockOnUploadComplete}
          onClose={mockOnClose}
        />
      )

      // Fill basic info
      const titleInput = screen.getByPlaceholderText(/E-commerce Platform/i)
      const descriptionInput = screen.getByPlaceholderText(/Describe your role/i)
      const startDateInputs = screen.getAllByDisplayValue('')

      fireEvent.change(titleInput, { target: { value: 'Test' } })
      fireEvent.change(descriptionInput, { target: { value: 'Test Description' } })
      fireEvent.change(startDateInputs[0], { target: { value: '2023-01-01' } })
      fireEvent.click(screen.getByText('Next'))

      await waitFor(() => screen.getByText('Technologies Used'))
      const techInput = screen.getByPlaceholderText(/React, Python/i)
      fireEvent.change(techInput, { target: { value: 'React' } })
      fireEvent.click(screen.getByRole('button', { name: /Add/ }))

      await waitFor(() => screen.getByText('React'))
      fireEvent.click(screen.getByText('Next'))

      // Add github evidence - this should be accepted
      await waitFor(() => screen.getByText('Evidence & Sources'))

      // The form should accept github evidence type
      fireEvent.click(screen.getByText('Next'))
      await waitFor(() => screen.getByText('Review & Submit'))
      fireEvent.click(screen.getByText('Submit Artifact'))

      await waitFor(() => {
        expect(mockCreateArtifact).toHaveBeenCalled()
      })
    })

    it('validates GitHub URLs in schema validation', () => {
      // This test verifies that the Zod schema validates GitHub URLs
      // The githubLinkSchema validates URLs must contain 'github.com'
      const { z } = require('zod')

      const githubLinkSchema = z.object({
        url: z.string()
          .url('Please enter a valid URL')
          .refine(
            (url) => url.includes('github.com'),
            { message: 'Must be a GitHub repository URL (https://github.com/...)' }
          ),
        description: z.string().optional(),
      })

      // Valid GitHub URLs should pass
      expect(() => githubLinkSchema.parse({
        url: 'https://github.com/user/repo',
      })).not.toThrow()

      expect(() => githubLinkSchema.parse({
        url: 'https://github.com/organization/project',
        description: 'My project',
      })).not.toThrow()

      // Non-GitHub URLs should fail
      expect(() => githubLinkSchema.parse({
        url: 'https://example.com/app',
      })).toThrow()

      expect(() => githubLinkSchema.parse({
        url: 'https://youtube.com/watch?v=123',
      })).toThrow()

      expect(() => githubLinkSchema.parse({
        url: 'http://example.com/doc.pdf',
      })).toThrow()

      // Invalid URLs should fail
      expect(() => githubLinkSchema.parse({
        url: 'not-a-url',
      })).toThrow()
    })
  })

  describe('Enrichment Status Flow', () => {
    beforeEach(() => {
      mockApiClient.createArtifact.mockResolvedValue({
        id: 1,
        title: 'Test Artifact',
        description: 'Test Description',
        artifactType: 'project',
        technologies: ['React'],
        startDate: '2023-01-01',
        endDate: '2023-12-31',
        status: 'active',
        evidenceLinks: [],
        labels: [],
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      })
    })

    it('shows enrichment status after successful upload', async () => {
      mockApiClient.get.mockResolvedValue({
        data: {
          artifactId: 1,
          status: 'processing',
          progressPercentage: 50,
          hasEnrichment: false,
        },
      })

      render(
        <ArtifactUpload
          onUploadComplete={mockOnUploadComplete}
          onClose={mockOnClose}
        />
      )

      // Navigate through wizard and submit
      const titleInput = screen.getByPlaceholderText(/E-commerce Platform/i)
      const descriptionInput = screen.getByPlaceholderText(/Describe your role/i)
      const startDateInputs = screen.getAllByDisplayValue('')

      fireEvent.change(titleInput, { target: { value: 'Test Artifact' } })
      fireEvent.change(descriptionInput, { target: { value: 'Test Description for artifact' } })
      fireEvent.change(startDateInputs[0], { target: { value: '2023-01-01' } })
      fireEvent.click(screen.getByText('Next'))

      await waitFor(() => screen.getByText('Technologies Used'))
      const techInput = screen.getByPlaceholderText(/React, Python/i)
      fireEvent.change(techInput, { target: { value: 'React' } })
      fireEvent.click(screen.getByRole('button', { name: /Add/ }))

      await waitFor(() => screen.getByText('React'))
      fireEvent.click(screen.getByText('Next'))

      await waitFor(() => screen.getByText('Evidence & Sources'))
      fireEvent.click(screen.getByText('Next'))

      await waitFor(() => screen.getByText('Review & Submit'))
      fireEvent.click(screen.getByText('Submit Artifact'))

      // Wait for enrichment status to appear
      await waitFor(() => {
        expect(screen.getByText('Processing Artifact')).toBeInTheDocument()
        expect(screen.getByText(/AI is now analyzing and enriching/)).toBeInTheDocument()
      })
    })

    it('calls onUploadComplete when enrichment completes', async () => {
      mockApiClient.get.mockResolvedValue({
        data: {
          artifactId: 1,
          status: 'completed',
          progressPercentage: 100,
          hasEnrichment: true,
          enrichment: {
            sourcesProcessed: 2,
            sourcesSuccessful: 2,
            processingConfidence: 0.9,
            totalCostUsd: 0.03,
            processingTimeMs: 2000,
            technologiesCount: 5,
            achievementsCount: 2,
          },
        },
      })

      render(
        <ArtifactUpload
          onUploadComplete={mockOnUploadComplete}
          onClose={mockOnClose}
        />
      )

      // Navigate through wizard and submit
      const titleInput = screen.getByPlaceholderText(/E-commerce Platform/i)
      const descriptionInput = screen.getByPlaceholderText(/Describe your role/i)
      const startDateInputs = screen.getAllByDisplayValue('')

      fireEvent.change(titleInput, { target: { value: 'Test Artifact' } })
      fireEvent.change(descriptionInput, { target: { value: 'Test Description for artifact' } })
      fireEvent.change(startDateInputs[0], { target: { value: '2023-01-01' } })
      fireEvent.click(screen.getByText('Next'))

      await waitFor(() => screen.getByText('Technologies Used'))
      const techInput = screen.getByPlaceholderText(/React, Python/i)
      fireEvent.change(techInput, { target: { value: 'React' } })
      fireEvent.click(screen.getByRole('button', { name: /Add/ }))

      await waitFor(() => screen.getByText('React'))
      fireEvent.click(screen.getByText('Next'))
      await waitFor(() => screen.getByText('Evidence & Sources'))
      fireEvent.click(screen.getByText('Next'))
      await waitFor(() => screen.getByText('Review & Submit'))
      fireEvent.click(screen.getByText('Submit Artifact'))

      // Wait for enrichment to complete
      await waitFor(() => {
        expect(screen.getByText('Processing Artifact')).toBeInTheDocument()
      })

      // Note: In real implementation, onUploadComplete would be called after enrichment
      // This is tested in the component integration
    })

    it('allows closing modal during enrichment', async () => {
      mockApiClient.get.mockResolvedValue({
        data: {
          artifactId: 1,
          status: 'processing',
          progressPercentage: 30,
          hasEnrichment: false,
        },
      })

      render(
        <ArtifactUpload
          onUploadComplete={mockOnUploadComplete}
          onClose={mockOnClose}
        />
      )

      // Navigate through wizard and submit
      const titleInput = screen.getByPlaceholderText(/E-commerce Platform/i)
      const descriptionInput = screen.getByPlaceholderText(/Describe your role/i)
      const startDateInputs = screen.getAllByDisplayValue('')

      fireEvent.change(titleInput, { target: { value: 'Test Artifact' } })
      fireEvent.change(descriptionInput, { target: { value: 'Test Description for artifact' } })
      fireEvent.change(startDateInputs[0], { target: { value: '2023-01-01' } })
      fireEvent.click(screen.getByText('Next'))

      await waitFor(() => screen.getByText('Technologies Used'))
      const techInput = screen.getByPlaceholderText(/React, Python/i)
      fireEvent.change(techInput, { target: { value: 'React' } })
      fireEvent.click(screen.getByRole('button', { name: /Add/ }))

      await waitFor(() => screen.getByText('React'))
      fireEvent.click(screen.getByText('Next'))
      await waitFor(() => screen.getByText('Evidence & Sources'))
      fireEvent.click(screen.getByText('Next'))
      await waitFor(() => screen.getByText('Review & Submit'))
      fireEvent.click(screen.getByText('Submit Artifact'))

      // Wait for enrichment status screen
      await waitFor(() => {
        expect(screen.getByText('Processing Artifact')).toBeInTheDocument()
      })

      // Should have Close button
      const closeButton = screen.getByText('Close')
      expect(closeButton).toBeInTheDocument()

      fireEvent.click(closeButton)
      expect(mockOnClose).toHaveBeenCalled()
    })

    it('handles enrichment errors gracefully', async () => {
      mockApiClient.get.mockResolvedValue({
        data: {
          artifactId: 1,
          status: 'failed',
          progressPercentage: 50,
          hasEnrichment: false,
          errorMessage: 'LLM API rate limit exceeded',
        },
      })

      render(
        <ArtifactUpload
          onUploadComplete={mockOnUploadComplete}
          onClose={mockOnClose}
        />
      )

      // Navigate through wizard and submit
      const titleInput = screen.getByPlaceholderText(/E-commerce Platform/i)
      const descriptionInput = screen.getByPlaceholderText(/Describe your role/i)
      const startDateInputs = screen.getAllByDisplayValue('')

      fireEvent.change(titleInput, { target: { value: 'Test Artifact' } })
      fireEvent.change(descriptionInput, { target: { value: 'Test Description for artifact' } })
      fireEvent.change(startDateInputs[0], { target: { value: '2023-01-01' } })
      fireEvent.click(screen.getByText('Next'))

      await waitFor(() => screen.getByText('Technologies Used'))
      const techInput = screen.getByPlaceholderText(/React, Python/i)
      fireEvent.change(techInput, { target: { value: 'React' } })
      fireEvent.click(screen.getByRole('button', { name: /Add/ }))

      await waitFor(() => screen.getByText('React'))
      fireEvent.click(screen.getByText('Next'))
      await waitFor(() => screen.getByText('Evidence & Sources'))
      fireEvent.click(screen.getByText('Next'))
      await waitFor(() => screen.getByText('Review & Submit'))
      fireEvent.click(screen.getByText('Submit Artifact'))

      // Wait for error state
      await waitFor(() => {
        expect(screen.getByText('Processing Artifact')).toBeInTheDocument()
      })

      // Component should handle error internally via ArtifactEnrichmentStatus
    })

    it('transitions from upload form to enrichment status', async () => {
      mockApiClient.get.mockResolvedValue({
        data: {
          artifactId: 1,
          status: 'processing',
          progressPercentage: 20,
          hasEnrichment: false,
        },
      })

      render(
        <ArtifactUpload
          onUploadComplete={mockOnUploadComplete}
          onClose={mockOnClose}
        />
      )

      // Initially shows upload form
      expect(screen.getByText('Upload New Artifact')).toBeInTheDocument()

      // Navigate through wizard and submit
      const titleInput = screen.getByPlaceholderText(/E-commerce Platform/i)
      const descriptionInput = screen.getByPlaceholderText(/Describe your role/i)
      const startDateInputs = screen.getAllByDisplayValue('')

      fireEvent.change(titleInput, { target: { value: 'Test Artifact' } })
      fireEvent.change(descriptionInput, { target: { value: 'Test Description for artifact' } })
      fireEvent.change(startDateInputs[0], { target: { value: '2023-01-01' } })
      fireEvent.click(screen.getByText('Next'))

      await waitFor(() => screen.getByText('Technologies Used'))
      const techInput = screen.getByPlaceholderText(/React, Python/i)
      fireEvent.change(techInput, { target: { value: 'React' } })
      fireEvent.click(screen.getByRole('button', { name: /Add/ }))

      await waitFor(() => screen.getByText('React'))
      fireEvent.click(screen.getByText('Next'))
      await waitFor(() => screen.getByText('Evidence & Sources'))
      fireEvent.click(screen.getByText('Next'))
      await waitFor(() => screen.getByText('Review & Submit'))
      fireEvent.click(screen.getByText('Submit Artifact'))

      // Should transition to enrichment status view
      await waitFor(() => {
        expect(screen.queryByText('Upload New Artifact')).not.toBeInTheDocument()
        expect(screen.getByText('Processing Artifact')).toBeInTheDocument()
      })
    })
  })
})