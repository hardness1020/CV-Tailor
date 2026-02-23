/**
 * Unit tests for GenerationDetailPage (ft-024 standalone bullet generation)
 *
 * Tests cover:
 * - CV metadata display
 * - Bullet points grouped by artifact
 * - Regeneration modal opening/closing
 * - Individual bullet approval/rejection/editing
 * - Polling for updates after regeneration
 *
 * These tests are FAILING until GenerationDetailPage is implemented (TDD RED phase)
 */

import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { useParams } from 'react-router-dom'
import GenerationDetailPage from '../GenerationDetailPage'
import { apiClient } from '@/services/apiClient'

// Mock API client
vi.mock('@/services/apiClient', () => ({
  apiClient: {
    getGeneration: vi.fn(),
    getBullets: vi.fn(),
    getGenerationBullets: vi.fn(),
    regenerateBullets: vi.fn(),
    regenerateGenerationBullets: vi.fn(),
    approveBullet: vi.fn(),
    rejectBullet: vi.fn(),
    editBullet: vi.fn(),
  }
}))

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: vi.fn(),
    useNavigate: () => vi.fn(),
  }
})

// Mock BulletRegenerationModal component
vi.mock('@/components/BulletRegenerationModal', () => ({
  default: ({
    isOpen,
    onClose,
    onRegenerate
  }: {
    isOpen: boolean
    onClose: () => void
    onRegenerate: (refinementPrompt: string, bulletIds?: number[], artifactIds?: number[]) => void
  }) => (
    isOpen ? (
      <div data-testid="bullet-regeneration-modal">
        <button onClick={onClose}>Close Modal</button>
        <button onClick={() => onRegenerate('Focus on leadership')}>
          Regenerate
        </button>
      </div>
    ) : null
  ),
}))

const mockUseParams = vi.mocked(useParams)

describe('GenerationDetailPage - CV Metadata Display', () => {
  const mockGeneration = {
    id: 'cv-123',
    type: 'cv' as const,
    status: 'bullets_generated' as const,
    progressPercentage: 50,
    createdAt: '2023-10-27T12:00:00Z',
    jobDescriptionHash: 'job-hash-456',
    metadata: {
      artifactsUsed: [1, 2],
      skillMatchScore: 85,
      missingSkills: ['Docker', 'AWS'],
      generationTime: 45,
      modelUsed: 'gpt-4',
    },
    job_description_data: {
      raw_text: 'Looking for senior React developer...',
      key_requirements: ['React', 'TypeScript', 'Node.js'],
    },
  }

  const mockBullets = [
    {
      id: 1,
      artifact_id: 1,
      artifact_title: 'E-commerce Platform',
      text: 'Led team of 6 engineers to deploy React-based marketplace',
      user_edited: false,
      user_approved: false,
      user_rejected: false,
      original_text: 'Led team of 6 engineers to deploy React-based marketplace',
      quality_metrics: {
        specificity_score: 0.85,
        impact_score: 0.75,
        action_verb_strength: 0.90,
      },
    },
    {
      id: 2,
      artifact_id: 1,
      artifact_title: 'E-commerce Platform',
      text: 'Implemented TypeScript migration reducing bugs by 40%',
      user_edited: false,
      user_approved: false,
      user_rejected: false,
      original_text: 'Implemented TypeScript migration reducing bugs by 40%',
      quality_metrics: {
        specificity_score: 0.90,
        impact_score: 0.85,
        action_verb_strength: 0.88,
      },
    },
    {
      id: 3,
      artifact_id: 2,
      artifact_title: 'API Service Redesign',
      text: 'Architected Node.js microservices handling 10M requests/day',
      user_edited: false,
      user_approved: false,
      user_rejected: false,
      original_text: 'Architected Node.js microservices handling 10M requests/day',
      quality_metrics: {
        specificity_score: 0.92,
        impact_score: 0.88,
        action_verb_strength: 0.85,
      },
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseParams.mockReturnValue({ id: 'cv-123' })
    vi.mocked(apiClient.getGeneration).mockResolvedValue(mockGeneration)
    vi.mocked(apiClient.getBullets).mockResolvedValue({ bullets: mockBullets })
    vi.mocked(apiClient.getGenerationBullets).mockResolvedValue({ bullets: mockBullets })
  })

  it('renders CV metadata correctly', async () => {
    /**
     * Acceptance (ft-024): GenerationDetailPage displays CV metadata
     * - Job description snippet
     * - Skill match score
     * - Missing skills
     * - Artifacts used count
     * - Generation status
     */
    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Looking for senior React developer/i)).toBeInTheDocument()
      expect(screen.getByText(/85%/i)).toBeInTheDocument() // Skill match score
      expect(screen.getByText(/Docker/i)).toBeInTheDocument() // Missing skill
      expect(screen.getByText(/AWS/i)).toBeInTheDocument() // Missing skill
      expect(screen.getByText(/2 artifacts/i)).toBeInTheDocument()
    })
  })

  it('displays bullets grouped by artifact', async () => {
    /**
     * Acceptance (ft-024): Bullets are grouped by artifact_title
     * - E-commerce Platform (2 bullets)
     * - API Service Redesign (1 bullet)
     */
    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('E-commerce Platform')).toBeInTheDocument()
      expect(screen.getByText('API Service Redesign')).toBeInTheDocument()
    })

    // Check bullet texts
    expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    expect(screen.getByText(/Implemented TypeScript migration/i)).toBeInTheDocument()
    expect(screen.getByText(/Architected Node.js microservices/i)).toBeInTheDocument()
  })

  it('displays quality metrics for each bullet', async () => {
    /**
     * Acceptance (ft-024): Show quality_metrics for each bullet
     * - specificity_score
     * - impact_score
     * - action_verb_strength
     */
    render(<GenerationDetailPage />)

    await waitFor(() => {
      // Quality metrics should be visible (displayed as percentages or scores)
      expect(screen.getByText(/85%/i)).toBeInTheDocument() // specificity_score for bullet 1
      expect(screen.getByText(/90%/i)).toBeInTheDocument() // specificity_score for bullet 2
    })
  })

  it('shows loading state while fetching CV data', () => {
    /**
     * Acceptance (ft-024): Display loading state
     */
    vi.mocked(apiClient.getGeneration).mockReturnValue(new Promise(() => {})) // Never resolves

    render(<GenerationDetailPage />)

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('shows error state when CV not found', async () => {
    /**
     * Acceptance (ft-024): Handle 404 error gracefully
     */
    vi.mocked(apiClient.getGeneration).mockRejectedValue({
      response: { status: 404 }
    })

    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/not found/i)).toBeInTheDocument()
    })
  })
})

describe('GenerationDetailPage - Bullet Regeneration', () => {
  const mockGeneration = {
    id: 'cv-123',
    type: 'cv' as const,
    status: 'bullets_generated' as const,
    progressPercentage: 50,
    createdAt: '2023-10-27T12:00:00Z',
    jobDescriptionHash: 'job-hash-456',
    metadata: {
      artifactsUsed: [1],
      skillMatchScore: 85,
      missingSkills: [],
      generationTime: 45,
      modelUsed: 'gpt-4',
    },
    job_description_data: {
      raw_text: 'Looking for senior React developer...',
      key_requirements: ['React', 'TypeScript'],
    },
  }

  const mockBullets = [
    {
      id: 1,
      artifact_id: 1,
      artifact_title: 'E-commerce Platform',
      text: 'Led team of 6 engineers',
      user_edited: false,
      user_approved: false,
      user_rejected: false,
      original_text: 'Led team of 6 engineers',
      quality_metrics: {
        specificity_score: 0.85,
        impact_score: 0.75,
        action_verb_strength: 0.90,
      },
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseParams.mockReturnValue({ id: 'cv-123' })
    vi.mocked(apiClient.getGeneration).mockResolvedValue(mockGeneration)
    vi.mocked(apiClient.getBullets).mockResolvedValue({ bullets: mockBullets })
    vi.mocked(apiClient.getGenerationBullets).mockResolvedValue({ bullets: mockBullets })
  })

  it('opens regeneration modal when "Regenerate Bullets" button clicked', async () => {
    /**
     * Acceptance (ft-024): User can open bullet regeneration modal
     */
    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    })

    const regenerateButton = screen.getByRole('button', { name: /regenerate bullets/i })
    fireEvent.click(regenerateButton)

    expect(screen.getByTestId('bullet-regeneration-modal')).toBeInTheDocument()
  })

  it('closes regeneration modal when close button clicked', async () => {
    /**
     * Acceptance (ft-024): User can close regeneration modal
     */
    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    })

    // Open modal
    const regenerateButton = screen.getByRole('button', { name: /regenerate bullets/i })
    fireEvent.click(regenerateButton)

    expect(screen.getByTestId('bullet-regeneration-modal')).toBeInTheDocument()

    // Close modal
    const closeButton = screen.getByText('Close Modal')
    fireEvent.click(closeButton)

    expect(screen.queryByTestId('bullet-regeneration-modal')).not.toBeInTheDocument()
  })

  it('calls regenerateBullets API when regeneration requested', async () => {
    /**
     * Acceptance (ft-024): Regenerate bullets with refinement_prompt
     */
    vi.mocked(apiClient.regenerateBullets).mockResolvedValue({
      bullets: mockBullets,
    })

    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    })

    // Open modal
    const regenerateButton = screen.getByRole('button', { name: /regenerate bullets/i })
    fireEvent.click(regenerateButton)

    // Trigger regeneration
    const regenerateModalButton = screen.getByText('Regenerate')
    fireEvent.click(regenerateModalButton)

    await waitFor(() => {
      expect(apiClient.regenerateBullets).toHaveBeenCalledWith('cv-123', {
        refinement_prompt: 'Focus on leadership',
        bullet_ids_to_regenerate: undefined,
        artifact_ids: undefined,
      })
    })
  })

  it('polls for updates after regeneration triggered', async () => {
    /**
     * Acceptance (ft-024): Poll getBullets after regeneration
     */
    vi.mocked(apiClient.regenerateBullets).mockResolvedValue({
      bullets: mockBullets,
    })

    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    })

    // Initial fetch
    expect(apiClient.getBullets).toHaveBeenCalledTimes(1)

    // Open modal and regenerate
    const regenerateButton = screen.getByRole('button', { name: /regenerate bullets/i })
    fireEvent.click(regenerateButton)

    const regenerateModalButton = screen.getByText('Regenerate')
    fireEvent.click(regenerateModalButton)

    // Should poll getBullets after regeneration
    await waitFor(() => {
      expect(apiClient.getBullets).toHaveBeenCalledTimes(2)
    }, { timeout: 3000 })
  })

  it('shows loading state during regeneration', async () => {
    /**
     * Acceptance (ft-024): Display loading state during regeneration
     */
    vi.mocked(apiClient.regenerateBullets).mockReturnValue(new Promise(() => {})) // Never resolves

    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    })

    // Open modal and regenerate
    const regenerateButton = screen.getByRole('button', { name: /regenerate bullets/i })
    fireEvent.click(regenerateButton)

    const regenerateModalButton = screen.getByText('Regenerate')
    fireEvent.click(regenerateModalButton)

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText(/regenerating/i)).toBeInTheDocument()
    })
  })
})

describe('GenerationDetailPage - Individual Bullet Approval', () => {
  const mockGeneration = {
    id: 'cv-123',
    type: 'cv' as const,
    status: 'bullets_generated' as const,
    progressPercentage: 50,
    createdAt: '2023-10-27T12:00:00Z',
    jobDescriptionHash: 'job-hash-456',
    metadata: {
      artifactsUsed: [1],
      skillMatchScore: 85,
      missingSkills: [],
      generationTime: 45,
      modelUsed: 'gpt-4',
    },
    job_description_data: {
      raw_text: 'Looking for senior React developer...',
      key_requirements: ['React'],
    },
  }

  const mockBullets = [
    {
      id: 1,
      artifact_id: 1,
      artifact_title: 'E-commerce Platform',
      text: 'Led team of 6 engineers',
      user_edited: false,
      user_approved: false,
      user_rejected: false,
      original_text: 'Led team of 6 engineers',
      quality_metrics: {
        specificity_score: 0.85,
        impact_score: 0.75,
        action_verb_strength: 0.90,
      },
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseParams.mockReturnValue({ id: 'cv-123' })
    vi.mocked(apiClient.getGeneration).mockResolvedValue(mockGeneration)
    vi.mocked(apiClient.getBullets).mockResolvedValue({ bullets: mockBullets })
    vi.mocked(apiClient.getGenerationBullets).mockResolvedValue({ bullets: mockBullets })
  })

  it('calls approveBullet API when approve button clicked', async () => {
    /**
     * Acceptance (ft-024): User can approve individual bullets
     */
    vi.mocked(apiClient.approveBullet).mockResolvedValue({
      ...mockBullets[0],
      user_approved: true,
    })

    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    })

    const approveButton = screen.getByRole('button', { name: /approve/i })
    fireEvent.click(approveButton)

    await waitFor(() => {
      expect(apiClient.approveBullet).toHaveBeenCalledWith('cv-123', 1)
    })
  })

  it('calls rejectBullet API when reject button clicked', async () => {
    /**
     * Acceptance (ft-024): User can reject individual bullets
     */
    vi.mocked(apiClient.rejectBullet).mockResolvedValue({
      ...mockBullets[0],
      user_rejected: true,
    })

    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    })

    const rejectButton = screen.getByRole('button', { name: /reject/i })
    fireEvent.click(rejectButton)

    await waitFor(() => {
      expect(apiClient.rejectBullet).toHaveBeenCalledWith('cv-123', 1)
    })
  })

  it('opens edit mode when edit button clicked', async () => {
    /**
     * Acceptance (ft-024): User can edit individual bullets inline
     */
    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    })

    const editButton = screen.getByRole('button', { name: /edit/i })
    fireEvent.click(editButton)

    // Should show textarea for editing
    const textarea = screen.getByRole('textbox')
    expect(textarea).toBeInTheDocument()
    expect(textarea).toHaveValue('Led team of 6 engineers')
  })

  it('calls editBullet API when save button clicked after editing', async () => {
    /**
     * Acceptance (ft-024): Save edited bullet text
     */
    vi.mocked(apiClient.editBullet).mockResolvedValue({
      ...mockBullets[0],
      text: 'Led team of 8 engineers (edited)',
      user_edited: true,
    })

    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    })

    // Enter edit mode
    const editButton = screen.getByRole('button', { name: /edit/i })
    fireEvent.click(editButton)

    // Edit text
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: 'Led team of 8 engineers (edited)' } })

    // Save
    const saveButton = screen.getByRole('button', { name: /save/i })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(apiClient.editBullet).toHaveBeenCalledWith('cv-123', 1, {
        text: 'Led team of 8 engineers (edited)',
      })
    })
  })

  it('shows visual indicator for approved bullets', async () => {
    /**
     * Acceptance (ft-024): Visual distinction for approved bullets
     */
    const approvedBullets = [
      {
        ...mockBullets[0],
        user_approved: true,
      },
    ]
    vi.mocked(apiClient.getBullets).mockResolvedValue({ bullets: approvedBullets })

    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    })

    // Should show approved indicator (e.g., checkmark icon, green border)
    expect(screen.getByTestId('approved-indicator')).toBeInTheDocument()
  })

  it('shows visual indicator for rejected bullets', async () => {
    /**
     * Acceptance (ft-024): Visual distinction for rejected bullets
     */
    const rejectedBullets = [
      {
        ...mockBullets[0],
        user_rejected: true,
      },
    ]
    vi.mocked(apiClient.getBullets).mockResolvedValue({ bullets: rejectedBullets })

    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 6 engineers/i)).toBeInTheDocument()
    })

    // Should show rejected indicator (e.g., X icon, red border)
    expect(screen.getByTestId('rejected-indicator')).toBeInTheDocument()
  })

  it('shows visual indicator for edited bullets', async () => {
    /**
     * Acceptance (ft-024): Visual distinction for edited bullets
     */
    const editedBullets = [
      {
        ...mockBullets[0],
        text: 'Led team of 8 engineers (edited)',
        user_edited: true,
      },
    ]
    vi.mocked(apiClient.getBullets).mockResolvedValue({ bullets: editedBullets })

    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Led team of 8 engineers \(edited\)/i)).toBeInTheDocument()
    })

    // Should show edited indicator (e.g., pencil icon, "Edited" badge)
    expect(screen.getByTestId('edited-indicator')).toBeInTheDocument()
  })
})

describe('GenerationDetailPage - Proceed to CV Assembly', () => {
  const mockGeneration = {
    id: 'cv-123',
    type: 'cv' as const,
    status: 'bullets_generated' as const,
    progressPercentage: 50,
    createdAt: '2023-10-27T12:00:00Z',
    jobDescriptionHash: 'job-hash-456',
    metadata: {
      artifactsUsed: [1],
      skillMatchScore: 85,
      missingSkills: [],
      generationTime: 45,
      modelUsed: 'gpt-4',
    },
    job_description_data: {
      raw_text: 'Looking for senior React developer...',
      key_requirements: ['React'],
    },
  }

  const mockBullets = [
    {
      id: 1,
      artifact_id: 1,
      artifact_title: 'E-commerce Platform',
      text: 'Led team of 6 engineers',
      user_edited: false,
      user_approved: true, // Approved
      user_rejected: false,
      original_text: 'Led team of 6 engineers',
      quality_metrics: {
        specificity_score: 0.85,
        impact_score: 0.75,
        action_verb_strength: 0.90,
      },
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseParams.mockReturnValue({ id: 'cv-123' })
    vi.mocked(apiClient.getGeneration).mockResolvedValue(mockGeneration)
    vi.mocked(apiClient.getBullets).mockResolvedValue({ bullets: mockBullets })
    vi.mocked(apiClient.getGenerationBullets).mockResolvedValue({ bullets: mockBullets })
  })

  it('shows "Proceed to CV Assembly" button when all bullets decided', async () => {
    /**
     * Acceptance (ft-024): Show proceed button when all bullets approved/rejected
     */
    render(<GenerationDetailPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /proceed to cv assembly/i })).toBeInTheDocument()
    })
  })

  it('disables "Proceed" button when not all bullets decided', async () => {
    /**
     * Acceptance (ft-024): Disable proceed button when bullets pending
     */
    const pendingBullets = [
      {
        ...mockBullets[0],
        user_approved: false, // Not decided
        user_rejected: false,
      },
    ]
    vi.mocked(apiClient.getBullets).mockResolvedValue({ bullets: pendingBullets })

    render(<GenerationDetailPage />)

    await waitFor(() => {
      const proceedButton = screen.getByRole('button', { name: /proceed to cv assembly/i })
      expect(proceedButton).toBeDisabled()
    })
  })
})
