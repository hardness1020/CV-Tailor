import { Loader2, CheckCircle2, XCircle, Sparkles, FileText } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { GeneratedDocument } from '@/types'

interface GenerationStatusBadgeProps {
  document: GeneratedDocument
  className?: string
}

/**
 * Compact generation status badge for CV cards
 * Shows pending/processing/bullets_ready/completed/failed states with progress
 */
export function GenerationStatusBadge({ document, className }: GenerationStatusBadgeProps) {
  const { status, progressPercentage = 0 } = document

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-all duration-200',
        status === 'pending' && 'bg-gray-100 text-gray-600 border border-gray-200',
        (status === 'processing' || status === 'bullets_ready' || status === 'bullets_approved' || status === 'assembling') &&
          'bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-700 border border-blue-200',
        status === 'completed' && 'bg-green-100 text-green-700 border border-green-200',
        status === 'failed' && 'bg-red-100 text-red-700 border border-red-200',
        className
      )}
    >
      {status === 'pending' && (
        <>
          <FileText className="h-3 w-3 opacity-50" />
          <span>Pending</span>
        </>
      )}

      {status === 'processing' && (
        <>
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Processing... {progressPercentage}%</span>
        </>
      )}

      {status === 'bullets_ready' && (
        <>
          <Sparkles className="h-3 w-3" />
          <span>Bullets Ready {progressPercentage}%</span>
        </>
      )}

      {status === 'bullets_approved' && (
        <>
          <Sparkles className="h-3 w-3" />
          <span>Bullets Approved {progressPercentage}%</span>
        </>
      )}

      {status === 'assembling' && (
        <>
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Assembling... {progressPercentage}%</span>
        </>
      )}

      {status === 'completed' && (
        <>
          <CheckCircle2 className="h-3 w-3" />
          <span>Completed</span>
        </>
      )}

      {status === 'failed' && (
        <>
          <XCircle className="h-3 w-3" />
          <span>Failed</span>
        </>
      )}
    </div>
  )
}
