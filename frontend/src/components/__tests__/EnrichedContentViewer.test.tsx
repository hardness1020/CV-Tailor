import { render, screen, fireEvent } from '@/test/utils'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { EnrichedContentViewer } from '../EnrichedContentViewer'
import type { Artifact } from '@/types'

describe('EnrichedContentViewer', () => {
  const mockOnReEnrich = vi.fn()
  const mockOnEdit = vi.fn()
  const mockOnAcceptAll = vi.fn()

  const baseArtifact: Artifact = {
    id: 1,
    title: 'Test Project',
    description: 'Original description',
    artifactType: 'project',
    startDate: '2024-01-01',
    technologies: ['Python', 'Django'],
    evidenceLinks: [],
    labels: [],
    status: 'active',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows no enrichment message when no enriched content exists', () => {
    render(
      <EnrichedContentViewer
        artifact={baseArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    expect(screen.getByText('No Enriched Content Yet')).toBeInTheDocument()
    expect(screen.getByText('Enrich with AI')).toBeInTheDocument()
  })

  it('triggers enrichment when Enrich with AI button is clicked', () => {
    render(
      <EnrichedContentViewer
        artifact={baseArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    const enrichButton = screen.getByText('Enrich with AI')
    fireEvent.click(enrichButton)

    expect(mockOnReEnrich).toHaveBeenCalledTimes(1)
  })

  it('disables enrich button when isEnriching is true', () => {
    render(
      <EnrichedContentViewer
        artifact={baseArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
        isEnriching={true}
      />
    )

    const enrichButton = screen.getByText('Enriching...')
    expect(enrichButton).toBeDisabled()
  })

  it('displays enriched content when available', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      unifiedDescription: 'AI-enhanced description with more detail',
      enrichedTechnologies: ['Python', 'Django', 'PostgreSQL', 'Redis'],
      enrichedAchievements: ['Improved performance by 50%', 'Reduced costs by $10k'],
      processingConfidence: 0.85,
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    expect(screen.getByText('AI-Enriched Content')).toBeInTheDocument()
    expect(screen.getByText('85% Confidence')).toBeInTheDocument()
  })

  it('shows description tab by default', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      unifiedDescription: 'AI-enhanced description',
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    expect(screen.getByText('Original Description')).toBeInTheDocument()
    expect(screen.getByText('AI-Enhanced Description')).toBeInTheDocument()
    expect(screen.getByText('Original description')).toBeInTheDocument()
    expect(screen.getByText('AI-enhanced description')).toBeInTheDocument()
  })

  it('switches to technologies tab when clicked', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      enrichedTechnologies: ['Python', 'Django', 'PostgreSQL'],
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    const techTab = screen.getByText('Technologies')
    fireEvent.click(techTab)

    expect(screen.getByText('Original Technologies')).toBeInTheDocument()
    expect(screen.getByText('AI-Extracted Technologies')).toBeInTheDocument()
    expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
  })

  it('shows technology counts in tab badge', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      enrichedTechnologies: ['Python', 'Django', 'PostgreSQL', 'Redis', 'Docker'],
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    // Technologies tab should show count badge
    const techTab = screen.getByText('Technologies')
    const badge = techTab.nextElementSibling
    expect(badge).toHaveTextContent('5')
  })

  it('switches to achievements tab when clicked', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      enrichedAchievements: [
        'Improved performance by 50%',
        'Reduced costs by $10k',
        'Increased user engagement by 30%',
      ],
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    const achievementsTab = screen.getByText('Achievements')
    fireEvent.click(achievementsTab)

    expect(screen.getByText('AI-Identified Achievements')).toBeInTheDocument()
    expect(screen.getByText('Improved performance by 50%')).toBeInTheDocument()
    expect(screen.getByText('Reduced costs by $10k')).toBeInTheDocument()
    expect(screen.getByText('Increased user engagement by 30%')).toBeInTheDocument()
  })

  it('shows achievement counts in tab badge', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      enrichedAchievements: ['Achievement 1', 'Achievement 2'],
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    const achievementsTab = screen.getByText('Achievements')
    const badge = achievementsTab.nextElementSibling
    expect(badge).toHaveTextContent('2')
  })

  it('numbers achievements correctly', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      enrichedAchievements: ['First achievement', 'Second achievement', 'Third achievement'],
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    const achievementsTab = screen.getByText('Achievements')
    fireEvent.click(achievementsTab)

    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('calls onEdit when Edit button is clicked', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      unifiedDescription: 'AI description',
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    const editButton = screen.getByText('Edit')
    fireEvent.click(editButton)

    expect(mockOnEdit).toHaveBeenCalledTimes(1)
  })

  it('calls onReEnrich when Re-enrich button is clicked', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      unifiedDescription: 'AI description',
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    const reEnrichButton = screen.getByText('Re-enrich')
    fireEvent.click(reEnrichButton)

    expect(mockOnReEnrich).toHaveBeenCalledTimes(1)
  })

  it('disables Re-enrich button when isEnriching is true', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      unifiedDescription: 'AI description',
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
        isEnriching={true}
      />
    )

    const reEnrichButton = screen.getByText('Re-enrich')
    expect(reEnrichButton).toBeDisabled()
  })

  it('calls onAcceptAll when Accept All button is clicked', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      unifiedDescription: 'AI description',
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    const acceptButton = screen.getByText('Accept All')
    fireEvent.click(acceptButton)

    expect(mockOnAcceptAll).toHaveBeenCalledTimes(1)
  })

  it('shows no enriched technologies message when empty', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      enrichedTechnologies: [],
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    const techTab = screen.getByText('Technologies')
    fireEvent.click(techTab)

    expect(screen.getByText('No enriched technologies available')).toBeInTheDocument()
  })

  it('shows no achievements message when empty', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      enrichedAchievements: [],
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    const achievementsTab = screen.getByText('Achievements')
    fireEvent.click(achievementsTab)

    expect(screen.getByText('No achievements identified yet')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      unifiedDescription: 'AI description',
    }

    const { container } = render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
        className="custom-test-class"
      />
    )

    const element = container.querySelector('.custom-test-class')
    expect(element).toBeInTheDocument()
  })

  it('displays side-by-side comparison for descriptions', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      description: 'Original short description',
      unifiedDescription: 'Enhanced description with much more detail and context',
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    expect(screen.getByText('Original Description')).toBeInTheDocument()
    expect(screen.getByText('AI-Enhanced Description')).toBeInTheDocument()
    expect(screen.getByText('Original short description')).toBeInTheDocument()
    expect(screen.getByText('Enhanced description with much more detail and context')).toBeInTheDocument()
  })

  it('displays confidence score when available', () => {
    const enrichedArtifact: Artifact = {
      ...baseArtifact,
      unifiedDescription: 'AI description',
      processingConfidence: 0.92,
    }

    render(
      <EnrichedContentViewer
        artifact={enrichedArtifact}
        onReEnrich={mockOnReEnrich}
        onEdit={mockOnEdit}
        onAcceptAll={mockOnAcceptAll}
      />
    )

    expect(screen.getByText('92% Confidence')).toBeInTheDocument()
  })
})
