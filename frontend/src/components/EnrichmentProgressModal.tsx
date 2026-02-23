import React from 'react'
import { Loader2, CheckCircle, AlertCircle, Sparkles } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { cn } from '@/utils/cn'

export interface EnrichmentStep {
  id: string
  label: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  message?: string
}

export interface EnrichmentProgressModalProps {
  isOpen: boolean
  onClose?: () => void
  steps?: EnrichmentStep[]
  currentStep?: string
  progress?: number // 0-100
  canCancel?: boolean
  onCancel?: () => void
}

const defaultSteps: EnrichmentStep[] = [
  {
    id: 'load-evidence',
    label: 'Loading Evidence',
    status: 'pending',
    message: 'Fetching evidence sources and documents...',
  },
  {
    id: 'extract-content',
    label: 'Extracting Content',
    status: 'pending',
    message: 'Processing evidence content with AI...',
  },
  {
    id: 'analyze',
    label: 'Analyzing',
    status: 'pending',
    message: 'Analyzing technologies and achievements...',
  },
  {
    id: 'generate',
    label: 'Generating Description',
    status: 'pending',
    message: 'Creating enhanced description...',
  },
  {
    id: 'finalize',
    label: 'Finalizing',
    status: 'pending',
    message: 'Saving enriched content...',
  },
]

const StepIcon: React.FC<{ status: EnrichmentStep['status'] }> = ({ status }) => {
  switch (status) {
    case 'processing':
      return <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
    case 'completed':
      return <CheckCircle className="h-5 w-5 text-green-600" />
    case 'error':
      return <AlertCircle className="h-5 w-5 text-red-600" />
    default:
      return <div className="h-5 w-5 rounded-full border-2 border-gray-300" />
  }
}

export const EnrichmentProgressModal: React.FC<EnrichmentProgressModalProps> = ({
  isOpen,
  onClose,
  steps = defaultSteps,
  currentStep,
  progress,
  canCancel = false,
  onCancel,
}) => {
  // Calculate overall progress if not provided
  const calculatedProgress =
    progress !== undefined
      ? progress
      : Math.round(
          (steps.filter((s) => s.status === 'completed').length / steps.length) * 100
        )

  // Determine if enrichment is complete
  const isComplete = steps.every((s) => s.status === 'completed')
  const hasError = steps.some((s) => s.status === 'error')

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose && isComplete ? onClose : () => {}}
      title={
        isComplete
          ? 'Enrichment Complete'
          : hasError
          ? 'Enrichment Error'
          : 'Enriching Artifact'
      }
      size="lg"
    >
      <div className="p-6 space-y-6">
        {/* Header Icon */}
        <div className="flex justify-center">
          <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center">
            {isComplete ? (
              <CheckCircle className="h-8 w-8 text-green-600" />
            ) : hasError ? (
              <AlertCircle className="h-8 w-8 text-red-600" />
            ) : (
              <Sparkles className="h-8 w-8 text-blue-600 animate-pulse" />
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-gray-700">Overall Progress</span>
            <span className="font-semibold text-blue-600">{calculatedProgress}%</span>
          </div>
          <div className="w-full h-2.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-500 ease-out',
                isComplete
                  ? 'bg-green-600'
                  : hasError
                  ? 'bg-red-600'
                  : 'bg-blue-600'
              )}
              style={{ width: `${calculatedProgress}%` }}
            />
          </div>
        </div>

        {/* Steps List */}
        <div className="space-y-3">
          {steps.map((step, index) => {
            const isActive = step.id === currentStep || step.status === 'processing'

            return (
              <div
                key={step.id}
                className={cn(
                  'flex items-start gap-3 p-3 rounded-lg transition-all',
                  isActive && 'bg-blue-50 border border-blue-200',
                  step.status === 'completed' && 'bg-green-50 border border-green-200',
                  step.status === 'error' && 'bg-red-50 border border-red-200',
                  step.status === 'pending' && 'bg-gray-50 border border-gray-200'
                )}
              >
                {/* Step Icon */}
                <div className="flex-shrink-0 mt-0.5">
                  <StepIcon status={step.status} />
                </div>

                {/* Step Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p
                      className={cn(
                        'text-sm font-semibold',
                        isActive
                          ? 'text-blue-900'
                          : step.status === 'completed'
                          ? 'text-green-900'
                          : step.status === 'error'
                          ? 'text-red-900'
                          : 'text-gray-700'
                      )}
                    >
                      {step.label}
                    </p>
                    {isActive && (
                      <span className="inline-flex items-center px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded-full animate-pulse">
                        In Progress
                      </span>
                    )}
                  </div>
                  {step.message && (
                    <p
                      className={cn(
                        'text-xs',
                        isActive
                          ? 'text-blue-700'
                          : step.status === 'error'
                          ? 'text-red-700'
                          : 'text-gray-600'
                      )}
                    >
                      {step.message}
                    </p>
                  )}
                </div>

                {/* Connector Line */}
                {index < steps.length - 1 && (
                  <div className="absolute left-[34px] h-6 w-0.5 bg-gray-300 -bottom-3" />
                )}
              </div>
            )
          })}
        </div>

        {/* Status Message */}
        {isComplete && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-900">
              <strong>Success!</strong> Your artifact has been enriched with AI-generated
              content. Review the suggestions in the AI Suggestions tab.
            </p>
          </div>
        )}

        {hasError && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-900">
              <strong>Error:</strong> Something went wrong during enrichment. Please try
              again or contact support if the issue persists.
            </p>
          </div>
        )}

        {/* Actions */}
        {!isComplete && canCancel && onCancel && (
          <div className="flex justify-center pt-2">
            <button
              onClick={onCancel}
              className="text-sm text-gray-600 hover:text-gray-900 font-medium underline"
            >
              Cancel Enrichment
            </button>
          </div>
        )}
      </div>
    </Modal>
  )
}
