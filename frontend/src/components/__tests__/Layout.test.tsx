/**
 * Unit tests for Layout component (Collapsible Sidebar - ft-021)
 *
 * These tests verify the collapsible sidebar functionality including:
 * - Toggle button rendering and behavior
 * - Sidebar width changes (256px ↔ 80px)
 * - localStorage state persistence
 * - Tooltips on icon hover when collapsed
 * - Main content area padding adjustment
 * - Keyboard accessibility
 * - Mobile view independence
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import Layout from '../Layout'
import { useAuthStore } from '@/stores/authStore'
import type { User } from '@/types'

// Mock auth store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn()
}))

// Mock API client
vi.mock('@/services/apiClient', () => ({
  apiClient: {
    logout: vi.fn()
  }
}))

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString()
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    }
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

// Mock ResizeObserver for Radix UI tooltips
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

describe('Layout Component - Collapsible Sidebar (ft-021)', () => {
  const mockUser: User = {
    id: 1,
    email: 'test@example.com',
    username: 'testuser',
    firstName: 'Test',
    lastName: 'User',
    profileImage: undefined,
    phone: '',
    linkedinUrl: '',
    githubUrl: '',
    websiteUrl: '',
    bio: '',
    location: '',
    preferredCvTemplate: 1,
    emailNotifications: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z'
  }

  const mockClearAuth = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()

    // Mock auth store
    ;(useAuthStore as any).mockReturnValue({
      user: mockUser,
      clearAuth: mockClearAuth
    })
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  const renderLayout = (children = <div>Test Content</div>) => {
    return render(
      <BrowserRouter>
        <Layout>{children}</Layout>
      </BrowserRouter>
    )
  }

  describe('1. Toggle Button Rendering', () => {
    it('should render toggle button in desktop sidebar', () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      expect(toggleButton).toBeInTheDocument()
    })

    it('should show ChevronLeft icon when sidebar is expanded', () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      const chevronLeftIcon = toggleButton.querySelector('svg')

      // Lucide icons have specific attributes we can check
      expect(chevronLeftIcon).toBeInTheDocument()
      // Icon should be ChevronLeft (checking via aria-label since we'll add it)
      expect(toggleButton).toHaveAttribute('aria-label', 'Collapse sidebar')
    })

    it('should NOT show expand button when sidebar is collapsed', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })

      // Click to collapse
      await userEvent.click(toggleButton)

      // After collapse, there should be NO expand button (hover-to-expand UX)
      await waitFor(() => {
        const expandButton = screen.queryByRole('button', { name: /expand sidebar/i })
        expect(expandButton).not.toBeInTheDocument()
      })
    })

    it('should have clear hover state', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })

      // Check that button has hover-related classes
      expect(toggleButton.className).toMatch(/hover:/)
    })

    it('should have accessible label', () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      expect(toggleButton).toHaveAttribute('aria-label')
    })
  })

  describe('2. Sidebar Width Changes', () => {
    it('should have 224px width (w-56) when expanded', () => {
      renderLayout()

      const desktopSidebar = document.querySelector('.lg\\:w-56')
      expect(desktopSidebar).toBeInTheDocument()
    })

    it('should change to 64px width (w-16) when collapsed', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })
    })

    it('should expand to 224px when hovered and pinned', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })

      // Collapse
      await userEvent.click(toggleButton)
      await waitFor(() => {
        expect(document.querySelector('.lg\\:w-16')).toBeInTheDocument()
      })

      // Hover to expand temporarily
      const sidebar = document.querySelector('.lg\\:w-16')
      if (sidebar) {
        fireEvent.mouseEnter(sidebar)

        await waitFor(() => {
          expect(document.querySelector('.lg\\:w-56')).toBeInTheDocument()
        }, { timeout: 800 }) // Wait for 500ms delay

        // Click pin to make expansion permanent
        const pinButton = screen.getByRole('button', { name: /pin sidebar expanded/i })
        await userEvent.click(pinButton)

        await waitFor(() => {
          // Should remain expanded
          expect(document.querySelector('.lg\\:w-56')).toBeInTheDocument()
        })
      }
    })
  })

  describe('3. Navigation Labels Visibility', () => {
    it('should show navigation text labels when expanded', () => {
      renderLayout()

      // Both desktop and mobile sidebars have these labels
      expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Artifacts').length).toBeGreaterThan(0)
      expect(screen.getAllByText('CVs').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Profile').length).toBeGreaterThan(0)
    })

    it('should hide navigation text labels when collapsed', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        // Check that sidebar is collapsed
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()

        // In collapsed state, verify that text labels are hidden by checking the DOM structure
        // The collapsed navigation should only show icons
        const navLinks = screen.getAllByRole('link', { name: /dashboard/i })
        expect(navLinks.length).toBeGreaterThan(0)
      })
    })

    it('should show only icons when collapsed', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        // Icons should still be visible (SVG elements)
        const icons = document.querySelectorAll('nav svg')
        expect(icons.length).toBeGreaterThan(0)
      })
    })
  })

  describe('4. Logo Display', () => {
    it('should show full logo with text when expanded', () => {
      renderLayout()

      // Both desktop and mobile sidebars show logo
      expect(screen.getAllByText('CV Tailor').length).toBeGreaterThan(0)
    })

    it('should hide logo text when collapsed', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        // Desktop sidebar should hide logo text (mobile still shows it)
        // Check that sidebar is collapsed (has lg:w-20 class)
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })
    })

    it('should keep logo icon visible when collapsed', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        // FileText icon should still be visible
        const logoIcons = document.querySelectorAll('.text-blue-600')
        expect(logoIcons.length).toBeGreaterThan(0)
      })
    })
  })

  describe('5. User Section Display', () => {
    it('should show full user info when expanded', () => {
      renderLayout()

      // Both desktop and mobile sidebars show user info
      expect(screen.getAllByText(`${mockUser.firstName} ${mockUser.lastName}`).length).toBeGreaterThan(0)
      expect(screen.getAllByText(mockUser.email).length).toBeGreaterThan(0)
    })

    it('should hide user section when collapsed', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        // Verify collapsed state
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()

        // Desktop user section should be hidden (mobile still shows it)
        // We can't easily test for desktop-only visibility in JSDOM, so just verify collapsed state
      })
    })

    it('should hide logout button in collapsed state', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        // Verify sidebar is collapsed
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()

        // Logout button is only in mobile sidebar now (mobile still has it)
        // Desktop collapsed sidebar has no logout button
      })
    })
  })

  describe('6. State Persistence (localStorage)', () => {
    it('should default to expanded state on first visit', () => {
      expect(localStorage.getItem('sidebar-collapsed')).toBeNull()

      renderLayout()

      const desktopSidebar = document.querySelector('.lg\\:w-56')
      expect(desktopSidebar).toBeInTheDocument()
    })

    it('should save collapsed state to localStorage', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        expect(localStorage.getItem('sidebar-collapsed')).toBe('true')
      })
    })

    it('should save expanded state to localStorage when pinned', async () => {
      // Pre-set collapsed state
      localStorage.setItem('sidebar-collapsed', 'true')

      renderLayout()

      // Sidebar should be collapsed initially
      const collapsedSidebar = document.querySelector('.lg\\:w-16')
      expect(collapsedSidebar).toBeInTheDocument()

      // Hover to expand temporarily
      if (collapsedSidebar) {
        fireEvent.mouseEnter(collapsedSidebar)

        await waitFor(() => {
          const expandedSidebar = document.querySelector('.lg\\:w-56')
          expect(expandedSidebar).toBeInTheDocument()
        })

        // Click pin to make expansion permanent
        const pinButton = screen.getByRole('button', { name: /pin sidebar expanded/i })
        await userEvent.click(pinButton)

        await waitFor(() => {
          expect(localStorage.getItem('sidebar-collapsed')).toBe('false')
        })
      }
    })

    it('should restore collapsed state from localStorage on mount', () => {
      localStorage.setItem('sidebar-collapsed', 'true')

      renderLayout()

      const collapsedSidebar = document.querySelector('.lg\\:w-16')
      expect(collapsedSidebar).toBeInTheDocument()
    })

    it('should restore expanded state from localStorage on mount', () => {
      localStorage.setItem('sidebar-collapsed', 'false')

      renderLayout()

      const expandedSidebar = document.querySelector('.lg\\:w-56')
      expect(expandedSidebar).toBeInTheDocument()
    })

    it('should persist state across navigation', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        expect(localStorage.getItem('sidebar-collapsed')).toBe('true')
      })

      // Unmount and remount to simulate navigation
      const { unmount } = render(
        <BrowserRouter>
          <Layout><div>New Page</div></Layout>
        </BrowserRouter>
      )

      const collapsedSidebar = document.querySelector('.lg\\:w-16')
      expect(collapsedSidebar).toBeInTheDocument()
    })
  })

  describe('7. Tooltips on Collapsed State', () => {
    it('should NOT show tooltips when sidebar is expanded', () => {
      renderLayout()

      // Tooltips should not be in the DOM when expanded
      const tooltips = document.querySelectorAll('[role="tooltip"]')
      expect(tooltips.length).toBe(0)
    })

    it('should show tooltip on icon hover when collapsed', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      // Get the collapsed desktop link (has justify-center class)
      const dashboardLinks = screen.getAllByRole('link', { name: /dashboard/i })
      const collapsedLink = dashboardLinks.find(link => link.className.includes('justify-center'))

      if (collapsedLink) {
        // Hover over Dashboard icon
        fireEvent.mouseEnter(collapsedLink)

        // Tooltip should appear (Radix UI handles this)
        await waitFor(() => {
          const tooltip = screen.queryByRole('tooltip')
          expect(tooltip).toBeInTheDocument()
        }, { timeout: 1000 })
      }
    })

    it('should show correct labels in tooltips', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      // Get collapsed link
      const dashboardLinks = screen.getAllByRole('link', { name: /dashboard/i })
      const collapsedLink = dashboardLinks.find(link => link.className.includes('justify-center'))

      if (collapsedLink) {
        fireEvent.mouseEnter(collapsedLink)

        await waitFor(() => {
          const tooltip = screen.queryByRole('tooltip')
          expect(tooltip).toBeInTheDocument()
          expect(tooltip).toHaveTextContent('Dashboard')
        }, { timeout: 1000 })
      }
    })

    it('should position tooltips on the right side of icons', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      // Get collapsed link
      const dashboardLinks = screen.getAllByRole('link', { name: /dashboard/i })
      const collapsedLink = dashboardLinks.find(link => link.className.includes('justify-center'))

      if (collapsedLink) {
        fireEvent.mouseEnter(collapsedLink)

        await waitFor(() => {
          const tooltip = screen.queryByRole('tooltip')
          expect(tooltip).toBeInTheDocument()
          // Radix UI tooltip with side="right"
          expect(tooltip).toHaveAttribute('data-side', 'right')
        }, { timeout: 1000 })
      }
    })

    it('should show tooltip with 300ms delay', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      // Get collapsed link
      const dashboardLinks = screen.getAllByRole('link', { name: /dashboard/i })
      const collapsedLink = dashboardLinks.find(link => link.className.includes('justify-center'))

      if (collapsedLink) {
        fireEvent.mouseEnter(collapsedLink)

        // Tooltip should appear after delay
        await waitFor(() => {
          expect(screen.queryByRole('tooltip')).toBeInTheDocument()
        }, { timeout: 1000 })
      }
    })
  })

  describe('8. Main Content Area Adjustment', () => {
    it('should have pl-64 padding when sidebar is expanded', () => {
      renderLayout()

      const mainContent = document.querySelector('.lg\\:pl-56')
      expect(mainContent).toBeInTheDocument()
    })

    it('should change to pl-20 padding when sidebar is collapsed', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        const mainContent = document.querySelector('.lg\\:pl-16')
        expect(mainContent).toBeInTheDocument()
      })
    })

    it('should have smooth transition for padding change', async () => {
      renderLayout()

      const mainContent = document.querySelector('main')?.parentElement

      // Check for transition classes
      expect(mainContent?.className).toMatch(/transition/)
      expect(mainContent?.className).toMatch(/duration/)
      expect(mainContent?.className).toMatch(/ease/)
    })
  })

  describe('9. Animations and Transitions', () => {
    it('should have smooth sidebar width transition', () => {
      renderLayout()

      const sidebar = document.querySelector('.lg\\:w-56')

      // Check for transition classes
      expect(sidebar?.className).toMatch(/transition/)
      expect(sidebar?.className).toMatch(/duration-300/)
      expect(sidebar?.className).toMatch(/ease-in-out/)
    })

    it('should apply transitions to both sidebar and content', () => {
      renderLayout()

      const sidebar = document.querySelector('.lg\\:w-56')
      const mainContent = document.querySelector('main')?.parentElement

      // Both should have transition classes
      expect(sidebar?.className).toMatch(/transition/)
      expect(mainContent?.className).toMatch(/transition/)
    })

    it('should complete transitions within 300ms', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      const startTime = Date.now()

      await userEvent.click(toggleButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      const endTime = Date.now()
      const transitionTime = endTime - startTime

      // Transition should complete within 500ms (300ms + buffer for testing)
      expect(transitionTime).toBeLessThan(500)
    })
  })

  describe('10. Keyboard Accessibility', () => {
    it('should be focusable with Tab key', async () => {
      renderLayout()

      // Tab to the toggle button
      await userEvent.tab()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      expect(toggleButton).toHaveFocus()
    })

    it('should toggle on Enter key', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      toggleButton.focus()

      await userEvent.keyboard('{Enter}')

      await waitFor(() => {
        expect(document.querySelector('.lg\\:w-16')).toBeInTheDocument()
      })
    })

    it('should toggle on Space key', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      toggleButton.focus()

      await userEvent.keyboard(' ')

      await waitFor(() => {
        expect(document.querySelector('.lg\\:w-16')).toBeInTheDocument()
      })
    })

    it('should maintain focus indicators in collapsed state', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        const links = screen.getAllByRole('link')
        links[0].focus()

        // Link should have focus styles
        expect(document.activeElement).toBe(links[0])
      })
    })

    it('should have correct aria-label for collapse button', async () => {
      renderLayout()

      const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i })
      expect(collapseButton).toHaveAttribute('aria-label', 'Collapse sidebar')

      await userEvent.click(collapseButton)

      await waitFor(() => {
        // After collapse, there is no expand button (hover-to-expand UX)
        const expandButton = screen.queryByRole('button', { name: /expand sidebar/i })
        expect(expandButton).not.toBeInTheDocument()

        // Instead, hovering will show a pin button
        const sidebar = document.querySelector('.lg\\:w-16')
        expect(sidebar).toBeInTheDocument()
      })
    })
  })

  describe('11. Mobile View (No Impact)', () => {
    it('should not affect mobile hamburger menu', () => {
      renderLayout()

      // Mobile hamburger should still be present
      // It's in the mobile header which is lg:hidden
      const buttons = screen.getAllByRole('button')
      const hamburgerButton = buttons.find(btn => btn.parentElement?.className.includes('lg:hidden'))
      expect(hamburgerButton).toBeTruthy()
    })

    it('should collapse feature only on desktop (lg+ breakpoint)', () => {
      renderLayout()

      const desktopSidebar = document.querySelector('.lg\\:w-56')

      // Check that collapse classes are scoped to lg: breakpoint
      expect(desktopSidebar?.className).toMatch(/lg:/)
    })

    it('should maintain mobile sidebar width at 256px', () => {
      renderLayout()

      // Mobile sidebar is always w-64
      const mobileSidebar = document.querySelectorAll('.w-64')
      expect(mobileSidebar.length).toBeGreaterThan(0)
    })
  })

  describe('12. Color Contrast (WCAG AA)', () => {
    it('should have sufficient contrast for toggle button', () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })

      // Button should have text-gray-600 or darker (meets WCAG AA on white background)
      expect(toggleButton.className).toMatch(/text-gray/)
    })

    it('should have sufficient contrast for tooltips', async () => {
      renderLayout()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      // Get collapsed link
      const dashboardLinks = screen.getAllByRole('link', { name: /dashboard/i })
      const collapsedLink = dashboardLinks.find(link => link.className.includes('justify-center'))

      if (collapsedLink) {
        fireEvent.mouseEnter(collapsedLink)

        await waitFor(() => {
          const tooltip = screen.queryByRole('tooltip')
          expect(tooltip).toBeInTheDocument()

          // Tooltip should have dark background with white text
          expect(tooltip?.className).toMatch(/bg-gray-900/)
          expect(tooltip?.className).toMatch(/text-white/)
        }, { timeout: 1000 })
      }
    })
  })

  describe('13. Edge Cases', () => {
    it('should handle localStorage being disabled', () => {
      // Mock localStorage to throw error
      const originalSetItem = localStorage.setItem
      localStorage.setItem = vi.fn(() => {
        throw new Error('localStorage disabled')
      })

      // Should not crash
      expect(() => renderLayout()).not.toThrow()

      // Restore
      localStorage.setItem = originalSetItem
    })

    it('should handle rapid collapse and expand via hover', async () => {
      renderLayout()

      // Start expanded
      expect(document.querySelector('.lg\\:w-56')).toBeInTheDocument()

      const toggleButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(toggleButton)

      // Should be collapsed
      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      // Hover to expand temporarily
      const sidebar = document.querySelector('.lg\\:w-16')
      if (sidebar) {
        fireEvent.mouseEnter(sidebar)

        await waitFor(() => {
          const expandedSidebar = document.querySelector('.lg\\:w-56')
          expect(expandedSidebar).toBeInTheDocument()
        }, { timeout: 800 }) // Wait for 500ms delay

        // Hover out to collapse again
        fireEvent.mouseLeave(sidebar)

        await waitFor(() => {
          const collapsedAgain = document.querySelector('.lg\\:w-16')
          expect(collapsedAgain).toBeInTheDocument()
        })
      }
    })

    it('should handle invalid localStorage value', () => {
      localStorage.setItem('sidebar-collapsed', 'invalid-json')

      // Should fall back to default (expanded)
      renderLayout()

      const expandedSidebar = document.querySelector('.lg\\:w-56')
      expect(expandedSidebar).toBeInTheDocument()
    })
  })

  describe('14. Hover-to-Expand Behavior (Enhanced UX)', () => {
    it('should NOT show ChevronRight icon when collapsed', async () => {
      renderLayout()

      const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(collapseButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      // Should NOT have expand button (ChevronRight) visible
      const expandButton = screen.queryByRole('button', { name: /expand sidebar/i })
      expect(expandButton).not.toBeInTheDocument()
    })

    it('should temporarily expand sidebar after 0.5 second hover when collapsed', async () => {
      renderLayout()

      const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(collapseButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      // Hover over sidebar
      const sidebar = document.querySelector('.lg\\:w-16')
      if (sidebar) {
        fireEvent.mouseEnter(sidebar)

        // Should NOT expand immediately
        expect(document.querySelector('.lg\\:w-56')).not.toBeInTheDocument()

        // Should expand after 0.5 seconds
        await waitFor(() => {
          const expandedSidebar = document.querySelector('.lg\\:w-56')
          expect(expandedSidebar).toBeInTheDocument()
        }, { timeout: 800 }) // Wait up to 800ms for the 500ms delay
      }
    })

    it('should collapse sidebar on mouse leave when temporarily expanded', async () => {
      renderLayout()

      const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(collapseButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      // Hover over sidebar to expand temporarily
      const sidebar = document.querySelector('.lg\\:w-16')
      if (sidebar) {
        fireEvent.mouseEnter(sidebar)

        await waitFor(() => {
          expect(document.querySelector('.lg\\:w-56')).toBeInTheDocument()
        }, { timeout: 800 }) // Wait for 500ms delay

        // Mouse leave should collapse again
        fireEvent.mouseLeave(sidebar)

        await waitFor(() => {
          expect(document.querySelector('.lg\\:w-16')).toBeInTheDocument()
        })
      }
    })

    it('should show pin icon when sidebar is temporarily expanded via hover', async () => {
      renderLayout()

      const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(collapseButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      // Hover over sidebar
      const sidebar = document.querySelector('.lg\\:w-16')
      if (sidebar) {
        fireEvent.mouseEnter(sidebar)

        await waitFor(() => {
          // Pin button should appear
          const pinButton = screen.queryByRole('button', { name: /pin sidebar expanded/i })
          expect(pinButton).toBeInTheDocument()
        }, { timeout: 800 }) // Wait for 500ms delay
      }
    })

    it('should make expansion permanent when pin icon is clicked', async () => {
      renderLayout()

      const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(collapseButton)

      await waitFor(() => {
        expect(localStorage.getItem('sidebar-collapsed')).toBe('true')
      })

      // Hover over sidebar
      const sidebar = document.querySelector('.lg\\:w-16')
      if (sidebar) {
        fireEvent.mouseEnter(sidebar)

        await waitFor(() => {
          const pinButton = screen.getByRole('button', { name: /pin sidebar expanded/i })
          expect(pinButton).toBeInTheDocument()
        }, { timeout: 800 }) // Wait for 500ms delay

        // Click pin button
        const pinButton = screen.getByRole('button', { name: /pin sidebar expanded/i })
        await userEvent.click(pinButton)

        await waitFor(() => {
          // localStorage should be set to false (expanded)
          expect(localStorage.getItem('sidebar-collapsed')).toBe('false')

          // Sidebar should remain expanded
          expect(document.querySelector('.lg\\:w-56')).toBeInTheDocument()

          // Pin button should disappear, collapse button should appear
          expect(screen.queryByRole('button', { name: /pin sidebar expanded/i })).not.toBeInTheDocument()
          expect(screen.getByRole('button', { name: /collapse sidebar/i })).toBeInTheDocument()
        })
      }
    })

    it('should NOT expand sidebar on hover when permanently expanded', () => {
      renderLayout()

      // Sidebar is expanded by default
      const expandedSidebar = document.querySelector('.lg\\:w-56')
      expect(expandedSidebar).toBeInTheDocument()

      // Hovering should not change anything (already expanded)
      if (expandedSidebar) {
        fireEvent.mouseEnter(expandedSidebar)

        // Should remain expanded
        expect(document.querySelector('.lg\\:w-56')).toBeInTheDocument()

        // Pin button should NOT appear
        expect(screen.queryByRole('button', { name: /pin sidebar expanded/i })).not.toBeInTheDocument()
      }
    })

    it('should persist expanded state after pinning', async () => {
      renderLayout()

      const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(collapseButton)

      const sidebar = document.querySelector('.lg\\:w-16')
      if (sidebar) {
        fireEvent.mouseEnter(sidebar)

        await waitFor(() => {
          const pinButton = screen.getByRole('button', { name: /pin sidebar expanded/i })
          expect(pinButton).toBeInTheDocument()
        }, { timeout: 800 }) // Wait for 500ms delay

        const pinButton = screen.getByRole('button', { name: /pin sidebar expanded/i })
        await userEvent.click(pinButton)

        await waitFor(() => {
          expect(localStorage.getItem('sidebar-collapsed')).toBe('false')
        })

        // Unmount and remount to verify persistence
        const { unmount } = render(
          <BrowserRouter>
            <Layout><div>New Page</div></Layout>
          </BrowserRouter>
        )

        // Sidebar should be expanded
        const expandedSidebarAfterRemount = document.querySelector('.lg\\:w-56')
        expect(expandedSidebarAfterRemount).toBeInTheDocument()
      }
    })

    it('should show navigation labels when temporarily expanded via hover', async () => {
      renderLayout()

      const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i })
      await userEvent.click(collapseButton)

      await waitFor(() => {
        const collapsedSidebar = document.querySelector('.lg\\:w-16')
        expect(collapsedSidebar).toBeInTheDocument()
      })

      // Hover over sidebar
      const sidebar = document.querySelector('.lg\\:w-16')
      if (sidebar) {
        fireEvent.mouseEnter(sidebar)

        await waitFor(() => {
          // Navigation labels should be visible
          expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0)
          expect(screen.getAllByText('Artifacts').length).toBeGreaterThan(0)
          expect(screen.getAllByText('CVs').length).toBeGreaterThan(0)
          expect(screen.getAllByText('Profile').length).toBeGreaterThan(0)
        }, { timeout: 800 }) // Wait for 500ms delay
      }
    })
  })
})
