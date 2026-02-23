import React from 'react'
import { AlertTriangle, AlertCircle, Info } from 'lucide-react'
import { cn } from '@/utils/cn'
import { Button } from './Button'

export interface ConfirmationModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void | Promise<void>
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'warning' | 'info'
  isLoading?: boolean
}

const variantConfig = {
  danger: {
    icon: AlertTriangle,
    iconColor: 'text-red-600',
    iconBg: 'bg-red-100',
    buttonVariant: 'danger' as const,
  },
  warning: {
    icon: AlertCircle,
    iconColor: 'text-amber-600',
    iconBg: 'bg-amber-100',
    buttonVariant: 'primary' as const,
  },
  info: {
    icon: Info,
    iconColor: 'text-blue-600',
    iconBg: 'bg-blue-100',
    buttonVariant: 'primary' as const,
  },
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'info',
  isLoading = false,
}) => {
  if (!isOpen) return null

  const config = variantConfig[variant]
  const Icon = config.icon

  const handleConfirm = async () => {
    await onConfirm()
    if (!isLoading) {
      onClose()
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto"
      aria-labelledby="confirmation-modal-title"
      role="dialog"
      aria-modal="true"
    >
      <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          aria-hidden="true"
          onClick={isLoading ? undefined : onClose}
        />

        {/* Center modal */}
        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">
          &#8203;
        </span>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:w-full sm:max-w-lg">
          <div className="bg-white px-6 pt-6 pb-4">
            <div className="sm:flex sm:items-start">
              {/* Icon */}
              <div
                className={cn(
                  'mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full sm:mx-0 sm:h-10 sm:w-10',
                  config.iconBg
                )}
              >
                <Icon className={cn('h-6 w-6', config.iconColor)} aria-hidden="true" />
              </div>

              {/* Content */}
              <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left flex-1">
                <h3
                  className="text-lg font-semibold leading-6 text-gray-900"
                  id="confirmation-modal-title"
                >
                  {title}
                </h3>
                <div className="mt-2">
                  <p className="text-sm text-gray-600 whitespace-pre-wrap">{message}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="bg-gray-50 px-6 py-4 sm:flex sm:flex-row-reverse gap-3">
            <Button
              onClick={handleConfirm}
              variant={config.buttonVariant}
              disabled={isLoading}
              className="w-full sm:w-auto"
            >
              {isLoading ? 'Processing...' : confirmLabel}
            </Button>
            <Button
              onClick={onClose}
              variant="outline"
              disabled={isLoading}
              className="w-full sm:w-auto mt-3 sm:mt-0"
            >
              {cancelLabel}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
