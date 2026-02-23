/**
 * SourceAttributionCard component (ft-030 - Anti-Hallucination Improvements)
 *
 * Displays source quotes with attribution for verified bullet points.
 * Implements ADR-041: Source Attribution Schema.
 *
 * Shows:
 * - Direct quote from source document
 * - Source location (page, section)
 * - Confidence score for the attribution
 */

import { FileText, MapPin, TrendingUp } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { SourceAttribution } from '@/types'

interface SourceAttributionCardProps {
  attributions: SourceAttribution[];
  className?: string;
  showTitle?: boolean;
}

export default function SourceAttributionCard({
  attributions,
  className,
  showTitle = true
}: SourceAttributionCardProps) {
  if (!attributions || attributions.length === 0) {
    return (
      <div className={cn(
        'p-4 rounded-lg border-2 border-dashed border-gray-200 bg-gray-50',
        className
      )}>
        <p className="text-sm text-gray-500 italic">
          No source attributions available
        </p>
      </div>
    )
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'green'
    if (confidence >= 0.6) return 'blue'
    if (confidence >= 0.4) return 'amber'
    return 'red'
  }

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'High'
    if (confidence >= 0.6) return 'Medium'
    if (confidence >= 0.4) return 'Low'
    return 'Very Low'
  }

  return (
    <div className={cn('space-y-3', className)}>
      {showTitle && (
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-600" />
          <h4 className="text-sm font-bold text-gray-900">
            Source Evidence
          </h4>
        </div>
      )}

      <div className="space-y-2">
        {attributions.map((attr, index) => {
          const confidenceColor = getConfidenceColor(attr.confidence)
          const confidenceLabel = getConfidenceLabel(attr.confidence)

          const colorClasses = {
            green: {
              bg: 'bg-green-50',
              border: 'border-green-200',
              badgeBg: 'bg-green-100',
              badgeText: 'text-green-700',
              iconColor: 'text-green-600'
            },
            blue: {
              bg: 'bg-blue-50',
              border: 'border-blue-200',
              badgeBg: 'bg-blue-100',
              badgeText: 'text-blue-700',
              iconColor: 'text-blue-600'
            },
            amber: {
              bg: 'bg-amber-50',
              border: 'border-amber-200',
              badgeBg: 'bg-amber-100',
              badgeText: 'text-amber-700',
              iconColor: 'text-amber-600'
            },
            red: {
              bg: 'bg-red-50',
              border: 'border-red-200',
              badgeBg: 'bg-red-100',
              badgeText: 'text-red-700',
              iconColor: 'text-red-600'
            }
          }

          const colors = colorClasses[confidenceColor]

          return (
            <div
              key={index}
              className={cn(
                'p-3 rounded-lg border-2 space-y-2',
                colors.bg,
                colors.border
              )}
            >
              {/* Quote */}
              <div className="flex items-start gap-2">
                <div className="flex-shrink-0 mt-0.5">
                  <div className={cn(
                    'w-1 h-12 rounded-full',
                    confidenceColor === 'green' ? 'bg-green-500' :
                    confidenceColor === 'blue' ? 'bg-blue-500' :
                    confidenceColor === 'amber' ? 'bg-amber-500' :
                    'bg-red-500'
                  )} />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-800 italic leading-relaxed">
                    "{attr.quote}"
                  </p>
                </div>
              </div>

              {/* Metadata */}
              <div className="flex items-center justify-between gap-2 pl-5">
                {/* Location */}
                <div className="flex items-center gap-1.5">
                  <MapPin className="h-3 w-3 text-gray-500" />
                  <span className="text-xs text-gray-600">
                    {attr.location}
                  </span>
                </div>

                {/* Confidence Badge */}
                <div className={cn(
                  'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-bold',
                  colors.badgeBg,
                  colors.badgeText
                )}>
                  <TrendingUp className="h-3 w-3" />
                  <span>{(attr.confidence * 100).toFixed(0)}% - {confidenceLabel}</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Summary Footer */}
      {attributions.length > 1 && (
        <div className="pt-2 border-t border-gray-200">
          <p className="text-xs text-gray-500">
            {attributions.length} source {attributions.length === 1 ? 'quote' : 'quotes'} found • Average confidence: {' '}
            <span className="font-bold text-gray-700">
              {(attributions.reduce((sum, a) => sum + a.confidence, 0) / attributions.length * 100).toFixed(0)}%
            </span>
          </p>
        </div>
      )}
    </div>
  )
}
