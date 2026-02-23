import { useState, useEffect } from 'react'
import { CheckCircle, AlertCircle, RefreshCw, ArrowRight, Sparkles, Info } from 'lucide-react'
import { cn } from '@/utils/cn'
import BulletCard from './BulletCard'
import { apiClient } from '@/services/apiClient'
import type { GenerationBulletsResponse, BulletsByArtifact } from '@/types'
import toast from 'react-hot-toast'

interface BulletReviewStepProps {
  generationId: string
  onApproveAndContinue: () => void
  onBack?: () => void
  className?: string
}

export default function BulletReviewStep({
  generationId,
  onApproveAndContinue,
  onBack,
  className
}: BulletReviewStepProps) {
  const [bulletsData, setBulletsData] = useState<GenerationBulletsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isApproving, setIsApproving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load bullets on mount
  useEffect(() => {
    loadBullets()
  }, [generationId])

  const loadBullets = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await apiClient.getGenerationBullets(generationId)
      setBulletsData(data)
    } catch (err: any) {
      console.error('Failed to load bullets:', err)
      setError(err.response?.data?.error || 'Failed to load bullets')
      toast.error('Failed to load bullets')
    } finally {
      setIsLoading(false)
    }
  }

  const handleBulletEdit = async (bulletId: number, newText: string) => {
    try {
      const result = await apiClient.editGenerationBullet(generationId, bulletId, newText)

      // Update local state with edited bullet
      setBulletsData(prev => {
        if (!prev) return prev

        const updatedArtifacts = prev.artifacts.map(artifact => ({
          ...artifact,
          bullets: artifact.bullets.map(bullet =>
            bullet.id === bulletId ? result.bullet : bullet
          )
        }))

        return {
          ...prev,
          artifacts: updatedArtifacts
        }
      })

      toast.success('Bullet updated successfully')
    } catch (err: any) {
      console.error('Failed to edit bullet:', err)
      toast.error(err.response?.data?.error || 'Failed to update bullet')
      throw err
    }
  }

  const handleApproveAll = async () => {
    setIsApproving(true)
    try {
      await apiClient.approveGenerationBullets(generationId)
      toast.success('All bullets approved!')
      onApproveAndContinue()
    } catch (err: any) {
      console.error('Failed to approve bullets:', err)
      toast.error(err.response?.data?.error || 'Failed to approve bullets')
    } finally {
      setIsApproving(false)
    }
  }

  if (isLoading) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-16', className)}>
        <div className="relative mb-6">
          <RefreshCw className="h-12 w-12 text-blue-600 animate-spin" />
          <div className="absolute inset-0 h-12 w-12 border-4 border-blue-200 rounded-full animate-ping" />
        </div>
        <h3 className="text-xl font-bold text-gray-900 mb-2">Loading Your Bullets</h3>
        <p className="text-gray-600">Fetching generated bullet points...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-16', className)}>
        <div className="p-4 bg-red-100 rounded-full mb-6">
          <AlertCircle className="h-12 w-12 text-red-600" />
        </div>
        <h3 className="text-xl font-bold text-red-900 mb-2">Failed to Load Bullets</h3>
        <p className="text-red-700 mb-6">{error}</p>
        <button
          onClick={loadBullets}
          className="flex items-center gap-2 px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl transition-all duration-300 transform hover:scale-105"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Retry</span>
        </button>
      </div>
    )
  }

  if (!bulletsData || bulletsData.artifacts.length === 0) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-16', className)}>
        <div className="p-4 bg-amber-100 rounded-full mb-6">
          <AlertCircle className="h-12 w-12 text-amber-600" />
        </div>
        <h3 className="text-xl font-bold text-gray-900 mb-2">No Bullets Found</h3>
        <p className="text-gray-600">No bullet points were generated for this CV.</p>
      </div>
    )
  }

  // Calculate statistics
  const totalBullets = bulletsData.artifacts.reduce((sum, a) => sum + a.bullets.length, 0)
  const editedBullets = bulletsData.artifacts.reduce(
    (sum, a) => sum + a.bullets.filter(b => b.userEdited).length,
    0
  )
  const avgQuality = bulletsData.artifacts.reduce(
    (sum, a) => sum + a.bullets.reduce((s, b) => s + b.qualityScore, 0),
    0
  ) / totalBullets

  return (
    <div className={cn('space-y-8', className)}>
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-full mb-6">
          <Sparkles className="h-4 w-4 text-purple-600" />
          <span className="text-sm font-semibold text-purple-700">Phase 1: Review & Approve</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Review Your Bullet Points</h2>
        <p className="text-gray-600 max-w-2xl mx-auto leading-relaxed">
          We've generated {totalBullets} bullet points from your selected artifacts. Review, edit if needed, and approve to continue.
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-2xl p-4">
          <div className="text-blue-700 text-sm font-bold mb-1">Total Bullets</div>
          <div className="text-3xl font-bold text-blue-900">{totalBullets}</div>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-2xl p-4">
          <div className="text-green-700 text-sm font-bold mb-1">Avg Quality</div>
          <div className="text-3xl font-bold text-green-900">{(avgQuality * 100).toFixed(0)}%</div>
        </div>
        <div className="bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-200 rounded-2xl p-4">
          <div className="text-purple-700 text-sm font-bold mb-1">Edited</div>
          <div className="text-3xl font-bold text-purple-900">{editedBullets}</div>
        </div>
        <div className="bg-gradient-to-br from-amber-50 to-yellow-50 border-2 border-amber-200 rounded-2xl p-4">
          <div className="text-amber-700 text-sm font-bold mb-1">Artifacts</div>
          <div className="text-3xl font-bold text-amber-900">{bulletsData.artifacts.length}</div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-2xl p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-xl flex items-center justify-center shadow-lg flex-shrink-0">
            <Info className="h-5 w-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-blue-900 mb-2">How to Review</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Each artifact has <strong>3 bullets</strong>: Achievement, Technical, Impact</li>
              <li>• <strong>Quality badges</strong> show action verbs, keyword relevance, and overall score</li>
              <li>• <strong>Click "Edit"</strong> to modify any bullet (60-150 characters)</li>
              <li>• When satisfied, click <strong>"Approve All & Continue"</strong> to generate your CV</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Bullets Grid */}
      <div className="grid grid-cols-1 gap-6">
        {bulletsData.artifacts.map((artifact: BulletsByArtifact) => (
          <BulletCard
            key={artifact.artifactId}
            artifactTitle={artifact.artifactTitle}
            bullets={artifact.bullets}
            onBulletEdit={handleBulletEdit}
          />
        ))}
      </div>

      {/* Action Buttons */}
      <div className="flex justify-between items-center pt-6 border-t-2 border-gray-200">
        {onBack && (
          <button
            onClick={onBack}
            disabled={isApproving}
            className="flex items-center gap-2 px-6 py-3 border-2 border-gray-300 text-gray-700 hover:text-gray-900 font-semibold rounded-xl hover:bg-gray-50 hover:border-gray-400 transition-all duration-200 transform hover:scale-105 disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
          >
            <span>Back</span>
          </button>
        )}

        <div className="flex-1" />

        <div className="flex flex-col items-end gap-3">
          <div className="text-center">
            <div className="text-sm font-bold text-gray-900">
              Ready to assemble your CV?
            </div>
            <div className="text-xs text-gray-500">
              All bullets will be used to create your final CV
            </div>
          </div>

          <button
            onClick={handleApproveAll}
            disabled={isApproving}
            className="group relative overflow-hidden bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold px-8 py-4 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 transform hover:scale-105 disabled:transform-none disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <div className="flex items-center gap-3">
              {isApproving ? (
                <>
                  <RefreshCw className="h-5 w-5 animate-spin" />
                  <span>Approving...</span>
                </>
              ) : (
                <>
                  <CheckCircle className="h-5 w-5" />
                  <span>Approve All & Continue</span>
                  <ArrowRight className="h-5 w-5 transform group-hover:translate-x-1 transition-transform duration-200" />
                </>
              )}
            </div>
            {!isApproving && (
              <div className="absolute inset-0 bg-white/10 transform -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
