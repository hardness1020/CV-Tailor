/**
 * ArtifactSourceAttribution component (ft-030 - GitHub Attribution Enhancement)
 *
 * Displays source attribution for artifact evidence items (technologies, achievements, patterns).
 * Shows file/page references, confidence scores, and source quotes.
 *
 * Features:
 * - Supports both PDF (page:section) and GitHub (file:line) formats
 * - Expandable source quote display
 * - Confidence score visualization
 * - Color-coded by confidence level
 */

import { useState } from 'react'
import { FileText, Github, ChevronDown, ChevronUp, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { SourceAttributionMetadata } from '@/types'

interface ArtifactSourceAttributionProps {
  attribution: SourceAttributionMetadata;
  contentType: 'pdf' | 'github' | 'linkedin' | 'web_profile' | 'markdown' | 'text';
  className?: string;
}

export default function ArtifactSourceAttribution({
  attribution,
  contentType,
  className
}: ArtifactSourceAttributionProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Determine confidence level and styling
  const getConfidenceInfo = (confidence: number) => {
    if (confidence >= 0.85) {
      return {
        label: 'High',
        icon: TrendingUp,
        bgColor: 'bg-green-50',
        textColor: 'text-green-700',
        borderColor: 'border-green-200',
        dotColor: 'bg-green-500'
      }
    } else if (confidence >= 0.70) {
      return {
        label: 'Medium',
        icon: Minus,
        bgColor: 'bg-blue-50',
        textColor: 'text-blue-700',
        borderColor: 'border-blue-200',
        dotColor: 'bg-blue-500'
      }
    } else if (confidence >= 0.50) {
      return {
        label: 'Low',
        icon: TrendingDown,
        bgColor: 'bg-amber-50',
        textColor: 'text-amber-700',
        borderColor: 'border-amber-200',
        dotColor: 'bg-amber-500'
      }
    } else {
      return {
        label: 'Very Low',
        icon: TrendingDown,
        bgColor: 'bg-red-50',
        textColor: 'text-red-700',
        borderColor: 'border-red-200',
        dotColor: 'bg-red-500'
      }
    }
  }

  const confidenceInfo = getConfidenceInfo(attribution.confidence)
  const ConfidenceIcon = confidenceInfo.icon
  const SourceIcon = contentType === 'github' ? Github : FileText

  return (
    <div className={cn('space-y-2', className)}>
      {/* Attribution Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <SourceIcon className="h-3.5 w-3.5 text-gray-500 flex-shrink-0" />
          <span className="text-xs text-gray-700 font-medium truncate">
            {attribution.source_location}
          </span>
        </div>

        {/* Confidence Badge */}
        <div className={cn(
          'flex items-center gap-1.5 px-2 py-0.5 rounded border',
          confidenceInfo.bgColor,
          confidenceInfo.borderColor
        )}>
          <div className={cn('w-1.5 h-1.5 rounded-full', confidenceInfo.dotColor)} />
          <ConfidenceIcon className={cn('h-3 w-3', confidenceInfo.textColor)} />
          <span className={cn('text-xs font-semibold', confidenceInfo.textColor)}>
            {(attribution.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Source Quote (Expandable) */}
      {attribution.source_quote && (
        <div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-gray-800 transition-colors"
          >
            {isExpanded ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
            <span className="font-medium">
              {isExpanded ? 'Hide' : 'Show'} source quote
            </span>
          </button>

          {isExpanded && (
            <div className={cn(
              'mt-2 p-2.5 rounded-lg border-l-2',
              confidenceInfo.bgColor,
              confidenceInfo.borderColor
            )}>
              <p className="text-xs text-gray-700 italic leading-relaxed">
                "{attribution.source_quote}"
              </p>
              {attribution.reasoning && (
                <p className="text-xs text-gray-600 mt-2">
                  <span className="font-semibold">Reasoning:</span> {attribution.reasoning}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
