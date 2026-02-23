/**
 * ConfidenceBadge component (ft-030 - Anti-Hallucination Improvements)
 *
 * Displays confidence scores and tier classification for verified bullet points.
 * Implements visual indicators based on ADR-043 confidence thresholds.
 *
 * Tiers:
 * - HIGH (≥0.85): Green - Auto-approved, verified against sources
 * - MEDIUM (0.70-0.84): Blue - Auto-approved with neutral indicator
 * - LOW (0.50-0.69): Amber - Flagged for user review
 * - CRITICAL (<0.50): Red - Blocked from finalization
 */

import { CheckCircle, AlertCircle, AlertTriangle, XCircle, Shield } from 'lucide-react'
import { cn } from '@/utils/cn'

export type ConfidenceTier = 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL'

interface ConfidenceBadgeProps {
  confidence: number // 0.0-1.0
  tier: ConfidenceTier
  requiresReview?: boolean
  isBlocked?: boolean
  showDetailed?: boolean
  className?: string
}

export default function ConfidenceBadge({
  confidence,
  tier,
  requiresReview = false,
  isBlocked = false,
  showDetailed = false,
  className
}: ConfidenceBadgeProps) {
  const getTierColor = (tier: ConfidenceTier) => {
    switch (tier) {
      case 'HIGH':
        return 'green'
      case 'MEDIUM':
        return 'blue'
      case 'LOW':
        return 'amber'
      case 'CRITICAL':
        return 'red'
      default:
        return 'gray'
    }
  }

  const getTierLabel = (tier: ConfidenceTier) => {
    switch (tier) {
      case 'HIGH':
        return 'Verified'
      case 'MEDIUM':
        return 'Likely Accurate'
      case 'LOW':
        return 'Needs Review'
      case 'CRITICAL':
        return 'Requires Edit'
      default:
        return 'Unknown'
    }
  }

  const getTierIcon = (tier: ConfidenceTier) => {
    switch (tier) {
      case 'HIGH':
        return CheckCircle
      case 'MEDIUM':
        return Shield
      case 'LOW':
        return AlertTriangle
      case 'CRITICAL':
        return XCircle
      default:
        return AlertCircle
    }
  }

  const getTierMessage = (tier: ConfidenceTier) => {
    switch (tier) {
      case 'HIGH':
        return 'High confidence - content verified against sources'
      case 'MEDIUM':
        return 'Medium confidence - content appears reasonable'
      case 'LOW':
        return 'Low confidence - please review for accuracy'
      case 'CRITICAL':
        return 'Critical confidence - blocked from use, requires review and editing'
      default:
        return 'Confidence information unavailable'
    }
  }

  const tierColor = getTierColor(tier)
  const tierLabel = getTierLabel(tier)
  const TierIcon = getTierIcon(tier)
  const tierMessage = getTierMessage(tier)

  const colorClasses = {
    green: {
      bg: 'bg-gradient-to-r from-green-50 to-emerald-50',
      border: 'border-green-300',
      text: 'text-green-800',
      badgeBg: 'bg-green-100',
      badgeText: 'text-green-700',
      iconColor: 'text-green-600',
      dotBg: 'bg-green-500'
    },
    blue: {
      bg: 'bg-gradient-to-r from-blue-50 to-cyan-50',
      border: 'border-blue-300',
      text: 'text-blue-800',
      badgeBg: 'bg-blue-100',
      badgeText: 'text-blue-700',
      iconColor: 'text-blue-600',
      dotBg: 'bg-blue-500'
    },
    amber: {
      bg: 'bg-gradient-to-r from-amber-50 to-yellow-50',
      border: 'border-amber-300',
      text: 'text-amber-800',
      badgeBg: 'bg-amber-100',
      badgeText: 'text-amber-700',
      iconColor: 'text-amber-600',
      dotBg: 'bg-amber-500'
    },
    red: {
      bg: 'bg-gradient-to-r from-red-50 to-rose-50',
      border: 'border-red-300',
      text: 'text-red-800',
      badgeBg: 'bg-red-100',
      badgeText: 'text-red-700',
      iconColor: 'text-red-600',
      dotBg: 'bg-red-500'
    },
    gray: {
      bg: 'bg-gradient-to-r from-gray-50 to-slate-50',
      border: 'border-gray-300',
      text: 'text-gray-800',
      badgeBg: 'bg-gray-100',
      badgeText: 'text-gray-700',
      iconColor: 'text-gray-600',
      dotBg: 'bg-gray-500'
    }
  }

  const colors = colorClasses[tierColor]

  if (!showDetailed) {
    // Compact badge view
    return (
      <div
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border',
          colors.badgeBg,
          colors.badgeText,
          colors.border,
          className
        )}
        title={`${tierLabel} (${(confidence * 100).toFixed(0)}% confidence)\n${tierMessage}\n${requiresReview ? '⚠️ Requires review' : ''}\n${isBlocked ? '🚫 Blocked from finalization' : ''}`}
      >
        <div className={cn('w-2 h-2 rounded-full', colors.dotBg)} />
        <span>{tierLabel}</span>
      </div>
    )
  }

  // Detailed badge view
  return (
    <div className={cn('space-y-2', className)}>
      {/* Overall Confidence Score */}
      <div className={cn(
        'flex items-center justify-between p-3 rounded-xl border-2',
        colors.bg,
        colors.border
      )}>
        <div className="flex items-center gap-2">
          <TierIcon className={cn('h-4 w-4', colors.iconColor)} />
          <span className={cn('text-sm font-bold', colors.text)}>
            Confidence
          </span>
        </div>
        <div className={cn(
          'px-3 py-1 rounded-full text-sm font-bold',
          colors.badgeBg,
          colors.badgeText
        )}>
          {(confidence * 100).toFixed(0)}% - {tierLabel}
        </div>
      </div>

      {/* Status Message */}
      <div className={cn(
        'flex items-start gap-2 p-2 rounded-lg border text-xs',
        colors.bg,
        colors.border
      )}>
        <AlertCircle className={cn('h-4 w-4 flex-shrink-0 mt-0.5', colors.iconColor)} />
        <p className={cn('leading-relaxed', colors.text)}>
          {tierMessage}
        </p>
      </div>

      {/* Review Status Indicators */}
      {(requiresReview || isBlocked) && (
        <div className="grid grid-cols-2 gap-2">
          {requiresReview && (
            <div className={cn(
              'flex items-center gap-2 p-2 rounded-lg border',
              'bg-amber-50 border-amber-200'
            )}>
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <div>
                <div className="text-xs font-bold text-amber-800">
                  Review Required
                </div>
                <div className="text-xs text-amber-600">
                  Check accuracy
                </div>
              </div>
            </div>
          )}

          {isBlocked && (
            <div className={cn(
              'flex items-center gap-2 p-2 rounded-lg border',
              'bg-red-50 border-red-200'
            )}>
              <XCircle className="h-4 w-4 text-red-600" />
              <div>
                <div className="text-xs font-bold text-red-800">
                  Blocked
                </div>
                <div className="text-xs text-red-600">
                  Must edit
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
