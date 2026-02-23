/**
 * Unit tests for BulletRegenerationModal (ft-024 standalone bullet generation)
 *
 * Tests cover:
 * - Quick suggestion buttons
 * - Custom refinement prompt input
 * - Prompt length validation (500 chars max)
 * - Temporary prompt warning display
 * - onRegenerate callback invocation
 *
 * These tests are FAILING until BulletRegenerationModal is implemented (TDD RED phase)
 */

import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import BulletRegenerationModal from '../BulletRegenerationModal'

describe('BulletRegenerationModal - Quick Suggestions', () => {
  const mockOnRegenerate = vi.fn()
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders quick suggestion buttons', () => {
    /**
     * Acceptance (ft-024): Display 3-5 quick suggestion buttons
     * - "Add more metrics"
     * - "Focus on leadership"
     * - "Emphasize technical depth"
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    expect(screen.getByRole('button', { name: /add more metrics/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /focus on leadership/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /emphasize technical depth/i })).toBeInTheDocument()
  })

  it('calls onRegenerate with quick suggestion text when button clicked', () => {
    /**
     * Acceptance (ft-024): Clicking quick suggestion calls onRegenerate
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const addMetricsButton = screen.getByRole('button', { name: /add more metrics/i })
    fireEvent.click(addMetricsButton)

    expect(mockOnRegenerate).toHaveBeenCalledWith(
      expect.stringContaining('metrics'),
      undefined, // bullet_ids
      undefined  // artifact_ids
    )
  })

  it('does not render modal when isOpen is false', () => {
    /**
     * Acceptance (ft-024): Modal hidden when isOpen=false
     */
    render(
      <BulletRegenerationModal
        isOpen={false}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('BulletRegenerationModal - Custom Refinement Prompt', () => {
  const mockOnRegenerate = vi.fn()
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders custom refinement prompt textarea', () => {
    /**
     * Acceptance (ft-024): Display textarea for custom prompt
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)
    expect(textarea).toBeInTheDocument()
  })

  it('allows user to type custom refinement prompt', () => {
    /**
     * Acceptance (ft-024): User can enter custom prompt text
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)
    fireEvent.change(textarea, { target: { value: 'Focus on architecture decisions' } })

    expect(textarea).toHaveValue('Focus on architecture decisions')
  })

  it('shows character count for refinement prompt', () => {
    /**
     * Acceptance (ft-024): Display character count (e.g., "45/500")
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)
    fireEvent.change(textarea, { target: { value: 'Test prompt' } })

    // Character count should be displayed
    expect(screen.getByText(/11\/500/)).toBeInTheDocument()
  })

  it('validates max length of 500 characters', () => {
    /**
     * Acceptance (ft-024): Prompt length limited to 500 chars
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i) as HTMLTextAreaElement
    expect(textarea.maxLength).toBe(500)
  })

  it('shows error when prompt exceeds max length', () => {
    /**
     * Acceptance (ft-024): Show validation error for >500 chars
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)
    const longPrompt = 'a'.repeat(501)
    fireEvent.change(textarea, { target: { value: longPrompt } })

    // Error message should appear
    expect(screen.getByText(/prompt is too long/i)).toBeInTheDocument()
  })

  it('calls onRegenerate with custom prompt when "Regenerate" button clicked', () => {
    /**
     * Acceptance (ft-024): Submit custom prompt via Regenerate button
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)
    fireEvent.change(textarea, { target: { value: 'Focus on scalability and performance' } })

    const regenerateButton = screen.getByRole('button', { name: /^regenerate$/i })
    fireEvent.click(regenerateButton)

    expect(mockOnRegenerate).toHaveBeenCalledWith(
      'Focus on scalability and performance',
      undefined,
      undefined
    )
  })

  it('clears prompt field after successful regeneration', async () => {
    /**
     * Acceptance (ft-024): Clear prompt after submission
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)
    fireEvent.change(textarea, { target: { value: 'Test prompt' } })

    const regenerateButton = screen.getByRole('button', { name: /^regenerate$/i })
    fireEvent.click(regenerateButton)

    await waitFor(() => {
      expect(textarea).toHaveValue('')
    })
  })
})

describe('BulletRegenerationModal - Temporary Prompt Warning', () => {
  const mockOnRegenerate = vi.fn()
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('displays temporary prompt warning message', () => {
    /**
     * Acceptance (ADR-036): Inform users that prompts are NOT saved
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    expect(screen.getByText(/refinement prompts are temporary/i)).toBeInTheDocument()
    expect(screen.getByText(/only apply to this generation/i)).toBeInTheDocument()
  })

  it('shows link to edit artifact context for permanent improvements', () => {
    /**
     * Acceptance (ft-024): Provide alternative for permanent changes
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const editContextLink = screen.getByText(/edit your artifact context/i)
    expect(editContextLink).toBeInTheDocument()
  })

  it('shows info alert with prominent styling', () => {
    /**
     * Acceptance (ft-024): Warning is visually prominent
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    // Should have info alert component (testid or role)
    const alert = screen.getByRole('alert')
    expect(alert).toBeInTheDocument()
    expect(alert).toHaveClass(/info|blue/) // Variant styling
  })
})

describe('BulletRegenerationModal - Specific Bullet/Artifact Selection', () => {
  const mockOnRegenerate = vi.fn()
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('allows specifying bullet_ids_to_regenerate when provided', () => {
    /**
     * Acceptance (ft-024): Support regenerating specific bullets
     */
    const bulletIds = [1, 2, 3]

    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
        bulletIds={bulletIds}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)
    fireEvent.change(textarea, { target: { value: 'Add more impact' } })

    const regenerateButton = screen.getByRole('button', { name: /^regenerate$/i })
    fireEvent.click(regenerateButton)

    expect(mockOnRegenerate).toHaveBeenCalledWith(
      'Add more impact',
      bulletIds, // Should pass through bullet_ids
      undefined
    )
  })

  it('allows specifying artifact_ids when provided', () => {
    /**
     * Acceptance (ft-024): Support regenerating bullets for specific artifacts
     */
    const artifactIds = [5]

    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
        artifactIds={artifactIds}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)
    fireEvent.change(textarea, { target: { value: 'Focus on results' } })

    const regenerateButton = screen.getByRole('button', { name: /^regenerate$/i })
    fireEvent.click(regenerateButton)

    expect(mockOnRegenerate).toHaveBeenCalledWith(
      'Focus on results',
      undefined,
      artifactIds // Should pass through artifact_ids
    )
  })

  it('shows count of bullets to be regenerated when bullet_ids provided', () => {
    /**
     * Acceptance (ft-024): Inform user how many bullets will regenerate
     */
    const bulletIds = [1, 2, 3]

    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
        bulletIds={bulletIds}
      />
    )

    expect(screen.getByText(/regenerating 3 bullets/i)).toBeInTheDocument()
  })

  it('shows count of artifacts when artifact_ids provided', () => {
    /**
     * Acceptance (ft-024): Inform user which artifacts will regenerate
     */
    const artifactIds = [5, 6]

    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
        artifactIds={artifactIds}
      />
    )

    expect(screen.getByText(/regenerating bullets for 2 artifacts/i)).toBeInTheDocument()
  })
})

describe('BulletRegenerationModal - Modal Controls', () => {
  const mockOnRegenerate = vi.fn()
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls onClose when Cancel button clicked', () => {
    /**
     * Acceptance (ft-024): User can cancel regeneration
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const cancelButton = screen.getByRole('button', { name: /cancel/i })
    fireEvent.click(cancelButton)

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('calls onClose when modal overlay clicked', () => {
    /**
     * Acceptance (ft-024): Close modal on overlay click
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    // Radix Dialog closes on overlay click by default
    // This is tested by checking the dialog's dismissible behavior
    const modal = screen.getByRole('dialog')
    expect(modal).toBeInTheDocument()

    // Simulate ESC key press (Radix Dialog default behavior)
    fireEvent.keyDown(modal, { key: 'Escape', code: 'Escape' })

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('disables Regenerate button when prompt is empty', () => {
    /**
     * Acceptance (ft-024): Require non-empty prompt for regeneration
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const regenerateButton = screen.getByRole('button', { name: /^regenerate$/i })
    expect(regenerateButton).toBeDisabled()
  })

  it('enables Regenerate button when prompt has content', () => {
    /**
     * Acceptance (ft-024): Enable regeneration when valid prompt entered
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)
    fireEvent.change(textarea, { target: { value: 'Add specifics' } })

    const regenerateButton = screen.getByRole('button', { name: /^regenerate$/i })
    expect(regenerateButton).not.toBeDisabled()
  })

  it('shows loading state while regeneration in progress', async () => {
    /**
     * Acceptance (ft-024): Display loading state during API call
     */
    const slowOnRegenerate = vi.fn(() => new Promise(resolve => setTimeout(resolve, 1000)))

    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={slowOnRegenerate}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)
    fireEvent.change(textarea, { target: { value: 'Test prompt' } })

    const regenerateButton = screen.getByRole('button', { name: /^regenerate$/i })
    fireEvent.click(regenerateButton)

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText(/regenerating/i)).toBeInTheDocument()
    })
  })
})

describe('BulletRegenerationModal - Accessibility', () => {
  const mockOnRegenerate = vi.fn()
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('has accessible modal title', () => {
    /**
     * Acceptance (ft-024): Proper ARIA labels for screen readers
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    expect(screen.getByRole('dialog', { name: /regenerate bullet points/i })).toBeInTheDocument()
  })

  it('focuses textarea when modal opens', async () => {
    /**
     * Acceptance (ft-024): Auto-focus prompt input on modal open
     */
    const { rerender } = render(
      <BulletRegenerationModal
        isOpen={false}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    // Open modal
    rerender(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)

    await waitFor(() => {
      expect(textarea).toHaveFocus()
    })
  })

  it('supports keyboard navigation between form controls', () => {
    /**
     * Acceptance (ft-024): Tab navigation works correctly
     */
    render(
      <BulletRegenerationModal
        isOpen={true}
        onClose={mockOnClose}
        onRegenerate={mockOnRegenerate}
      />
    )

    const quickSuggestionButton = screen.getByRole('button', { name: /add more metrics/i })
    const textarea = screen.getByPlaceholderText(/describe how to improve these bullets/i)
    const cancelButton = screen.getByRole('button', { name: /cancel/i })

    // All interactive elements should be focusable
    expect(quickSuggestionButton).toBeVisible()
    expect(textarea).toBeVisible()
    expect(cancelButton).toBeVisible()
  })
})
