import React, { useEffect, ReactNode } from 'react'
import { X } from 'lucide-react'
import { WizardStepIndicator, WizardStep } from './WizardStepIndicator'

export type { WizardStep }

export interface WizardFlowProps {
  title: string
  steps: WizardStep[]
  currentStep: number
  onStepChange: (step: number) => void
  onCancel: () => void
  gradientTheme?: 'purple' | 'blue' | 'custom'
  customGradient?: string
  children: ReactNode
}

export const WizardFlow: React.FC<WizardFlowProps> = ({
  title,
  steps,
  currentStep,
  onStepChange,
  onCancel,
  gradientTheme = 'purple',
  customGradient,
  children
}) => {
  // Gradient theme classes
  const gradientClasses = {
    purple: 'bg-gradient-to-br from-purple-50 to-pink-50',
    blue: 'bg-gradient-to-br from-blue-50 to-indigo-50',
    custom: customGradient || 'bg-gradient-to-br from-gray-50 to-white'
  }

  const selectedGradient = gradientClasses[gradientTheme]

  // Handle ESC key to close wizard
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.code === 'Escape') {
        onCancel()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [onCancel])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="wizard-title"
      className={`min-h-screen p-4 sm:p-6 ${selectedGradient}`}
    >
      <div className="max-w-4xl mx-auto">
        {/* Header with title and close button */}
        <div className="flex items-center justify-between mb-8">
          <h1
            id="wizard-title"
            className="text-3xl font-bold text-gray-900"
          >
            {title}
          </h1>

          <button
            type="button"
            onClick={onCancel}
            aria-label="Close wizard"
            className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-white/50 transition-colors duration-150"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Step Indicator */}
        <div className="mb-8">
          <WizardStepIndicator
            steps={steps}
            currentStep={currentStep}
            onStepClick={onStepChange}
          />
        </div>

        {/* Content Area */}
        <div className="bg-white rounded-2xl shadow-xl border border-gray-200 p-8 min-h-[600px]">
          {children}
        </div>
      </div>
    </div>
  )
}
