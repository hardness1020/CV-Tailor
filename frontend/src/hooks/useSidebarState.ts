import { useState, useEffect } from 'react'

/**
 * Custom hook for managing collapsible sidebar state with localStorage persistence
 *
 * This hook manages the collapsed/expanded state of the sidebar and automatically
 * persists the state to localStorage for persistence across page reloads and sessions.
 *
 * @param storageKey - Key used for localStorage persistence (default: 'sidebar-collapsed')
 * @returns Tuple of [isCollapsed, toggleSidebar]
 *
 * @example
 * ```tsx
 * function Sidebar() {
 *   const [isCollapsed, toggleSidebar] = useSidebarState()
 *
 *   return (
 *     <div className={isCollapsed ? 'w-20' : 'w-64'}>
 *       <button onClick={toggleSidebar}>Toggle</button>
 *     </div>
 *   )
 * }
 * ```
 *
 * @remarks
 * - Handles localStorage errors gracefully (e.g., when disabled or quota exceeded)
 * - Returns false (expanded) as default if no saved state exists
 * - State persists across page reloads and browser sessions
 *
 * @see {@link https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage | localStorage API}
 */
export function useSidebarState(
  storageKey: string = 'sidebar-collapsed'
): [boolean, () => void] {
  // Initialize state from localStorage with error handling
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem(storageKey)
      return saved ? JSON.parse(saved) : false
    } catch (error) {
      // Gracefully handle localStorage errors (disabled, quota exceeded, etc.)
      console.warn('Failed to read sidebar state from localStorage:', error)
      return false // Default to expanded state
    }
  })

  // Persist state changes to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(isCollapsed))
    } catch (error) {
      // Gracefully handle localStorage errors (quota exceeded, disabled, etc.)
      console.error('Failed to save sidebar state to localStorage:', error)
    }
  }, [isCollapsed, storageKey])

  // Toggle function for easy state flipping
  const toggleSidebar = () => {
    setIsCollapsed((prev) => !prev)
  }

  return [isCollapsed, toggleSidebar]
}
