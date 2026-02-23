import React, { useState } from 'react'
import { Check, X, Edit2, Save, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Tooltip } from '@/components/ui/Tooltip'
import { cn } from '@/utils/cn'

export interface AchievementCardProps {
  achievement: string
  index: number
  isAccepted?: boolean
  isRejected?: boolean
  onApprove?: (achievement: string, index: number) => void
  onReject?: (achievement: string, index: number) => void
  onEdit?: (achievement: string, index: number, newText: string) => void
  showActions?: boolean
  className?: string
}

export const AchievementCard: React.FC<AchievementCardProps> = ({
  achievement,
  index,
  isAccepted = false,
  isRejected = false,
  onApprove,
  onReject,
  onEdit,
  showActions = true,
  className,
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState(achievement)

  const handleSaveEdit = () => {
    if (onEdit && editText.trim() !== achievement) {
      onEdit(achievement, index, editText.trim())
    }
    setIsEditing(false)
  }

  const handleCancelEdit = () => {
    setEditText(achievement)
    setIsEditing(false)
  }

  return (
    <Card
      className={cn(
        'p-4 transition-all duration-200',
        isAccepted && 'bg-green-50 border-2 border-green-200',
        isRejected && 'bg-red-50 border-2 border-red-200 opacity-60',
        !isAccepted && !isRejected && 'border border-gray-200 hover:border-gray-300',
        className
      )}
    >
      <div className="flex items-start gap-3">
        {/* Index Badge */}
        <div
          className={cn(
            'flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold',
            isAccepted
              ? 'bg-green-600 text-white'
              : isRejected
              ? 'bg-red-600 text-white'
              : 'bg-blue-600 text-white'
          )}
        >
          {index + 1}
        </div>

        {/* Achievement Text */}
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <div className="space-y-2">
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                className="w-full px-3 py-2 text-sm text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={3}
                autoFocus
              />
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="primary"
                  onClick={handleSaveEdit}
                  className="flex items-center gap-1"
                >
                  <Save className="h-3 w-3" />
                  Save
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCancelEdit}
                  className="flex items-center gap-1"
                >
                  <XCircle className="h-3 w-3" />
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <>
              <p
                className={cn(
                  'text-sm leading-relaxed',
                  isAccepted
                    ? 'text-green-900 font-medium'
                    : isRejected
                    ? 'text-red-900 line-through'
                    : 'text-gray-900'
                )}
              >
                {achievement}
              </p>

              {/* Status Indicator */}
              {(isAccepted || isRejected) && (
                <div className="mt-2 flex items-center gap-1.5">
                  {isAccepted && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full border border-green-300">
                      <Check className="h-3 w-3" />
                      Accepted
                    </span>
                  )}
                  {isRejected && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full border border-red-300">
                      <X className="h-3 w-3" />
                      Rejected
                    </span>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Action Buttons */}
        {showActions && !isEditing && (
          <div className="flex-shrink-0 flex items-center gap-1">
            {onEdit && !isRejected && (
              <Tooltip content="Edit achievement" position="left">
                <button
                  onClick={() => setIsEditing(true)}
                  className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                  aria-label="Edit achievement"
                >
                  <Edit2 className="h-4 w-4" />
                </button>
              </Tooltip>
            )}

            {onApprove && !isAccepted && !isRejected && (
              <Tooltip content="Approve achievement" position="left">
                <button
                  onClick={() => onApprove(achievement, index)}
                  className="p-1.5 text-gray-600 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                  aria-label="Approve achievement"
                >
                  <Check className="h-4 w-4" />
                </button>
              </Tooltip>
            )}

            {onReject && !isRejected && (
              <Tooltip content={isAccepted ? "Undo approval" : "Reject achievement"} position="left">
                <button
                  onClick={() => onReject(achievement, index)}
                  className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                  aria-label={isAccepted ? "Undo approval" : "Reject achievement"}
                >
                  <X className="h-4 w-4" />
                </button>
              </Tooltip>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
