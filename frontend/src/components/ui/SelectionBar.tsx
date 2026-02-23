import { Trash2 } from 'lucide-react'
import { Button } from './Button'
import type { PageTheme } from '@/utils/pageThemes'
import { cn } from '@/utils/cn'

interface SelectionBarProps {
  selectedCount: number
  itemName: string // 'CV' or 'artifact'
  onClear: () => void
  onDelete: () => void
  theme: PageTheme
}

export function SelectionBar({
  selectedCount,
  itemName,
  onClear,
  onDelete,
  theme
}: SelectionBarProps) {
  if (selectedCount === 0) return null

  const itemText = selectedCount === 1 ? itemName : `${itemName}s`

  return (
    <div className={cn(
      'border-t border-gray-200 p-4 rounded-b-xl',
      `bg-${theme.colors.selectionBg}`
    )}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className={cn(
            'flex items-center justify-center w-8 h-8 text-white text-xs font-semibold rounded-full',
            `bg-${theme.colors.primary}`
          )}>
            {selectedCount}
          </div>
          <span className={cn(
            'text-sm font-medium',
            `text-${theme.colors.primary}`
          )}>
            {selectedCount} {itemText} selected
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onClear}
            className={cn(
              'text-sm font-medium transition-colors',
              `text-${theme.colors.primary}`,
              `hover:text-${theme.colors.primaryDark}`
            )}
          >
            Clear selection
          </button>
          <Button
            onClick={onDelete}
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Trash2 className="h-4 w-4" />
            Delete Selected
          </Button>
        </div>
      </div>
    </div>
  )
}
