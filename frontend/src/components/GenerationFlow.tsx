import { useState, useEffect, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import {
  Zap,
  FileText,
  CheckCircle,
  AlertCircle,
  Check,
  ArrowLeft,
  ArrowRight,
  Sparkles,
  Target,
  Loader2,
  Brain,
  ExternalLink,
} from 'lucide-react'
import { useArtifacts } from '@/hooks/useArtifacts'
import { useGeneration } from '@/hooks/useGeneration'
import { useGenerationStatus } from '@/hooks/useGenerationStatus'
import { cn } from '@/utils/cn'
import { WizardStepIndicator, WizardStep } from '@/components/ui/WizardStepIndicator'
import { CancelConfirmationDialog } from '@/components/ui/CancelConfirmationDialog'
import { useWizardProgress } from '@/hooks/useWizardProgress'

const generationSchema = z.object({
  jobDescription: z.string().min(50, 'Job description must be at least 50 characters'),
  companyName: z.string().min(1, 'Company name is required'),
  roleTitle: z.string().min(1, 'Role title is required'),
  labelIds: z.array(z.number()).default([]),
})

type GenerationForm = z.infer<typeof generationSchema>

interface GenerationFlowProps {
  onClose?: () => void
}

export default function GenerationFlow({ onClose }: GenerationFlowProps) {
  const [step, setStep] = useState(1)
  const [selectedArtifacts, setSelectedArtifacts] = useState<number[]>([])
  const [currentGeneration, setCurrentGeneration] = useState<string | null>(null)
  const [showCancelDialog, setShowCancelDialog] = useState(false)
  const navigate = useNavigate()

  // Wizard steps configuration (3 steps: Job Analysis → Artifacts → Generate)
  const wizardSteps: WizardStep[] = [
    { id: 'job-analysis', label: 'Job Analysis', icon: Target },
    { id: 'select-artifacts', label: 'Select Artifacts', icon: FileText },
    { id: 'generate', label: 'Generate', icon: Zap },
  ]

  const { artifacts, loadArtifacts } = useArtifacts()
  const { createGeneration, activeGenerations } = useGeneration()

  // Get current generation from store to check status
  const storeGeneration = activeGenerations.find(g => g.id === currentGeneration)
  const shouldPoll = !!currentGeneration &&
                     step === 3 &&
                     storeGeneration?.status !== undefined &&
                     !['completed', 'failed', 'bullets_ready'].includes(storeGeneration.status)

  // Poll generation status when active (consolidated pattern)
  const { status: generationStatus } = useGenerationStatus({
    generationId: currentGeneration || '',
    enabled: shouldPoll,
    pollingInterval: 10000,
    onComplete: () => {
      // Generation complete - status will be reflected in activeGenerations
    },
    onError: (error) => {
      console.error('Generation status polling error:', error)
    }
  })

  const formMethods = useForm<GenerationForm>({
    resolver: zodResolver(generationSchema),
    mode: 'onChange',
  })

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = formMethods

  const formData = watch()

  // Wizard progress tracking (3 steps)
  const wizardProgress = useWizardProgress(3, formMethods as any)

  // Load artifacts on component mount
  useEffect(() => {
    loadArtifacts()
  }, []) // loadArtifacts is stable from Zustand, so we don't need it in dependencies

  const onSubmit = async (data: GenerationForm) => {
    console.log('Form submission triggered with data:', data)
    console.log('Selected artifacts:', selectedArtifacts)

    try {
      const requestData = {
        ...data,
        artifactIds: selectedArtifacts,
      }
      console.log('Sending request to createGeneration:', requestData)

      const generationId = await createGeneration(requestData)
      console.log('Generation started with ID:', generationId)

      // Store generation ID and move to step 3
      setCurrentGeneration(generationId)
      wizardProgress.markStepCompleted(2)
      setStep(3)
    } catch (error) {
      console.error('Generation failed:', error)
      // Show more detailed error information
      if (error instanceof Error) {
        console.error('Error message:', error.message)
        console.error('Error stack:', error.stack)
      }
    }
  }

  const analyzeJobDescription = async () => {
    // Move to artifact selection step
    wizardProgress.markStepCompleted(1)
    setStep(2)
  }

  // Handle close: show cancel confirmation if form touched
  const handleClose = useCallback(() => {
    if (wizardProgress.isFormTouched || step > 1) {
      setShowCancelDialog(true)
    } else {
      onClose?.()
    }
  }, [onClose, wizardProgress.isFormTouched, step])

  // Handle confirmed cancellation
  const handleConfirmCancel = useCallback(() => {
    setShowCancelDialog(false)
    onClose?.()
  }, [onClose])

  // Handle step indicator clicks - only allow navigation to previous steps
  const handleStepClick = useCallback((stepNum: number) => {
    if (stepNum < step) {
      setStep(stepNum)
    }
  }, [step])

  const renderJobDescriptionStep = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
          <Target className="h-5 w-5 text-blue-600" />
          Job Analysis
        </h2>
        <p className="text-base text-gray-500">
          Tell us about the position you're applying for
        </p>
      </div>

      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="block text-base font-semibold text-gray-800 mb-2">
              Company Name <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                {...register('companyName')}
                type="text"
                className={cn(
                  'w-full px-4 py-3 border-2 rounded-xl text-base font-medium transition-all duration-200 placeholder:text-gray-400',
                  'focus:ring-4 focus:ring-blue-100 focus:border-blue-500 focus:outline-none',
                  errors.companyName ? 'border-red-300' : 'border-gray-200'
                )}
                placeholder="e.g., Google, Meta, Apple"
              />
              {errors.companyName && (
                <p className="mt-2 text-base text-red-600 flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  {errors.companyName.message}
                </p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-base font-semibold text-gray-800 mb-2">
              Role Title <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                {...register('roleTitle')}
                type="text"
                className={cn(
                  'w-full px-4 py-3 border-2 rounded-xl text-base font-medium transition-all duration-200 placeholder:text-gray-400',
                  'focus:ring-4 focus:ring-blue-100 focus:border-blue-500 focus:outline-none',
                  errors.roleTitle ? 'border-red-300' : 'border-gray-200'
                )}
                placeholder="e.g., Senior Software Engineer"
              />
              {errors.roleTitle && (
                <p className="mt-2 text-base text-red-600 flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  {errors.roleTitle.message}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <label className="block text-base font-semibold text-gray-800 mb-2">
            Job Description <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <textarea
              {...register('jobDescription')}
              rows={12}
              className={cn(
                'w-full px-4 py-4 border-2 rounded-xl text-base font-medium transition-all duration-200 resize-none placeholder:text-gray-400',
                'focus:ring-4 focus:ring-blue-100 focus:border-blue-500 focus:outline-none',
                errors.jobDescription ? 'border-red-300' : 'border-gray-200'
              )}
              placeholder="Paste the complete job description here...

Tip: Include requirements, responsibilities, and preferred qualifications for best matching results."
            />
            <div className="absolute bottom-3 right-3 text-sm text-gray-500">
              {formData.jobDescription?.length || 0} characters
            </div>
            {errors.jobDescription && (
              <p className="mt-2 text-base text-red-600 flex items-center gap-1">
                <AlertCircle className="h-4 w-4" />
                {errors.jobDescription.message}
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between pt-8 mt-8 border-t-2 border-gray-100">
        <div></div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleClose}
            className="px-6 py-3 text-gray-700 font-semibold rounded-xl hover:bg-gray-100 transition-all duration-200"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={analyzeJobDescription}
            disabled={!formData.jobDescription || !formData.companyName || !formData.roleTitle}
            className="px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-xl transition-all duration-200 transform hover:scale-105 disabled:opacity-50 disabled:transform-none flex items-center gap-2 shadow-lg disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed disabled:shadow-md"
          >
            Next
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )

  const renderArtifactSelectionStep = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
          <FileText className="h-5 w-5 text-blue-600" />
          Select Artifacts
        </h2>
        <p className="text-base text-gray-500">
          Choose the artifacts you want to include in your CV
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {artifacts.map((artifact: any) => (
          <div
            key={artifact.id}
            className={cn(
              'group relative overflow-hidden border-2 rounded-2xl p-6 cursor-pointer transition-all duration-300 transform hover:scale-102 hover:shadow-lg',
              selectedArtifacts.includes(artifact.id)
                ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-indigo-50 shadow-lg scale-102'
                : 'border-gray-200 hover:border-gray-300 bg-white hover:bg-gray-50'
            )}
            onClick={() => {
              setSelectedArtifacts(prev =>
                prev.includes(artifact.id)
                  ? prev.filter(id => id !== artifact.id)
                  : [...prev, artifact.id]
              )
            }}
          >
            {/* Background decoration */}
            <div className={cn(
              "absolute top-0 right-0 w-24 h-24 rounded-full -translate-y-12 translate-x-12 transition-all duration-500",
              selectedArtifacts.includes(artifact.id)
                ? "bg-gradient-to-br from-blue-400/10 to-indigo-400/10 scale-150"
                : "bg-gradient-to-br from-gray-400/5 to-gray-400/5 group-hover:scale-125"
            )} />

            <div className="relative flex items-start space-x-4">
              <div className="relative mt-1">
                <input
                  type="checkbox"
                  checked={selectedArtifacts.includes(artifact.id)}
                  onChange={() => {}} // Controlled by click handler
                  className="h-5 w-5 text-blue-600 focus:ring-blue-500 border-2 border-gray-300 rounded-lg transition-all duration-200"
                />
                {selectedArtifacts.includes(artifact.id) && (
                  <div className="absolute inset-0 bg-blue-500 rounded-lg flex items-center justify-center">
                    <CheckCircle className="h-3 w-3 text-white" />
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-xl flex items-center justify-center shadow-md flex-shrink-0">
                      <FileText className="h-4 w-4 text-white" />
                    </div>
                    <h3 className="font-bold text-gray-900 truncate text-base">{artifact.title}</h3>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mb-4 leading-relaxed line-clamp-2">{artifact.description}</p>
                <div className="flex flex-wrap gap-2">
                  {artifact.technologies.slice(0, 4).map((tech: string) => (
                    <span
                      key={tech}
                      className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-xs font-medium text-gray-700 rounded-full transition-colors duration-200"
                    >
                      {tech}
                    </span>
                  ))}
                  {artifact.technologies.length > 4 && (
                    <span className="px-3 py-1.5 bg-gray-200 text-xs font-medium text-gray-600 rounded-full">
                      +{artifact.technologies.length - 4} more
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between pt-8 mt-8 border-t-2 border-gray-100">
        <div>
          <button
            type="button"
            onClick={() => setStep(1)}
            className="px-6 py-3 text-gray-700 font-semibold rounded-xl hover:bg-gray-100 transition-all duration-200 flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleClose}
            className="px-6 py-3 text-gray-700 font-semibold rounded-xl hover:bg-gray-100 transition-all duration-200"
          >
            Cancel
          </button>

          <button
            type="submit"
            disabled={selectedArtifacts.length === 0}
            className="px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold rounded-xl transition-all duration-200 transform hover:scale-105 disabled:opacity-50 disabled:transform-none flex items-center gap-2 shadow-lg disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed disabled:shadow-md"
          >
            <Check className="h-4 w-4" />
            Generate Bullets
          </button>
        </div>
      </div>
    </div>
  )

  const renderGenerationStep = () => {
    // Use status from polling hook if available, fallback to store (storeGeneration defined above)
    const status = generationStatus?.status || storeGeneration?.status
    const progressPercentage = generationStatus?.progress_percentage || storeGeneration?.progressPercentage || 0

    const isGenerating = status === 'pending' || status === 'processing'
    const isBulletsReady = status === 'bullets_ready'
    const isCompleted = status === 'completed'
    const isFailed = status === 'failed'

    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-blue-600" />
            {isGenerating ? 'Generating Your Bullets' :
             isBulletsReady || isCompleted ? 'Bullets Ready!' :
             isFailed ? 'Generation Failed' :
             'Starting Generation'}
          </h2>
          <p className="text-base text-gray-500">
            {isGenerating
              ? 'AI is analyzing your artifacts and creating tailored bullet points...'
              : isBulletsReady || isCompleted
              ? 'Your bullet points have been generated successfully!'
              : isFailed
              ? 'Something went wrong during generation.'
              : 'Initializing...'}
          </p>
        </div>

        {/* Loading State */}
        {isGenerating && (
          <div className="text-center py-16 relative">
            {/* Background animation */}
            <div className="absolute inset-0 overflow-hidden">
              <div className="absolute top-1/4 left-1/4 w-32 h-32 bg-blue-400/5 rounded-full animate-pulse" />
              <div className="absolute top-3/4 right-1/4 w-24 h-24 bg-purple-400/5 rounded-full animate-pulse animation-delay-1000" />
              <div className="absolute top-1/2 left-1/2 w-40 h-40 bg-indigo-400/5 rounded-full animate-pulse animation-delay-2000" />
            </div>

            <div className="relative">
              <div className="inline-flex items-center gap-4 mb-8">
                <div className="relative">
                  <Loader2 className="h-12 w-12 text-blue-600 animate-spin" />
                  <div className="absolute inset-0 h-12 w-12 border-4 border-blue-200 rounded-full animate-ping" />
                </div>
                <div className="text-left">
                  <div className="text-xl font-bold text-gray-900">Generating Bullet Points</div>
                  <div className="text-sm text-gray-500">AI is working its magic...</div>
                </div>
              </div>

              <div className="w-full max-w-lg mx-auto">
                <div className="bg-gradient-to-r from-gray-200 to-gray-300 rounded-full h-4 mb-4 shadow-inner overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 h-full rounded-full transition-all duration-700 ease-out shadow-sm relative"
                    style={{ width: `${progressPercentage}%` }}
                  >
                    <div className="absolute inset-0 bg-white/20 rounded-full" />
                    <div className="absolute right-1 top-1/2 transform -translate-y-1/2 w-2 h-2 bg-white rounded-full shadow-sm" />
                  </div>
                </div>

                <div className="flex justify-between items-center text-sm">
                  <span className="font-bold text-gray-700">{progressPercentage}% Complete</span>
                  <span className="text-gray-500">This usually takes 30-60 seconds</span>
                </div>
              </div>

              <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-4xl mx-auto">
                {[
                  { icon: Brain, text: 'Analyzing job requirements', delay: '0ms' },
                  { icon: Target, text: 'Matching relevant artifacts', delay: '200ms' },
                  { icon: Sparkles, text: 'Generating content', delay: '400ms' },
                  { icon: CheckCircle, text: 'Optimizing for ATS', delay: '600ms' }
                ].map((item) => (
                  <div
                    key={item.text}
                    className="flex flex-col items-center gap-3 p-4 bg-white/60 rounded-2xl border border-gray-200 backdrop-blur-sm"
                    style={{ animationDelay: item.delay }}
                  >
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-2xl flex items-center justify-center shadow-lg">
                      <item.icon className="h-6 w-6 text-white" />
                    </div>
                    <div className="text-xs font-semibold text-gray-700 text-center leading-tight">
                      {item.text}
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-8 text-sm text-gray-500">
                <p className="font-medium mb-2">What happens next?</p>
                <p>Once generation completes, you'll be able to view and manage your bullets in detail.</p>
              </div>
            </div>
          </div>
        )}

        {/* Success State - Bullets Ready */}
        {(isBulletsReady || isCompleted) && (
          <div className="space-y-6">
            <div className="bg-green-50 border-2 border-green-200 rounded-2xl p-8 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="text-2xl font-bold text-green-900 mb-2">Bullets Generated Successfully!</h3>
              <p className="text-green-700 mb-6">
                Your tailored bullet points are ready for review and customization.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto mb-6">
                <div className="bg-white/70 rounded-xl p-4 border border-green-200">
                  <div className="text-3xl font-bold text-green-600">{selectedArtifacts.length}</div>
                  <div className="text-sm text-gray-600">Artifacts Used</div>
                </div>
                <div className="bg-white/70 rounded-xl p-4 border border-green-200">
                  <div className="text-3xl font-bold text-blue-600">~12</div>
                  <div className="text-sm text-gray-600">Bullets Created</div>
                </div>
                <div className="bg-white/70 rounded-xl p-4 border border-green-200">
                  <div className="text-3xl font-bold text-purple-600">100%</div>
                  <div className="text-sm text-gray-600">Job Match</div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => navigate(`/generations/${currentGeneration}`)}
                className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-xl transition-all duration-200 transform hover:scale-105 shadow-lg"
              >
                <ExternalLink className="h-5 w-5" />
                View Full Details & Manage Bullets
              </button>

              <p className="text-sm text-gray-500 mt-4">
                Review, edit, approve, or regenerate your bullets on the detail page.
              </p>
            </div>
          </div>
        )}

        {/* Failed State */}
        {isFailed && (
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
              <AlertCircle className="h-8 w-8 text-red-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Generation Failed</h3>
            <p className="text-gray-600 mb-6">
              Something went wrong during generation. Please try again.
            </p>
            <button
              type="button"
              onClick={() => {
                setCurrentGeneration(null)
                setStep(1)
              }}
              className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-all duration-200"
            >
              Start Over
            </button>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex items-center justify-between pt-8 mt-8 border-t-2 border-gray-100">
          <div>
            {!isBulletsReady && !isCompleted && !isFailed && (
              <button
                type="button"
                onClick={handleClose}
                disabled={isGenerating}
                className="px-6 py-3 text-gray-700 font-semibold rounded-xl hover:bg-gray-100 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Close button removed when bullets are successfully generated */}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-br from-blue-50/30 to-indigo-50/30 min-h-full">
      {/* Header */}
      <div className="max-w-6xl mx-auto px-6 pt-6 pb-3">
        <div className="mb-2">
          <h1 className="text-3xl lg:text-4xl font-extrabold bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-600 bg-clip-text text-transparent mb-1.5 leading-tight">
            Generate Tailored CV
          </h1>
          <p className="text-base lg:text-lg text-gray-700">
            Transform job descriptions into perfect resumes using AI and your professional artifacts.
          </p>
        </div>
      </div>

      {/* Step Indicator - Full Width Sticky */}
      <div className="sticky top-0 z-40 bg-gradient-to-br from-blue-50/30 to-indigo-50/30 border-b border-blue-100/30">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <WizardStepIndicator
            steps={wizardSteps}
            currentStep={step}
            onStepClick={handleStepClick}
            colorScheme="blue"
          />
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 mt-4">
        {/* Form */}
        <div className="relative bg-white rounded-2xl shadow-2xl border-2 border-gray-100 p-8 mb-6">
          {/* AI-Powered Corner Ribbon */}
          <div className="absolute top-0 right-0 w-40 h-40 overflow-hidden pointer-events-none">
            <div className="absolute transform rotate-45 bg-gradient-to-br from-blue-600 to-indigo-600 text-white text-center font-bold shadow-lg top-10 -right-10 w-48 py-2">
              <div className="flex items-center justify-center gap-1">
                <Sparkles className="h-3 w-3" />
                <span className="text-xs">AI-Powered</span>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit(onSubmit)}>
            {step === 1 && renderJobDescriptionStep()}
            {step === 2 && renderArtifactSelectionStep()}
            {step === 3 && renderGenerationStep()}
          </form>
        </div>
      </div>

      {/* Cancel Confirmation Dialog */}
      <CancelConfirmationDialog
        isOpen={showCancelDialog}
        progress={{
          currentStep: step,
          touchedSteps: wizardProgress.progress.touchedSteps,
          completedSteps: wizardProgress.progress.completedSteps,
          formData: wizardProgress.progress.formData
        }}
        onConfirm={handleConfirmCancel}
        onCancel={() => setShowCancelDialog(false)}
      />
    </div>
  )
}