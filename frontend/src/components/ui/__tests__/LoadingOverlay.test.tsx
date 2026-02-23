import { render, screen, fireEvent } from '@/test/utils'
import { vi, describe, it, expect } from 'vitest'
import { LoadingOverlay } from '../LoadingOverlay'

describe('LoadingOverlay', () => {
  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <LoadingOverlay isOpen={false} message="Loading..." />
    )

    expect(container.firstChild).toBeNull()
  })

  it('renders overlay when isOpen is true', () => {
    render(<LoadingOverlay isOpen={true} message="Processing your request..." />)

    expect(screen.getByText('Processing your request...')).toBeInTheDocument()
  })

  it('displays animated spinner when overlay is open', () => {
    const { container } = render(
      <LoadingOverlay isOpen={true} message="Please wait..." />
    )

    // Check for spinner with animate-spin class
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('shows progress bar when progress prop is provided', () => {
    render(
      <LoadingOverlay isOpen={true} message="Enriching..." progress={45} />
    )

    expect(screen.getByText('45%')).toBeInTheDocument()
    expect(screen.getByText('Processing...')).toBeInTheDocument()
  })

  it('hides progress bar when progress prop is undefined', () => {
    render(<LoadingOverlay isOpen={true} message="Loading..." />)

    expect(screen.queryByText('Processing...')).not.toBeInTheDocument()
    expect(screen.queryByText('%')).not.toBeInTheDocument()
  })

  it('updates progress bar width based on progress value', () => {
    const { container } = render(
      <LoadingOverlay isOpen={true} message="Processing..." progress={75} />
    )

    const progressBar = container.querySelector('[style*="width"]')
    expect(progressBar).toHaveStyle({ width: '75%' })
  })

  it('handles 0% progress correctly', () => {
    const { container } = render(
      <LoadingOverlay isOpen={true} message="Starting..." progress={0} />
    )

    expect(screen.getByText('0%')).toBeInTheDocument()
    const progressBar = container.querySelector('[style*="width"]')
    expect(progressBar).toHaveStyle({ width: '0%' })
  })

  it('handles 100% progress correctly', () => {
    const { container } = render(
      <LoadingOverlay isOpen={true} message="Almost done..." progress={100} />
    )

    expect(screen.getByText('100%')).toBeInTheDocument()
    const progressBar = container.querySelector('[style*="width"]')
    expect(progressBar).toHaveStyle({ width: '100%' })
  })

  it('applies backdrop blur styling', () => {
    const { container } = render(
      <LoadingOverlay isOpen={true} message="Loading..." />
    )

    const backdrop = container.firstChild
    expect(backdrop).toHaveClass('backdrop-blur-sm')
    expect(backdrop).toHaveClass('bg-black/50')
  })

  it('prevents clicking through overlay (non-dismissible)', () => {
    const handleBackdropClick = vi.fn()

    const { container } = render(
      <div onClick={handleBackdropClick}>
        <LoadingOverlay isOpen={true} message="Processing..." />
      </div>
    )

    const overlay = container.querySelector('.fixed')
    fireEvent.click(overlay!)

    // Overlay should consume the click, not propagate to parent
    expect(handleBackdropClick).not.toHaveBeenCalled()
  })

  it('centers content vertically and horizontally', () => {
    const { container } = render(
      <LoadingOverlay isOpen={true} message="Loading..." />
    )

    const overlay = container.firstChild
    expect(overlay).toHaveClass('flex', 'items-center', 'justify-center')
  })

  it('has high z-index to appear above other content', () => {
    const { container } = render(
      <LoadingOverlay isOpen={true} message="Loading..." />
    )

    const overlay = container.firstChild
    expect(overlay).toHaveClass('z-50')
  })

  it('uses gradient progress bar styling', () => {
    const { container } = render(
      <LoadingOverlay isOpen={true} message="Processing..." progress={50} />
    )

    const progressBar = container.querySelector('.bg-gradient-to-r')
    expect(progressBar).toBeInTheDocument()
    expect(progressBar).toHaveClass('from-purple-600', 'to-pink-600')
  })

  it('shows pulsing animation effect on spinner', () => {
    const { container } = render(
      <LoadingOverlay isOpen={true} message="Processing..." />
    )

    const pulsingRing = container.querySelector('.animate-ping')
    expect(pulsingRing).toBeInTheDocument()
    expect(pulsingRing).toHaveClass('opacity-75')
  })

  it('transitions overlay appearance smoothly', () => {
    const { rerender } = render(
      <LoadingOverlay isOpen={false} message="Loading..." />
    )

    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()

    rerender(<LoadingOverlay isOpen={true} message="Loading..." />)

    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('updates message dynamically', () => {
    const { rerender } = render(
      <LoadingOverlay isOpen={true} message="Starting process..." />
    )

    expect(screen.getByText('Starting process...')).toBeInTheDocument()

    rerender(<LoadingOverlay isOpen={true} message="Almost finished..." />)

    expect(screen.queryByText('Starting process...')).not.toBeInTheDocument()
    expect(screen.getByText('Almost finished...')).toBeInTheDocument()
  })

  it('updates progress value dynamically', () => {
    const { rerender } = render(
      <LoadingOverlay isOpen={true} message="Processing..." progress={25} />
    )

    expect(screen.getByText('25%')).toBeInTheDocument()

    rerender(<LoadingOverlay isOpen={true} message="Processing..." progress={75} />)

    expect(screen.queryByText('25%')).not.toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()
  })
})
