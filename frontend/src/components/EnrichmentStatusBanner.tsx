import { Loader2, XCircle } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { EnrichmentStatus } from '@/hooks/useEnrichmentStatus'

interface EnrichmentStatusBannerProps {
  status: EnrichmentStatus
  className?: string
}

/**
 * Full-width enrichment status banner for artifact detail page
 * Shows processing progress or errors (NOT completion - that's redundant with badge + AI Content tab)
 */
export function EnrichmentStatusBanner({
  status,
  className
}: EnrichmentStatusBannerProps) {

  // Only show banner during processing or when failed (completion is shown in badge + AI Content tab)
  if (status.status !== 'processing' && status.status !== 'failed') {
    return null
  }

  return (
    <div
      className={cn(
        'rounded-xl border-2 p-5 transition-all duration-300 animate-in fade-in slide-in-from-top-2',
        status.status === 'processing' && 'bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200',
        status.status === 'failed' && 'bg-gradient-to-r from-red-50 to-orange-50 border-red-200',
        className
      )}
    >
      {/* Processing State */}
      {status.status === 'processing' && (
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 p-2 bg-white rounded-lg border-2 border-purple-200">
            <Loader2 className="h-6 w-6 text-purple-600 animate-spin" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-lg font-bold text-purple-900">
                AI Enrichment in Progress
              </h3>
              {status.progressPercentage !== undefined && (
                <span className="text-sm font-semibold text-purple-600">
                  {status.progressPercentage}%
                </span>
              )}
            </div>
            <p className="text-sm text-purple-700 mb-3">
              Analyzing your artifact and extracting insights, technologies, and achievements...
            </p>

            {/* Progress Bar */}
            {status.progressPercentage !== undefined && (
              <div className="w-full bg-white rounded-full h-2 border border-purple-200 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-600 to-pink-600 transition-all duration-500 ease-out"
                  style={{ width: `${status.progressPercentage}%` }}
                />
              </div>
            )}

            {/* Stats */}
            {status.sourcesProcessed !== undefined && (
              <div className="mt-3 flex items-center gap-4 text-xs text-purple-600">
                <span className="font-medium">
                  {status.sourcesProcessed} sources processed
                </span>
                {status.sourcesSuccessful !== undefined && (
                  <span>
                    {status.sourcesSuccessful} successful
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Failed State */}
      {status.status === 'failed' && (
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 p-2 bg-white rounded-lg border-2 border-red-200">
            <XCircle className="h-6 w-6 text-red-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-bold text-red-900 mb-2">
              Enrichment Failed
            </h3>
            <p className="text-sm text-red-700">
              {status.errorMessage || 'An error occurred during AI enrichment. Please try again later.'}
            </p>
            {status.sourcesProcessed !== undefined && (
              <p className="text-xs text-red-600 mt-2">
                Processed {status.sourcesProcessed} sources before failure
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
