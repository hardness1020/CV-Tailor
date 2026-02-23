/**
 * StatusBadge - Display artifact completion status
 * Shows visual indicators for draft, processing, review_pending, reunifying, review_finalized, complete, abandoned
 */

import { FileText, Loader2, Eye, CheckCircle2, XCircle, Sparkles, ThumbsUp } from 'lucide-react'
import { ArtifactStatus } from '@/types'

interface StatusBadgeProps {
  status: ArtifactStatus
  size?: 'sm' | 'md'
  showIcon?: boolean
  className?: string
}

const statusConfig: Record<
  ArtifactStatus,
  { label: string; icon: typeof FileText; colorClass: string; bgClass: string }
> = {
  draft: {
    label: 'Draft',
    icon: FileText,
    colorClass: 'text-yellow-700',
    bgClass: 'bg-yellow-100 border-yellow-200',
  },
  processing: {
    label: 'Processing',
    icon: Loader2,
    colorClass: 'text-blue-700',
    bgClass: 'bg-blue-100 border-blue-200',
  },
  review_pending: {
    label: 'Review Pending',
    icon: Eye,
    colorClass: 'text-orange-700',
    bgClass: 'bg-orange-100 border-orange-200',
  },
  reunifying: {
    label: 'Finalizing',
    icon: Sparkles,
    colorClass: 'text-purple-700',
    bgClass: 'bg-purple-100 border-purple-200',
  },
  review_finalized: {
    label: 'Awaiting Acceptance',
    icon: ThumbsUp,
    colorClass: 'text-indigo-700',
    bgClass: 'bg-indigo-100 border-indigo-200',
  },
  complete: {
    label: 'Complete',
    icon: CheckCircle2,
    colorClass: 'text-green-700',
    bgClass: 'bg-green-100 border-green-200',
  },
  abandoned: {
    label: 'Abandoned',
    icon: XCircle,
    colorClass: 'text-gray-700',
    bgClass: 'bg-gray-100 border-gray-200',
  },
}

export function StatusBadge({
  status,
  size = 'sm',
  showIcon = true,
  className = ''
}: StatusBadgeProps) {
  // Defensive: fall back to 'draft' if status is unknown/invalid
  const config = statusConfig[status] || statusConfig['draft']
  const Icon = config.icon

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
  const iconSize = size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${config.bgClass} ${config.colorClass} ${sizeClasses} ${className}`}
    >
      {showIcon && (
        <Icon
          className={`${iconSize} ${status === 'processing' ? 'animate-spin' : ''}`}
        />
      )}
      {config.label}
    </span>
  )
}
