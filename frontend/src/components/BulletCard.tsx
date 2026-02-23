import { useState } from 'react'
import { FileText, Edit2, Check, X, Info, Undo, AlertTriangle, Eye } from 'lucide-react'
import { cn } from '@/utils/cn'
import BulletQualityBadge from './BulletQualityBadge'
import ConfidenceBadge from './ConfidenceBadge'
import ReviewModal from './ReviewModal'
import type { BulletPoint } from '@/types'

interface BulletCardProps {
  artifactTitle: string
  artifactDescription?: string
  bullets: BulletPoint[]
  onBulletEdit: (bulletId: number, newText: string) => Promise<void>
  onBulletApprove?: (bulletId: number) => void
  onBulletReject?: (bulletId: number, regenerate?: boolean) => void // ft-030
  readonly?: boolean
  className?: string
}

const BULLET_TYPE_LABELS = {
  achievement: { label: 'Achievement', color: 'blue', icon: '🎯' },
  technical: { label: 'Technical', color: 'purple', icon: '⚙️' },
  impact: { label: 'Impact', color: 'green', icon: '📈' }
}

export default function BulletCard({
  artifactTitle,
  artifactDescription,
  bullets,
  onBulletEdit,
  onBulletApprove,
  onBulletReject,
  readonly = false,
  className
}: BulletCardProps) {
  const [editingBulletId, setEditingBulletId] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [reviewingBullet, setReviewingBullet] = useState<BulletPoint | null>(null) // ft-030

  const handleStartEdit = (bullet: BulletPoint) => {
    setEditingBulletId(bullet.id)
    setEditText(bullet.text)
  }

  const handleSaveEdit = async (bulletId: number) => {
    if (editText.length < 60 || editText.length > 150) {
      return // Validation handled by UI
    }

    setIsSaving(true)
    try {
      await onBulletEdit(bulletId, editText)
      setEditingBulletId(null)
    } catch (error) {
      console.error('Failed to save bullet edit:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancelEdit = () => {
    setEditingBulletId(null)
    setEditText('')
  }

  const sortedBullets = [...bullets].sort((a, b) => a.position - b.position)

  return (
    <div className={cn('group', className)}>
      {/* Artifact Header */}
      <div className="bg-gradient-to-br from-gray-50 to-white rounded-t-2xl border-2 border-gray-200 border-b-0 p-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-2xl flex items-center justify-center shadow-lg flex-shrink-0">
            <FileText className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-bold text-gray-900 mb-1">{artifactTitle}</h3>
            {artifactDescription && (
              <p className="text-sm text-gray-600 line-clamp-2 leading-relaxed">
                {artifactDescription}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Bullets Container */}
      <div className="bg-white rounded-b-2xl border-2 border-gray-200 border-t-0 p-6 space-y-4">
        {sortedBullets.map((bullet) => {
          const isEditing = editingBulletId === bullet.id
          const typeInfo = BULLET_TYPE_LABELS[bullet.bulletType]
          const charCount = isEditing ? editText.length : bullet.text.length
          const isValidLength = charCount >= 60 && charCount <= 150

          return (
            <div
              key={bullet.id}
              className={cn(
                'group/bullet relative p-4 rounded-xl border-2 transition-all duration-300',
                isEditing
                  ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-indigo-50 shadow-lg'
                  : bullet.is_blocked // ft-030: Blocked bullets (CRITICAL tier)
                  ? 'border-red-400 bg-gradient-to-br from-red-50 to-rose-50 shadow-md'
                  : bullet.requires_review // ft-030: Flagged for review (LOW tier)
                  ? 'border-amber-400 bg-gradient-to-br from-amber-50 to-yellow-50'
                  : bullet.userApproved || bullet.is_approved
                  ? 'border-green-300 bg-gradient-to-br from-green-50/50 to-emerald-50/50'
                  : 'border-gray-200 bg-gray-50 hover:border-gray-300'
              )}
            >
              {/* Bullet Type Badge */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{typeInfo.icon}</span>
                  <div>
                    <div className={cn(
                      'text-xs font-bold uppercase tracking-wide',
                      typeInfo.color === 'blue' ? 'text-blue-700' :
                      typeInfo.color === 'purple' ? 'text-purple-700' :
                      'text-green-700'
                    )}>
                      Position {bullet.position}: {typeInfo.label}
                    </div>
                    {bullet.userEdited && !isEditing && (
                      <div className="flex items-center gap-1 text-xs text-amber-600 mt-1">
                        <Edit2 className="h-3 w-3" />
                        <span>Edited by you</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Quality and Confidence Badges */}
                <div className="flex flex-col items-end gap-2">
                  <BulletQualityBadge
                    qualityScore={bullet.qualityScore}
                    hasActionVerb={bullet.hasActionVerb}
                    keywordRelevanceScore={bullet.keywordRelevanceScore}
                  />
                  {/* ft-030: Confidence Badge */}
                  {bullet.confidence_tier && (
                    <ConfidenceBadge
                      confidence={bullet.confidence || 0}
                      tier={bullet.confidence_tier}
                      requiresReview={bullet.requires_review}
                      isBlocked={bullet.is_blocked}
                      showDetailed={false}
                    />
                  )}
                </div>
              </div>

              {/* ft-030: Review Warning Banner */}
              {(bullet.requires_review || bullet.is_blocked) && !isEditing && (
                <div className={cn(
                  'flex items-start gap-2 p-2 mb-3 rounded-lg border text-xs',
                  bullet.is_blocked
                    ? 'bg-red-50 border-red-200'
                    : 'bg-amber-50 border-amber-200'
                )}>
                  <AlertTriangle className={cn(
                    'h-4 w-4 flex-shrink-0 mt-0.5',
                    bullet.is_blocked ? 'text-red-600' : 'text-amber-600'
                  )} />
                  <p className={cn(
                    bullet.is_blocked ? 'text-red-800' : 'text-amber-800'
                  )}>
                    {bullet.is_blocked
                      ? 'This bullet is blocked from finalization due to low confidence. Please review and edit.'
                      : 'This bullet is flagged for review. Please verify the accuracy.'}
                  </p>
                </div>
              )}

              {/* Bullet Text or Edit Mode */}
              {isEditing ? (
                <div className="space-y-3">
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className={cn(
                      'w-full px-4 py-3 border-2 rounded-xl font-medium text-gray-900 resize-none focus:outline-none focus:ring-4 transition-all duration-200',
                      isValidLength
                        ? 'border-blue-300 focus:border-blue-500 focus:ring-blue-100'
                        : 'border-red-300 focus:border-red-500 focus:ring-red-100'
                    )}
                    rows={3}
                    placeholder="Edit bullet point (60-150 characters)..."
                  />

                  {/* Character Count */}
                  <div className="flex items-center justify-between text-xs">
                    <span className={cn(
                      'font-bold',
                      isValidLength ? 'text-green-700' : 'text-red-700'
                    )}>
                      {charCount} / 150 characters
                      {charCount < 60 && ` (need ${60 - charCount} more)`}
                    </span>
                    {bullet.originalText && (
                      <button
                        onClick={() => setEditText(bullet.originalText)}
                        className="flex items-center gap-1 px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 transition-colors"
                        title="Restore original LLM-generated text"
                      >
                        <Undo className="h-3 w-3" />
                        <span>Restore original</span>
                      </button>
                    )}
                  </div>

                  {/* Edit Actions */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSaveEdit(bullet.id)}
                      disabled={!isValidLength || isSaving}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold rounded-xl transition-all duration-300 transform hover:scale-105 disabled:transform-none disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      <Check className="h-4 w-4" />
                      <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      disabled={isSaving}
                      className="flex items-center justify-center gap-2 px-4 py-2 border-2 border-gray-300 text-gray-700 hover:bg-gray-50 font-bold rounded-xl transition-all duration-300"
                    >
                      <X className="h-4 w-4" />
                      <span>Cancel</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Bullet Text */}
                  <p className="text-sm text-gray-800 leading-relaxed font-medium">
                    • {bullet.text}
                  </p>

                  {/* Original Text Tooltip (if edited) */}
                  {bullet.userEdited && bullet.originalText && (
                    <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                      <Info className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div className="text-xs">
                        <div className="font-bold text-amber-800 mb-1">Original LLM text:</div>
                        <div className="text-amber-700">{bullet.originalText}</div>
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  {!readonly && (
                    <div className="flex items-center gap-2 pt-2 flex-wrap">
                      {/* ft-030: Review Button for flagged bullets */}
                      {(bullet.requires_review || bullet.is_blocked || bullet.confidence_tier) && (
                        <button
                          onClick={() => setReviewingBullet(bullet)}
                          className={cn(
                            'flex items-center gap-2 px-3 py-1.5 font-semibold rounded-lg transition-all duration-200 text-sm',
                            bullet.is_blocked
                              ? 'bg-red-100 hover:bg-red-200 text-red-800 border-2 border-red-300'
                              : bullet.requires_review
                              ? 'bg-amber-100 hover:bg-amber-200 text-amber-800 border-2 border-amber-300'
                              : 'border-2 border-blue-300 text-blue-700 hover:border-blue-500 hover:bg-blue-50'
                          )}
                        >
                          <Eye className="h-3.5 w-3.5" />
                          <span>Review Evidence</span>
                        </button>
                      )}

                      <button
                        onClick={() => handleStartEdit(bullet)}
                        className="flex items-center gap-2 px-3 py-1.5 border-2 border-gray-300 text-gray-700 hover:border-blue-500 hover:text-blue-700 hover:bg-blue-50 font-semibold rounded-lg transition-all duration-200 text-sm"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                        <span>Edit</span>
                      </button>

                      {onBulletApprove && !bullet.userApproved && !bullet.is_approved && (
                        <button
                          onClick={() => onBulletApprove(bullet.id)}
                          className="flex items-center gap-2 px-3 py-1.5 bg-green-100 hover:bg-green-200 text-green-800 font-semibold rounded-lg transition-all duration-200 text-sm"
                        >
                          <Check className="h-3.5 w-3.5" />
                          <span>Approve</span>
                        </button>
                      )}

                      {(bullet.userApproved || bullet.is_approved) && (
                        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-green-100 text-green-800 font-semibold rounded-lg text-sm">
                          <Check className="h-3.5 w-3.5" />
                          <span>Approved</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* ft-030: Review Modal */}
      {reviewingBullet && (
        <ReviewModal
          isOpen={true}
          onClose={() => setReviewingBullet(null)}
          bullet={reviewingBullet}
          onApprove={async (bulletId) => {
            if (onBulletApprove) {
              onBulletApprove(bulletId)
            }
            setReviewingBullet(null)
          }}
          onReject={async (bulletId, regenerate) => {
            if (onBulletReject) {
              onBulletReject(bulletId, regenerate)
            }
            setReviewingBullet(null)
          }}
          onEdit={async (bulletId, newText) => {
            await onBulletEdit(bulletId, newText)
            setReviewingBullet(null)
          }}
          isLoading={isSaving}
        />
      )}
    </div>
  )
}
