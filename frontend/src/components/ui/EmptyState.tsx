import { LucideIcon, Plus, ArrowRight } from 'lucide-react'
import { Button } from './Button'
import type { PageTheme } from '@/utils/pageThemes'
import { cn } from '@/utils/cn'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
  theme: PageTheme
  showFiltered?: boolean
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  theme,
  showFiltered = false
}: EmptyStateProps) {
  return (
    <div className="text-center py-12 sm:py-16">
      <h3 className="text-xl font-bold text-gray-900 mb-3">
        {title}
      </h3>
      <p className="text-gray-600 mb-6 max-w-lg mx-auto leading-relaxed">
        {description}
      </p>
      {!showFiltered && actionLabel && onAction && (
        <Button
          onClick={onAction}
          className={cn(
            'group relative overflow-hidden text-white font-semibold px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105',
            `bg-gradient-to-r from-${theme.colors.primary} to-${theme.colors.secondary}`,
            `hover:from-${theme.colors.primaryDark} hover:to-${theme.colors.secondaryDark}`
          )}
        >
          <div className="flex items-center gap-3">
            <Plus className="h-5 w-5" />
            <span>{actionLabel}</span>
            <ArrowRight className="h-5 w-5 transform group-hover:translate-x-1 transition-transform duration-200" />
          </div>
        </Button>
      )}
    </div>
  )
}
