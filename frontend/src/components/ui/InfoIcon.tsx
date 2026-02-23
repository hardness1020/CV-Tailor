import { Info, Lock, AlertTriangle, Sparkles } from 'lucide-react'
import { useState } from 'react'

interface InfoIconProps {
  /**
   * Tooltip message to display on hover
   */
  tooltip: string
  /**
   * Icon variant
   * - info: General information (blue)
   * - lock: Preserved/immutable field (green)
   * - warning: AI will replace (amber)
   * - ai: AI-generated content (purple)
   */
  variant?: 'info' | 'lock' | 'warning' | 'ai'
  /**
   * Icon size (Tailwind class)
   */
  size?: 'sm' | 'md' | 'lg'
  /**
   * Additional CSS classes
   */
  className?: string
}

const iconMap = {
  info: Info,
  lock: Lock,
  warning: AlertTriangle,
  ai: Sparkles,
}

const colorMap = {
  info: 'text-blue-500 hover:text-blue-600',
  lock: 'text-green-600 hover:text-green-700',
  warning: 'text-amber-600 hover:text-amber-700',
  ai: 'text-purple-600 hover:text-purple-700',
}

const bgColorMap = {
  info: 'bg-blue-50 border-blue-200',
  lock: 'bg-green-50 border-green-200',
  warning: 'bg-amber-50 border-amber-200',
  ai: 'bg-purple-50 border-purple-200',
}

const sizeMap = {
  sm: 'h-3 w-3',
  md: 'h-4 w-4',
  lg: 'h-5 w-5',
}

/**
 * InfoIcon - Display an icon with tooltip on hover
 *
 * @example
 * <InfoIcon tooltip="This field is preserved during enrichment" variant="lock" />
 * <InfoIcon tooltip="AI will replace this content" variant="warning" />
 */
export function InfoIcon({
  tooltip,
  variant = 'info',
  size = 'sm',
  className = ''
}: InfoIconProps) {
  const [showTooltip, setShowTooltip] = useState(false)
  const Icon = iconMap[variant]

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onFocus={() => setShowTooltip(true)}
        onBlur={() => setShowTooltip(false)}
        className={`inline-flex items-center justify-center transition-colors cursor-help ${colorMap[variant]} ${className}`}
        aria-label={tooltip}
      >
        <Icon className={sizeMap[size]} />
      </button>

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute z-50 bottom-full left-1/2 transform -translate-x-1/2 mb-2 pointer-events-none">
          <div className={`px-3 py-2 text-xs font-medium rounded-lg shadow-lg border ${bgColorMap[variant]} whitespace-nowrap`}>
            {tooltip}
            {/* Arrow */}
            <div className={`absolute top-full left-1/2 transform -translate-x-1/2 -mt-px`}>
              <div className={`border-4 border-transparent ${
                variant === 'info' ? 'border-t-blue-50' :
                variant === 'lock' ? 'border-t-green-50' :
                variant === 'warning' ? 'border-t-amber-50' :
                'border-t-purple-50'
              }`} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
