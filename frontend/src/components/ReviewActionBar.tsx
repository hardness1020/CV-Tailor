/**
 * ReviewActionBar component (ft-030 - Anti-Hallucination Improvements)
 *
 * Provides action buttons for reviewing flagged bullet points.
 * Implements ADR-044: Review Workflow UX.
 *
 * Actions:
 * - Approve: Accept bullet as-is
 * - Edit: Modify bullet text manually
 * - Reject: Reject bullet (optionally trigger regeneration)
 */

import { useState } from 'react'
import { CheckCircle, XCircle, Edit3, RotateCcw } from 'lucide-react'
import { cn } from '@/utils/cn'
import { Button } from './ui/Button'

interface ReviewActionBarProps {
  bulletId: number;
  bulletText: string;
  isBlocked?: boolean;
  onApprove: (bulletId: number) => void | Promise<void>;
  onReject: (bulletId: number, regenerate?: boolean) => void | Promise<void>;
  onEdit: (bulletId: number, newText: string) => void | Promise<void>;
  isLoading?: boolean;
  className?: string;
}

export default function ReviewActionBar({
  bulletId,
  bulletText,
  isBlocked = false,
  onApprove,
  onReject,
  onEdit,
  isLoading = false,
  className
}: ReviewActionBarProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editedText, setEditedText] = useState(bulletText)
  const [showRegenerateOption, setShowRegenerateOption] = useState(false)

  const handleApprove = async () => {
    await onApprove(bulletId)
  }

  const handleReject = async (regenerate: boolean = false) => {
    await onReject(bulletId, regenerate)
    setShowRegenerateOption(false)
  }

  const handleStartEdit = () => {
    setEditedText(bulletText)
    setIsEditing(true)
  }

  const handleSaveEdit = async () => {
    if (editedText.trim() && editedText !== bulletText) {
      await onEdit(bulletId, editedText)
    }
    setIsEditing(false)
  }

  const handleCancelEdit = () => {
    setEditedText(bulletText)
    setIsEditing(false)
  }

  if (isEditing) {
    return (
      <div className={cn('space-y-3', className)}>
        {/* Edit Mode */}
        <div className="space-y-2">
          <label className="block text-sm font-bold text-gray-700">
            Edit Bullet Text
          </label>
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            className={cn(
              'w-full p-3 text-sm rounded-lg border-2',
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
              'transition-all duration-200'
            )}
            rows={3}
            minLength={60}
            maxLength={150}
            disabled={isLoading}
          />
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>
              {editedText.length} / 150 characters
            </span>
            {editedText.length < 60 && (
              <span className="text-amber-600 font-bold">
                Minimum 60 characters required
              </span>
            )}
          </div>
        </div>

        {/* Edit Actions */}
        <div className="flex gap-2">
          <Button
            onClick={handleSaveEdit}
            disabled={isLoading || editedText.length < 60 || editedText.length > 150 || editedText === bulletText}
            className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
          >
            <CheckCircle className="h-4 w-4 mr-2" />
            Save Changes
          </Button>
          <Button
            onClick={handleCancelEdit}
            disabled={isLoading}
            variant="outline"
            className="flex-1"
          >
            Cancel
          </Button>
        </div>
      </div>
    )
  }

  if (showRegenerateOption) {
    return (
      <div className={cn('space-y-3', className)}>
        {/* Regenerate Confirmation */}
        <div className="p-3 bg-amber-50 border-2 border-amber-200 rounded-lg">
          <p className="text-sm text-amber-800 mb-3">
            Would you like to regenerate this bullet automatically?
          </p>
          <div className="flex gap-2">
            <Button
              onClick={() => handleReject(true)}
              disabled={isLoading}
              className="flex-1 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700"
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Yes, Regenerate
            </Button>
            <Button
              onClick={() => handleReject(false)}
              disabled={isLoading}
              variant="outline"
              className="flex-1"
            >
              No, Just Remove
            </Button>
            <Button
              onClick={() => setShowRegenerateOption(false)}
              disabled={isLoading}
              variant="outline"
            >
              Cancel
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('space-y-3', className)}>
      {/* Blocked Warning */}
      {isBlocked && (
        <div className="p-3 bg-red-50 border-2 border-red-200 rounded-lg">
          <div className="flex items-start gap-2">
            <XCircle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-bold text-red-800">
                Blocked from Finalization
              </p>
              <p className="text-xs text-red-600 mt-1">
                This bullet has critical confidence issues and cannot be used without editing or approval override.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Primary Actions */}
      <div className="grid grid-cols-3 gap-2">
        {/* Approve Button */}
        <Button
          onClick={handleApprove}
          disabled={isLoading}
          className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
        >
          <CheckCircle className="h-4 w-4 mr-1.5" />
          Approve
        </Button>

        {/* Edit Button */}
        <Button
          onClick={handleStartEdit}
          disabled={isLoading}
          className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700"
        >
          <Edit3 className="h-4 w-4 mr-1.5" />
          Edit
        </Button>

        {/* Reject Button */}
        <Button
          onClick={() => setShowRegenerateOption(true)}
          disabled={isLoading}
          variant="outline"
          className="border-red-300 text-red-700 hover:bg-red-50 hover:border-red-400"
        >
          <XCircle className="h-4 w-4 mr-1.5" />
          Reject
        </Button>
      </div>

      {/* Helper Text */}
      <p className="text-xs text-gray-500 text-center">
        Review the source evidence above before taking action
      </p>
    </div>
  )
}
