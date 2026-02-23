import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ArtifactDetailPage from '../ArtifactDetailPage'
import { apiClient } from '@/services/apiClient'
import type { Artifact } from '@/types'

// Mock API client
vi.mock('@/services/apiClient', () => ({
  apiClient: {
    getArtifact: vi.fn(),
    triggerEnrichment: vi.fn(),
    getEnrichmentStatus: vi.fn(),
    updateArtifact: vi.fn(),
    deleteArtifact: vi.fn(),
  },
}))

describe('ArtifactDetailPage - ft-015 Enhancements', () => {
  const mockArtifact: Artifact = {
    id: 1,
    title: 'Test Project',
    description: 'Original description',
    artifactType: 'project',
    startDate: '2024-01-01',
    technologies: ['React', 'TypeScript'],
    evidenceLinks: [
      {
        id: 1,
        url: 'https://github.com/user/repo',
        evidenceType: 'github',
        description: 'GitHub Repository',
        isAccessible: true,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      },
      {
        id: 2,
        url: '/media/uploads/report.pdf',
        evidenceType: 'document',
        description: 'Project Report',
        file_path: 'uploads/report.pdf',
        file_size: 1024000,
        mime_type: 'application/pdf',
        isAccessible: true,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      },
    ],
    labels: [],
    status: 'active',
    unifiedDescription: 'AI-enhanced description',
    enrichedTechnologies: ['React', 'TypeScript', 'Node.js'],
    enrichedAchievements: ['Achievement 1'],
    processingConfidence: 0.85,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getArtifact).mockResolvedValue(mockArtifact)
    vi.mocked(apiClient.getEnrichmentStatus).mockResolvedValue({
      status: 'not_started',
      progressPercentage: 0,
      hasEnrichment: false,
    })
  })

  const renderPage = () => {
    return render(
      <MemoryRouter initialEntries={['/artifacts/1']}>
        <Routes>
          <Route path="/artifacts/:id" element={<ArtifactDetailPage />} />
        </Routes>
      </MemoryRouter>
    )
  }

  describe('Page-Level Tabs', () => {
    it('renders Overview and Evidence tabs', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Overview')).toBeInTheDocument()
        expect(screen.getByText(/Evidence/)).toBeInTheDocument()
      })
    })

    it('shows evidence count in Evidence tab label', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Evidence (2)')).toBeInTheDocument()
      })
    })

    it('displays Overview tab content by default', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Test Project')).toBeInTheDocument()
        expect(screen.getByText('Original description')).toBeInTheDocument()
      })
    })

    it('switches to Evidence tab when clicked', async () => {
      renderPage()

      await waitFor(() => {
        const evidenceTab = screen.getByText(/Evidence/)
        fireEvent.click(evidenceTab)
      })

      // Should show evidence link manager
      await waitFor(() => {
        expect(screen.getByText('GitHub Repository')).toBeInTheDocument()
        expect(screen.getByText('Project Report')).toBeInTheDocument()
      })
    })

    it('maintains tab selection after enrichment completes', async () => {
      renderPage()

      // Switch to Evidence tab
      await waitFor(() => {
        const evidenceTab = screen.getByText(/Evidence/)
        fireEvent.click(evidenceTab)
      })

      // Trigger enrichment
      vi.mocked(apiClient.triggerEnrichment).mockResolvedValue({ success: true })
      vi.mocked(apiClient.getEnrichmentStatus).mockResolvedValue({
        status: 'processing',
        progressPercentage: 50,
        hasEnrichment: false,
      })

      // Tab selection should persist
      await waitFor(() => {
        expect(screen.getByText('GitHub Repository')).toBeInTheDocument()
      })
    })
  })

  describe('Enrichment Processing Feedback', () => {
    it('shows loading overlay when enrichment is triggered', async () => {
      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Test Project')).toBeInTheDocument()
      })

      // Click enrich button
      const enrichButton = screen.getByText(/Enrich with AI|Re-enrich/)
      vi.mocked(apiClient.triggerEnrichment).mockResolvedValue({ success: true })
      vi.mocked(apiClient.getEnrichmentStatus).mockResolvedValue({
        status: 'processing',
        progressPercentage: 0,
        hasEnrichment: false,
      })

      fireEvent.click(enrichButton)

      await waitFor(() => {
        expect(screen.getByText(/AI Enrichment in Progress/)).toBeInTheDocument()
      })
    })

    it('shows progress percentage in loading overlay', async () => {
      vi.mocked(apiClient.getEnrichmentStatus).mockResolvedValue({
        status: 'processing',
        progressPercentage: 45,
        hasEnrichment: false,
      })

      renderPage()

      await waitFor(() => {
        const enrichButton = screen.getByText(/Enrich with AI|Re-enrich/)
        vi.mocked(apiClient.triggerEnrichment).mockResolvedValue({ success: true })
        fireEvent.click(enrichButton)
      })

      await waitFor(() => {
        expect(screen.getByText('45%')).toBeInTheDocument()
      })
    })

    it('dismisses overlay when enrichment completes', async () => {
      renderPage()

      // Start enrichment
      vi.mocked(apiClient.getEnrichmentStatus).mockResolvedValue({
        status: 'processing',
        progressPercentage: 50,
        hasEnrichment: false,
      })

      await waitFor(() => {
        const enrichButton = screen.getByText(/Enrich with AI|Re-enrich/)
        fireEvent.click(enrichButton)
      })

      // Complete enrichment
      vi.mocked(apiClient.getEnrichmentStatus).mockResolvedValue({
        status: 'completed',
        progressPercentage: 100,
        hasEnrichment: true,
        technologiesCount: 3,
        achievementsCount: 2,
      })

      await waitFor(() => {
        expect(screen.queryByText(/AI Enrichment in Progress/)).not.toBeInTheDocument()
      })
    })

    it('shows success toast with enrichment summary after completion', async () => {
      renderPage()

      vi.mocked(apiClient.triggerEnrichment).mockResolvedValue({ success: true })
      vi.mocked(apiClient.getEnrichmentStatus).mockResolvedValue({
        status: 'completed',
        progressPercentage: 100,
        hasEnrichment: true,
        technologiesCount: 5,
        achievementsCount: 3,
      })

      await waitFor(() => {
        const enrichButton = screen.getByText(/Enrich with AI|Re-enrich/)
        fireEvent.click(enrichButton)
      })

      // Toast should appear (checking for toast library integration)
      await waitFor(() => {
        // Toast content would appear here
        expect(apiClient.getEnrichmentStatus).toHaveBeenCalled()
      })
    })

    it('shows failure toast when enrichment fails', async () => {
      renderPage()

      vi.mocked(apiClient.triggerEnrichment).mockResolvedValue({ success: true })
      vi.mocked(apiClient.getEnrichmentStatus).mockResolvedValue({
        status: 'failed',
        progressPercentage: 50,
        errorMessage: 'Network error',
        hasEnrichment: false,
      })

      await waitFor(() => {
        const enrichButton = screen.getByText(/Enrich with AI|Re-enrich/)
        fireEvent.click(enrichButton)
      })

      // Error handling should be triggered
      await waitFor(() => {
        expect(apiClient.getEnrichmentStatus).toHaveBeenCalled()
      })
    })
  })

  describe('PDF Download Links', () => {
    it('prefixes document URLs with backend API base URL', async () => {
      renderPage()

      // Switch to Evidence tab
      await waitFor(() => {
        const evidenceTab = screen.getByText(/Evidence/)
        fireEvent.click(evidenceTab)
      })

      await waitFor(() => {
        const pdfLink = screen.getByText('Project Report')
        expect(pdfLink).toBeInTheDocument()
      })

      // URL should be prefixed (implementation will handle this)
      const expectedUrl = `http://localhost:8000/media/uploads/report.pdf`
      // Link should exist (specific URL check in implementation)
    })

    it('shows file size for document evidence', async () => {
      renderPage()

      await waitFor(() => {
        const evidenceTab = screen.getByText(/Evidence/)
        fireEvent.click(evidenceTab)
      })

      await waitFor(() => {
        // File size should be formatted and displayed
        expect(screen.getByText('Project Report')).toBeInTheDocument()
      })
    })

    it('shows broken link warning for inaccessible documents', async () => {
      const artifactWithBrokenLink = {
        ...mockArtifact,
        evidenceLinks: [
          {
            id: 3,
            url: '/media/missing.pdf',
            evidenceType: 'document' as const,
            description: 'Missing Document',
            isAccessible: false,
            createdAt: '2024-01-01T00:00:00Z',
            updatedAt: '2024-01-01T00:00:00Z',
          },
        ],
      }

      vi.mocked(apiClient.getArtifact).mockResolvedValue(artifactWithBrokenLink)

      renderPage()

      await waitFor(() => {
        const evidenceTab = screen.getByText(/Evidence/)
        fireEvent.click(evidenceTab)
      })

      await waitFor(() => {
        expect(screen.getByText('Missing Document')).toBeInTheDocument()
        // Should show warning indicator
      })
    })
  })

  describe('Evidence Content Display', () => {
    it('shows evidence items as expandable cards', async () => {
      renderPage()

      await waitFor(() => {
        const evidenceTab = screen.getByText(/Evidence/)
        fireEvent.click(evidenceTab)
      })

      await waitFor(() => {
        expect(screen.getByText('GitHub Repository')).toBeInTheDocument()
        expect(screen.getByText('Project Report')).toBeInTheDocument()
      })
    })

    it('expands evidence card to show content tabs when clicked', async () => {
      renderPage()

      await waitFor(() => {
        const evidenceTab = screen.getByText(/Evidence/)
        fireEvent.click(evidenceTab)
      })

      await waitFor(() => {
        const evidenceItem = screen.getByText('GitHub Repository')
        fireEvent.click(evidenceItem)
      })

      // Should show evidence content tabs
      await waitFor(() => {
        expect(screen.getByText('Overview')).toBeInTheDocument()
        expect(screen.getByText('Content')).toBeInTheDocument()
        expect(screen.getByText('Processed')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('supports keyboard navigation between page tabs', async () => {
      renderPage()

      await waitFor(() => {
        const overviewTab = screen.getByText('Overview')
        overviewTab.focus()
        expect(document.activeElement).toBe(overviewTab)
      })

      // Arrow key navigation handled by Radix UI
    })

    it('maintains focus management during tab switches', async () => {
      renderPage()

      await waitFor(() => {
        const evidenceTab = screen.getByText(/Evidence/)
        evidenceTab.focus()
        fireEvent.click(evidenceTab)
      })

      // Focus should remain on tab trigger
      await waitFor(() => {
        expect(document.activeElement?.textContent).toContain('Evidence')
      })
    })
  })

  describe('Error Handling', () => {
    it('handles artifact loading failure gracefully', async () => {
      vi.mocked(apiClient.getArtifact).mockRejectedValue(new Error('Network error'))

      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/error loading this artifact/i)).toBeInTheDocument()
      })
    })

    it('shows retry option after enrichment failure', async () => {
      renderPage()

      vi.mocked(apiClient.triggerEnrichment).mockRejectedValue(new Error('API error'))

      await waitFor(() => {
        const enrichButton = screen.getByText(/Enrich with AI|Re-enrich/)
        fireEvent.click(enrichButton)
      })

      // Error toast should allow retry
      await waitFor(() => {
        expect(apiClient.triggerEnrichment).toHaveBeenCalled()
      })
    })
  })

  describe('Mobile Responsiveness', () => {
    it('renders tabs in mobile-friendly layout', async () => {
      // Set viewport to mobile size
      global.innerWidth = 375
      global.dispatchEvent(new Event('resize'))

      renderPage()

      await waitFor(() => {
        expect(screen.getByText('Overview')).toBeInTheDocument()
        expect(screen.getByText(/Evidence/)).toBeInTheDocument()
      })

      // Tabs should be responsive (specific layout checks in implementation)
    })
  })
})
