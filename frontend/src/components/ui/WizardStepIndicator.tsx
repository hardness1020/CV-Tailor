import React from 'react'
import { LucideIcon, Check } from 'lucide-react'

export interface WizardStep {
  id: string
  label: string
  icon: LucideIcon
  isOptional?: boolean
}

export interface WizardStepIndicatorProps {
  steps: WizardStep[]
  currentStep: number
  onStepClick?: (step: number) => void
  colorScheme?: 'purple' | 'blue'
}

export const WizardStepIndicator: React.FC<WizardStepIndicatorProps> = ({
  steps,
  currentStep,
  onStepClick,
  colorScheme = 'purple'
}) => {
  // Handle edge case: empty steps array
  if (!steps || steps.length === 0) {
    return null
  }

  const handleStepClick = (stepNumber: number) => {
    // Don't allow clicking the current step
    if (stepNumber === currentStep) {
      return
    }

    // Only allow clicking if onStepClick is provided
    if (onStepClick) {
      onStepClick(stepNumber)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent, stepNumber: number) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleStepClick(stepNumber)
    } else if (e.key === 'ArrowRight') {
      e.preventDefault()
      const nextStep = Math.min(stepNumber + 1, steps.length)
      const nextButton = document.querySelector(
        `[aria-label="Step ${nextStep}: ${steps[nextStep - 1]?.label}"]`
      ) as HTMLElement
      nextButton?.focus()
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault()
      const prevStep = Math.max(stepNumber - 1, 1)
      const prevButton = document.querySelector(
        `[aria-label="Step ${prevStep}: ${steps[prevStep - 1]?.label}"]`
      ) as HTMLElement
      prevButton?.focus()
    }
  }

  return (
    <div className="relative">
      {/* Background progress bar */}
      <div className="absolute top-6 left-0 right-0 h-1 bg-gray-200 rounded-full" />

      {/* Animated filled progress bar */}
      <div
        className={`absolute top-6 left-0 h-1 rounded-full transition-all duration-500 ease-out ${
          colorScheme === 'blue'
            ? 'bg-gradient-to-r from-blue-600 to-indigo-600'
            : 'bg-gradient-to-r from-purple-600 to-pink-600'
        }`}
        style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
      />

      {/* Step items */}
      <div className="flex justify-between relative">
        {steps.map((step, index) => {
          const stepNumber = index + 1
          const isActive = stepNumber === currentStep
          const isCompleted = stepNumber < currentStep
          const isPending = stepNumber > currentStep
          const isClickable = onStepClick && !isActive

          return (
            <div key={step.id} className="flex flex-col items-center z-10">
              {/* Number badge instead of icon circle */}
              <button
                type="button"
                role="tab"
                aria-label={`Step ${stepNumber}: ${step.label}`}
                aria-current={isActive ? 'step' : undefined}
                aria-disabled={!isClickable}
                onClick={() => handleStepClick(stepNumber)}
                onKeyDown={(e) => handleKeyDown(e, stepNumber)}
                disabled={!isClickable}
                className={`
                  w-12 h-12 rounded-full flex items-center justify-center
                  font-bold text-lg transition-all duration-300 ease-out
                  ${isActive ? (colorScheme === 'blue'
                    ? 'bg-gradient-to-br from-blue-600 to-indigo-600 text-white scale-110 shadow-xl ring-4 ring-blue-100'
                    : 'bg-gradient-to-br from-purple-600 to-pink-600 text-white scale-110 shadow-xl ring-4 ring-purple-100') : ''}
                  ${isCompleted ? 'bg-white border-2 border-emerald-500 text-emerald-600 shadow-md' : ''}
                  ${isPending ? 'bg-white border-2 border-gray-300 text-gray-400' : ''}
                  ${isClickable ? 'hover:scale-105 hover:shadow-lg cursor-pointer' : ''}
                  ${isActive ? 'cursor-default' : ''}
                  ${!isClickable ? 'cursor-not-allowed' : ''}
                `}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5 stroke-[3]" />
                ) : (
                  stepNumber
                )}

                {/* Optional badge */}
                {step.isOptional && (
                  <span className="absolute -top-1 -right-1 text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full font-medium">
                    Opt
                  </span>
                )}
              </button>

              {/* Label */}
              <span
                className={`
                  mt-3 text-sm font-semibold text-center transition-colors duration-200
                  ${isActive ? (colorScheme === 'blue' ? 'text-blue-700' : 'text-purple-700') : ''}
                  ${isCompleted ? 'text-emerald-600' : ''}
                  ${isPending ? 'text-gray-500' : ''}
                `}
              >
                {step.label}
                {step.isOptional && (
                  <span className="text-xs text-gray-400 ml-1">(Optional)</span>
                )}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Add checkmark animation to global styles (or include in component with <style jsx>)
// This is handled via Tailwind's animate-[checkmark_...] syntax above
