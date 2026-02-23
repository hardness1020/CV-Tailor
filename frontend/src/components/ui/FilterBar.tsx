import { Search, Grid, List } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { PageTheme } from '@/utils/pageThemes'

interface StatusFilterOption {
  value: string
  label: string
}

interface FilterBarProps {
  // Search
  searchQuery: string
  onSearchChange: (query: string) => void
  searchPlaceholder?: string

  // View mode
  viewMode: 'grid' | 'list'
  onViewModeChange: (mode: 'grid' | 'list') => void

  // Optional status filter
  statusFilter?: {
    value: string
    options: StatusFilterOption[]
    onChange: (value: string) => void
  }

  // Theme
  theme: PageTheme
}

// Map theme colors to actual Tailwind color values for focus states
const getColorValue = (colorClass: string): string => {
  // Extract color from classes like "blue-600" or "purple-500"
  const colorMap: Record<string, string> = {
    'blue-500': 'rgb(59 130 246)',
    'blue-600': 'rgb(37 99 235)',
    'blue-100': 'rgba(219 234 254 / 0.5)',
    'purple-500': 'rgb(168 85 247)',
    'purple-600': 'rgb(147 51 234)',
    'purple-100': 'rgba(243 232 255 / 0.5)',
  }
  return colorMap[colorClass] || 'rgb(59 130 246)'
}

/**
 * Shared filter bar component for list/grid pages
 * Includes search input, optional status filter, and view mode toggle
 */
export function FilterBar({
  searchQuery,
  onSearchChange,
  searchPlaceholder = 'Search...',
  viewMode,
  onViewModeChange,
  statusFilter,
  theme,
}: FilterBarProps) {
  const focusBorderColor = getColorValue(theme.colors.focusBorder)
  const focusRingColor = getColorValue(theme.colors.focusRing)
  const primaryColor = getColorValue(theme.colors.primary)

  return (
    <div className="p-4 sm:p-4">
      <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        {/* Search */}
        <div className="flex-1 max-w-lg">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder={searchPlaceholder}
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="block w-full pl-11 pr-4 py-3 border-2 border-gray-200 rounded-xl text-sm font-medium placeholder-gray-400 transition-all duration-200"
              onFocus={(e) => {
                e.target.style.borderColor = focusBorderColor
                e.target.style.boxShadow = `0 0 0 4px ${focusRingColor}`
              }}
              onBlur={(e) => {
                e.target.style.borderColor = ''
                e.target.style.boxShadow = ''
              }}
            />
          </div>
        </div>

        <div className="flex items-end gap-3">
          {/* Status Filter (optional) */}
          {statusFilter && (
            <div>
              <select
                value={statusFilter.value}
                onChange={(e) => statusFilter.onChange(e.target.value)}
                className="px-4 py-3 border-2 border-gray-200 rounded-xl text-sm font-semibold bg-white min-w-[120px] transition-all duration-200"
                onFocus={(e) => {
                  e.target.style.borderColor = focusBorderColor
                  e.target.style.boxShadow = `0 0 0 4px ${focusRingColor}`
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = ''
                  e.target.style.boxShadow = ''
                }}
              >
                {statusFilter.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* View Mode Toggle */}
          <div>
            <div className="inline-flex rounded-xl border-2 border-gray-200 bg-gray-50 p-1">
              <button
                onClick={() => onViewModeChange('list')}
                className={cn(
                  'inline-flex items-center justify-center px-3 py-2 text-sm font-bold rounded-lg transition-all duration-200',
                  viewMode === 'list'
                    ? 'bg-white shadow-md'
                    : 'text-gray-600 hover:text-gray-900'
                )}
                style={
                  viewMode === 'list'
                    ? {
                        color: primaryColor,
                      }
                    : undefined
                }
              >
                <List className="h-4 w-4" />
                <span className="ml-1.5 hidden sm:inline">List</span>
              </button>
              <button
                onClick={() => onViewModeChange('grid')}
                className={cn(
                  'inline-flex items-center justify-center px-3 py-2 text-sm font-bold rounded-lg transition-all duration-200',
                  viewMode === 'grid'
                    ? 'bg-white shadow-md'
                    : 'text-gray-600 hover:text-gray-900'
                )}
                style={
                  viewMode === 'grid'
                    ? {
                        color: primaryColor,
                      }
                    : undefined
                }
              >
                <Grid className="h-4 w-4" />
                <span className="ml-1.5 hidden sm:inline">Grid</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
