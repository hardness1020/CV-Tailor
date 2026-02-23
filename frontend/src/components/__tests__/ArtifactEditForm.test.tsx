import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { ArtifactEditForm } from '../ArtifactEditForm'
import { apiClient } from '@/services/apiClient'
import type { Artifact } from '@/types'

// Mock the API client
vi.mock('@/services/apiClient', () => ({
  apiClient: {
    getTechnologySuggestions: vi.fn()
  }
}))

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

const mockArtifact: Artifact = {
  id: 1,
  title: 'Test Project',
  description: 'Test description',
  artifact_type: 'project',
  start_date: '2023-01-01',
  end_date: '2023-12-31',
  technologies: ['Python', 'Django'],
  evidence_links: [],
  extracted_metadata: {},
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T00:00:00Z'
}

describe('ArtifactEditForm', () => {
  const mockOnSave = vi.fn()
  const mockOnCancel = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getTechnologySuggestions).mockResolvedValue([
      'Python', 'Django', 'React', 'TypeScript', 'Node.js'
    ])
  })

  it('renders artifact edit form with initial values', async () => {
    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    expect(screen.getByDisplayValue('Test Project')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Test description')).toBeInTheDocument()
    expect(screen.getByDisplayValue('2023-01-01')).toBeInTheDocument()
    expect(screen.getByDisplayValue('2023-12-31')).toBeInTheDocument()

    // Check that technologies are displayed
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('Django')).toBeInTheDocument()
    expect(screen.getByText('john@example.com')).toBeInTheDocument()
  })

  it('loads technology suggestions on mount', async () => {
    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    await waitFor(() => {
      expect(apiClient.getTechnologySuggestions).toHaveBeenCalled()
    })
  })

  it('marks form as dirty when values change', async () => {
    const user = userEvent.setup()

    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    // Initially, save button should be disabled (not dirty)
    expect(screen.getByRole('button', { name: /save changes/i })).toBeDisabled()

    // Change title
    const titleInput = screen.getByDisplayValue('Test Project')
    await user.clear(titleInput)
    await user.type(titleInput, 'Updated Project')

    // Form should now be dirty, save button enabled
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /save changes/i })).not.toBeDisabled()
      expect(screen.getByText('Unsaved changes')).toBeInTheDocument()
    })
  })

  it('validates required fields', async () => {
    const user = userEvent.setup()

    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    // Clear required field
    const titleInput = screen.getByDisplayValue('Test Project')
    await user.clear(titleInput)

    // Try to submit
    const saveButton = screen.getByRole('button', { name: /save changes/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText('Title is required')).toBeInTheDocument()
      expect(mockOnSave).not.toHaveBeenCalled()
    })
  })

  it('validates date range', async () => {
    const user = userEvent.setup()

    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    // Set end date before start date
    const endDateInput = screen.getByDisplayValue('2023-12-31')
    await user.clear(endDateInput)
    await user.type(endDateInput, '2022-12-31')

    // Try to submit
    const saveButton = screen.getByRole('button', { name: /save changes/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText('End date must be after start date')).toBeInTheDocument()
      expect(mockOnSave).not.toHaveBeenCalled()
    })
  })

  it('submits only changed fields', async () => {
    const user = userEvent.setup()
    mockOnSave.mockResolvedValue(undefined)

    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    // Change only title and description
    const titleInput = screen.getByDisplayValue('Test Project')
    await user.clear(titleInput)
    await user.type(titleInput, 'Updated Project')

    const descriptionInput = screen.getByDisplayValue('Test description')
    await user.clear(descriptionInput)
    await user.type(descriptionInput, 'Updated description')

    // Submit form
    const saveButton = screen.getByRole('button', { name: /save changes/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith({
        title: 'Updated Project',
        description: 'Updated description'
      })
    })
  })

  it('handles save success', async () => {
    const user = userEvent.setup()
    mockOnSave.mockResolvedValue(undefined)

    const { toast } = await import('react-hot-toast')

    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    // Make a change and save
    const titleInput = screen.getByDisplayValue('Test Project')
    await user.clear(titleInput)
    await user.type(titleInput, 'Updated Project')

    const saveButton = screen.getByRole('button', { name: /save changes/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Artifact updated successfully')
    })
  })

  it('handles save error', async () => {
    const user = userEvent.setup()
    const error = new Error('Save failed')
    mockOnSave.mockRejectedValue(error)

    const { toast } = await import('react-hot-toast')

    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    // Make a change and try to save
    const titleInput = screen.getByDisplayValue('Test Project')
    await user.clear(titleInput)
    await user.type(titleInput, 'Updated Project')

    const saveButton = screen.getByRole('button', { name: /save changes/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to update artifact')
    })
  })

  it('shows confirmation dialog on cancel with unsaved changes', async () => {
    const user = userEvent.setup()
    // Mock window.confirm
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    // Make a change
    const titleInput = screen.getByDisplayValue('Test Project')
    await user.clear(titleInput)
    await user.type(titleInput, 'Updated Project')

    // Click cancel
    const cancelButton = screen.getByRole('button', { name: /cancel/i })
    await user.click(cancelButton)

    expect(confirmSpy).toHaveBeenCalledWith('You have unsaved changes. Are you sure you want to cancel?')
    expect(mockOnCancel).toHaveBeenCalled()

    confirmSpy.mockRestore()
  })

  it('cancels without confirmation when no changes', async () => {
    const user = userEvent.setup()
    const confirmSpy = vi.spyOn(window, 'confirm')

    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    // Click cancel without making changes
    const cancelButton = screen.getByRole('button', { name: /cancel/i })
    await user.click(cancelButton)

    expect(confirmSpy).not.toHaveBeenCalled()
    expect(mockOnCancel).toHaveBeenCalled()

    confirmSpy.mockRestore()
  })

  it('handles technology tags correctly', async () => {
    const user = userEvent.setup()
    mockOnSave.mockResolvedValue(undefined)

    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    // Find technology input and add a new technology
    const techInput = screen.getByPlaceholderText(/add technologies/i)
    await user.type(techInput, 'React{enter}')

    // Submit form
    const saveButton = screen.getByRole('button', { name: /save changes/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith({
        technologies: ['Python', 'Django', 'React']
      })
    })
  })

  it('disables form when loading', () => {
    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
        isLoading={true}
      />
    )

    expect(screen.getByRole('button', { name: /save changes/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled()
  })

  it('shows loading state during submission', async () => {
    const user = userEvent.setup()
    // Mock a slow save operation
    mockOnSave.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

    render(
      <ArtifactEditForm
        artifact={mockArtifact}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )

    // Make a change
    const titleInput = screen.getByDisplayValue('Test Project')
    await user.clear(titleInput)
    await user.type(titleInput, 'Updated Project')

    // Submit form
    const saveButton = screen.getByRole('button', { name: /save changes/i })
    await user.click(saveButton)

    // Button should show loading state
    expect(saveButton).toBeDisabled()
    expect(saveButton).toHaveTextContent('Saving') // Assuming loading text

    // Wait for operation to complete
    await waitFor(() => {
      expect(saveButton).not.toBeDisabled()
    }, { timeout: 200 })
  })
})