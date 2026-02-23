import React, { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { ArtifactSelector } from '@/components/ArtifactSelector'
import { apiClient } from '@/services/apiClient'
import { ArrowLeft, ArrowRight, Zap } from 'lucide-react'
import { cn } from '@/utils/cn'

export default function GenerationWorkflow() {
  const [step, setStep] = useState(1)
  const [jobDescription, setJobDescription] = useState('')
  const [selectedArtifactIds, setSelectedArtifactIds] = useState<number[]>([])
  const [validationError, setValidationError] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)

  const handleNext = () => {
    if (step === 1 && jobDescription.trim()) {
      setStep(2)
    }
  }

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1)
      setValidationError('')
    }
  }

  const handleGenerate = async () => {
    if (selectedArtifactIds.length === 0) {
      setValidationError('Please select at least 1 artifact to continue')
      return
    }

    setValidationError('')
    setIsGenerating(true)

    try {
      await apiClient.createGeneration({
        jobDescription,
        companyName: 'Company', // TODO: Add company name field
        roleTitle: 'Role', // TODO: Add role title field
        labelIds: [],
        generationPreferences: {
          tone: 'professional',
          length: 'detailed',
          focusAreas: []
        },
        artifactIds: selectedArtifactIds
      })
      // Success - would navigate to results
    } catch (error) {
      console.error('Generation failed:', error)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleUseTopFive = async () => {
    setValidationError('')
    setIsGenerating(true)

    try {
      // Call generateCV without artifact_ids for automatic selection
      await apiClient.createGeneration({
        jobDescription,
        companyName: 'Company',
        roleTitle: 'Role',
        labelIds: [],
        generationPreferences: {
          tone: 'professional',
          length: 'detailed',
          focusAreas: []
        }
        // No artifactIds - use automatic selection
      })
      // Success - would navigate to results
    } catch (error) {
      console.error('Generation failed:', error)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSelectionChange = (artifactIds: number[]) => {
    setSelectedArtifactIds(artifactIds)
    setValidationError('')
  }

  const renderStepIndicator = () => (
    <div className="flex items-center justify-center mb-8 space-x-4">
      {[
        { number: 1, title: 'Job Description' },
        { number: 2, title: 'Artifacts' },
        { number: 3, title: 'Review' }
      ].map((stepItem, index) => (
        <React.Fragment key={stepItem.number}>
          <div className="flex items-center gap-2">
            <div
              className={cn(
                'flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold transition-all',
                step >= stepItem.number
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-200 text-gray-500'
              )}
            >
              {stepItem.number}
            </div>
            <span
              className={cn(
                'text-sm font-medium',
                step >= stepItem.number ? 'text-purple-600' : 'text-gray-500'
              )}
            >
              {stepItem.title}
            </span>
          </div>
          {index < 2 && (
            <div className="w-12 h-0.5 bg-gray-200">
              <div
                className={cn(
                  'h-full bg-purple-600 transition-all',
                  step > stepItem.number ? 'w-full' : 'w-0'
                )}
              />
            </div>
          )}
        </React.Fragment>
      ))}
    </div>
  )

  const renderJobDescriptionStep = () => (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Enter Job Description
        </h2>
        <p className="text-gray-600">
          Paste the job description to help us find the best matching artifacts
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label htmlFor="job-description" className="block text-sm font-medium text-gray-700 mb-2">
            Job Description *
          </label>
          <textarea
            id="job-description"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            rows={12}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none"
            placeholder="Paste the job description here..."
          />
        </div>
      </div>

      <div className="flex justify-end">
        <Button
          onClick={handleNext}
          disabled={!jobDescription.trim()}
          className="flex items-center gap-2"
        >
          Next
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )

  const renderArtifactSelectionStep = () => (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Select Artifacts
        </h2>
        <p className="text-gray-600">
          We've found {selectedArtifactIds.length} artifact{selectedArtifactIds.length !== 1 ? 's' : ''} for you
        </p>
      </div>

      <ArtifactSelector
        jobDescription={jobDescription}
        onSelectionChange={handleSelectionChange}
        initialSelection={selectedArtifactIds}
      />

      {validationError && (
        <div className="text-center">
          <p className="text-red-600 text-sm font-medium">{validationError}</p>
        </div>
      )}

      <div className="flex justify-between items-center pt-6">
        <Button
          variant="outline"
          onClick={handleBack}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={handleUseTopFive}
            disabled={isGenerating}
            loading={isGenerating}
          >
            Use Top 5
          </Button>

          <Button
            onClick={handleGenerate}
            disabled={isGenerating}
            loading={isGenerating}
            className="flex items-center gap-2"
          >
            <Zap className="h-4 w-4" />
            Generate CV
          </Button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6">
      <Card className="p-8">
        {renderStepIndicator()}

        <div className="mt-8">
          {step === 1 && renderJobDescriptionStep()}
          {step === 2 && renderArtifactSelectionStep()}
        </div>
      </Card>
    </div>
  )
}
