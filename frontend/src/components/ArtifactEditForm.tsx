import React, { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { TagInput } from '@/components/ui/TagInput'
import { DatePicker } from '@/components/ui/DatePicker'
import { Card } from '@/components/ui/Card'
import type { Artifact, ArtifactCreateData } from '@/types'
import { apiClient } from '@/services/apiClient'

interface ArtifactEditFormProps {
  artifact: Artifact
  onSave: (updates: Partial<ArtifactCreateData>) => Promise<void>
  onCancel: () => void
  isLoading?: boolean
}

interface FormData {
  title: string
  description: string
  userContext?: string  // NEW (ft-018)
  artifactType: string
  startDate: string
  endDate: string
  technologies: string[]
}

const ARTIFACT_TYPES = [
  { value: 'project', label: 'Project' },
  { value: 'publication', label: 'Publication' },
  { value: 'presentation', label: 'Presentation' },
  { value: 'certification', label: 'Certification' },
  { value: 'experience', label: 'Work Experience' },
  { value: 'education', label: 'Education' }
]

export const ArtifactEditForm: React.FC<ArtifactEditFormProps> = ({
  artifact,
  onSave,
  onCancel,
  isLoading = false
}) => {
  const [isDirty, setIsDirty] = useState(false)
  const [technologySuggestions, setTechnologySuggestions] = useState<string[]>([])

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting }
  } = useForm<FormData>({
    defaultValues: {
      title: artifact.title,
      description: artifact.description,
      userContext: artifact.userContext || '',  // NEW (ft-018)
      artifactType: artifact.artifactType,
      startDate: artifact.startDate || '',
      endDate: artifact.endDate || '',
      technologies: artifact.technologies || []
    }
  })

  // Watch for changes to mark form as dirty
  const watchedValues = watch()
  useEffect(() => {
    const originalValues = {
      title: artifact.title,
      description: artifact.description,
      userContext: artifact.userContext || '',  // NEW (ft-018)
      artifactType: artifact.artifactType,
      startDate: artifact.startDate || '',
      endDate: artifact.endDate || '',
      technologies: artifact.technologies || []
    }

    const hasChanges = JSON.stringify(watchedValues) !== JSON.stringify(originalValues)
    setIsDirty(hasChanges)
  }, [watchedValues, artifact])

  // Load technology suggestions
  useEffect(() => {
    const loadSuggestions = async () => {
      try {
        const suggestions = await apiClient.getTechnologySuggestions()
        setTechnologySuggestions(suggestions)
      } catch (error) {
        console.error('Failed to load technology suggestions:', error)
      }
    }
    loadSuggestions()
  }, [])

  const onSubmit = async (data: FormData) => {
    try {
      const updates: Partial<ArtifactCreateData> = {}

      // Only include changed fields
      if (data.title !== artifact.title) updates.title = data.title
      if (data.description !== artifact.description) updates.description = data.description
      if (data.userContext !== (artifact.userContext || '')) updates.userContext = data.userContext || undefined  // NEW (ft-018)
      if (data.artifactType !== artifact.artifactType) {
        updates.artifactType = data.artifactType as 'project' | 'experience' | 'education' | 'certification' | 'publication' | 'presentation'
      }
      if (data.startDate !== (artifact.startDate || '')) {
        updates.startDate = data.startDate || undefined
      }
      if (data.endDate !== (artifact.endDate || '')) {
        updates.endDate = data.endDate || undefined
      }
      if (JSON.stringify(data.technologies) !== JSON.stringify(artifact.technologies || [])) {
        updates.technologies = data.technologies
      }

      // Only call onSave if there are actual changes
      if (Object.keys(updates).length > 0) {
        await onSave(updates)
        setIsDirty(false)
      } else {
        // No changes, just close the modal
        onCancel()
      }
    } catch (error) {
      console.error('Failed to update artifact:', error)
      // Let the parent component handle error display
      throw error
    }
  }

  const handleCancel = () => {
    if (isDirty) {
      if (window.confirm('You have unsaved changes. Are you sure you want to cancel?')) {
        onCancel()
      }
    } else {
      onCancel()
    }
  }

  const validateDates = (startDate: string, endDate: string) => {
    if (startDate && endDate && new Date(startDate) > new Date(endDate)) {
      return 'End date must be after start date'
    }
    return true
  }

  return (
    <Card className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 break-words">
          Edit Artifact: {artifact.title}
        </h2>
        <p className="text-gray-600 mt-1">
          Update your artifact information and evidence
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div>
          <Input
            label="Title"
            placeholder="Enter artifact title"
            error={errors.title?.message}
            required
            {...register('title', {
              required: 'Title is required',
              maxLength: { value: 255, message: 'Title must be less than 255 characters' }
            })}
          />
        </div>

        <div>
          <Textarea
            label="Description"
            placeholder="Describe your artifact, its purpose, and key achievements"
            rows={5}
            error={errors.description?.message}
            required
            {...register('description', {
              required: 'Description is required',
              maxLength: { value: 5000, message: 'Description must be less than 5000 characters' }
            })}
          />
        </div>

        {/* User Context (ft-018) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Additional Context <span className="text-gray-500 font-normal">(Optional)</span>
          </label>
          <textarea
            rows={4}
            placeholder="e.g., Led a team of 6 engineers, Reduced infrastructure costs by 40%, Managed $2M budget"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
            {...register('userContext', {
              maxLength: { value: 1000, message: 'Context cannot exceed 1000 characters' }
            })}
          />
          {errors.userContext && (
            <p className="mt-1 text-sm text-red-600">{errors.userContext.message}</p>
          )}
          <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
            <span className="flex items-center gap-1">
              <span>🔒</span> Preserved during enrichment
            </span>
            <span className="font-medium">
              {watch('userContext')?.length || 0}/1000 characters
            </span>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            💡 Provide details that can't be extracted from evidence (team size, budget, impact metrics, presentations)
          </p>
        </div>

        <div>
          <Select
            label="Type"
            options={ARTIFACT_TYPES}
            error={errors.artifactType?.message}
            {...register('artifactType', { required: 'Type is required' })}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <DatePicker
              label="Start Date"
              value={watch('startDate')}
              onChange={(date) => setValue('startDate', date, { shouldDirty: true })}
              error={errors.startDate?.message}
            />
          </div>
          <div>
            <DatePicker
              label="End Date"
              value={watch('endDate')}
              onChange={(date) => setValue('endDate', date, { shouldDirty: true })}
              error={errors.endDate?.message}
              validate={(date) => validateDates(watch('startDate'), date)}
            />
          </div>
        </div>

        <div>
          <TagInput
            label="Technologies"
            placeholder="Add technologies used (press Enter to add)"
            value={watch('technologies')}
            onChange={(technologies) => setValue('technologies', technologies, { shouldDirty: true })}
            suggestions={technologySuggestions}
            error={errors.technologies?.message}
          />
          <p className="text-sm text-gray-500 mt-1">
            Add technologies, frameworks, and tools used in this artifact
          </p>
        </div>

        <div className="flex items-center justify-between pt-6 border-t border-gray-200">
          <div className="flex items-center space-x-2">
            {isDirty && (
              <span className="text-sm text-amber-600 flex items-center">
                <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Unsaved changes
              </span>
            )}
          </div>

          <div className="flex items-center space-x-3">
            <Button
              type="button"
              variant="secondary"
              onClick={handleCancel}
              disabled={isSubmitting || isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!isDirty || isSubmitting || isLoading}
              loading={isSubmitting || isLoading}
            >
              Save Changes
            </Button>
          </div>
        </div>
      </form>
    </Card>
  )
}