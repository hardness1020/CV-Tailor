import { Loader2, CheckCircle2, XCircle, Sparkles } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useEnrichmentStatus, type EnrichmentStatus } from '@/hooks/useEnrichmentStatus'

interface EnrichmentStatusBadgeProps {
  artifactId: number
  className?: string
  /** Pass enrichment status from parent to avoid duplicate polling */
  enrichmentStatus?: EnrichmentStatus
}

/**
 * Compact enrichment status badge for artifact cards
 * Shows not_started/processing/completed/failed states with auto-polling
 */
export function EnrichmentStatusBadge({ artifactId, className, enrichmentStatus: externalStatus }: EnrichmentStatusBadgeProps) {
  // Use external status if provided (for detail pages), otherwise poll independently (for card lists)
  const { status: internalStatus } = useEnrichmentStatus({
    artifactId,
    enabled: !externalStatus, // Only poll if external status not provided
    pollingInterval: 3000
  })

  const status = externalStatus || internalStatus

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-all duration-200 animate-in fade-in',
        status.status === 'not_started' && 'bg-gray-100 text-gray-600 border border-gray-200',
        status.status === 'processing' && 'bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 border border-purple-200',
        status.status === 'completed' && 'bg-green-100 text-green-700 border border-green-200',
        status.status === 'failed' && 'bg-red-100 text-red-700 border border-red-200',
        className
      )}
    >
      {status.status === 'not_started' && (
        <>
          <Sparkles className="h-3 w-3 opacity-50" />
          <span>Not Enriched</span>
        </>
      )}

      {status.status === 'processing' && (
        <>
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Enriching...</span>
        </>
      )}

      {status.status === 'completed' && (
        <>
          <CheckCircle2 className="h-3 w-3" />
          <span>Enriched</span>
        </>
      )}

      {status.status === 'failed' && (
        <>
          <XCircle className="h-3 w-3" />
          <span>Failed</span>
        </>
      )}
    </div>
  )
}
