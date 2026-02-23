import { ReactNode } from 'react'
import { LucideIcon } from 'lucide-react'
import type { PageTheme } from '@/utils/pageThemes'
import { cn } from '@/utils/cn'

interface PageHeaderProps {
  badgeIcon: LucideIcon
  badgeText: string
  title: string
  titleHighlight: string
  description: string
  theme: PageTheme
  children?: ReactNode
}

export function PageHeader({
  badgeIcon: BadgeIcon,
  badgeText,
  title,
  titleHighlight,
  description,
  theme,
  children
}: PageHeaderProps) {
  return (
    <div className="mb-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className={cn(
            'inline-flex items-center gap-2 px-3 py-1.5 border rounded-full mb-3',
            `bg-gradient-to-r from-${theme.colors.primary}-50 to-${theme.colors.secondary}-50`,
            `border-${theme.colors.badgeBorder}`
          )}>
            <BadgeIcon className={cn('h-4 w-4', `text-${theme.colors.primary}`)} />
            <span className={cn('text-sm font-medium', `text-${theme.colors.badgeText}`)}>
              {badgeText}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 tracking-tight mb-2">
            {title}
            <span className={cn(
              'bg-gradient-to-r bg-clip-text text-transparent',
              `from-${theme.colors.primary} to-${theme.colors.secondary}`
            )}>
              {' '}{titleHighlight}
            </span>
          </h1>
          <p className="text-gray-600 max-w-2xl">
            {description}
          </p>
        </div>
        {children}
      </div>
    </div>
  )
}
