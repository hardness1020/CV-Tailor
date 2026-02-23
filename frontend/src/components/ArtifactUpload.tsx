import { useState, useCallback, useEffect, useRef, FormEvent } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import {
  Upload,
  X,
  Plus,
  FileText,
  Github,
  Loader2,
  ArrowLeft,
  ArrowRight,
  Check,
  Sparkles,
  Calendar,
  Paperclip,
  Eye,
  CheckCircle,
  AlertCircle,
  XCircle,
  Star
} from 'lucide-react'
import { useArtifactStore } from '@/stores/artifactStore'
import { useEnrichmentStore } from '@/stores/enrichmentStore'
import { apiClient } from '@/services/apiClient'
import { cn } from '@/utils/cn'
import { formatDateRange } from '@/utils/formatters'
import { WizardStepIndicator, WizardStep } from '@/components/ui/WizardStepIndicator'
import { CancelConfirmationDialog } from '@/components/ui/CancelConfirmationDialog'
import { useWizardProgress } from '@/hooks/useWizardProgress'
import { ConsolidatedProcessingStep } from '@/components/wizard/ConsolidatedProcessingStep'
import { ConsolidatedReunificationStep } from '@/components/wizard/ConsolidatedReunificationStep'
import { useArtifactNavigation } from '@/hooks/useArtifactNavigation'

// GitHub-specific link schema (no type selector needed)
const githubLinkSchema = z.object({
  url: z.string()
    .url('Please enter a valid URL')
    .refine(
      (url) => url.includes('github.com'),
      { message: 'Must be a GitHub repository URL (https://github.com/...)' }
    ),
  description: z.string().optional(), // Description is optional
})

const artifactSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().optional(), // OPTIONAL (ft-018) - AI will enhance this using evidence
  userContext: z.string().max(1000, 'Context cannot exceed 1000 characters').optional(), // NEW (ft-018)
  startDate: z.string().min(1, 'Start date is required'),
  endDate: z.string().optional(),
  // technologies removed - auto-extracted from evidence only (6-step wizard consolidation)
  githubLinks: z.array(githubLinkSchema), // Renamed from evidenceLinks
  labelIds: z.array(z.number()),
})

type ArtifactForm = z.infer<typeof artifactSchema>

interface ArtifactUploadProps {
  onUploadComplete?: (artifact: any) => void
  onClose?: () => void
}

const TOTAL_STEPS = 6 // 6-step wizard: Basic Info (1), Context (2), Evidence (3), Confirmation (4), Processing & Review (5), Reunification & Acceptance (6)

const wizardSteps: WizardStep[] = [
  { id: 'basic', label: 'Basic Info', icon: FileText },           // Step 1
  { id: 'context', label: 'Your Context', icon: Star },           // Step 2
  { id: 'evidence', label: 'Evidence', icon: Paperclip },         // Step 3 (was 4)
  { id: 'review-confirmation', label: 'Confirm Details', icon: Eye },      // Step 4 (was 5)
  { id: 'processing-review', label: 'Evidence Review', icon: Loader2 },// Step 5 (consolidates old 6+7)
  { id: 'reunification-acceptance', label: 'Final Review', icon: Sparkles }, // Step 6 (consolidates old 8+9)
]

export default function ArtifactUpload({ onUploadComplete, onClose }: ArtifactUploadProps) {
  const navigate = useNavigate()
  const { artifactId: routeArtifactId } = useParams<{ artifactId?: string }>() // Resume capability: Get artifact ID from route
  const [searchParams] = useSearchParams() // ft-046: URL query parameters for re-enrich flow

  // ft-046: Support both route params (/artifacts/:id) and query params (?artifactId=X&startStep=Y)
  const queryArtifactId = searchParams.get('artifactId')
  const queryStartStep = searchParams.get('startStep')
  const artifactId = routeArtifactId || queryArtifactId || null

  const [currentStep, setCurrentStep] = useState(1)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [createdArtifactId, setCreatedArtifactId] = useState<string | null>(artifactId || null) // Track created artifact ID
  const [isLoadingExistingArtifact, setIsLoadingExistingArtifact] = useState(!!artifactId) // Show loading when resuming
  const hasResumed = useRef(false) // Guard to prevent double toast in React Strict Mode
  const { addArtifact } = useArtifactStore()
  const { setActiveEnrichment } = useEnrichmentStore()

  // Use navigation hook for artifact routing
  const { getResumeStep } = useArtifactNavigation()

  // Wizard progress tracking and cancel dialog
  const [showCancelDialog, setShowCancelDialog] = useState(false)

  // Evidence validation state (Layer 2 validation from ft-010)
  const [isValidating, setIsValidating] = useState(false)
  const [validationResults, setValidationResults] = useState<Record<number, {
    status: 'success' | 'warning' | 'error'
    message: string | null
    accessible: boolean
  }>>({})

  const formMethods = useForm<ArtifactForm>({
    resolver: zodResolver(artifactSchema),
    mode: 'onChange',
    defaultValues: {
      githubLinks: [],
      labelIds: [],
    },
  })

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
    trigger,
  } = formMethods

  // Wizard progress tracking (cast to untyped UseFormReturn to satisfy hook signature)
  const wizardProgress = useWizardProgress(TOTAL_STEPS, formMethods as any)

  // Handle close: use provided callback or navigate back
  const handleClose = useCallback(() => {
    // Check if user has unsaved changes
    if (wizardProgress.isFormTouched) {
      setShowCancelDialog(true)
    } else {
      if (onClose) {
        onClose()
      } else {
        navigate('/artifacts')
      }
    }
  }, [onClose, navigate, wizardProgress.isFormTouched])

  // Handle confirmed cancellation
  const handleConfirmCancel = useCallback(() => {
    setShowCancelDialog(false)
    if (onClose) {
      onClose()
    } else {
      navigate('/artifacts')
    }
  }, [onClose, navigate])

  // Resume capability: Load existing artifact data if artifactId is provided
  useEffect(() => {
    if (!artifactId) {
      // New upload session - reset state
      setCurrentStep(1)
      setUploadedFiles([])
      setIsLoadingExistingArtifact(false)
      hasResumed.current = false // Reset guard for new upload
      return
    }

    // Prevent double execution (React 18 Strict Mode + re-renders)
    if (hasResumed.current) {
      console.log('[ArtifactUpload] Already resumed, skipping duplicate load')
      return
    }

    // Mark as resumed immediately to prevent double execution
    hasResumed.current = true

    // Resume existing artifact
    const loadExistingArtifact = async () => {
      try {
        console.log(`[ArtifactUpload] Resuming artifact ${artifactId}`)
        setIsLoadingExistingArtifact(true)

        const artifact = await apiClient.getArtifact(parseInt(artifactId))

        // DEBUG: Log full artifact data
        console.log('[DEBUG] ========== ARTIFACT RESUME DEBUG ==========')
        console.log('[DEBUG] Full artifact object:', JSON.stringify(artifact, null, 2))
        console.log('[DEBUG] artifact.id:', artifact.id)
        console.log('[DEBUG] artifact.status:', artifact.status)
        console.log('[DEBUG] artifact.lastWizardStep:', artifact.lastWizardStep)
        console.log('[DEBUG] Type of lastWizardStep:', typeof artifact.lastWizardStep)

        // Pre-populate form with existing data
        setValue('title', artifact.title)
        setValue('description', artifact.description || '')
        setValue('userContext', artifact.userContext || '')
        setValue('startDate', artifact.startDate)
        setValue('endDate', artifact.endDate || '')
        // technologies removed - auto-extracted from evidence only
        setValue('githubLinks', artifact.evidenceLinks?.map(link => ({
          url: link.url,
          description: link.description || ''
        })) || [])

        // Determine which step to start at using centralized navigation logic
        const explicitStep = queryStartStep ? parseInt(queryStartStep) : undefined
        const resumeStep = getResumeStep(artifact, explicitStep)

        console.log('[DEBUG] Final resumeStep value:', resumeStep)
        console.log('[DEBUG] Type of resumeStep:', typeof resumeStep)
        console.log(`[ArtifactUpload] Resuming at step ${resumeStep} (status: ${artifact.status})`)

        // IMPORTANT: Set step BEFORE clearing loading state to prevent flash
        console.log('[DEBUG] About to call setCurrentStep with:', resumeStep)
        setCurrentStep(resumeStep)
        console.log('[DEBUG] Called setCurrentStep')
        setCreatedArtifactId(artifactId)
        console.log('[DEBUG] ========== END ARTIFACT RESUME DEBUG ==========')


        // Show toast after step is set
        toast.success('Resumed incomplete artifact')
      } catch (error: any) {
        console.error('[ArtifactUpload] Failed to load existing artifact:', error)
        toast.error('Failed to load artifact. Starting fresh.')
        // Fall back to new upload
        setCurrentStep(1)
        setCreatedArtifactId(null)
        hasResumed.current = false // Reset guard on error
      } finally {
        // Clear loading AFTER step is set
        setIsLoadingExistingArtifact(false)
      }
    }

    loadExistingArtifact()
  }, [artifactId, queryStartStep]) // ft-046: Added queryStartStep dependency

  // DEBUG: Monitor currentStep changes
  useEffect(() => {
    console.log('[DEBUG] 🔄 currentStep state changed to:', currentStep)
  }, [currentStep])

  const { fields: githubFields, append: appendGithubLink, remove: removeGithubLink } = useFieldArray({
    control,
    name: 'githubLinks',
  })

  // Reset validation state when GitHub links are removed
  useEffect(() => {
    // Clear validation results when links are removed
    setValidationResults({})
  }, [githubFields.length])

  // Track last_wizard_step for resume capability
  useEffect(() => {
    // Only track if artifact has been created
    if (!createdArtifactId) return

    const updateLastStep = async () => {
      try {
        await apiClient.updateArtifact(parseInt(createdArtifactId), {
          lastWizardStep: currentStep
        })
        console.log(`[ArtifactUpload] Updated lastWizardStep to ${currentStep}`)
      } catch (error) {
        console.error('[ArtifactUpload] Failed to update lastWizardStep:', error)
      }
    }

    // Update step on change
    updateLastStep()

    // Add beforeunload handler to save step when user tries to leave
    const handleBeforeUnload = () => {
      // Save step synchronously using sendBeacon with proper Content-Type
      const blob = new Blob(
        [JSON.stringify({ lastWizardStep: currentStep })],
        { type: 'application/json' }
      )
      navigator.sendBeacon(
        `/api/v1/artifacts/${createdArtifactId}/`,
        blob
      )
    }

    window.addEventListener('beforeunload', handleBeforeUnload)

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [currentStep, createdArtifactId])

  const title = watch('title')
  const userContext = watch('userContext')
  const startDate = watch('startDate')
  const endDate = watch('endDate')

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.filter(file => {
      if (file.size > 10 * 1024 * 1024) {
        toast.error(`File ${file.name} is too large. Maximum size is 10MB.`)
        return false
      }

      const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
      if (!allowedTypes.includes(file.type)) {
        toast.error(`File ${file.name} is not supported. Please upload PDF or Word documents.`)
        return false
      }

      return true
    })

    setUploadedFiles(prev => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    multiple: true,
    maxFiles: 10,
  })

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleNext = async () => {
    let isValid = false

    // Validate current step fields (6-step wizard)
    if (currentStep === 1) {
      // Step 1: Basic Information (title, startDate, endDate)
      isValid = await trigger(['title', 'startDate', 'endDate'])
    } else if (currentStep === 2) {
      // Step 2: Your Context (userContext is optional, always allow progression)
      isValid = true
    } else if (currentStep === 3) {
      // Step 3: Evidence & Sources - validate before proceeding to confirmation
      isValid = await trigger(['githubLinks'])

      // Check if all GitHub links are validated
      const links = watch('githubLinks')
      if (links.length > 0) {
        const allValidated = links.every((_, index) => validationResults[index])
        if (!allValidated) {
          toast.error('Please validate all GitHub links before proceeding')
          return
        }

        // Check if any have validation errors
        const hasErrors = links.some((_, index) => validationResults[index]?.status === 'error')
        if (hasErrors) {
          toast.error('Please fix GitHub link errors before proceeding')
          return
        }
      }

      // v1.2.0: Require at least 1 evidence source
      const hasGithubLinks = links.length > 0
      const hasUploadedFiles = uploadedFiles.length > 0

      if (!hasGithubLinks && !hasUploadedFiles) {
        toast.error('Please add at least one evidence source (GitHub repository or file) before proceeding')
        return
      }
    } else if (currentStep === 4) {
      // Step 4: Confirmation - CREATE or UPDATE ARTIFACT and trigger enrichment
      setIsSubmitting(true)
      try {
        const data = watch()
        const artifactData = {
          title: data.title,
          description: data.description,
          user_context: data.userContext || undefined,
          start_date: data.startDate,
          end_date: data.endDate || undefined,
          // technologies removed - auto-extracted from evidence only
          evidence_links: data.githubLinks.map(link => ({
            url: link.url,
            evidence_type: 'github',
            description: link.description || '',
          })),
          labelIds: data.labelIds || [],
        }

        let artifact
        // ft-046: If we have createdArtifactId, we're updating an existing artifact (re-enrich flow)
        if (createdArtifactId) {
          artifact = await apiClient.updateArtifact(parseInt(createdArtifactId), artifactData)
          console.log('[ArtifactUpload] Artifact updated:', artifact.id)
        } else {
          // Creating new artifact
          artifact = await apiClient.createArtifact(artifactData)
          console.log('[ArtifactUpload] Artifact created:', artifact.id)
          setCreatedArtifactId(String(artifact.id))
          addArtifact(artifact)
        }

        if (uploadedFiles.length > 0) {
          await apiClient.uploadArtifactFiles(artifact.id, uploadedFiles)
          console.log('[ArtifactUpload] Files uploaded')
        }

        // Backend auto-triggers enrichment via Evidence post_save signal
        console.log('[ArtifactUpload] Enrichment auto-triggered by backend signal')

        isValid = true
      } catch (error) {
        console.error('Artifact create/update error:', error)
        toast.error(`Failed to ${createdArtifactId ? 'update' : 'create'} artifact. Please try again.`)
        setIsSubmitting(false)
        return
      } finally {
        setIsSubmitting(false)
      }
    } else if (currentStep === 5) {
      // Step 5: Processing & Evidence Review - handled by ConsolidatedProcessingStep (auto-advances)
      isValid = true
    } else if (currentStep === 6) {
      // Step 6: Reunification & Acceptance - handled by ConsolidatedReunificationStep (navigates to detail page)
      isValid = true
    }

    if (isValid) {
      // Mark current step as touched and completed
      wizardProgress.markStepTouched(currentStep)
      wizardProgress.markStepCompleted(currentStep)

      setCurrentStep(prev => {
        const nextStep = Math.min(prev + 1, TOTAL_STEPS)
        // Mark next step as touched
        wizardProgress.markStepTouched(nextStep)
        return nextStep
      })
    }
  }

  const handleBack = () => {
    setCurrentStep(prev => {
      const prevStep = Math.max(prev - 1, 1)
      // Mark previous step as touched when returning
      wizardProgress.markStepTouched(prevStep)
      return prevStep
    })
  }

  const onSubmit = async (_data: ArtifactForm) => {
    // ft-045: Artifact already created at Step 4, evidence reviewed and finalized at Step 6
    // Step 7 is just final review before navigating away
    console.log('[ArtifactUpload] Final submit - artifact already created and finalized')

    if (!createdArtifactId) {
      toast.error('No artifact created - please go back and complete all steps')
      return
    }

    setIsSubmitting(true)
    try {
      // Set active enrichment to show on artifacts page (optional - artifact already enriched)
      setActiveEnrichment(parseInt(createdArtifactId))

      // Notify parent and navigate back to artifacts page
      onUploadComplete?.({ id: parseInt(createdArtifactId) })
      navigate('/artifacts')
    } catch (error) {
      console.error('Navigation error:', error)
      toast.error('Failed to complete submission.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleFormSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()

    // Only allow actual submission on step 7 (final review page) (ft-045)
    if (currentStep < TOTAL_STEPS) {
      // On earlier steps, pressing Enter should just go to next step
      handleNext()
      return
    }

    // On step 7, proceed with actual form submission (navigate away)
    handleSubmit(onSubmit)(e)
  }

  // Show loading UI while fetching existing artifact for resume
  if (isLoadingExistingArtifact) {
    return (
      <div className="bg-gradient-to-br from-purple-50/30 to-pink-50/30 min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 text-purple-600 animate-spin mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Loading Artifact...</h2>
          <p className="text-gray-600">Resuming your work in progress</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-br from-purple-50/30 to-pink-50/30 min-h-full">
      {/* Header */}
      <div className="max-w-6xl mx-auto px-6 pt-6 pb-3">
        <div className="mb-2">
          <h1 className="text-3xl lg:text-4xl font-extrabold bg-gradient-to-r from-purple-600 via-pink-600 to-purple-600 bg-clip-text text-transparent mb-1.5 leading-tight">
            Upload New Artifact
          </h1>
          <p className="text-base lg:text-lg text-gray-700 max-w-2xl">
            Share your work and achievements. Our AI will enhance them for your applications.
          </p>
        </div>
      </div>

      {/* Step Indicator - Full Width Sticky */}
      <div className="sticky top-0 z-40 bg-gradient-to-br from-purple-50/30 to-pink-50/30 border-b border-purple-100/30">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <WizardStepIndicator
            steps={wizardSteps}
            currentStep={currentStep}
          />
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 mt-4">
        {/* Form */}
        <div className="relative bg-white rounded-2xl shadow-2xl border-2 border-gray-100 p-8 mb-6">
          {/* AI-Powered Corner Ribbon */}
          <div className="absolute top-0 right-0 w-40 h-40 overflow-hidden pointer-events-none">
            <div className="absolute transform rotate-45 bg-gradient-to-br from-purple-600 to-pink-600 text-white text-center font-bold shadow-lg top-10 -right-10 w-48 py-2">
              <div className="flex items-center justify-center gap-1">
                <Sparkles className="h-3 w-3" />
                <span className="text-xs">AI-Powered</span>
              </div>
            </div>
          </div>

          <form onSubmit={handleFormSubmit}>
            {/* Step 1: Basic Information */}
            {currentStep === 1 && (
              <div className="space-y-6 animate-in fade-in duration-300">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
                    <FileText className="h-5 w-5 text-purple-600" />
                    Basic Information
                  </h2>
                  <p className="text-base text-gray-500">Tell us about your project or achievement</p>
                </div>

                {/* Title */}
                <div>
                  <label className="block text-base font-semibold text-gray-800 mb-2">
                    Title <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('title')}
                    type="text"
                    className={cn(
                      'w-full px-4 py-3 border-2 rounded-xl text-base font-medium transition-all duration-200',
                      'focus:ring-4 focus:ring-purple-100 focus:border-purple-500 focus:outline-none',
                      errors.title ? 'border-red-300' : 'border-gray-200'
                    )}
                    placeholder="e.g., E-commerce Platform for Local Businesses"
                  />
                  {errors.title && (
                    <p className="mt-2 text-base text-red-600 flex items-center gap-1">
                      <X className="h-4 w-4" />
                      {errors.title.message}
                    </p>
                  )}
                  <p className="mt-1 text-sm text-gray-500">
                    Give your artifact a clear, descriptive title
                  </p>
                </div>

                {/* Date Range */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-base font-semibold text-gray-800 mb-2">
                      <Calendar className="h-4 w-4 inline mr-1" />
                      Start Date <span className="text-red-500">*</span>
                    </label>
                    <input
                      {...register('startDate')}
                      type="date"
                      className={cn(
                        'w-full px-4 py-3 border-2 rounded-xl text-base font-medium transition-all duration-200',
                        'focus:ring-4 focus:ring-purple-100 focus:border-purple-500 focus:outline-none',
                        errors.startDate ? 'border-red-300' : 'border-gray-200'
                      )}
                    />
                    {errors.startDate && (
                      <p className="mt-2 text-base text-red-600">{errors.startDate.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-base font-semibold text-gray-800 mb-2">
                      <Calendar className="h-4 w-4 inline mr-1" />
                      End Date <span className="text-gray-400 text-xs">(optional)</span>
                    </label>
                    <input
                      {...register('endDate')}
                      type="date"
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-base font-medium transition-all duration-200 focus:ring-4 focus:ring-purple-100 focus:border-purple-500 focus:outline-none"
                    />
                    <p className="mt-1 text-sm text-gray-500">Leave blank if ongoing</p>
                  </div>
                </div>

              </div>
            )}

            {/* Step 2: Your Context */}
            {currentStep === 2 && (
              <div className="space-y-6 animate-in fade-in duration-300">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
                    <Star className="h-5 w-5 text-purple-600 fill-current" />
                    Your Context
                    <span className="ml-2 text-xs bg-gradient-to-r from-purple-600 to-pink-600 text-white px-2 py-1 rounded-full font-semibold">
                      MOST IMPORTANT
                    </span>
                  </h2>
                  <p className="text-base text-gray-500">
                    Share specific achievements, metrics, and impact. This will be preserved and highlighted in your CV.
                  </p>
                </div>

                {/* Info callout */}
                <div className="bg-purple-50 border-l-4 border-purple-600 rounded-lg p-4">
                  <p className="text-base text-purple-900 font-semibold mb-1">
                    🔒 This content is preserved exactly as you write it
                  </p>
                  <p className="text-sm text-gray-700">
                    Our AI will enhance other sections, but your context remains untouched and will be featured prominently in your CV.
                  </p>
                </div>

                {/* Textarea */}
                <div>
                  <label className="block text-base font-semibold text-gray-800 mb-2">
                    Share Your Achievements & Impact
                    <span className="ml-2 text-gray-400 text-xs">(Optional but Highly Recommended)</span>
                  </label>
                  <textarea
                    {...register('userContext')}
                    rows={8}
                    maxLength={1000}
                    className={cn(
                      'w-full px-4 py-3 border-2 rounded-xl text-base font-medium transition-all duration-200 resize-none',
                      'focus:ring-4 focus:ring-purple-100 focus:border-purple-500 focus:outline-none',
                      errors.userContext ? 'border-red-300' : 'border-gray-200'
                    )}
                    placeholder="e.g., Led a team of 6 engineers over 18 months, Reduced infrastructure costs by 40% ($50K annually), Presented at conference with 500+ attendees, Managed $2M project budget"
                  />

                  {/* Character counter and tip */}
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-sm text-purple-700 font-medium">
                      💡 Include numbers, team sizes, time periods, and tangible results
                    </span>
                    <span className="text-sm text-gray-600">
                      {userContext?.length || 0}/1000
                    </span>
                  </div>

                  {errors.userContext && (
                    <p className="mt-2 text-base text-red-600 flex items-center gap-1">
                      <X className="h-4 w-4" />
                      {errors.userContext.message}
                    </p>
                  )}

                  {/* Examples (auto-expanded) */}
                  <details className="mt-3" open>
                    <summary className="text-sm text-purple-700 cursor-pointer hover:underline font-semibold">
                      See examples of strong context
                    </summary>
                    <ul className="mt-3 ml-6 space-y-2 text-sm text-gray-700 list-disc">
                      <li><strong>Led a team of 6 engineers</strong> over 18 months</li>
                      <li><strong>Reduced infrastructure costs by 40%</strong> ($50K annually)</li>
                      <li><strong>Presented at conference with 500+ attendees</strong></li>
                      <li><strong>Managed $2M project budget</strong></li>
                      <li><strong>Mentored 3 junior developers</strong> to promotion</li>
                    </ul>
                  </details>
                </div>
              </div>
            )}

            {/* Step 3: Evidence & Sources (was Step 4) */}
            {currentStep === 3 && (
              <div className="space-y-6 animate-in fade-in duration-300">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
                    <Paperclip className="h-5 w-5 text-purple-600" />
                    Evidence & Sources
                  </h2>
                  <p className="text-base text-gray-500">
                    Upload documents or add links to showcase your work (optional)
                  </p>
                </div>

                {/* Evidence Required Warning */}
                {watch('githubLinks').length === 0 && uploadedFiles.length === 0 && (
                  <div className="p-4 bg-amber-50 border-2 border-amber-200 rounded-xl flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-semibold text-amber-900">Evidence Source Required</p>
                      <p className="text-xs text-amber-700 mt-1">
                        Add at least one GitHub repository or upload a file to enable AI enrichment.
                      </p>
                    </div>
                  </div>
                )}

                {/* Unified Evidence Section */}
                <div className="space-y-4">
                  {/* File Upload Dropzone */}
                  <div>
                    <label className="block text-sm font-semibold text-gray-800 mb-3">
                      📎 Upload Documents
                    </label>
                    <div
                      {...getRootProps()}
                      className={cn(
                        'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200',
                        isDragActive
                          ? 'border-purple-400 bg-purple-50 scale-105'
                          : 'border-gray-300 hover:border-purple-400 hover:bg-purple-50/50'
                      )}
                    >
                      <input {...getInputProps()} />
                      <Upload className="h-10 w-10 text-purple-400 mx-auto mb-3" />
                      {isDragActive ? (
                        <p className="text-purple-600 font-medium">Drop files here...</p>
                      ) : (
                        <div>
                          <p className="text-gray-700 font-medium mb-1">
                            Drag & drop files here, or click to browse
                          </p>
                          <p className="text-xs text-gray-500">
                            PDF and Word documents (max 10MB each)
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Uploaded Files List */}
                  {uploadedFiles.length > 0 && (
                    <div className="space-y-2">
                      {uploadedFiles.map((file, index) => (
                        <div
                          key={index}
                          className="flex items-center gap-3 p-4 bg-white border-2 border-purple-100 rounded-xl hover:border-purple-300 transition-all duration-200"
                        >
                          <div className="flex-shrink-0 w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                            <FileText className="h-5 w-5 text-purple-600" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-gray-900 truncate">
                              {file.name}
                            </p>
                            <p className="text-xs text-gray-500">
                              {(file.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeFile(index)}
                            className="flex-shrink-0 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Divider */}
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-gray-200"></div>
                    </div>
                    <div className="relative flex justify-center text-xs">
                      <span className="px-2 bg-white text-gray-500 font-medium">OR</span>
                    </div>
                  </div>

                  {/* GitHub Repositories Section */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <label className="flex items-center gap-2 text-sm font-semibold text-gray-800">
                        <Github className="h-4 w-4 text-purple-600" />
                        GitHub Repositories
                      </label>

                      {/* Add Repository Button - disabled if there are unvalidated links */}
                      <button
                        type="button"
                        onClick={() => appendGithubLink({ url: '', description: '' })}
                        disabled={githubFields.some((_, idx) => !validationResults[idx] || validationResults[idx].status === 'error')}
                        className="text-sm text-purple-600 hover:text-purple-700 font-semibold flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                        title={githubFields.some((_, idx) => !validationResults[idx]) ? 'Please validate existing repositories first' : ''}
                      >
                        <Plus className="h-4 w-4" />
                        Add Repository
                      </button>
                    </div>

                    {/* Info message */}
                    {githubFields.length === 0 && (
                      <p className="text-xs text-gray-500 mb-3">
                        Add GitHub repository links to showcase your code. Each link will be validated before you can add another.
                      </p>
                    )}

                    {/* GitHub Links List */}
                    {githubFields.length > 0 ? (
                      <div className="space-y-3">
                        {githubFields.map((field, index) => (
                          <div
                            key={field.id}
                            className="p-4 bg-white border-2 border-purple-100 rounded-xl hover:border-purple-300 transition-all duration-200"
                          >
                            <div className="flex items-start gap-3">
                              <div className="flex-shrink-0 w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mt-1">
                                <Github className="h-5 w-5 text-purple-600" />
                              </div>
                              <div className="flex-1 space-y-3">
                                {/* GitHub URL Input with inline Validate button */}
                                <div className="flex gap-2">
                                  <input
                                    {...register(`githubLinks.${index}.url`)}
                                    type="url"
                                    placeholder="https://github.com/username/repository"
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') {
                                        e.preventDefault()
                                      }
                                    }}
                                    className={cn(
                                      'flex-1 px-3 py-2 border-2 rounded-lg text-sm font-medium focus:ring-2 focus:ring-purple-100 focus:border-purple-500 focus:outline-none',
                                      errors.githubLinks?.[index]?.url && 'border-red-300',
                                      validationResults[index]?.status === 'error' && 'border-red-300',
                                      validationResults[index]?.status === 'warning' && 'border-yellow-300',
                                      validationResults[index]?.status === 'success' && 'border-green-300',
                                      !errors.githubLinks?.[index]?.url && !validationResults[index] && 'border-gray-200'
                                    )}
                                  />

                                  {/* Inline Validate Button */}
                                  <button
                                    type="button"
                                    onClick={async () => {
                                      const url = watch(`githubLinks.${index}.url`)
                                      if (!url) return

                                      setIsValidating(true)
                                      try {
                                        const response = await apiClient.validateEvidenceLinks([
                                          { url, evidence_type: 'github' }
                                        ])
                                        setValidationResults(prev => ({
                                          ...prev,
                                          [index]: response.results[0]
                                        }))
                                      } catch (error) {
                                        console.error('Validation error:', error)
                                        toast.error('Failed to validate repository')
                                      } finally {
                                        setIsValidating(false)
                                      }
                                    }}
                                    disabled={isValidating || !watch(`githubLinks.${index}.url`) || !!errors.githubLinks?.[index]?.url}
                                    className={cn(
                                      'px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-1.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed',
                                      validationResults[index]?.status === 'success'
                                        ? 'bg-green-50 text-green-700 border-2 border-green-200'
                                        : 'bg-blue-50 text-blue-600 hover:bg-blue-100 border-2 border-blue-200'
                                    )}
                                  >
                                    {isValidating ? (
                                      <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Validating
                                      </>
                                    ) : validationResults[index]?.status === 'success' ? (
                                      <>
                                        <CheckCircle className="h-4 w-4" />
                                        Validated
                                      </>
                                    ) : (
                                      <>
                                        <CheckCircle className="h-4 w-4" />
                                        Validate
                                      </>
                                    )}
                                  </button>
                                </div>

                                {/* Validation Result Message */}
                                {validationResults[index] && (
                                  <div className={cn(
                                    'flex items-start gap-2 px-3 py-2 rounded-lg text-xs font-medium',
                                    validationResults[index].status === 'success' && 'bg-green-50 text-green-700 border border-green-200',
                                    validationResults[index].status === 'warning' && 'bg-yellow-50 text-yellow-700 border border-yellow-200',
                                    validationResults[index].status === 'error' && 'bg-red-50 text-red-700 border border-red-200'
                                  )}>
                                    {validationResults[index].status === 'success' && <CheckCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />}
                                    {validationResults[index].status === 'warning' && <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />}
                                    {validationResults[index].status === 'error' && <XCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />}
                                    <span>{validationResults[index].message}</span>
                                  </div>
                                )}

                                {/* Form Validation Error */}
                                {errors.githubLinks?.[index]?.url && !validationResults[index] && (
                                  <p className="text-xs text-red-600">
                                    {errors.githubLinks[index]?.url?.message}
                                  </p>
                                )}

                                {/* Description Input - only show after validation */}
                                {validationResults[index] && (
                                  <input
                                    {...register(`githubLinks.${index}.description`)}
                                    type="text"
                                    placeholder="Brief description (optional)"
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') {
                                        e.preventDefault()
                                      }
                                    }}
                                    className={cn(
                                      'w-full px-3 py-2 border-2 rounded-lg text-sm font-medium focus:ring-2 focus:ring-purple-100 focus:border-purple-500 focus:outline-none',
                                      errors.githubLinks?.[index]?.description ? 'border-red-300' : 'border-gray-200'
                                    )}
                                  />
                                )}
                                {errors.githubLinks?.[index]?.description && (
                                  <p className="text-xs text-red-600">
                                    {errors.githubLinks[index]?.description?.message}
                                  </p>
                                )}
                              </div>
                              <button
                                type="button"
                                onClick={() => {
                                  removeGithubLink(index)
                                  // Remove validation result for this index
                                  setValidationResults(prev => {
                                    const newResults = { ...prev }
                                    delete newResults[index]
                                    return newResults
                                  })
                                }}
                                className="flex-shrink-0 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors mt-1"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}

                    {uploadedFiles.length === 0 && githubFields.length === 0 && (
                      <div className="p-8 bg-gray-50 rounded-xl border-2 border-dashed border-gray-300 text-center">
                        <Paperclip className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                        <p className="text-sm text-gray-500 mb-1">
                          No evidence added yet
                        </p>
                        <p className="text-xs text-gray-400">
                          Upload files or add links to strengthen your portfolio
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Step 5: Processing (ft-045) */}
            {/* Step 6: Processing (enrichment) */}
            {/* Step 5: Processing & Evidence Review (consolidated) */}
            {currentStep === 5 && createdArtifactId && (
              <div className="space-y-6 animate-in fade-in duration-300">
                <ConsolidatedProcessingStep
                  artifactId={createdArtifactId}
                  onComplete={() => {
                    console.log('[ArtifactUpload] Processing & evidence review complete, advancing to reunification')
                    setCurrentStep(6)
                  }}
                  onError={(error) => {
                    console.error('[ArtifactUpload] Processing or evidence review failed:', error)
                    toast.error(`Failed: ${error}`)
                  }}
                />
              </div>
            )}

            {/* Step 6: Reunification & Acceptance (consolidated) */}
            {currentStep === 6 && createdArtifactId && (
              <div className="space-y-6 animate-in fade-in duration-300">
                <ConsolidatedReunificationStep
                  artifactId={createdArtifactId}
                  onAcceptComplete={() => {
                    console.log('[ArtifactUpload] Artifact accepted, wizard complete')
                    navigate(`/artifacts/${createdArtifactId}`)
                  }}
                  onError={(error) => {
                    console.error('[ArtifactUpload] Reunification or acceptance failed:', error)
                    toast.error(`Failed: ${error}`)
                  }}
                />
              </div>
            )}

            {/* Step 4: Confirmation (Review before creating artifact) - was Step 5 */}
            {currentStep === 4 && (
              <div className="space-y-6 animate-in fade-in duration-300">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
                    <Eye className="h-5 w-5 text-purple-600" />
                    Confirm Your Details
                  </h2>
                  <p className="text-base text-gray-500">Check your details before we create your artifact</p>
                </div>

                {/* Summary Cards */}
                <div className="space-y-4">
                  {/* Basic Info */}
                  <div className="p-6 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl border-2 border-purple-200">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-sm font-semibold text-purple-900 mb-1">Basic Information</h3>
                        <p className="text-xs text-purple-600">Step 1 of 6</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setCurrentStep(1)}
                        className="text-xs text-purple-600 hover:text-purple-700 font-semibold"
                      >
                        Edit
                      </button>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <p className="text-xs font-medium text-gray-600 mb-1">Title</p>
                        <p className="text-sm font-semibold text-gray-900">{title || 'Not set'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-600 mb-1">Duration</p>
                        <p className="text-sm font-semibold text-gray-900">
                          {startDate ? formatDateRange(startDate, endDate) : 'Not set'}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Your Context */}
                  <div className="p-6 bg-gradient-to-br from-amber-50 to-yellow-50 rounded-xl border-2 border-amber-200">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-sm font-semibold text-amber-900 mb-1">Your Context</h3>
                        <p className="text-xs text-amber-600">Step 2 of 6</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setCurrentStep(2)}
                        className="text-xs text-amber-600 hover:text-amber-700 font-semibold"
                      >
                        Edit
                      </button>
                    </div>
                    {userContext ? (
                      <p className="text-sm text-gray-800 whitespace-pre-wrap">
                        {userContext}
                      </p>
                    ) : (
                      <p className="text-sm text-gray-500 italic">
                        No context provided
                      </p>
                    )}
                  </div>

                  {/* Evidence */}
                  <div className="p-6 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl border-2 border-green-200">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-sm font-semibold text-green-900 mb-1">Evidence & Sources</h3>
                        <p className="text-xs text-green-600">Step 3 of 6</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setCurrentStep(3)}
                        className="text-xs text-green-600 hover:text-green-700 font-semibold"
                      >
                        Edit
                      </button>
                    </div>
                    <div className="space-y-2">
                      {uploadedFiles.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-gray-600 mb-2">Files ({uploadedFiles.length})</p>
                          {uploadedFiles.map((file, index) => (
                            <p key={index} className="text-sm text-gray-700 flex items-center gap-2">
                              <FileText className="h-4 w-4 text-green-600" />
                              {file.name}
                            </p>
                          ))}
                        </div>
                      )}
                      {githubFields.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-gray-600 mb-2">GitHub Repositories ({githubFields.length})</p>
                          {githubFields.map((field, _index) => (
                            <p key={field.id} className="text-sm text-gray-700 flex items-center gap-2">
                              <Github className="h-4 w-4 text-green-600" />
                              GitHub Repository
                            </p>
                          ))}
                        </div>
                      )}
                      {uploadedFiles.length === 0 && githubFields.length === 0 && (
                        <p className="text-base text-gray-500">No evidence added</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Info Banner */}
                <div className="p-4 bg-blue-50 border-2 border-blue-200 rounded-xl">
                  <div className="flex gap-3">
                    <Sparkles className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-semibold text-blue-900 mb-1">
                        Ready to Create
                      </p>
                      <p className="text-xs text-blue-700">
                        After creating your artifact, our AI will analyze and enrich it with additional insights,
                        technologies, and achievements from your evidence sources.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Navigation Controls - Hidden during Step 5 (Processing & Review) and Step 6 (Reunification & Acceptance) */}
            {currentStep !== 5 && currentStep !== 6 && (
              <div className="flex items-center justify-between pt-8 mt-8 border-t-2 border-gray-100">
                <div>
                  {currentStep > 1 && (
                    <button
                      type="button"
                      onClick={handleBack}
                      disabled={isSubmitting}
                      className="px-6 py-3 text-gray-700 font-semibold rounded-xl hover:bg-gray-100 transition-all duration-200 flex items-center gap-2 disabled:opacity-50"
                    >
                      <ArrowLeft className="h-4 w-4" />
                      Back
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={handleClose}
                    disabled={isSubmitting}
                    className="px-6 py-3 text-gray-700 font-semibold rounded-xl hover:bg-gray-100 transition-all duration-200 disabled:opacity-50"
                  >
                    Cancel
                  </button>

                  {currentStep < TOTAL_STEPS ? (
                    <>
                      <button
                        type="button"
                        onClick={handleNext}
                        disabled={isSubmitting}
                        className="px-8 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold rounded-xl transition-all duration-200 transform hover:scale-105 disabled:opacity-50 disabled:transform-none flex items-center gap-2 shadow-lg"
                      >
                        {currentStep === 5 ? (
                          <>
                            {isSubmitting ? (
                              <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Creating Artifact...
                              </>
                            ) : (
                              <>
                                <Sparkles className="h-4 w-4" />
                                Create Artifact & Start Processing
                              </>
                            )}
                          </>
                        ) : (
                          <>
                            Next
                            <ArrowRight className="h-4 w-4" />
                          </>
                        )}
                      </button>
                    </>
                  ) : (
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold rounded-xl transition-all duration-200 transform hover:scale-105 disabled:opacity-50 disabled:transform-none flex items-center gap-2 shadow-lg"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Uploading...
                      </>
                    ) : (
                      <>
                        <Check className="h-4 w-4" />
                        Submit Artifact
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
            )}
          </form>
        </div>
      </div>

      {/* Cancel Confirmation Dialog */}
      <CancelConfirmationDialog
        isOpen={showCancelDialog}
        progress={{
          currentStep,
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
