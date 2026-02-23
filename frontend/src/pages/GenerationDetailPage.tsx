import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { BulletRegenerationModal } from '@/components/BulletRegenerationModal'
import { useGenerationStatus } from '@/hooks/useGenerationStatus'
import { apiClient } from '@/services/apiClient'
import toast from 'react-hot-toast'
import type { GeneratedDocument, GenerationBulletsResponse, BulletPoint } from '@/types'

export default function GenerationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [generation, setGeneration] = useState<GeneratedDocument | null>(null)
  const [bullets, setBullets] = useState<GenerationBulletsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showRegenerationModal, setShowRegenerationModal] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)

  // Poll status for in-progress generations (ft-026)
  const { status: generationStatus, isPolling } = useGenerationStatus({
    generationId: id!,
    enabled: !!id && generation?.status !== undefined && !['completed', 'failed', 'bullets_ready'].includes(generation.status),
    pollingInterval: 10000,
    onComplete: async () => {
      toast.success('Generation complete!')
      // Reload full generation data
      await loadGenerationDetails()
    },
    onError: (error) => {
      toast.error(error)
    }
  })

  useEffect(() => {
    if (id) {
      loadGenerationDetails()
    }
  }, [id])

  const loadGenerationDetails = async () => {
    if (!id) return

    setIsLoading(true)
    try {
      const [genData, bulletsData] = await Promise.all([
        apiClient.getGeneration(id),
        apiClient.getGenerationBullets(id)
      ])
      setGeneration(genData)
      setBullets(bulletsData)
    } catch (error: any) {
      console.error('Failed to load generation details:', error)
      toast.error(error.response?.data?.error || 'Failed to load generation details')
    } finally {
      setIsLoading(false)
    }
  }

  const handleRegenerateBullets = async (refinementPrompt?: string) => {
    if (!id) return

    setIsRegenerating(true)
    try {
      const result = await apiClient.regenerateGenerationBullets(id, {
        refinementPrompt
      })

      toast.success(`${result.bullets_regenerated} bullets regenerated successfully!`)
      setShowRegenerationModal(false)

      // Reload bullets
      await loadGenerationDetails()
    } catch (error: any) {
      console.error('Failed to regenerate bullets:', error)
      toast.error(error.response?.data?.error || 'Failed to regenerate bullets')
    } finally {
      setIsRegenerating(false)
    }
  }

  const handleBulletAction = async (
    bulletId: number,
    action: 'approve' | 'reject' | 'edit',
    editedText?: string
  ) => {
    if (!id) return

    try {
      await apiClient.approveBulletActions(id, [{
        bullet_id: bulletId,
        action,
        edited_text: editedText
      }])

      toast.success(`Bullet ${action}d successfully`)
      await loadGenerationDetails()
    } catch (error: any) {
      console.error(`Failed to ${action} bullet:`, error)
      toast.error(error.response?.data?.error || `Failed to ${action} bullet`)
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <p>Loading generation details...</p>
      </div>
    )
  }

  if (!generation || !bullets) {
    return (
      <div className="container mx-auto px-4 py-8">
        <p>Generation not found</p>
        <Button onClick={() => navigate('/generations')} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Generations
        </Button>
      </div>
    )
  }

  const artifactCount = bullets.artifacts?.length || 0

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <Button
          variant="outline"
          onClick={() => navigate('/generations')}
          className="mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Generations
        </Button>

        <Card className="p-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold">{generation.jobTitle || 'Document Generation'}</h1>
              <p className="text-gray-600 mt-1">{generation.companyName || 'Company'}</p>
              <div className="mt-4 flex gap-4 text-sm text-gray-500">
                <span>Status: <span className="font-medium">{generation.status}</span></span>
                <span>Created: {new Date(generation.createdAt).toLocaleDateString()}</span>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => setShowRegenerationModal(true)}
                variant="outline"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Regenerate Bullets
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Progress Section - Show when polling (ft-026) */}
      {isPolling && generationStatus && (
        <Card className="p-6 mb-6 bg-blue-50 border-blue-200">
          <h2 className="text-lg font-semibold mb-4">Generation Progress</h2>

          {/* Progress Bar */}
          <div className="mb-4">
            <div className="flex justify-between text-sm mb-2">
              <span className="font-medium">
                {generationStatus.current_phase === 'bullet_generation' && 'Generating Bullets...'}
                {generationStatus.current_phase === 'assembly' && 'Assembling Document...'}
                {generationStatus.current_phase === 'bullet_review' && 'Ready for Review'}
                {generationStatus.current_phase === 'completed' && 'Completed'}
              </span>
              <span className="text-gray-600">{generationStatus.progress_percentage}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${generationStatus.progress_percentage}%` }}
              />
            </div>
          </div>

          {/* Bullet Generation Details */}
          {generationStatus.phase_details?.bullet_generation && (
            <div className="text-sm text-gray-700 space-y-1">
              <p>
                Processing artifacts: {generationStatus.phase_details.bullet_generation.artifacts_processed}
                / {generationStatus.phase_details.bullet_generation.artifacts_total}
              </p>
              <p>
                Bullets generated: {generationStatus.phase_details.bullet_generation.bullets_generated}
              </p>
            </div>
          )}

          {/* Sub-job Status List */}
          {generationStatus.bullet_generation_jobs && generationStatus.bullet_generation_jobs.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium">Artifact Processing:</p>
              {generationStatus.bullet_generation_jobs.map(job => (
                <div key={job.job_id} className="flex items-center justify-between text-sm p-2 bg-white rounded border border-gray-200">
                  <span className="truncate flex-1">{job.artifact_title}</span>
                  <span className={`font-medium ml-4 ${
                    job.status === 'completed' ? 'text-green-600' :
                    job.status === 'failed' ? 'text-red-600' :
                    job.status === 'processing' ? 'text-blue-600' :
                    'text-gray-500'
                  }`}>
                    {job.status} ({job.bullets_generated} bullets)
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Bullets by Artifact */}
      <div className="space-y-6">
        <h2 className="text-xl font-semibold">Generated Bullets</h2>
        {bullets.artifacts?.map((artifactGroup: any) => (
          <Card key={artifactGroup.artifact_id} className="p-6">
            <h3 className="text-lg font-medium mb-4">{artifactGroup.artifact_title}</h3>
            <div className="space-y-4">
              {artifactGroup.bullets?.map((bullet: BulletPoint) => (
                <div
                  key={bullet.id}
                  className={`p-4 rounded-lg border ${
                    bullet.userApproved
                      ? 'bg-green-50 border-green-200'
                      : bullet.userRejected
                      ? 'bg-red-50 border-red-200'
                      : 'bg-white border-gray-200'
                  }`}
                >
                  <p className="text-gray-800">{bullet.text}</p>
                  <div className="flex gap-2 mt-3">
                    {!bullet.userApproved && !bullet.userRejected && (
                      <>
                        <Button
                          size="sm"
                          onClick={() => handleBulletAction(bullet.id, 'approve')}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => handleBulletAction(bullet.id, 'reject')}
                        >
                          Reject
                        </Button>
                      </>
                    )}
                    {bullet.userApproved && (
                      <span className="text-sm text-green-700 font-medium">✓ Approved</span>
                    )}
                    {bullet.userRejected && (
                      <span className="text-sm text-red-700 font-medium">✗ Rejected</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      {/* Regeneration Modal */}
      <BulletRegenerationModal
        isOpen={showRegenerationModal}
        onClose={() => setShowRegenerationModal(false)}
        onRegenerate={handleRegenerateBullets}
        artifactCount={artifactCount}
        isLoading={isRegenerating}
      />
    </div>
  )
}
