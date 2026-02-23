import React from 'react'
import { AlertTriangle, WifiOff, ServerCrash, FileQuestion, RefreshCw, ArrowLeft, Home } from 'lucide-react'
import { Button } from './Button'
import { Card } from './Card'
import { cn } from '@/utils/cn'

export type ErrorType = 'network' | 'server' | 'notFound' | 'generic'

export interface ErrorStateProps {
  type?: ErrorType
  title?: string
  message?: string
  onRetry?: () => void
  onGoBack?: () => void
  onGoHome?: () => void
  className?: string
  isRetrying?: boolean
}

const errorConfig: Record<ErrorType, {
  icon: React.ElementType
  iconColor: string
  iconBg: string
  defaultTitle: string
  defaultMessage: string
}> = {
  network: {
    icon: WifiOff,
    iconColor: 'text-orange-600',
    iconBg: 'bg-orange-100',
    defaultTitle: 'Connection Problem',
    defaultMessage: 'Unable to connect to the server. Please check your internet connection and try again.',
  },
  server: {
    icon: ServerCrash,
    iconColor: 'text-red-600',
    iconBg: 'bg-red-100',
    defaultTitle: 'Server Error',
    defaultMessage: 'Something went wrong on our end. We\'re working to fix it. Please try again in a few moments.',
  },
  notFound: {
    icon: FileQuestion,
    iconColor: 'text-blue-600',
    iconBg: 'bg-blue-100',
    defaultTitle: 'Not Found',
    defaultMessage: 'The resource you\'re looking for doesn\'t exist or has been moved.',
  },
  generic: {
    icon: AlertTriangle,
    iconColor: 'text-amber-600',
    iconBg: 'bg-amber-100',
    defaultTitle: 'Something Went Wrong',
    defaultMessage: 'An unexpected error occurred. Please try again.',
  },
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  type = 'generic',
  title,
  message,
  onRetry,
  onGoBack,
  onGoHome,
  className,
  isRetrying = false,
}) => {
  const config = errorConfig[type]
  const Icon = config.icon

  return (
    <Card className={cn('p-8 text-center', className)}>
      {/* Icon */}
      <div className="flex justify-center mb-6">
        <div className={cn(
          'w-16 h-16 rounded-full flex items-center justify-center',
          config.iconBg
        )}>
          <Icon className={cn('h-8 w-8', config.iconColor)} />
        </div>
      </div>

      {/* Title */}
      <h3 className="text-xl font-bold text-gray-900 mb-3">
        {title || config.defaultTitle}
      </h3>

      {/* Message */}
      <p className="text-gray-600 mb-6 max-w-md mx-auto leading-relaxed">
        {message || config.defaultMessage}
      </p>

      {/* Action Buttons */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        {onRetry && (
          <Button
            onClick={onRetry}
            disabled={isRetrying}
            variant="primary"
            className="flex items-center gap-2"
          >
            <RefreshCw className={cn('h-4 w-4', isRetrying && 'animate-spin')} />
            {isRetrying ? 'Retrying...' : 'Try Again'}
          </Button>
        )}

        {onGoBack && (
          <Button
            onClick={onGoBack}
            variant="outline"
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </Button>
        )}

        {onGoHome && (
          <Button
            onClick={onGoHome}
            variant="outline"
            className="flex items-center gap-2"
          >
            <Home className="h-4 w-4" />
            Go Home
          </Button>
        )}
      </div>
    </Card>
  )
}
