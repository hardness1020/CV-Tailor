import { ReactNode, useState } from 'react'
import { LucideIcon } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { PageTheme } from '@/utils/pageThemes'

interface SelectableCardProps {
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
 * Shared selectable card component for grid view
 * Handles selection, hover states, and common layout patterns
 */
export function SelectableCard({
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
}: SelectableCardProps) {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <div
      onClick={onClick}
      className={cn(
        'group relative overflow-hidden border rounded-2xl p-6 transition-all duration-200 cursor-pointer bg-white',
        'hover:shadow-lg hover:-translate-y-0.5',
        isSelected
          ? `border-${theme.colors.selectionBorder} shadow-lg ring-4 ring-${theme.colors.selectionRing}`
          : 'border-gray-200 shadow-sm hover:border-gray-300',
        className
      )}
      style={
        isSelected
          ? {
              borderColor: `rgb(${theme.colors.selectionBorder === 'blue-500' ? '59 130 246' : '168 85 247'})`,
              boxShadow: `0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1), 0 0 0 4px ${
                theme.colors.selectionBorder === 'blue-500' ? 'rgba(59 130 246 / 0.1)' : 'rgba(168 85 247 / 0.1)'
              }`,
            }
          : undefined
      }
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Selection overlay */}
      {isSelected && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundColor:
              theme.colors.selectionBorder === 'blue-500' ? 'rgba(239 246 255 / 0.5)' : 'rgba(250 245 255 / 0.5)',
          }}
        />
      )}

      <div className="relative">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-4 flex-1">
            <div
              className={cn('w-12 h-12 rounded-lg flex items-center justify-center transition-colors')}
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
            <div className="flex-1 min-w-0">{header}</div>
          </div>

          {/* Selection checkbox and actions */}
          <div className="flex items-center gap-2 ml-4">
            {/* Action buttons */}
            {actions && <div className="flex items-center gap-1 mr-2">{actions}</div>}

            {/* Selection checkbox */}
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
        </div>

        {/* Main content */}
        {content}

        {/* Optional footer */}
        {footer && <div className="mt-4">{footer}</div>}
      </div>

      {/* Hover effect overlay */}
      <div
        className={cn('absolute inset-0 rounded-2xl transition-opacity duration-300 pointer-events-none')}
        style={{
          background:
            theme.colors.selectionBorder === 'blue-500'
              ? 'linear-gradient(to bottom right, rgba(59, 130, 246, 0.05), rgba(99, 102, 241, 0.05))'
              : 'linear-gradient(to bottom right, rgba(168, 85, 247, 0.05), rgba(236, 72, 153, 0.05))',
          opacity: isHovered ? 1 : 0,
        }}
      />
    </div>
  )
}
