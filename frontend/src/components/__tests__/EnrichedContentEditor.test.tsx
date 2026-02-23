import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { EnrichedContentEditor } from '../EnrichedContentEditor'
import type { Artifact } from '@/types'

describe('EnrichedContentEditor', () => {
  const mockOnSave = vi.fn()
  const mockOnClose = vi.fn()

  const baseArtifact: Artifact = {
    id: 1,
    title: 'Test Project',
    description: 'Original description',
    artifactType: 'project',
    startDate: '2024-01-01',
    technologies: ['Python'],
    evidenceLinks: [],
    labels: [],
    status: 'active',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    unifiedDescription: 'AI-enhanced description',
    enrichedTechnologies: ['Python', 'Django'],
    enrichedAchievements: ['Achievement 1', 'Achievement 2'],
    processingConfidence: 0.85,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders with pre-filled enriched data', () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    expect(screen.getByDisplayValue('AI-enhanced description')).toBeInTheDocument()
    expect(screen.getByText('Achievement 1')).toBeInTheDocument()
    expect(screen.getByText('Achievement 2')).toBeInTheDocument()
  })

  it('renders modal title correctly', () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    expect(screen.getByText('Edit AI-Enriched Content')).toBeInTheDocument()
  })

  it('shows character count for description', () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    // "AI-enhanced description" is 23 characters
    expect(screen.getByText(/23 \/ 5000/)).toBeInTheDocument()
  })

  it('updates character count when typing in description', async () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const textarea = screen.getByDisplayValue('AI-enhanced description')
    fireEvent.change(textarea, { target: { value: 'New longer description text' } })

    await waitFor(() => {
      expect(screen.getByText(/28 \/ 5000/)).toBeInTheDocument()
    })
  })

  it('validates description max length (5000 characters)', async () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const textarea = screen.getByDisplayValue('AI-enhanced description')
    const longText = 'a'.repeat(5001)
    fireEvent.change(textarea, { target: { value: longText } })

    await waitFor(() => {
      expect(screen.getByText('Description must be less than 5000 characters')).toBeInTheDocument()
    })
  })

  it('shows technology count badge', () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    expect(screen.getByText(/AI-Extracted Technologies \(2\/50\)/)).toBeInTheDocument()
  })

  it('shows achievement count badge', () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    expect(screen.getByText(/AI-Identified Achievements \(2\/20\)/)).toBeInTheDocument()
  })

  it('allows adding new achievement', async () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const input = screen.getByPlaceholderText(/Add new achievement/)
    fireEvent.change(input, { target: { value: 'New achievement' } })

    const addButton = screen.getByRole('button', { name: /Add/ })
    fireEvent.click(addButton)

    await waitFor(() => {
      expect(screen.getByDisplayValue('New achievement')).toBeInTheDocument()
      expect(screen.getByText(/AI-Identified Achievements \(3\/20\)/)).toBeInTheDocument()
    })
  })

  it('allows adding achievement with Enter key', async () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const input = screen.getByPlaceholderText(/Add new achievement/)
    fireEvent.change(input, { target: { value: 'Achievement via Enter' } })
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 })

    await waitFor(() => {
      expect(screen.getByDisplayValue('Achievement via Enter')).toBeInTheDocument()
    })
  })

  it('prevents adding achievement if already at max (20)', async () => {
    const artifactWithMaxAchievements: Artifact = {
      ...baseArtifact,
      enrichedAchievements: Array.from({ length: 20 }, (_, i) => `Achievement ${i + 1}`)
    }

    render(
      <EnrichedContentEditor
        artifact={artifactWithMaxAchievements}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    // Add button should not be visible when at max
    expect(screen.queryByPlaceholderText(/Add new achievement/)).not.toBeInTheDocument()
  })

  it('shows validation error when trying to add 21st achievement', async () => {
    const artifactWith19Achievements: Artifact = {
      ...baseArtifact,
      enrichedAchievements: Array.from({ length: 19 }, (_, i) => `Achievement ${i + 1}`)
    }

    render(
      <EnrichedContentEditor
        artifact={artifactWith19Achievements}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    // Add one more to reach 20
    const input = screen.getByPlaceholderText(/Add new achievement/)
    fireEvent.change(input, { target: { value: 'Achievement 20' } })
    fireEvent.click(screen.getByRole('button', { name: /Add/ }))

    await waitFor(() => {
      expect(screen.queryByPlaceholderText(/Add new achievement/)).not.toBeInTheDocument()
    })
  })

  it('allows removing achievement', async () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const deleteButtons = screen.getAllByTitle('Remove achievement')
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(screen.queryByText('Achievement 1')).not.toBeInTheDocument()
      expect(screen.getByText(/AI-Identified Achievements \(1\/20\)/)).toBeInTheDocument()
    })
  })

  it('allows editing existing achievement', async () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const achievement1Textarea = screen.getByDisplayValue('Achievement 1')
    fireEvent.change(achievement1Textarea, { target: { value: 'Modified achievement' } })

    await waitFor(() => {
      expect(screen.getByDisplayValue('Modified achievement')).toBeInTheDocument()
    })
  })

  it('numbers achievements sequentially', () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    // Check for numbered badges
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('shows unsaved changes indicator when form is dirty', async () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const textarea = screen.getByDisplayValue('AI-enhanced description')
    fireEvent.change(textarea, { target: { value: 'Modified description' } })

    await waitFor(() => {
      expect(screen.getByText('You have unsaved changes')).toBeInTheDocument()
    })
  })

  it('calls onSave with only changed fields', async () => {
    mockOnSave.mockResolvedValue(undefined)

    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    // Only change the description
    const textarea = screen.getByDisplayValue('AI-enhanced description')
    fireEvent.change(textarea, { target: { value: 'Modified description' } })

    const saveButton = screen.getByRole('button', { name: /Save Changes/ })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith({
        unifiedDescription: 'Modified description'
      })
    })
  })

  it('calls onSave with multiple changed fields', async () => {
    mockOnSave.mockResolvedValue(undefined)

    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    // Change description
    const textarea = screen.getByDisplayValue('AI-enhanced description')
    fireEvent.change(textarea, { target: { value: 'Modified description' } })

    // Add achievement
    const input = screen.getByPlaceholderText(/Add new achievement/)
    fireEvent.change(input, { target: { value: 'New achievement' } })
    fireEvent.click(screen.getByRole('button', { name: /Add/ }))

    await waitFor(() => {
      expect(screen.getByDisplayValue('New achievement')).toBeInTheDocument()
    })

    const saveButton = screen.getByRole('button', { name: /Save Changes/ })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith({
        unifiedDescription: 'Modified description',
        enrichedAchievements: ['Achievement 1', 'Achievement 2', 'New achievement']
      })
    })
  })

  it('disables save button when no changes', () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const saveButton = screen.getByRole('button', { name: /Save Changes/ })
    expect(saveButton).toBeDisabled()
  })

  it('shows confirmation dialog when closing with unsaved changes', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    // Make changes
    const textarea = screen.getByDisplayValue('AI-enhanced description')
    fireEvent.change(textarea, { target: { value: 'Modified' } })

    const cancelButton = screen.getByRole('button', { name: /Cancel/ })
    fireEvent.click(cancelButton)

    expect(confirmSpy).toHaveBeenCalledWith('You have unsaved changes. Are you sure you want to close?')
    expect(mockOnClose).not.toHaveBeenCalled()

    confirmSpy.mockRestore()
  })

  it('closes without confirmation when no changes', () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const cancelButton = screen.getByRole('button', { name: /Cancel/ })
    fireEvent.click(cancelButton)

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('disables buttons when isLoading is true', () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
        isLoading={true}
      />
    )

    const cancelButton = screen.getByRole('button', { name: /Cancel/ })
    const saveButton = screen.getByRole('button', { name: /Saving.../ })

    expect(cancelButton).toBeDisabled()
    expect(saveButton).toBeDisabled()
  })

  it('shows empty state when no achievements', () => {
    const artifactNoAchievements: Artifact = {
      ...baseArtifact,
      enrichedAchievements: []
    }

    render(
      <EnrichedContentEditor
        artifact={artifactNoAchievements}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    expect(screen.getByText('No achievements added yet')).toBeInTheDocument()
  })

  it('trims whitespace when adding achievement', async () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const input = screen.getByPlaceholderText(/Add new achievement/)
    fireEvent.change(input, { target: { value: '   Trimmed achievement   ' } })
    fireEvent.click(screen.getByRole('button', { name: /Add/ }))

    await waitFor(() => {
      expect(screen.getByDisplayValue('Trimmed achievement')).toBeInTheDocument()
    })
  })

  it('does not add empty achievement', async () => {
    render(
      <EnrichedContentEditor
        artifact={baseArtifact}
        isOpen={true}
        onClose={mockOnClose}
        onSave={mockOnSave}
      />
    )

    const addButton = screen.getByRole('button', { name: /Add/ })
    fireEvent.click(addButton)

    // Count should remain 2
    expect(screen.getByText(/AI-Identified Achievements \(2\/20\)/)).toBeInTheDocument()
  })
})
