import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { Plus, Trash2, Save, AlertCircle } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'
import { TagInput } from '@/components/ui/TagInput'
import { cn } from '@/utils/cn'
import type { Artifact } from '@/types'

interface EnrichedContentEditorProps {
  artifact: Artifact
  isOpen: boolean
  onClose: () => void
  onSave: (data: EnrichedContentUpdate) => Promise<void>
  isLoading?: boolean
}

export interface EnrichedContentUpdate {
  unifiedDescription?: string
  enrichedTechnologies?: string[]
  enrichedAchievements?: string[]
}

interface FormData {
  unifiedDescription: string
  enrichedTechnologies: string[]
  enrichedAchievements: string[]
}

export function EnrichedContentEditor({
  artifact,
  isOpen,
  onClose,
  onSave,
  isLoading = false
}: EnrichedContentEditorProps) {
  const [achievements, setAchievements] = useState<string[]>([])
  const [newAchievement, setNewAchievement] = useState('')
  const [isDirty, setIsDirty] = useState(false)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting }
  } = useForm<FormData>({
    defaultValues: {
      unifiedDescription: artifact.unifiedDescription || '',
      enrichedTechnologies: artifact.enrichedTechnologies || [],
      enrichedAchievements: artifact.enrichedAchievements || []
    }
  })

  const watchedDescription = watch('unifiedDescription')
  const watchedTechnologies = watch('enrichedTechnologies')

  // Initialize achievements from artifact
  useEffect(() => {
    setAchievements(artifact.enrichedAchievements || [])
  }, [artifact.enrichedAchievements])

  // Track if form is dirty
  useEffect(() => {
    const hasChanges =
      watchedDescription !== (artifact.unifiedDescription || '') ||
      JSON.stringify(watchedTechnologies) !== JSON.stringify(artifact.enrichedTechnologies || []) ||
      JSON.stringify(achievements) !== JSON.stringify(artifact.enrichedAchievements || [])

    setIsDirty(hasChanges)
  }, [watchedDescription, watchedTechnologies, achievements, artifact])

  const addAchievement = () => {
    if (!newAchievement.trim()) return

    if (achievements.length >= 20) {
      setValidationErrors(prev => ({
        ...prev,
        achievements: 'Maximum 20 achievements allowed'
      }))
      return
    }

    setAchievements(prev => [...prev, newAchievement.trim()])
    setNewAchievement('')
    setValidationErrors(prev => {
      const { achievements, ...rest } = prev
      return rest
    })
  }

  const removeAchievement = (index: number) => {
    setAchievements(prev => prev.filter((_, i) => i !== index))
  }

  const updateAchievement = (index: number, value: string) => {
    setAchievements(prev => prev.map((ach, i) => i === index ? value : ach))
  }

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    if (watchedDescription && watchedDescription.length > 5000) {
      errors.description = 'Description must be less than 5000 characters'
    }

    if (watchedTechnologies.length > 50) {
      errors.technologies = 'Maximum 50 technologies allowed'
    }

    if (achievements.length > 20) {
      errors.achievements = 'Maximum 20 achievements allowed'
    }

    setValidationErrors(errors)
    return Object.keys(errors).length === 0
  }

  const onSubmit = async (data: FormData) => {
    if (!validateForm()) return

    try {
      const updates: EnrichedContentUpdate = {}

      if (data.unifiedDescription !== (artifact.unifiedDescription || '')) {
        updates.unifiedDescription = data.unifiedDescription
      }

      if (JSON.stringify(data.enrichedTechnologies) !== JSON.stringify(artifact.enrichedTechnologies || [])) {
        updates.enrichedTechnologies = data.enrichedTechnologies
      }

      if (JSON.stringify(achievements) !== JSON.stringify(artifact.enrichedAchievements || [])) {
        updates.enrichedAchievements = achievements
      }

      // Only save if there are changes
      if (Object.keys(updates).length > 0) {
        await onSave(updates)
        setIsDirty(false)
      } else {
        handleClose()
      }
    } catch (error) {
      console.error('Failed to save enriched content:', error)
      // Let parent component handle error display
      throw error
    }
  }

  const handleClose = () => {
    if (isDirty) {
      if (window.confirm('You have unsaved changes. Are you sure you want to close?')) {
        onClose()
      }
    } else {
      onClose()
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Edit AI-Enriched Content"
      size="xl"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 p-6">
        {/* Unified Description */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-semibold text-gray-800">
              AI-Enhanced Description
            </label>
            <span className={cn(
              "text-xs",
              watchedDescription.length > 5000 ? "text-red-600 font-medium" : "text-gray-500"
            )}>
              {watchedDescription.length} / 5000
            </span>
          </div>
          <Textarea
            rows={8}
            placeholder="Edit the AI-enhanced description..."
            className="font-mono text-sm"
            {...register('unifiedDescription')}
          />
          {validationErrors.description && (
            <div className="flex items-center gap-2 mt-2 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              <span>{validationErrors.description}</span>
            </div>
          )}
          {errors.unifiedDescription && (
            <p className="text-sm text-red-600 mt-1">{errors.unifiedDescription.message}</p>
          )}
        </div>

        {/* Enriched Technologies */}
        <div>
          <label className="block text-sm font-semibold text-gray-800 mb-2">
            AI-Extracted Technologies ({watchedTechnologies.length}/50)
          </label>
          <TagInput
            value={watchedTechnologies}
            onChange={(technologies) => setValue('enrichedTechnologies', technologies, { shouldDirty: true })}
            placeholder="Add technology (press Enter)"
          />
          {validationErrors.technologies && (
            <div className="flex items-center gap-2 mt-2 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              <span>{validationErrors.technologies}</span>
            </div>
          )}
          <p className="text-xs text-gray-500 mt-1">
            Add technologies identified by AI analysis
          </p>
        </div>

        {/* Enriched Achievements */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-semibold text-gray-800">
              AI-Identified Achievements ({achievements.length}/20)
            </label>
          </div>

          {/* Achievement List */}
          <div className="space-y-2 mb-3 max-h-64 overflow-y-auto">
            {achievements.map((achievement, index) => (
              <div key={index} className="flex items-start gap-2 bg-gray-50 p-3 rounded-lg border border-gray-200">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-600 text-white flex items-center justify-center text-xs font-bold mt-1">
                  {index + 1}
                </div>
                <textarea
                  value={achievement}
                  onChange={(e) => updateAchievement(index, e.target.value)}
                  className="flex-1 bg-white border border-gray-200 rounded-md px-3 py-2 text-sm resize-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  rows={2}
                />
                <button
                  type="button"
                  onClick={() => removeAchievement(index)}
                  className="flex-shrink-0 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors mt-1"
                  title="Remove achievement"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
            {achievements.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-8 bg-gray-50 rounded-lg border border-gray-200 border-dashed">
                No achievements added yet
              </p>
            )}
          </div>

          {/* Add Achievement Input */}
          {achievements.length < 20 && (
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <textarea
                  value={newAchievement}
                  onChange={(e) => setNewAchievement(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      addAchievement()
                    }
                  }}
                  placeholder="Add new achievement (press Enter to add)"
                  className="w-full bg-white border-2 border-gray-200 rounded-md px-3 py-2 text-sm resize-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  rows={2}
                />
              </div>
              <button
                type="button"
                onClick={addAchievement}
                className="flex-shrink-0 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors flex items-center gap-2 h-[42px]"
              >
                <Plus className="h-4 w-4" />
                Add
              </button>
            </div>
          )}

          {validationErrors.achievements && (
            <div className="flex items-center gap-2 mt-2 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              <span>{validationErrors.achievements}</span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-6 border-t border-gray-200">
          <div className="flex items-center gap-2">
            {isDirty && (
              <div className="flex items-center gap-2 text-sm text-amber-600">
                <AlertCircle className="h-4 w-4" />
                <span className="font-medium">You have unsaved changes</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting || isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!isDirty || isSubmitting || isLoading}
              className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-medium"
            >
              {(isSubmitting || isLoading) ? (
                <>Saving...</>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  )
}
