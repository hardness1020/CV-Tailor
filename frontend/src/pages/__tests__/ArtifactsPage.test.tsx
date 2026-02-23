import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import ArtifactsPage from '../ArtifactsPage'
import { useArtifacts } from '@/hooks/useArtifacts'
import { useArtifactStore } from '@/stores/artifactStore'

// Mock hooks
vi.mock('@/hooks/useArtifacts', () => ({
  useArtifacts: vi.fn(),
}))

vi.mock('@/stores/artifactStore', () => ({
  useArtifactStore: vi.fn(),
}))

// Mock react-router-dom
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
    useNavigate: () => mockNavigate,
  }
})

const mockUseArtifacts = vi.mocked(useArtifacts)
const mockUseArtifactStore = vi.mocked(useArtifactStore)

describe('ArtifactsPage', () => {
  const mockArtifacts = [
    {
      id: 1,
      title: 'Test Artifact 1',
      description: 'Test Description 1',
      technologies: ['React', 'TypeScript'],
      startDate: '2023-01-01',
      endDate: '2023-12-31',
      status: 'active' as const,
      evidenceLinks: [],
      labels: [],
    },
    {
      id: 2,
      title: 'Test Artifact 2',
      description: 'Test Description 2',
      technologies: ['Vue', 'JavaScript'],
      startDate: '2023-06-01',
      endDate: '2023-12-31',
      status: 'active' as const,
      evidenceLinks: [],
      labels: [],
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
    mockUseArtifacts.mockReturnValue({
      artifacts: mockArtifacts,
      loadArtifacts: vi.fn(),
      createArtifact: vi.fn(),
      updateArtifact: vi.fn(),
      deleteArtifact: vi.fn(),
      bulkDelete: vi.fn(),
      uploadProgress: {},
      isLoading: false,
      error: null,
    })

    mockUseArtifactStore.mockReturnValue({
      artifacts: mockArtifacts,
      selectedArtifacts: [],
      filters: {},
      isLoading: false,
      error: null,
      toggleSelection: vi.fn(),
      clearSelection: vi.fn(),
      setArtifacts: vi.fn(),
      addArtifact: vi.fn(),
      updateArtifact: vi.fn(),
      deleteArtifact: vi.fn(),
      setLoading: vi.fn(),
      setError: vi.fn(),
      setFilters: vi.fn(),
    })
  })

  it('renders artifacts page correctly', () => {
    render(<ArtifactsPage />)

    expect(screen.getByText('Professional')).toBeInTheDocument()
    expect(screen.getByText('Upload Artifact')).toBeInTheDocument()
    expect(screen.getByText('Test Artifact 1')).toBeInTheDocument()
    expect(screen.getByText('Test Artifact 2')).toBeInTheDocument()
  })

  it('filters artifacts by search query', async () => {
    render(<ArtifactsPage />)

    const searchInput = screen.getByPlaceholderText('Search by title, description, or technology...')
    fireEvent.change(searchInput, { target: { value: 'React' } })

    await waitFor(() => {
      expect(screen.getByText('Test Artifact 1')).toBeInTheDocument()
      expect(screen.queryByText('Test Artifact 2')).not.toBeInTheDocument()
    })
  })

  it('toggles between grid and list view', () => {
    render(<ArtifactsPage />)

    const listViewButton = screen.getByRole('button', { name: /list/i })
    fireEvent.click(listViewButton)

    // In list view, we should see edit and delete buttons
    expect(screen.getAllByTitle('Edit artifact')).toHaveLength(2)
    expect(screen.getAllByTitle('Delete artifact')).toHaveLength(2)
  })

  it('opens upload dialog when upload button is clicked', () => {
    render(<ArtifactsPage />)

    const uploadButton = screen.getByText('Upload Artifact')
    fireEvent.click(uploadButton)

    expect(screen.getByText('Upload Artifact')).toBeInTheDocument()
  })

  it('shows empty state when no artifacts', () => {
    mockUseArtifacts.mockReturnValue({
      artifacts: [],
      loadArtifacts: vi.fn(),
      createArtifact: vi.fn(),
      updateArtifact: vi.fn(),
      deleteArtifact: vi.fn(),
      bulkDelete: vi.fn(),
      uploadProgress: {},
      isLoading: false,
      error: null,
    })

    mockUseArtifactStore.mockReturnValue({
      artifacts: [],
      selectedArtifacts: [],
      filters: {},
      isLoading: false,
      error: null,
      toggleSelection: vi.fn(),
      clearSelection: vi.fn(),
      setArtifacts: vi.fn(),
      addArtifact: vi.fn(),
      updateArtifact: vi.fn(),
      deleteArtifact: vi.fn(),
      setLoading: vi.fn(),
      setError: vi.fn(),
      setFilters: vi.fn(),
    })

    render(<ArtifactsPage />)

    expect(screen.getByText('No artifacts found')).toBeInTheDocument()
    expect(screen.getByText('Upload First Artifact')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    mockUseArtifacts.mockReturnValue({
      artifacts: [],
      loadArtifacts: vi.fn(),
      createArtifact: vi.fn(),
      updateArtifact: vi.fn(),
      deleteArtifact: vi.fn(),
      bulkDelete: vi.fn(),
      uploadProgress: {},
      isLoading: true,
      error: null,
    })

    render(<ArtifactsPage />)

    expect(screen.getByText('Loading artifacts...')).toBeInTheDocument()
  })

  it('navigates to artifact detail when card is clicked in grid view', () => {
    render(<ArtifactsPage />)

    const artifactCard = screen.getByText('Test Artifact 1').closest('div[class*="cursor-pointer"]')
    expect(artifactCard).toBeInTheDocument()

    if (artifactCard) {
      fireEvent.click(artifactCard)
    }

    expect(mockNavigate).toHaveBeenCalledWith('/artifacts/1')
  })

  it('toggles selection when checkbox is clicked without navigating', () => {
    const mockToggleSelection = vi.fn()
    mockUseArtifactStore.mockReturnValue({
      artifacts: mockArtifacts,
      selectedArtifacts: [],
      filters: {},
      isLoading: false,
      error: null,
      toggleSelection: mockToggleSelection,
      clearSelection: vi.fn(),
      setArtifacts: vi.fn(),
      addArtifact: vi.fn(),
      updateArtifact: vi.fn(),
      deleteArtifact: vi.fn(),
      setLoading: vi.fn(),
      setError: vi.fn(),
      setFilters: vi.fn(),
    })

    render(<ArtifactsPage />)

    // Find checkbox by looking for the rounded border div
    const checkboxes = document.querySelectorAll('.border-2.rounded')
    expect(checkboxes.length).toBeGreaterThan(0)

    // Click the first checkbox
    fireEvent.click(checkboxes[0])

    // Should toggle selection but not navigate
    expect(mockToggleSelection).toHaveBeenCalledWith(1)
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('navigates to artifact detail when list item is clicked', () => {
    render(<ArtifactsPage />)

    // Switch to list view
    const listViewButton = screen.getByRole('button', { name: /list/i })
    fireEvent.click(listViewButton)

    const artifactItem = screen.getByText('Test Artifact 1').closest('div[class*="cursor-pointer"]')
    expect(artifactItem).toBeInTheDocument()

    if (artifactItem) {
      fireEvent.click(artifactItem)
    }

    expect(mockNavigate).toHaveBeenCalledWith('/artifacts/1')
  })
})