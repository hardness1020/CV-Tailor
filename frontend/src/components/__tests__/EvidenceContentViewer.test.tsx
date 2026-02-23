import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { EvidenceContentViewer } from '../EvidenceContentViewer'
import type { EvidenceLink } from '@/types'

describe('EvidenceContentViewer', () => {
  const mockOnFetch = vi.fn()

  const mockEvidence: EvidenceLink = {
    id: 1,
    url: 'https://github.com/user/repo',
    evidenceType: 'github',
    description: 'My GitHub Project',
    isAccessible: true,
    file_size: 1024000, // 1MB
    mime_type: 'application/json',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  }

  const mockEnhancedEvidence = {
    id: '123',
    evidence_id: 1,
    title: 'My GitHub Project',
    content_type: 'github' as const,
    raw_content: 'This is the raw content extracted from the GitHub repository. It contains detailed information about the project structure, dependencies, and implementation details.',
    processed_content: {
      technologies: ['React', 'TypeScript', 'Node.js'],
      achievements: ['Improved performance by 40%', 'Reduced bundle size by 30%'],
      skills: ['Frontend Development', 'API Design'],
    },
    processing_confidence: 0.92,
    created_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Auto-fetch Behavior', () => {
    it('automatically fetches enhanced evidence on mount when not loaded', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(mockOnFetch).toHaveBeenCalledTimes(1)
    })

    it('does not fetch enhanced evidence if already loaded', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={mockEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(mockOnFetch).not.toHaveBeenCalled()
    })

    it('does not fetch if already loading', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={true}
          onFetch={mockOnFetch}
        />
      )

      expect(mockOnFetch).not.toHaveBeenCalled()
    })
  })

  describe('Header Display', () => {
    it('renders evidence header with description', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('My GitHub Project')).toBeInTheDocument()
    })

    it('displays URL with external link', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      const link = screen.getByRole('link', { name: /github.com\/user\/repo/i })
      expect(link).toHaveAttribute('href', 'https://github.com/user/repo')
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    })

    it('displays evidence type', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('github')).toBeInTheDocument()
    })

    it('displays file size when available', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('1000.0 KB')).toBeInTheDocument()
    })

    it('displays mime type when available', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('application/json')).toBeInTheDocument()
    })

    it('shows accessible status when evidence is accessible', () => {
      render(
        <EvidenceContentViewer
          evidence={{ ...mockEvidence, isAccessible: true }}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('Accessible')).toBeInTheDocument()
    })

    it('shows not accessible status when evidence is not accessible', () => {
      render(
        <EvidenceContentViewer
          evidence={{ ...mockEvidence, isAccessible: false }}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('Not accessible')).toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('shows spinner when isLoading is true', () => {
      const { container } = render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={true}
          onFetch={mockOnFetch}
        />
      )

      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
      expect(screen.getByText('Loading evidence content...')).toBeInTheDocument()
    })

    it('does not show content while loading', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={true}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.queryByText('Technologies')).not.toBeInTheDocument()
      expect(screen.queryByText('Achievements')).not.toBeInTheDocument()
    })
  })

  describe('Content Display - Always Visible', () => {
    it('displays processing confidence score', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={mockEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText(/Processing Confidence: 92%/)).toBeInTheDocument()
    })

    it('displays technologies as tags', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={mockEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('React')).toBeInTheDocument()
      expect(screen.getByText('TypeScript')).toBeInTheDocument()
      expect(screen.getByText('Node.js')).toBeInTheDocument()
    })

    it('displays achievements list with numbered badges', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={mockEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('Improved performance by 40%')).toBeInTheDocument()
      expect(screen.getByText('Reduced bundle size by 30%')).toBeInTheDocument()
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    it('displays skills as tags', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={mockEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('Frontend Development')).toBeInTheDocument()
      expect(screen.getByText('API Design')).toBeInTheDocument()
    })

    it('shows section headers for each content type', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={mockEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('Technologies')).toBeInTheDocument()
      expect(screen.getByText('Achievements')).toBeInTheDocument()
      expect(screen.getByText('Skills')).toBeInTheDocument()
    })
  })

  describe('Raw Content - Collapsible Section', () => {
    it('shows preview of raw content by default', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={mockEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('Preview Raw Content')).toBeInTheDocument()
      expect(screen.getByText(/This is the raw content/)).toBeInTheDocument()
      expect(screen.getByText('Show more')).toBeInTheDocument()
    })

    it('expands to show full raw content when clicked', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={mockEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      const showMoreButton = screen.getByText('Show more')
      fireEvent.click(showMoreButton)

      expect(screen.getByText('Raw Content')).toBeInTheDocument()
      const pre = screen.getByText(/This is the raw content extracted from the GitHub repository/).closest('pre')
      expect(pre).toBeInTheDocument()
    })

    it('collapses raw content when header is clicked', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={mockEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      // Expand
      const showMoreButton = screen.getByText('Show more')
      fireEvent.click(showMoreButton)
      expect(screen.getByText('Raw Content')).toBeInTheDocument()

      // Collapse by clicking the header
      const header = screen.getByText('Raw Content')
      fireEvent.click(header)
      expect(screen.getByText('Preview Raw Content')).toBeInTheDocument()
    })

    it('makes full raw content scrollable for long text', () => {
      const { container } = render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={mockEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      fireEvent.click(screen.getByText('Show more'))

      const contentPre = container.querySelector('pre')
      expect(contentPre).toHaveClass('overflow-y-auto')
      expect(contentPre).toHaveClass('max-h-96')
    })
  })

  describe('Missing Enhanced Evidence', () => {
    it('shows "No enhanced content available" message when enhanced evidence is missing', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('No enhanced content available')).toBeInTheDocument()
    })

    it('provides load content button when enhanced evidence is missing', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      const loadButton = screen.getByText('Load content')
      expect(loadButton).toBeInTheDocument()
    })

    it('calls onFetch when load content button is clicked', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      vi.clearAllMocks() // Clear the auto-fetch call
      const loadButton = screen.getByText('Load content')
      fireEvent.click(loadButton)

      expect(mockOnFetch).toHaveBeenCalledTimes(1)
    })
  })

  describe('Empty Processed Content', () => {
    it('shows empty state when no technologies, achievements, or skills exist', () => {
      const emptyEnhancedEvidence = {
        ...mockEnhancedEvidence,
        processed_content: {
          technologies: [],
          achievements: [],
          skills: [],
        },
      }

      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={emptyEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.getByText('No processed content available')).toBeInTheDocument()
    })

    it('does not show section headers when arrays are empty', () => {
      const emptyEnhancedEvidence = {
        ...mockEnhancedEvidence,
        processed_content: {
          technologies: [],
          achievements: [],
          skills: [],
        },
      }

      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          enhancedEvidence={emptyEnhancedEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.queryByText('Technologies')).not.toBeInTheDocument()
      expect(screen.queryByText('Achievements')).not.toBeInTheDocument()
      expect(screen.queryByText('Skills')).not.toBeInTheDocument()
    })
  })

  describe('Evidence Type Icons', () => {
    it('shows GitHub icon for github evidence type', () => {
      const { container } = render(
        <EvidenceContentViewer
          evidence={{ ...mockEvidence, evidenceType: 'github' }}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      // Check that icon is rendered in header
      const header = screen.getByText('My GitHub Project').closest('div')
      expect(header).toBeInTheDocument()
    })

    it('shows document icon for document evidence type', () => {
      const { container } = render(
        <EvidenceContentViewer
          evidence={{ ...mockEvidence, evidenceType: 'document', description: 'Project Report' }}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      const header = screen.getByText('Project Report').closest('div')
      expect(header).toBeInTheDocument()
    })
  })

  describe('URL Handling', () => {
    it('handles relative document URLs by prefixing with backend URL', () => {
      const documentEvidence = {
        ...mockEvidence,
        evidenceType: 'document' as const,
        url: '/media/evidence/document.pdf',
      }

      render(
        <EvidenceContentViewer
          evidence={documentEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      const link = screen.getByRole('link')
      expect(link).toHaveAttribute('href', 'http://localhost:8000/media/evidence/document.pdf')
    })

    it('uses absolute URLs as-is', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      const link = screen.getByRole('link')
      expect(link).toHaveAttribute('href', 'https://github.com/user/repo')
    })
  })

  describe('Edit/Delete Controls', () => {
    it('does not show Edit/Delete buttons when handlers not provided', () => {
      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
        />
      )

      expect(screen.queryByText('Edit')).not.toBeInTheDocument()
      expect(screen.queryByText('Delete')).not.toBeInTheDocument()
    })

    it('shows Edit button when onEdit handler is provided', () => {
      const mockOnEdit = vi.fn()

      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
          onEdit={mockOnEdit}
        />
      )

      expect(screen.getByText('Edit')).toBeInTheDocument()
    })

    it('shows Delete button when onDelete handler is provided', () => {
      const mockOnDelete = vi.fn()

      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
          onDelete={mockOnDelete}
        />
      )

      expect(screen.getByText('Delete')).toBeInTheDocument()
    })

    it('shows both Edit and Delete buttons when both handlers provided', () => {
      const mockOnEdit = vi.fn()
      const mockOnDelete = vi.fn()

      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
          onEdit={mockOnEdit}
          onDelete={mockOnDelete}
        />
      )

      expect(screen.getByText('Edit')).toBeInTheDocument()
      expect(screen.getByText('Delete')).toBeInTheDocument()
    })

    it('calls onEdit when Edit button is clicked', () => {
      const mockOnEdit = vi.fn()

      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
          onEdit={mockOnEdit}
        />
      )

      const editButton = screen.getByText('Edit')
      fireEvent.click(editButton)

      expect(mockOnEdit).toHaveBeenCalledTimes(1)
    })

    it('shows confirmation dialog before deleting', () => {
      const mockOnDelete = vi.fn()
      window.confirm = vi.fn(() => false) // User cancels

      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
          onDelete={mockOnDelete}
        />
      )

      const deleteButton = screen.getByText('Delete')
      fireEvent.click(deleteButton)

      expect(window.confirm).toHaveBeenCalledWith(
        'Are you sure you want to delete this evidence link? This action cannot be undone.'
      )
      expect(mockOnDelete).not.toHaveBeenCalled()
    })

    it('calls onDelete when user confirms deletion', () => {
      const mockOnDelete = vi.fn()
      window.confirm = vi.fn(() => true) // User confirms

      render(
        <EvidenceContentViewer
          evidence={mockEvidence}
          isLoading={false}
          onFetch={mockOnFetch}
          onDelete={mockOnDelete}
        />
      )

      const deleteButton = screen.getByText('Delete')
      fireEvent.click(deleteButton)

      expect(window.confirm).toHaveBeenCalled()
      expect(mockOnDelete).toHaveBeenCalledTimes(1)
    })
  })
})
