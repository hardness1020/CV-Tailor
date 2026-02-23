import React from 'react'
import { Loader2 } from 'lucide-react'

interface LoadingOverlayProps {
  isOpen: boolean
  message: string
  progress?: number
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  isOpen,
  message,
  progress,
}) => {
  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="bg-white rounded-xl p-8 shadow-2xl flex flex-col items-center gap-4 max-w-md w-full mx-4">
        {/* Spinner with pulsing ring */}
        <div className="relative">
          <Loader2 className="h-12 w-12 animate-spin text-purple-600" />
          <div className="absolute inset-0 h-12 w-12 border-4 border-purple-200 rounded-full animate-ping opacity-75" />
        </div>

        {/* Message */}
        <p className="text-lg font-medium text-gray-900 text-center">{message}</p>

        {/* Progress Bar (optional) */}
        {progress !== undefined && (
          <div className="w-full">
            <div className="flex justify-between text-xs text-gray-600 mb-2">
              <span>Processing...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-600 to-pink-600 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
