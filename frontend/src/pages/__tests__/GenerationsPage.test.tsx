import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import GenerationsPage from '../GenerationsPage'
import { useGeneration } from '@/hooks/useGeneration'

// Mock hooks
vi.mock('@/hooks/useGeneration', () => ({
  useGeneration: vi.fn(),
}))

// Mock ExportDialog component
vi.mock('@/components/ExportDialog', () => ({
  default: ({ isOpen }: { isOpen: boolean }) => (
    isOpen ? <div>Export Dialog</div> : null
  ),
}))

// Mock react-router-dom
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
      <a href={to}>{children}</a>
    ),
    useNavigate: () => mockNavigate,
  }
})

const mockUseGeneration = vi.mocked(useGeneration)

describe('GenerationsPage', () => {
  const mockCompletedDocuments = [
    {
      id: '1',
      type: 'cv' as const,
      status: 'completed' as const,
      progressPercentage: 100,
      createdAt: '2023-01-01T00:00:00Z',
      jobDescriptionHash: 'hash1',
      metadata: {
        artifactsUsed: [1, 2],
        skillMatchScore: 85,
        missingSkills: [],
        generationTime: 120,
        modelUsed: 'gpt-4',
      },
    },
    {
      id: '2',
      type: 'cover_letter' as const,
      status: 'completed' as const,
      progressPercentage: 100,
      createdAt: '2023-01-02T00:00:00Z',
      jobDescriptionHash: 'hash2',
      metadata: {
        artifactsUsed: [3],
        skillMatchScore: 92,
        missingSkills: [],
        generationTime: 90,
        modelUsed: 'gpt-4',
      },
    },
    {
      id: '3',
      type: 'cv' as const,
      status: 'failed' as const,
      progressPercentage: 0,
      createdAt: '2023-01-03T00:00:00Z',
      jobDescriptionHash: 'hash3',
    },
  ]

  const mockActiveGenerations = [
    {
      id: '4',
      type: 'cv' as const,
      status: 'processing' as const,
      progressPercentage: 45,
      createdAt: '2023-01-04T00:00:00Z',
      jobDescriptionHash: 'hash4',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
    mockUseGeneration.mockReturnValue({
      completedDocuments: mockCompletedDocuments,
      activeGenerations: mockActiveGenerations,
      selectedDocuments: [],
      isGenerating: false,
      toggleSelection: vi.fn(),
      clearSelection: vi.fn(),
      deleteDocument: vi.fn(),
      bulkDeleteDocuments: vi.fn(),
      createGeneration: vi.fn(),
      generateCoverLetter: vi.fn(),
      cancelGeneration: vi.fn(),
      rateGeneration: vi.fn(),
      loadUserGenerations: vi.fn(),
      getBullets: vi.fn(),
      editBullet: vi.fn(),
      approveBullets: vi.fn(),
      assembleFinalCV: vi.fn(),
    })
  })

  it('renders CVs page correctly', () => {
    render(<GenerationsPage />)

    expect(screen.getByText('Your')).toBeInTheDocument()
    expect(screen.getByText('Generate CV')).toBeInTheDocument()
    // There are multiple "CV Generation" texts (active + completed)
    expect(screen.getAllByText('CV Generation').length).toBeGreaterThan(0)
    expect(screen.getByText('Cover Letter')).toBeInTheDocument()
  })

  it('displays active generations section when there are active generations', () => {
    render(<GenerationsPage />)

    expect(screen.getByText('Active Generations')).toBeInTheDocument()
    expect(screen.getByText(/45%/)).toBeInTheDocument()
    expect(screen.getByText(/Processing artifacts.../)).toBeInTheDocument()
  })

  it('hides active generations section when there are none', () => {
    mockUseGeneration.mockReturnValue({
      completedDocuments: mockCompletedDocuments,
      activeGenerations: [],
      selectedDocuments: [],
      isGenerating: false,
      toggleSelection: vi.fn(),
      clearSelection: vi.fn(),
      deleteDocument: vi.fn(),
      bulkDeleteDocuments: vi.fn(),
      createGeneration: vi.fn(),
      generateCoverLetter: vi.fn(),
      cancelGeneration: vi.fn(),
      rateGeneration: vi.fn(),
      loadUserGenerations: vi.fn(),
      getBullets: vi.fn(),
      editBullet: vi.fn(),
      approveBullets: vi.fn(),
      assembleFinalCV: vi.fn(),
    })

    render(<GenerationsPage />)

    expect(screen.queryByText('Active Generations')).not.toBeInTheDocument()
  })

  it('filters documents by search query', async () => {
    render(<GenerationsPage />)

    const searchInput = screen.getByPlaceholderText('Search by type, job description, or model...')
    fireEvent.change(searchInput, { target: { value: 'gpt-4' } })

    await waitFor(() => {
      // Should show documents with gpt-4 model
      expect(screen.getAllByText('CV Generation').length).toBeGreaterThan(0)
      // Failed document without metadata should not be shown
      const failedBadges = screen.queryAllByText('✗ Failed')
      expect(failedBadges.length).toBe(0)
    })
  })

  it('filters documents by status', async () => {
    render(<GenerationsPage />)

    const statusSelect = screen.getByRole('combobox')
    fireEvent.change(statusSelect, { target: { value: 'completed' } })

    await waitFor(() => {
      // Should only show completed documents
      expect(screen.queryByText('✗ Failed')).not.toBeInTheDocument()
      const completedBadges = screen.getAllByText('✓ Completed')
      expect(completedBadges.length).toBe(2)
    })
  })

  it('toggles between grid and list view', () => {
    render(<GenerationsPage />)

    // Default is list view
    expect(screen.getAllByTitle('Export CV').length).toBeGreaterThan(0)

    // Switch to grid view
    const gridButton = screen.getByRole('button', { name: /grid/i })
    fireEvent.click(gridButton)

    // Grid view should still show export buttons
    expect(screen.getAllByText('Export').length).toBeGreaterThan(0)
  })

  it('toggles selection when checkbox is clicked', () => {
    const mockToggleSelection = vi.fn()
    mockUseGeneration.mockReturnValue({
      completedDocuments: mockCompletedDocuments,
      activeGenerations: [],
      selectedDocuments: [],
      isGenerating: false,
      toggleSelection: mockToggleSelection,
      clearSelection: vi.fn(),
      deleteDocument: vi.fn(),
      bulkDeleteDocuments: vi.fn(),
      createGeneration: vi.fn(),
      generateCoverLetter: vi.fn(),
      cancelGeneration: vi.fn(),
      rateGeneration: vi.fn(),
      loadUserGenerations: vi.fn(),
      getBullets: vi.fn(),
      editBullet: vi.fn(),
      approveBullets: vi.fn(),
      assembleFinalCV: vi.fn(),
    })

    render(<GenerationsPage />)

    // Find checkbox by looking for the rounded border div
    const checkboxes = document.querySelectorAll('.border-2.rounded')
    expect(checkboxes.length).toBeGreaterThan(0)

    // Click the first checkbox
    fireEvent.click(checkboxes[0])

    // Should toggle selection
    expect(mockToggleSelection).toHaveBeenCalledWith('1')
  })

  it('shows selection actions when documents are selected', () => {
    mockUseGeneration.mockReturnValue({
      completedDocuments: mockCompletedDocuments,
      activeGenerations: [],
      selectedDocuments: ['1', '2'],
      isGenerating: false,
      toggleSelection: vi.fn(),
      clearSelection: vi.fn(),
      deleteDocument: vi.fn(),
      bulkDeleteDocuments: vi.fn(),
      createGeneration: vi.fn(),
      generateCoverLetter: vi.fn(),
      cancelGeneration: vi.fn(),
      rateGeneration: vi.fn(),
      loadUserGenerations: vi.fn(),
      getBullets: vi.fn(),
      editBullet: vi.fn(),
      approveBullets: vi.fn(),
      assembleFinalCV: vi.fn(),
    })

    render(<GenerationsPage />)

    expect(screen.getByText('2 CVs selected')).toBeInTheDocument()
    expect(screen.getByText('Delete Selected')).toBeInTheDocument()
    expect(screen.getByText('Clear selection')).toBeInTheDocument()
  })

  it('clears selection when clear button is clicked', () => {
    const mockClearSelection = vi.fn()
    mockUseGeneration.mockReturnValue({
      completedDocuments: mockCompletedDocuments,
      activeGenerations: [],
      selectedDocuments: ['1', '2'],
      isGenerating: false,
      toggleSelection: vi.fn(),
      clearSelection: mockClearSelection,
      deleteDocument: vi.fn(),
      bulkDeleteDocuments: vi.fn(),
      createGeneration: vi.fn(),
      generateCoverLetter: vi.fn(),
      cancelGeneration: vi.fn(),
      rateGeneration: vi.fn(),
      loadUserGenerations: vi.fn(),
      getBullets: vi.fn(),
      editBullet: vi.fn(),
      approveBullets: vi.fn(),
      assembleFinalCV: vi.fn(),
    })

    render(<GenerationsPage />)

    const clearButton = screen.getByText('Clear selection')
    fireEvent.click(clearButton)

    expect(mockClearSelection).toHaveBeenCalled()
  })

  it('shows confirmation dialog and deletes selected documents', () => {
    const mockBulkDelete = vi.fn()
    window.confirm = vi.fn(() => true)

    mockUseGeneration.mockReturnValue({
      completedDocuments: mockCompletedDocuments,
      activeGenerations: [],
      selectedDocuments: ['1', '2'],
      isGenerating: false,
      toggleSelection: vi.fn(),
      clearSelection: vi.fn(),
      deleteDocument: vi.fn(),
      bulkDeleteDocuments: mockBulkDelete,
      createGeneration: vi.fn(),
      generateCoverLetter: vi.fn(),
      cancelGeneration: vi.fn(),
      rateGeneration: vi.fn(),
      loadUserGenerations: vi.fn(),
      getBullets: vi.fn(),
      editBullet: vi.fn(),
      approveBullets: vi.fn(),
      assembleFinalCV: vi.fn(),
    })

    render(<GenerationsPage />)

    const deleteButton = screen.getByText('Delete Selected')
    fireEvent.click(deleteButton)

    expect(window.confirm).toHaveBeenCalledWith('Delete 2 selected CVs?')
    expect(mockBulkDelete).toHaveBeenCalledWith(['1', '2'])
  })

  it('shows empty state when no documents', () => {
    mockUseGeneration.mockReturnValue({
      completedDocuments: [],
      activeGenerations: [],
      selectedDocuments: [],
      isGenerating: false,
      toggleSelection: vi.fn(),
      clearSelection: vi.fn(),
      deleteDocument: vi.fn(),
      bulkDeleteDocuments: vi.fn(),
      createGeneration: vi.fn(),
      generateCoverLetter: vi.fn(),
      cancelGeneration: vi.fn(),
      rateGeneration: vi.fn(),
      loadUserGenerations: vi.fn(),
      getBullets: vi.fn(),
      editBullet: vi.fn(),
      approveBullets: vi.fn(),
      assembleFinalCV: vi.fn(),
    })

    render(<GenerationsPage />)

    expect(screen.getByText('Ready to create your first CV?')).toBeInTheDocument()
    expect(screen.getByText('Generate Your First CV')).toBeInTheDocument()
  })

  it('shows "no CVs found" message when search has no results', () => {
    render(<GenerationsPage />)

    const searchInput = screen.getByPlaceholderText('Search by type, job description, or model...')
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } })

    expect(screen.getByText('No CVs found')).toBeInTheDocument()
    expect(screen.getByText(/Try adjusting your search or filters/)).toBeInTheDocument()
  })

  it('displays metadata correctly in grid view', () => {
    render(<GenerationsPage />)

    // Switch to grid view
    const gridButton = screen.getByRole('button', { name: /grid/i })
    fireEvent.click(gridButton)

    // Check for metadata
    expect(screen.getByText('85%')).toBeInTheDocument()
    expect(screen.getByText('92%')).toBeInTheDocument()
    expect(screen.getByText('2 items')).toBeInTheDocument()
    expect(screen.getByText('1 items')).toBeInTheDocument()
  })

  it('displays metadata correctly in list view', () => {
    render(<GenerationsPage />)

    // Default is list view - check for metadata (multiple documents have these labels)
    expect(screen.getAllByText('Match:').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Artifacts:').length).toBeGreaterThan(0)
    expect(screen.getAllByText('gpt-4').length).toBeGreaterThan(0)
  })

  it('shows different status badges for completed and failed documents', () => {
    render(<GenerationsPage />)

    // Check for completed badges
    const completedBadges = screen.getAllByText('✓ Completed')
    expect(completedBadges.length).toBe(2)

    // Check for failed badge
    expect(screen.getByText('✗ Failed')).toBeInTheDocument()
  })

  it('opens export dialog when export button is clicked in grid view', () => {
    render(<GenerationsPage />)

    // Switch to grid view
    const gridButton = screen.getByRole('button', { name: /grid/i })
    fireEvent.click(gridButton)

    const exportButtons = screen.getAllByText('Export')
    fireEvent.click(exportButtons[0])

    // Export dialog should be open
    expect(screen.getByText('Export Dialog')).toBeInTheDocument()
  })

  it('opens export dialog when export button is clicked in list view', () => {
    render(<GenerationsPage />)

    // Find export buttons in list view
    const exportButtons = screen.getAllByText('Export')
    fireEvent.click(exportButtons[0])

    // Export dialog should be open
    expect(screen.getByText('Export Dialog')).toBeInTheDocument()
  })
})
