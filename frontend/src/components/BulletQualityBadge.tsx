import { CheckCircle, XCircle, TrendingUp } from 'lucide-react'
import { cn } from '@/utils/cn'

interface BulletQualityBadgeProps {
  qualityScore: number
  hasActionVerb: boolean
  keywordRelevanceScore: number
  showDetailed?: boolean
  className?: string
}

export default function BulletQualityBadge({
  qualityScore,
  hasActionVerb,
  keywordRelevanceScore,
  showDetailed = false,
  className
}: BulletQualityBadgeProps) {
  const getQualityColor = (score: number) => {
    if (score >= 0.8) return 'green'
    if (score >= 0.6) return 'yellow'
    return 'red'
  }

  const getQualityLabel = (score: number) => {
    if (score >= 0.8) return 'Excellent'
    if (score >= 0.6) return 'Good'
    return 'Needs Improvement'
  }

  const qualityColor = getQualityColor(qualityScore)
  const qualityLabel = getQualityLabel(qualityScore)

  const colorClasses = {
    green: {
      bg: 'bg-gradient-to-r from-green-50 to-emerald-50',
      border: 'border-green-300',
      text: 'text-green-800',
      badgeBg: 'bg-green-100',
      badgeText: 'text-green-700'
    },
    yellow: {
      bg: 'bg-gradient-to-r from-yellow-50 to-amber-50',
      border: 'border-yellow-300',
      text: 'text-yellow-800',
      badgeBg: 'bg-yellow-100',
      badgeText: 'text-yellow-700'
    },
    red: {
      bg: 'bg-gradient-to-r from-red-50 to-rose-50',
      border: 'border-red-300',
      text: 'text-red-800',
      badgeBg: 'bg-red-100',
      badgeText: 'text-red-700'
    }
  }

  const colors = colorClasses[qualityColor]

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
        title={`Quality: ${qualityLabel} (${(qualityScore * 100).toFixed(0)}%)\nAction Verb: ${hasActionVerb ? 'Yes' : 'No'}\nKeyword Relevance: ${(keywordRelevanceScore * 100).toFixed(0)}%`}
      >
        <div className={cn(
          'w-2 h-2 rounded-full',
          qualityColor === 'green' ? 'bg-green-500' :
          qualityColor === 'yellow' ? 'bg-yellow-500' :
          'bg-red-500'
        )} />
        <span>{(qualityScore * 100).toFixed(0)}%</span>
      </div>
    )
  }

  // Detailed badge view
  return (
    <div className={cn('space-y-2', className)}>
      {/* Overall Quality Score */}
      <div className={cn(
        'flex items-center justify-between p-3 rounded-xl border-2',
        colors.bg,
        colors.border
      )}>
        <div className="flex items-center gap-2">
          <TrendingUp className={cn('h-4 w-4', colors.text)} />
          <span className={cn('text-sm font-bold', colors.text)}>
            Overall Quality
          </span>
        </div>
        <div className={cn(
          'px-3 py-1 rounded-full text-sm font-bold',
          colors.badgeBg,
          colors.badgeText
        )}>
          {(qualityScore * 100).toFixed(0)}% - {qualityLabel}
        </div>
      </div>

      {/* Quality Metrics Grid */}
      <div className="grid grid-cols-2 gap-2">
        {/* Action Verb Check */}
        <div className={cn(
          'flex items-center gap-2 p-2 rounded-lg border',
          hasActionVerb
            ? 'bg-green-50 border-green-200'
            : 'bg-red-50 border-red-200'
        )}>
          {hasActionVerb ? (
            <CheckCircle className="h-4 w-4 text-green-600" />
          ) : (
            <XCircle className="h-4 w-4 text-red-600" />
          )}
          <div>
            <div className={cn(
              'text-xs font-bold',
              hasActionVerb ? 'text-green-800' : 'text-red-800'
            )}>
              Action Verb
            </div>
            <div className={cn(
              'text-xs',
              hasActionVerb ? 'text-green-600' : 'text-red-600'
            )}>
              {hasActionVerb ? 'Present' : 'Missing'}
            </div>
          </div>
        </div>

        {/* Keyword Relevance */}
        <div className={cn(
          'flex items-center gap-2 p-2 rounded-lg border',
          keywordRelevanceScore >= 0.7
            ? 'bg-green-50 border-green-200'
            : keywordRelevanceScore >= 0.5
            ? 'bg-yellow-50 border-yellow-200'
            : 'bg-red-50 border-red-200'
        )}>
          <div className={cn(
            'w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold',
            keywordRelevanceScore >= 0.7
              ? 'bg-green-100 text-green-700'
              : keywordRelevanceScore >= 0.5
              ? 'bg-yellow-100 text-yellow-700'
              : 'bg-red-100 text-red-700'
          )}>
            {(keywordRelevanceScore * 100).toFixed(0)}%
          </div>
          <div>
            <div className={cn(
              'text-xs font-bold',
              keywordRelevanceScore >= 0.7
                ? 'text-green-800'
                : keywordRelevanceScore >= 0.5
                ? 'text-yellow-800'
                : 'text-red-800'
            )}>
              Keywords
            </div>
            <div className={cn(
              'text-xs',
              keywordRelevanceScore >= 0.7
                ? 'text-green-600'
                : keywordRelevanceScore >= 0.5
                ? 'text-yellow-600'
                : 'text-red-600'
            )}>
              {keywordRelevanceScore >= 0.7 ? 'Strong' : keywordRelevanceScore >= 0.5 ? 'Fair' : 'Weak'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
