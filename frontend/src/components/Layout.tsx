import { ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  FolderOpen,
  Zap,
  User,
  LogOut,
  FileText,
  Menu,
  X,
  ChevronLeft,
  Pin,
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { apiClient } from '@/services/apiClient'
import { cn } from '@/utils/cn'
import { useSidebarState } from '@/hooks/useSidebarState'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, color: 'emerald' },
  { name: 'Artifacts', href: '/artifacts', icon: FolderOpen, color: 'purple' },
  { name: 'Generations', href: '/generations', icon: Zap, color: 'blue' },
  { name: 'Profile', href: '/profile', icon: User, color: 'indigo' },
]

/**
 * Main layout component with collapsible sidebar navigation
 *
 * Features:
 * - Responsive sidebar (collapsible on desktop, slide-in on mobile)
 * - Persistent sidebar state via localStorage (ft-021)
 * - Accessible tooltips when sidebar is collapsed
 * - User profile section with logout functionality
 *
 * @param props - Component props
 * @param props.children - Page content to render in main area
 *
 * @example
 * ```tsx
 * <Layout>
 *   <DashboardPage />
 * </Layout>
 * ```
 */
export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const { user, clearAuth } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Collapsible sidebar state with localStorage persistence (ft-021)
  const [isCollapsed, toggleSidebar] = useSidebarState()

  // Determine background color based on current route
  const getBackgroundColor = () => {
    const path = location.pathname
    if (path === '/' || path === '/dashboard') return 'bg-emerald-50/30'
    if (path.startsWith('/artifacts')) return 'bg-purple-50/30'
    if (path.startsWith('/generations')) return 'bg-blue-50/30'
    if (path === '/profile') return 'bg-orange-50/30'
    return 'bg-gray-50' // fallback
  }

  // Temporary hover state (does not persist)
  const [isHovered, setIsHovered] = useState(false)

  // Hover delay timeout reference
  const [hoverTimeout, setHoverTimeout] = useState<NodeJS.Timeout | null>(null)

  // Computed: sidebar should show as expanded if NOT collapsed OR if hovered
  const isExpanded = !isCollapsed || isHovered

  // Handle mouse enter with 0.5-second delay
  const handleMouseEnter = () => {
    if (isCollapsed) {
      const timeout = setTimeout(() => {
        setIsHovered(true)
      }, 500) // 0.5 second delay
      setHoverTimeout(timeout)
    }
  }

  // Handle mouse leave: clear timeout and collapse if hovered
  const handleMouseLeave = () => {
    if (hoverTimeout) {
      clearTimeout(hoverTimeout)
      setHoverTimeout(null)
    }
    if (isCollapsed) {
      setIsHovered(false)
    }
  }

  // Handle pin click: make expansion permanent
  const handlePin = () => {
    if (hoverTimeout) {
      clearTimeout(hoverTimeout)
      setHoverTimeout(null)
    }
    toggleSidebar() // This will set isCollapsed to false
    setIsHovered(false) // Clear hover state
  }

  // Handle collapse click
  const handleCollapse = () => {
    if (hoverTimeout) {
      clearTimeout(hoverTimeout)
      setHoverTimeout(null)
    }
    toggleSidebar() // This will set isCollapsed to true
    setIsHovered(false)
  }

  const handleLogout = async () => {
    try {
      await apiClient.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      clearAuth()
    }
  }

  return (
    <div className={cn("min-h-screen", getBackgroundColor())}>
      {/* Mobile menu overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
        </div>
      )}

      {/* Desktop sidebar */}
      <div
        className={cn(
          "hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-50 lg:block lg:bg-white lg:shadow-lg transition-all duration-300 ease-in-out",
          isExpanded ? "lg:w-56" : "lg:w-16"
        )}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <div className="flex h-full flex-col">
          {/* Logo with toggle/pin button */}
          <div className={cn(
            "flex h-16 items-center justify-between",
            isExpanded ? "px-6" : "px-2"
          )}>
            <div className={cn(
              "flex items-center",
              isExpanded ? "space-x-2" : "justify-center w-full"
            )}>
              <FileText className="h-8 w-8 text-blue-600" />
              {isExpanded && <span className="text-xl font-bold text-gray-900">CV Tailor</span>}
            </div>

            {/* Show collapse button when permanently expanded */}
            {!isCollapsed && (
              <button
                onClick={handleCollapse}
                className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors duration-200"
                aria-label="Collapse sidebar"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
            )}

            {/* Show pin button when temporarily expanded via hover */}
            {isCollapsed && isHovered && (
              <button
                onClick={handlePin}
                className="p-2 text-gray-600 hover:bg-blue-100 hover:text-blue-600 rounded-lg transition-colors duration-200"
                aria-label="Pin sidebar expanded"
              >
                <Pin className="h-5 w-5" />
              </button>
            )}
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1 px-4 py-4">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                    isExpanded ? '' : 'justify-center',
                    isActive
                      ? item.color === 'emerald' ? 'bg-emerald-50 text-emerald-600 border-r-2 border-emerald-600'
                      : item.color === 'purple' ? 'bg-purple-50 text-purple-600 border-r-2 border-purple-600'
                      : item.color === 'blue' ? 'bg-blue-50 text-blue-600 border-r-2 border-blue-600'
                      : item.color === 'indigo' ? 'bg-indigo-50 text-indigo-600 border-r-2 border-indigo-600'
                      : 'bg-blue-50 text-blue-600 border-r-2 border-blue-600'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  )}
                >
                  <item.icon
                    className={cn(
                      'h-5 w-5 flex-shrink-0',
                      isExpanded && 'mr-3',
                      isActive
                        ? item.color === 'emerald' ? 'text-emerald-600'
                        : item.color === 'purple' ? 'text-purple-600'
                        : item.color === 'blue' ? 'text-blue-600'
                        : item.color === 'indigo' ? 'text-indigo-600'
                        : 'text-blue-600'
                        : 'text-gray-400 group-hover:text-gray-500'
                    )}
                  />
                  {isExpanded && <span>{item.name}</span>}
                </Link>
              )
            })}
          </nav>

          {/* User section - only show when expanded */}
          {isExpanded && (
            <div className="border-t border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-sm">
                  <span className="text-sm font-semibold text-white">
                    {user?.firstName?.[0]}{user?.lastName?.[0]}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-900 truncate">
                    {user?.firstName} {user?.lastName}
                  </p>
                  <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all duration-200"
                  title="Logout"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mobile sidebar */}
      <div className={cn(
        "fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 shadow-xl transform transition-transform duration-300 ease-in-out lg:hidden",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex h-full flex-col">
          {/* Logo with close button */}
          <div className="flex h-16 items-center justify-between px-6 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <FileText className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-semibold text-gray-900">CV Tailor</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-all duration-200"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6">
            <div className="space-y-1">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={cn(
                      'group flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200',
                      isActive
                        ? item.color === 'emerald' ? 'bg-emerald-50 text-emerald-700 shadow-sm'
                        : item.color === 'purple' ? 'bg-purple-50 text-purple-700 shadow-sm'
                        : item.color === 'blue' ? 'bg-blue-50 text-blue-700 shadow-sm'
                        : item.color === 'indigo' ? 'bg-indigo-50 text-indigo-700 shadow-sm'
                        : 'bg-blue-50 text-blue-700 shadow-sm'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    )}
                  >
                    <item.icon
                      className={cn(
                        'h-5 w-5 flex-shrink-0',
                        isActive
                          ? item.color === 'emerald' ? 'text-emerald-600'
                          : item.color === 'purple' ? 'text-purple-600'
                          : item.color === 'blue' ? 'text-blue-600'
                          : item.color === 'indigo' ? 'text-indigo-600'
                          : 'text-blue-600'
                          : 'text-gray-400 group-hover:text-gray-600'
                      )}
                    />
                    {item.name}
                  </Link>
                )
              })}
            </div>
          </nav>

          {/* User section */}
          <div className="border-t border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-sm">
                <span className="text-sm font-semibold text-white">
                  {user?.firstName?.[0]}{user?.lastName?.[0]}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate">
                  {user?.firstName} {user?.lastName}
                </p>
                <p className="text-xs text-gray-500 truncate">{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all duration-200"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className={cn(
        "transition-all duration-300 ease-in-out",
        isExpanded ? "lg:pl-56" : "lg:pl-16"
      )}>
        {/* Mobile header with hamburger menu */}
        <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-white/95 backdrop-blur-sm px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:hidden">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all duration-200"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="flex items-center gap-3">
            <div className="w-6 h-6 bg-blue-600 rounded-md flex items-center justify-center">
              <FileText className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-semibold text-gray-900">CV Tailor</span>
          </div>
        </div>

        <main>
          {children}
        </main>
      </div>
    </div>
  )
}