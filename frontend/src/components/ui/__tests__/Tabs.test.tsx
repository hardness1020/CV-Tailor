import { render, screen, fireEvent } from '@/test/utils'
import { vi, describe, it, expect } from 'vitest'
import { Tabs } from '../Tabs'

describe('Tabs', () => {
  it('renders all tab triggers correctly', () => {
    render(
      <Tabs.Root defaultValue="tab1">
        <Tabs.List>
          <Tabs.Trigger value="tab1">Tab 1</Tabs.Trigger>
          <Tabs.Trigger value="tab2">Tab 2</Tabs.Trigger>
          <Tabs.Trigger value="tab3">Tab 3</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="tab1">Content 1</Tabs.Content>
        <Tabs.Content value="tab2">Content 2</Tabs.Content>
        <Tabs.Content value="tab3">Content 3</Tabs.Content>
      </Tabs.Root>
    )

    expect(screen.getByText('Tab 1')).toBeInTheDocument()
    expect(screen.getByText('Tab 2')).toBeInTheDocument()
    expect(screen.getByText('Tab 3')).toBeInTheDocument()
  })

  it('shows default tab content on initial render', () => {
    render(
      <Tabs.Root defaultValue="overview">
        <Tabs.List>
          <Tabs.Trigger value="overview">Overview</Tabs.Trigger>
          <Tabs.Trigger value="evidence">Evidence</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="overview">
          <div>Overview content is visible</div>
        </Tabs.Content>
        <Tabs.Content value="evidence">
          <div>Evidence content is hidden</div>
        </Tabs.Content>
      </Tabs.Root>
    )

    expect(screen.getByText('Overview content is visible')).toBeInTheDocument()
    expect(screen.queryByText('Evidence content is hidden')).not.toBeInTheDocument()
  })

  it('switches tab content when clicking different tab trigger', () => {
    render(
      <Tabs.Root defaultValue="tab1">
        <Tabs.List>
          <Tabs.Trigger value="tab1">Tab 1</Tabs.Trigger>
          <Tabs.Trigger value="tab2">Tab 2</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="tab1">First tab content</Tabs.Content>
        <Tabs.Content value="tab2">Second tab content</Tabs.Content>
      </Tabs.Root>
    )

    // Initially shows tab1 content
    expect(screen.getByText('First tab content')).toBeInTheDocument()
    expect(screen.queryByText('Second tab content')).not.toBeInTheDocument()

    // Click tab2
    fireEvent.click(screen.getByText('Tab 2'))

    // Now shows tab2 content
    expect(screen.queryByText('First tab content')).not.toBeInTheDocument()
    expect(screen.getByText('Second tab content')).toBeInTheDocument()
  })

  it('applies active state styling to selected tab', () => {
    render(
      <Tabs.Root defaultValue="active">
        <Tabs.List>
          <Tabs.Trigger value="active">Active Tab</Tabs.Trigger>
          <Tabs.Trigger value="inactive">Inactive Tab</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="active">Active content</Tabs.Content>
        <Tabs.Content value="inactive">Inactive content</Tabs.Content>
      </Tabs.Root>
    )

    const activeTab = screen.getByText('Active Tab')
    const inactiveTab = screen.getByText('Inactive Tab')

    // Active tab should have data-state="active"
    expect(activeTab).toHaveAttribute('data-state', 'active')
    expect(inactiveTab).toHaveAttribute('data-state', 'inactive')
  })

  it('displays count badge when count prop is provided', () => {
    render(
      <Tabs.Root defaultValue="tab1">
        <Tabs.List>
          <Tabs.Trigger value="tab1" count={5}>
            Tab with count
          </Tabs.Trigger>
          <Tabs.Trigger value="tab2">Tab without count</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="tab1">Content 1</Tabs.Content>
        <Tabs.Content value="tab2">Content 2</Tabs.Content>
      </Tabs.Root>
    )

    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('5')).toHaveClass('bg-purple-100', 'text-purple-700', 'rounded-full')
  })

  it('supports keyboard navigation with arrow keys', () => {
    render(
      <Tabs.Root defaultValue="tab1">
        <Tabs.List>
          <Tabs.Trigger value="tab1">Tab 1</Tabs.Trigger>
          <Tabs.Trigger value="tab2">Tab 2</Tabs.Trigger>
          <Tabs.Trigger value="tab3">Tab 3</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="tab1">Content 1</Tabs.Content>
        <Tabs.Content value="tab2">Content 2</Tabs.Content>
        <Tabs.Content value="tab3">Content 3</Tabs.Content>
      </Tabs.Root>
    )

    const tab1 = screen.getByText('Tab 1')

    // Focus first tab
    tab1.focus()
    expect(document.activeElement).toBe(tab1)

    // Arrow right should move focus to next tab
    fireEvent.keyDown(tab1, { key: 'ArrowRight' })
    expect(document.activeElement).toBe(screen.getByText('Tab 2'))
  })

  it('applies custom className to Tabs.List', () => {
    const { container } = render(
      <Tabs.Root defaultValue="tab1">
        <Tabs.List className="custom-tabs-list">
          <Tabs.Trigger value="tab1">Tab 1</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="tab1">Content</Tabs.Content>
      </Tabs.Root>
    )

    const tabsList = container.querySelector('.custom-tabs-list')
    expect(tabsList).toBeInTheDocument()
  })

  it('maintains tab selection state after re-render', () => {
    const { rerender } = render(
      <Tabs.Root defaultValue="tab1">
        <Tabs.List>
          <Tabs.Trigger value="tab1">Tab 1</Tabs.Trigger>
          <Tabs.Trigger value="tab2">Tab 2</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="tab1">Content 1</Tabs.Content>
        <Tabs.Content value="tab2">Content 2</Tabs.Content>
      </Tabs.Root>
    )

    // Switch to tab2
    fireEvent.click(screen.getByText('Tab 2'))
    expect(screen.getByText('Content 2')).toBeInTheDocument()

    // Re-render
    rerender(
      <Tabs.Root defaultValue="tab1">
        <Tabs.List>
          <Tabs.Trigger value="tab1">Tab 1</Tabs.Trigger>
          <Tabs.Trigger value="tab2">Tab 2</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="tab1">Content 1</Tabs.Content>
        <Tabs.Content value="tab2">Content 2 - Updated</Tabs.Content>
      </Tabs.Root>
    )

    // Should still show tab2 content
    expect(screen.getByText('Content 2 - Updated')).toBeInTheDocument()
  })
})
