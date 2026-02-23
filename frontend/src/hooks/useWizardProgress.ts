import { useState, useCallback, useMemo } from 'react'
import { UseFormReturn } from 'react-hook-form'

export interface WizardProgressState {
  currentStep: number
  touchedSteps: Set<number>
  completedSteps: Set<number>
  formData: Record<string, any>
}

export interface UseWizardProgressReturn {
  progress: WizardProgressState
  isFormTouched: boolean
  completionPercentage: number
  markStepTouched: (step: number) => void
  markStepCompleted: (step: number) => void
  updateFormData: (stepData: Record<string, any>) => void
  reset: () => void
}

export const useWizardProgress = (
  totalSteps: number,
  formMethods?: UseFormReturn
): UseWizardProgressReturn => {
  const [progress, setProgress] = useState<WizardProgressState>({
    currentStep: 1,
    touchedSteps: new Set<number>(),
    completedSteps: new Set<number>(),
    formData: {}
  })

  // Computed: isFormTouched
  // Check formMethods.formState.isDirty first, then fall back to touchedSteps
  const isFormTouched = useMemo(() => {
    if (formMethods?.formState?.isDirty) {
      return true
    }
    return progress.touchedSteps.size > 0
  }, [formMethods?.formState?.isDirty, progress.touchedSteps.size])

  // Computed: completionPercentage
  const completionPercentage = useMemo(() => {
    if (totalSteps === 0) {
      return 0
    }
    return (progress.completedSteps.size / totalSteps) * 100
  }, [progress.completedSteps.size, totalSteps])

  // Method: markStepTouched
  const markStepTouched = useCallback((step: number) => {
    // Validate step number (ignore if invalid)
    if (step < 1) {
      console.warn(`useWizardProgress: Invalid step number ${step} (must be >= 1)`)
      return
    }

    setProgress(prev => {
      const newTouchedSteps = new Set(prev.touchedSteps)
      newTouchedSteps.add(step)

      return {
        ...prev,
        touchedSteps: newTouchedSteps
      }
    })
  }, [])

  // Method: markStepCompleted
  const markStepCompleted = useCallback((step: number) => {
    // Validate step number (ignore if invalid)
    if (step < 1 || step > totalSteps) {
      console.warn(
        `useWizardProgress: Invalid step number ${step} (must be 1-${totalSteps})`
      )
      return
    }

    setProgress(prev => {
      const newCompletedSteps = new Set(prev.completedSteps)
      newCompletedSteps.add(step)

      return {
        ...prev,
        completedSteps: newCompletedSteps
      }
    })
  }, [totalSteps])

  // Method: updateFormData
  const updateFormData = useCallback((stepData: Record<string, any>) => {
    setProgress(prev => ({
      ...prev,
      formData: {
        ...prev.formData,
        ...stepData
      }
    }))
  }, [])

  // Method: reset
  const reset = useCallback(() => {
    setProgress({
      currentStep: 1,
      touchedSteps: new Set<number>(),
      completedSteps: new Set<number>(),
      formData: {}
    })
  }, [])

  return {
    progress,
    isFormTouched,
    completionPercentage,
    markStepTouched,
    markStepCompleted,
    updateFormData,
    reset
  }
}
