import { ReactNode } from 'react'
import { LucideIcon } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { PageTheme } from '@/utils/pageThemes'

interface SelectableListItemProps {
  // Selection state
  isSelected: boolean
  onToggleSelect: () => void

  // Click handler for navigation
  onClick: () => void

  // Icon configuration
  icon: LucideIcon
  theme: PageTheme

  // Content slots
  header: ReactNode
  content: ReactNode
  footer?: ReactNode

  // Optional action buttons (shown on hover)
  actions?: ReactNode

  // Additional styling
  className?: string
}

/**
 * Shared selectable list item component for list view
 * Handles selection, hover states, and common layout patterns
 */
export function SelectableListItem({
  isSelected,
  onToggleSelect,
  onClick,
  icon: Icon,
  theme,
  header,
  content,
  footer,
  actions,
  className,
}: SelectableListItemProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'group relative bg-white rounded-xl border transition-all duration-200 cursor-pointer overflow-hidden',
        'hover:shadow-md hover:border-gray-300',
        isSelected
          ? `border-${theme.colors.selectionBorder} shadow-md ring-4 ring-${theme.colors.selectionRing}`
          : 'border-gray-200 shadow-sm',
        className
      )}
      style={
        isSelected
          ? {
              borderColor: `rgb(${theme.colors.selectionBorder === 'blue-500' ? '59 130 246' : '168 85 247'})`,
              boxShadow: `0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1), 0 0 0 4px ${
                theme.colors.selectionBorder === 'blue-500' ? 'rgba(59 130 246 / 0.1)' : 'rgba(168 85 247 / 0.1)'
              }`,
            }
          : undefined
      }
    >
      {/* Selection overlay */}
      {isSelected && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundColor:
              theme.colors.selectionBorder === 'blue-500' ? 'rgba(239 246 255 / 0.3)' : 'rgba(250 245 255 / 0.3)',
          }}
        />
      )}

      <div className="p-6">
        <div className="flex items-start gap-4">
          {/* Selection checkbox */}
          <div className="flex items-center pt-1">
            <div
              onClick={(e) => {
                e.stopPropagation()
                onToggleSelect()
              }}
              className={cn(
                'w-5 h-5 rounded border-2 flex items-center justify-center transition-all cursor-pointer'
              )}
              style={
                isSelected
                  ? {
                      backgroundColor:
                        theme.colors.selectionBorder === 'blue-500' ? 'rgb(37 99 235)' : 'rgb(147 51 234)',
                      borderColor: theme.colors.selectionBorder === 'blue-500' ? 'rgb(37 99 235)' : 'rgb(147 51 234)',
                      color: 'white',
                    }
                  : {
                      borderColor: 'rgb(209 213 219)',
                    }
              }
            >
              {isSelected && (
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
          </div>

          {/* Icon */}
          <div
            className={cn('flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center transition-colors')}
            style={
              isSelected
                ? {
                    backgroundColor:
                      theme.colors.selectionBorder === 'blue-500' ? 'rgb(37 99 235)' : 'rgb(147 51 234)',
                    color: 'white',
                  }
                : {
                    backgroundColor:
                      theme.colors.selectionBorder === 'blue-500' ? 'rgb(219 234 254)' : 'rgb(243 232 255)',
                    color: theme.colors.selectionBorder === 'blue-500' ? 'rgb(37 99 235)' : 'rgb(147 51 234)',
                  }
            }
          >
            <Icon className="h-6 w-6" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1 min-w-0">{header}</div>

              {/* Actions */}
              {actions && <div className="flex items-center gap-1 ml-4">{actions}</div>}
            </div>

            {/* Main content */}
            {content}

            {/* Optional footer */}
            {footer && <div className="mt-4">{footer}</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
