import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { EvidenceLinkManager } from '../EvidenceLinkManager'
import { apiClient } from '@/services/apiClient'
import type { EvidenceLink } from '@/types'

// Mock the API client
vi.mock('@/services/apiClient', () => ({
  apiClient: {
    addEvidenceLink: vi.fn(),
    updateEvidenceLink: vi.fn(),
    deleteEvidenceLink: vi.fn()
  }
}))

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

const mockEvidenceLinks: EvidenceLink[] = [
  {
    id: 1,
    url: 'https://github.com/user/project',
    evidenceType: 'github',
    description: 'Project repository',
    isAccessible: true,
    createdAt: '2023-01-01T00:00:00Z'
  },
  {
    id: 2,
    url: 'https://example.com/document.pdf',
    evidenceType: 'document',
    description: 'Project documentation',
    isAccessible: false,  // One link not accessible for test differentiation
    createdAt: '2023-01-02T00:00:00Z'
  }
]

describe('EvidenceLinkManager', () => {
  const mockOnUpdate = vi.fn()
  const artifactId = 123

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders evidence links list', () => {
    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={mockEvidenceLinks}
        onUpdate={mockOnUpdate}
      />
    )

    expect(screen.getByText('Evidence Links')).toBeInTheDocument()
    expect(screen.getByText('GitHub Repository')).toBeInTheDocument()
    expect(screen.getByText('https://github.com/user/project')).toBeInTheDocument()
    expect(screen.getByText('Project repository')).toBeInTheDocument()
    expect(screen.getByText('Document/PDF')).toBeInTheDocument()
    expect(screen.getByText('https://example.com/document.pdf')).toBeInTheDocument()
  })

  it('shows accessibility status for links', () => {
    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={mockEvidenceLinks}
        onUpdate={mockOnUpdate}
      />
    )

    expect(screen.getByText('Accessible')).toBeInTheDocument()
    expect(screen.getByText('Not accessible')).toBeInTheDocument()
  })

  it('shows empty state when no links', () => {
    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={[]}
        onUpdate={mockOnUpdate}
      />
    )

    expect(screen.getByText('No evidence links added yet')).toBeInTheDocument()
    expect(screen.getByText('Add links to showcase your work')).toBeInTheDocument()
  })

  it('opens add evidence link form', async () => {
    const user = userEvent.setup()

    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={[]}
        onUpdate={mockOnUpdate}
      />
    )

    const addButton = screen.getByRole('button', { name: /add evidence link/i })
    await user.click(addButton)

    expect(screen.getByText('Add Evidence Link')).toBeInTheDocument()
    expect(screen.getByLabelText(/url/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/link type/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument()
  })

  it('adds evidence link successfully', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.addEvidenceLink).mockResolvedValue({
      id: 3,
      url: 'https://github.com/user/new-repo',
      evidenceType: 'github',
      description: 'New link',
      createdAt: '2023-01-03T00:00:00Z'
    })

    const { toast } = await import('react-hot-toast')

    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={[]}
        onUpdate={mockOnUpdate}
      />
    )

    // Open add form
    await user.click(screen.getByRole('button', { name: /add evidence link/i }))

    // Fill form
    await user.type(screen.getByLabelText(/url/i), 'https://github.com/user/new-repo')
    await user.selectOptions(screen.getByLabelText(/link type/i), 'github')
    await user.type(screen.getByLabelText(/description/i), 'New link description')

    // Submit
    await user.click(screen.getByRole('button', { name: /add link/i }))

    await waitFor(() => {
      expect(apiClient.addEvidenceLink).toHaveBeenCalledWith(artifactId, {
        url: 'https://github.com/user/new-repo',
        evidenceType: 'github',
        description: 'New link description'
      })
      expect(mockOnUpdate).toHaveBeenCalled()
      expect(toast.success).toHaveBeenCalledWith('Evidence link added successfully')
    })
  })

  it('validates URL format when adding link', async () => {
    const user = userEvent.setup()

    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={[]}
        onUpdate={mockOnUpdate}
      />
    )

    // Open add form
    await user.click(screen.getByRole('button', { name: /add evidence link/i }))

    // Enter invalid URL
    await user.type(screen.getByLabelText(/url/i), 'invalid-url')

    // Try to submit
    await user.click(screen.getByRole('button', { name: /add link/i }))

    await waitFor(() => {
      expect(screen.getByText(/please enter a valid url/i)).toBeInTheDocument()
      expect(apiClient.addEvidenceLink).not.toHaveBeenCalled()
    })
  })

  it('handles add link error', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.addEvidenceLink).mockRejectedValue(new Error('API Error'))

    const { toast } = await import('react-hot-toast')

    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={[]}
        onUpdate={mockOnUpdate}
      />
    )

    // Open add form and fill valid data
    await user.click(screen.getByRole('button', { name: /add evidence link/i }))
    await user.type(screen.getByLabelText(/url/i), 'https://valid-url.com')

    // Submit
    await user.click(screen.getByRole('button', { name: /add link/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to add evidence link')
    })
  })

  it('cancels adding evidence link', async () => {
    const user = userEvent.setup()

    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={[]}
        onUpdate={mockOnUpdate}
      />
    )

    // Open add form
    await user.click(screen.getByRole('button', { name: /add evidence link/i }))
    expect(screen.getByText('Add Evidence Link')).toBeInTheDocument()

    // Cancel
    await user.click(screen.getByRole('button', { name: /cancel/i }))

    await waitFor(() => {
      expect(screen.queryByText('Add Evidence Link')).not.toBeInTheDocument()
    })
  })

  it('opens edit modal for evidence link', async () => {
    const user = userEvent.setup()

    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={mockEvidenceLinks}
        onUpdate={mockOnUpdate}
      />
    )

    // Click edit button for first link
    const editButtons = screen.getAllByRole('button', { name: /edit/i })
    await user.click(editButtons[0])

    expect(screen.getByText('Edit Evidence Link')).toBeInTheDocument()
    expect(screen.getByDisplayValue('https://github.com/user/project')).toBeInTheDocument()
  })

  it('updates evidence link successfully', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.updateEvidenceLink).mockResolvedValue({
      id: 1,
      url: 'https://github.com/user/updated-repo',
      evidenceType: 'github',
      description: 'Updated description',
      updatedAt: '2023-01-04T00:00:00Z'
    })

    const { toast } = await import('react-hot-toast')

    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={mockEvidenceLinks}
        onUpdate={mockOnUpdate}
      />
    )

    // Open edit modal
    const editButtons = screen.getAllByRole('button', { name: /edit/i })
    await user.click(editButtons[0])

    // Update URL
    const urlInput = screen.getByDisplayValue('https://github.com/user/project')
    await user.clear(urlInput)
    await user.type(urlInput, 'https://github.com/user/updated-repo')

    // Save changes
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      expect(apiClient.updateEvidenceLink).toHaveBeenCalledWith(1, {
        url: 'https://github.com/user/updated-repo',
        evidenceType: 'github',
        description: 'Project repository'
      })
      expect(mockOnUpdate).toHaveBeenCalled()
      expect(toast.success).toHaveBeenCalledWith('Evidence link updated successfully')
    })
  })

  it('deletes evidence link with confirmation', async () => {
    const user = userEvent.setup()
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(apiClient.deleteEvidenceLink).mockResolvedValue()

    const { toast } = await import('react-hot-toast')

    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={mockEvidenceLinks}
        onUpdate={mockOnUpdate}
      />
    )

    // Click delete button
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    await user.click(deleteButtons[0])

    expect(confirmSpy).toHaveBeenCalledWith('Are you sure you want to delete this evidence link?')

    await waitFor(() => {
      expect(apiClient.deleteEvidenceLink).toHaveBeenCalledWith(1)
      expect(mockOnUpdate).toHaveBeenCalled()
      expect(toast.success).toHaveBeenCalledWith('Evidence link deleted successfully')
    })

    confirmSpy.mockRestore()
  })

  it('cancels delete when confirmation is denied', async () => {
    const user = userEvent.setup()
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={mockEvidenceLinks}
        onUpdate={mockOnUpdate}
      />
    )

    // Click delete button
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    await user.click(deleteButtons[0])

    expect(confirmSpy).toHaveBeenCalled()
    expect(apiClient.deleteEvidenceLink).not.toHaveBeenCalled()

    confirmSpy.mockRestore()
  })

  it('handles delete error', async () => {
    const user = userEvent.setup()
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(apiClient.deleteEvidenceLink).mockRejectedValue(new Error('Delete failed'))

    const { toast } = await import('react-hot-toast')

    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={mockEvidenceLinks}
        onUpdate={mockOnUpdate}
      />
    )

    // Click delete button
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    await user.click(deleteButtons[0])

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to delete evidence link')
    })

    confirmSpy.mockRestore()
  })

  it('opens external links in new tab', () => {
    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={mockEvidenceLinks}
        onUpdate={mockOnUpdate}
      />
    )

    const githubLink = screen.getByRole('link', { name: 'https://github.com/user/project' })
    expect(githubLink).toHaveAttribute('href', 'https://github.com/user/project')
    expect(githubLink).toHaveAttribute('target', '_blank')
    expect(githubLink).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('displays correct icons for different link types', () => {
    const linksWithDifferentTypes: EvidenceLink[] = [
      { ...mockEvidenceLinks[0], evidenceType: 'github' },
      { ...mockEvidenceLinks[1], id: 3, evidenceType: 'document' }
    ]

    render(
      <EvidenceLinkManager
        artifactId={artifactId}
        links={linksWithDifferentTypes}
        onUpdate={mockOnUpdate}
      />
    )

    // Check that icons are displayed for supported evidence types
    const icons = screen.getAllByText('🔗')
    expect(icons.length).toBeGreaterThan(0) // github icon
    expect(screen.getByText('📄')).toBeInTheDocument() // document icon
  })
})