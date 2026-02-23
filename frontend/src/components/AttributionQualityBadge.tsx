/**
 * AttributionQualityBadge component (ft-030 - GitHub Attribution Enhancement)
 *
 * Displays attribution quality metrics for artifact evidence extraction.
 * Shows coverage (% of items with source quotes) and inferred ratio (% of low-confidence items).
 *
 * Features:
 * - Visual progress indicators for coverage and inferred ratio
 * - Color-coded status (good/warning/poor)
 * - Expandable detailed metrics breakdown
 * - Targets: ≥95% coverage, ≤20% inferred ratio
 */

import { useState } from 'react'
import { Shield, ChevronDown, ChevronUp, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { AttributionQualityMetrics } from '@/types'

interface AttributionQualityBadgeProps {
  overallCoverage: number;  // 0.0-1.0
  overallInferredRatio: number;  // 0.0-1.0
  documentationMetrics?: AttributionQualityMetrics;
  codeMetrics?: AttributionQualityMetrics;
  className?: string;
}

export default function AttributionQualityBadge({
  overallCoverage,
  overallInferredRatio,
  documentationMetrics,
  codeMetrics,
  className
}: AttributionQualityBadgeProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Determine overall quality status
  const getQualityStatus = () => {
    // Good: ≥95% coverage AND ≤20% inferred
    if (overallCoverage >= 0.95 && overallInferredRatio <= 0.20) {
      return {
        label: 'Excellent',
        icon: CheckCircle2,
        bgColor: 'bg-green-50',
        textColor: 'text-green-700',
        borderColor: 'border-green-300',
        dotColor: 'bg-green-500'
      }
    }
    // Warning: ≥85% coverage AND ≤30% inferred
    else if (overallCoverage >= 0.85 && overallInferredRatio <= 0.30) {
      return {
        label: 'Good',
        icon: AlertTriangle,
        bgColor: 'bg-blue-50',
        textColor: 'text-blue-700',
        borderColor: 'border-blue-300',
        dotColor: 'bg-blue-500'
      }
    }
    // Poor: below thresholds
    else {
      return {
        label: 'Needs Review',
        icon: XCircle,
        bgColor: 'bg-amber-50',
        textColor: 'text-amber-700',
        borderColor: 'border-amber-300',
        dotColor: 'bg-amber-500'
      }
    }
  }

  const qualityStatus = getQualityStatus()

  return (
    <div className={cn('space-y-3', className)}>
      {/* Quality Badge Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'w-full flex items-center gap-3 p-3 rounded-lg border-2 transition-colors',
          qualityStatus.bgColor,
          qualityStatus.borderColor,
          'hover:bg-opacity-80'
        )}
      >
        <div className={cn('flex items-center gap-2 flex-1 min-w-0')}>
          <Shield className={cn('h-4 w-4 flex-shrink-0', qualityStatus.textColor)} />
          <div className="text-left flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={cn('text-sm font-bold', qualityStatus.textColor)}>
                Source Attribution: {qualityStatus.label}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs mt-0.5">
              <span className={qualityStatus.textColor}>
                {(overallCoverage * 100).toFixed(0)}% coverage
              </span>
              <span className="text-gray-400">•</span>
              <span className={qualityStatus.textColor}>
                {(overallInferredRatio * 100).toFixed(0)}% inferred
              </span>
            </div>
          </div>
        </div>

        {isExpanded ? (
          <ChevronUp className={cn('h-4 w-4 flex-shrink-0', qualityStatus.textColor)} />
        ) : (
          <ChevronDown className={cn('h-4 w-4 flex-shrink-0', qualityStatus.textColor)} />
        )}
      </button>

      {/* Expanded Details */}
      {isExpanded && (
        <div className={cn(
          'p-4 rounded-lg border',
          qualityStatus.bgColor,
          qualityStatus.borderColor
        )}>
          <div className="space-y-4">
            {/* Coverage Progress */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-gray-700">Attribution Coverage</span>
                <span className="text-xs font-bold text-gray-900">
                  {(overallCoverage * 100).toFixed(1)}% (Target: ≥95%)
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-300',
                    overallCoverage >= 0.95 ? 'bg-green-500' :
                    overallCoverage >= 0.85 ? 'bg-blue-500' :
                    'bg-amber-500'
                  )}
                  style={{ width: `${Math.min(overallCoverage * 100, 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-600 mt-1">
                Percentage of items with source quotes from documents/code
              </p>
            </div>

            {/* Inferred Ratio Progress */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-gray-700">Inferred Items</span>
                <span className="text-xs font-bold text-gray-900">
                  {(overallInferredRatio * 100).toFixed(1)}% (Target: ≤20%)
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-300',
                    overallInferredRatio <= 0.20 ? 'bg-green-500' :
                    overallInferredRatio <= 0.30 ? 'bg-blue-500' :
                    'bg-amber-500'
                  )}
                  style={{ width: `${Math.min(overallInferredRatio * 100, 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-600 mt-1">
                Percentage of low-confidence items (confidence &lt; 50%)
              </p>
            </div>

            {/* Source Breakdown */}
            {(documentationMetrics || codeMetrics) && (
              <div className="pt-3 border-t border-gray-300">
                <h4 className="text-xs font-semibold text-gray-700 mb-2">Source Breakdown</h4>
                <div className="grid grid-cols-2 gap-3">
                  {/* Documentation Metrics */}
                  {documentationMetrics && (
                    <div className="p-2 bg-white rounded border border-gray-200">
                      <p className="text-xs font-semibold text-gray-700 mb-1">Documentation</p>
                      <div className="space-y-1 text-xs text-gray-600">
                        <div className="flex justify-between">
                          <span>Coverage:</span>
                          <span className="font-semibold">{(documentationMetrics.coverage * 100).toFixed(0)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Inferred:</span>
                          <span className="font-semibold">{(documentationMetrics.inferred_ratio * 100).toFixed(0)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Items:</span>
                          <span className="font-semibold">{documentationMetrics.total_items}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Code Metrics */}
                  {codeMetrics && (
                    <div className="p-2 bg-white rounded border border-gray-200">
                      <p className="text-xs font-semibold text-gray-700 mb-1">Source Code</p>
                      <div className="space-y-1 text-xs text-gray-600">
                        <div className="flex justify-between">
                          <span>Coverage:</span>
                          <span className="font-semibold">{(codeMetrics.coverage * 100).toFixed(0)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Inferred:</span>
                          <span className="font-semibold">{(codeMetrics.inferred_ratio * 100).toFixed(0)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Items:</span>
                          <span className="font-semibold">{codeMetrics.total_items}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
