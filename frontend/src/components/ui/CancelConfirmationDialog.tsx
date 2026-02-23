import React, { useEffect, useRef, useCallback } from 'react'
import { AlertTriangle } from 'lucide-react'

export interface WizardProgressState {
  currentStep: number
  touchedSteps: Set<number>
  completedSteps: Set<number>
  formData: Record<string, any>
}

export interface CancelConfirmationDialogProps {
  isOpen: boolean
  progress: WizardProgressState
  onConfirm: () => void
  onCancel: () => void
}

export const CancelConfirmationDialog: React.FC<CancelConfirmationDialogProps> = ({
  isOpen,
  progress,
  onConfirm,
  onCancel
}) => {
  const keepEditingButtonRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)

  // Handle ESC key (wrapped in useCallback to prevent stale closures)
  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' || e.code === 'Escape') {
      onCancel()
    }
  }, [onCancel])

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen, handleEscape])

  // Focus on "Keep Editing" button when dialog opens
  useEffect(() => {
    if (isOpen && keepEditingButtonRef.current) {
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        keepEditingButtonRef.current?.focus()
      }, 100)
    }
  }, [isOpen])

  // Don't render anything if not open (after all hooks to follow Rules of Hooks)
  if (!isOpen) {
    return null
  }

  // Calculate summary statistics
  const completedCount = progress.completedSteps.size
  const touchedCount = progress.touchedSteps.size

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Only close if clicking the backdrop itself, not the dialog content
    if (e.target === e.currentTarget) {
      onCancel()
    }
  }

  // Focus trap: Tab should cycle between buttons
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Tab') {
      const focusableElements = dialogRef.current?.querySelectorAll(
        'button:not([disabled])'
      ) as NodeListOf<HTMLElement>

      if (focusableElements && focusableElements.length > 0) {
        const firstElement = focusableElements[0]
        const lastElement = focusableElements[focusableElements.length - 1]

        if (e.shiftKey) {
          // Shift+Tab: If on first element, go to last
          if (document.activeElement === firstElement) {
            e.preventDefault()
            lastElement.focus()
          }
        } else {
          // Tab: If on last element, go to first
          if (document.activeElement === lastElement) {
            e.preventDefault()
            firstElement.focus()
          }
        }
      }
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 transition-opacity duration-300 ease-out"
      onClick={handleBackdropClick}
      aria-hidden="true"
    >
      <div
        ref={dialogRef}
        role="alertdialog"
        aria-labelledby="cancel-dialog-title"
        aria-describedby="cancel-dialog-message"
        aria-modal="true"
        onKeyDown={handleKeyDown}
        className="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full transform transition-all duration-300 ease-out scale-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Icon and Title */}
        <div className="flex items-start gap-4 mb-4">
          <div className="flex-shrink-0">
            <AlertTriangle className="w-6 h-6 text-amber-600" />
          </div>
          <div className="flex-1">
            <h2
              id="cancel-dialog-title"
              className="text-xl font-semibold text-gray-900"
            >
              Unsaved Changes
            </h2>
          </div>
        </div>

        {/* Message */}
        <div id="cancel-dialog-message" className="mb-6">
          <p className="text-gray-700 mb-3">
            You have unsaved changes on Step {progress.currentStep}. If you exit now, all progress will be lost.
          </p>

          {/* Changes Summary */}
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm font-medium text-gray-900 mb-2">Your Progress:</p>
            <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
              <li>
                {completedCount} of {touchedCount} {touchedCount === 1 ? 'step' : 'steps'} completed
              </li>
            </ul>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            ref={keepEditingButtonRef}
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2 bg-gray-100 text-gray-900 font-medium rounded-lg hover:bg-gray-200 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2"
          >
            Keep Editing
          </button>

          <button
            type="button"
            onClick={onConfirm}
            className="flex-1 px-4 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Discard & Exit
          </button>
        </div>
      </div>
    </div>
  )
}
