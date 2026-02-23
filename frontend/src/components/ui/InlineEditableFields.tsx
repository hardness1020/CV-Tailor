/**
 * Inline Editable Field Components
 * Provides inline editing for artifact fields matching the wizard Step 6 UX pattern
 */

import React, { useState, useEffect } from 'react'
import { Edit2, Save, X, XCircle, Plus, Calendar } from 'lucide-react'
import { cn } from '@/utils/cn'

// ============================================================================
// Shared Types and Utilities
// ============================================================================

// Character counter component (from EvidenceContentViewer)
const CharacterCounter: React.FC<{ current: number; max?: number }> = ({ current, max }) => {
  const isNearLimit = max && current > max * 0.9
  const isOverLimit = max && current > max

  return (
    <div
      className={`text-xs mt-1 ${
        isOverLimit ? 'text-red-600 font-medium' : isNearLimit ? 'text-amber-600' : 'text-gray-500'
      }`}
    >
      {current}{max ? `/${max}` : ''} characters
    </div>
  )
}

// ============================================================================
// InlineEditableText - For single-line text (title)
// ============================================================================

interface InlineEditableTextProps {
  value: string
  onSave: (value: string) => Promise<void>
  placeholder?: string
  className?: string
  inputClassName?: string
  maxLength?: number
}

export const InlineEditableText: React.FC<InlineEditableTextProps> = ({
  value,
  onSave,
  placeholder = 'Enter text...',
  className,
  inputClassName,
  maxLength
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editedValue, setEditedValue] = useState(value)
  const [isDirty, setIsDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isEditing) {
      setEditedValue(value)
      setIsDirty(false)
    }
  }, [isEditing, value])

  useEffect(() => {
    if (isEditing) {
      setIsDirty(editedValue !== value)
    }
  }, [editedValue, value, isEditing])

  const handleSave = async () => {
    if (!isDirty) {
      setIsEditing(false)
      return
    }

    setSaving(true)
    try {
      await onSave(editedValue)
      setIsEditing(false)
    } catch (error) {
      console.error('Save failed:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    if (isDirty) {
      const confirmDiscard = window.confirm(
        'You have unsaved changes. Are you sure you want to discard them?'
      )
      if (!confirmDiscard) return
    }

    setEditedValue(value || '')
    setIsDirty(false)
    setIsEditing(false)
  }

  if (!isEditing) {
    return (
      <div
        className={cn(
          'group flex items-center gap-2 cursor-pointer hover:bg-purple-50/30 rounded px-2 py-1 transition-colors',
          className
        )}
        onClick={() => setIsEditing(true)}
      >
        <span className="flex-1">{value || placeholder}</span>
        <Edit2 className="h-4 w-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)}>
      <input
        type="text"
        value={editedValue}
        onChange={(e) => setEditedValue(e.target.value)}
        maxLength={maxLength}
        className={cn(
          'w-full px-3 py-2 border-2 border-purple-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent',
          inputClassName
        )}
        placeholder={placeholder}
        autoFocus
      />
      {maxLength && <CharacterCounter current={editedValue.length} max={maxLength} />}

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleCancel}
          disabled={saving}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <X className="h-4 w-4" />
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !isDirty}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          title={!isDirty ? 'No changes to save' : ''}
        >
          {saving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Saving...
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Save
            </>
          )}
        </button>
      </div>
    </div>
  )
}

// ============================================================================
// InlineEditableTextarea - For multi-line text (description, userContext)
// ============================================================================

interface InlineEditableTextareaProps {
  value: string | undefined
  onSave: (value: string) => Promise<void>
  placeholder?: string
  rows?: number
  maxLength?: number
  className?: string
}

export const InlineEditableTextarea: React.FC<InlineEditableTextareaProps> = ({
  value,
  onSave,
  placeholder = 'Enter text...',
  rows = 4,
  maxLength = 500,
  className
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editedValue, setEditedValue] = useState(value || '')
  const [isDirty, setIsDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isEditing) {
      setEditedValue(value || '')
      setIsDirty(false)
    }
  }, [isEditing, value])

  useEffect(() => {
    if (isEditing) {
      setIsDirty(editedValue !== value)
    }
  }, [editedValue, value, isEditing])

  const handleSave = async () => {
    if (!isDirty) {
      setIsEditing(false)
      return
    }

    setSaving(true)
    try {
      await onSave(editedValue)
      setIsEditing(false)
    } catch (error) {
      console.error('Save failed:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    if (isDirty) {
      const confirmDiscard = window.confirm(
        'You have unsaved changes. Are you sure you want to discard them?'
      )
      if (!confirmDiscard) return
    }

    setEditedValue(value || '')
    setIsDirty(false)
    setIsEditing(false)
  }

  if (!isEditing) {
    return (
      <div
        className={cn(
          'group cursor-pointer hover:bg-purple-50/30 rounded p-3 transition-colors relative',
          className
        )}
        onClick={() => setIsEditing(true)}
      >
        <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
          {value || <span className="text-gray-400">{placeholder}</span>}
        </p>
        <Edit2 className="h-4 w-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity absolute top-2 right-2" />
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)}>
      <textarea
        value={editedValue}
        onChange={(e) => setEditedValue(e.target.value)}
        rows={rows}
        className="w-full px-3 py-2 border-2 border-purple-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
        placeholder={placeholder}
        autoFocus
      />
      <CharacterCounter current={editedValue.length} max={maxLength} />

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleCancel}
          disabled={saving}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <X className="h-4 w-4" />
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !isDirty}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          title={!isDirty ? 'No changes to save' : ''}
        >
          {saving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Saving...
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Save
            </>
          )}
        </button>
      </div>
    </div>
  )
}

// ============================================================================
// InlineEditableSelect - For select dropdowns (artifactType)
// ============================================================================

interface SelectOption {
  value: string
  label: string
}

interface InlineEditableSelectProps {
  value: string
  options: SelectOption[]
  onSave: (value: string) => Promise<void>
  className?: string
}

export const InlineEditableSelect: React.FC<InlineEditableSelectProps> = ({
  value,
  options,
  onSave,
  className
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editedValue, setEditedValue] = useState(value)
  const [isDirty, setIsDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isEditing) {
      setEditedValue(value)
      setIsDirty(false)
    }
  }, [isEditing, value])

  useEffect(() => {
    if (isEditing) {
      setIsDirty(editedValue !== value)
    }
  }, [editedValue, value, isEditing])

  const handleSave = async () => {
    if (!isDirty) {
      setIsEditing(false)
      return
    }

    setSaving(true)
    try {
      await onSave(editedValue)
      setIsEditing(false)
    } catch (error) {
      console.error('Save failed:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setEditedValue(value || '')
    setIsDirty(false)
    setIsEditing(false)
  }

  const selectedOption = options.find(opt => opt.value === value)

  if (!isEditing) {
    return (
      <div
        className={cn(
          'group inline-flex items-center gap-2 cursor-pointer hover:bg-purple-50/30 rounded px-2 py-1 transition-colors',
          className
        )}
        onClick={() => setIsEditing(true)}
      >
        <span>{selectedOption?.label || value}</span>
        <Edit2 className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)}>
      <select
        value={editedValue}
        onChange={(e) => setEditedValue(e.target.value)}
        className="px-3 py-2 border-2 border-purple-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
        autoFocus
      >
        {options.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleCancel}
          disabled={saving}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <X className="h-4 w-4" />
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !isDirty}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          title={!isDirty ? 'No changes to save' : ''}
        >
          {saving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Saving...
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Save
            </>
          )}
        </button>
      </div>
    </div>
  )
}

// ============================================================================
// InlineEditableDateRange - For start/end dates
// ============================================================================

interface InlineEditableDateRangeProps {
  startDate: string
  endDate: string | null
  onSave: (startDate: string, endDate: string | null) => Promise<void>
  className?: string
}

export const InlineEditableDateRange: React.FC<InlineEditableDateRangeProps> = ({
  startDate,
  endDate,
  onSave,
  className
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editedStartDate, setEditedStartDate] = useState(startDate)
  const [editedEndDate, setEditedEndDate] = useState(endDate || '')
  const [isDirty, setIsDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isEditing) {
      setEditedStartDate(startDate)
      setEditedEndDate(endDate || '')
      setIsDirty(false)
    }
  }, [isEditing, startDate, endDate])

  useEffect(() => {
    if (isEditing) {
      const hasChanges = editedStartDate !== startDate || (editedEndDate || null) !== endDate
      setIsDirty(hasChanges)
    }
  }, [editedStartDate, editedEndDate, startDate, endDate, isEditing])

  const handleSave = async () => {
    if (!isDirty) {
      setIsEditing(false)
      return
    }

    setSaving(true)
    try {
      await onSave(editedStartDate, editedEndDate || null)
      setIsEditing(false)
    } catch (error) {
      console.error('Save failed:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    if (isDirty) {
      const confirmDiscard = window.confirm(
        'You have unsaved changes. Are you sure you want to discard them?'
      )
      if (!confirmDiscard) return
    }

    setEditedStartDate(startDate)
    setEditedEndDate(endDate || '')
    setIsDirty(false)
    setIsEditing(false)
  }

  const formatDateDisplay = (start: string, end: string | null) => {
    const startFormatted = new Date(start).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
    const endFormatted = end ? new Date(end).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 'Present'
    return `${startFormatted} - ${endFormatted}`
  }

  if (!isEditing) {
    return (
      <div
        className={cn(
          'group inline-flex items-center gap-2 cursor-pointer hover:bg-purple-50/30 rounded px-2 py-1 transition-colors',
          className
        )}
        onClick={() => setIsEditing(true)}
      >
        <Calendar className="h-4 w-4 text-gray-500" />
        <span>{formatDateDisplay(startDate, endDate)}</span>
        <Edit2 className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    )
  }

  return (
    <div className={cn('space-y-3', className)}>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Start Date</label>
          <input
            type="date"
            value={editedStartDate}
            onChange={(e) => setEditedStartDate(e.target.value)}
            className="w-full px-3 py-2 border-2 border-purple-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">End Date (optional)</label>
          <input
            type="date"
            value={editedEndDate}
            onChange={(e) => setEditedEndDate(e.target.value)}
            className="w-full px-3 py-2 border-2 border-purple-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
            placeholder="Present"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleCancel}
          disabled={saving}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <X className="h-4 w-4" />
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !isDirty}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          title={!isDirty ? 'No changes to save' : ''}
        >
          {saving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Saving...
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Save
            </>
          )}
        </button>
      </div>
    </div>
  )
}

// ============================================================================
// InlineEditableTags - For technology tags
// ============================================================================

interface InlineEditableTagsProps {
  tags: string[]
  onSave: (tags: string[]) => Promise<void>
  placeholder?: string
  className?: string
}

export const InlineEditableTags: React.FC<InlineEditableTagsProps> = ({
  tags,
  onSave,
  placeholder = 'Add tags...',
  className
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editedTags, setEditedTags] = useState<string[]>(tags)
  const [inputValue, setInputValue] = useState('')
  const [isDirty, setIsDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isEditing) {
      setEditedTags(tags)
      setInputValue('')
      setIsDirty(false)
    }
  }, [isEditing, tags])

  useEffect(() => {
    if (isEditing) {
      const hasChanges = JSON.stringify(editedTags.sort()) !== JSON.stringify(tags.sort())
      setIsDirty(hasChanges)
    }
  }, [editedTags, tags, isEditing])

  const handleAddTag = () => {
    const trimmed = inputValue.trim()
    if (trimmed && !editedTags.includes(trimmed)) {
      setEditedTags([...editedTags, trimmed])
      setInputValue('')
    }
  }

  const handleRemoveTag = (tagToRemove: string) => {
    setEditedTags(editedTags.filter(tag => tag !== tagToRemove))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAddTag()
    }
  }

  const handleSave = async () => {
    if (!isDirty) {
      setIsEditing(false)
      return
    }

    setSaving(true)
    try {
      await onSave(editedTags)
      setIsEditing(false)
    } catch (error) {
      console.error('Save failed:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    if (isDirty) {
      const confirmDiscard = window.confirm(
        'You have unsaved changes. Are you sure you want to discard them?'
      )
      if (!confirmDiscard) return
    }

    setEditedTags(tags)
    setInputValue('')
    setIsDirty(false)
    setIsEditing(false)
  }

  if (!isEditing) {
    return (
      <div
        className={cn(
          'group cursor-pointer hover:bg-purple-50/30 rounded p-3 transition-colors relative',
          className
        )}
        onClick={() => setIsEditing(true)}
      >
        <div className="flex flex-wrap gap-2">
          {tags.map((tag, index) => (
            <span
              key={index}
              className="inline-flex items-center px-3 py-1 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-900 text-sm rounded-lg border border-purple-300 font-semibold"
            >
              {tag}
            </span>
          ))}
          {tags.length === 0 && (
            <span className="text-sm text-gray-400">{placeholder}</span>
          )}
        </div>
        <Edit2 className="h-4 w-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity absolute top-2 right-2" />
      </div>
    )
  }

  return (
    <div className={cn('space-y-3', className)}>
      {/* Edited tags */}
      <div className="flex flex-wrap gap-2">
        {editedTags.map((tag, idx) => (
          <span
            key={idx}
            className="inline-flex items-center gap-1 px-3 py-1 bg-gradient-to-r from-purple-100 to-blue-100 text-purple-800 rounded-full text-sm shadow-sm"
          >
            {tag}
            <button
              type="button"
              onClick={() => handleRemoveTag(tag)}
              className="hover:bg-purple-200 rounded-full p-0.5 transition-colors"
              title="Remove"
            >
              <XCircle className="w-3.5 h-3.5" />
            </button>
          </span>
        ))}
      </div>

      {/* Add new tag */}
      <div className="flex gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
          placeholder={placeholder}
        />
        <button
          type="button"
          onClick={handleAddTag}
          className="flex items-center gap-1 px-3 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-md hover:from-purple-700 hover:to-blue-700 transition-all shadow-sm text-sm"
        >
          <Plus className="w-4 h-4" />
          Add
        </button>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleCancel}
          disabled={saving}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <X className="h-4 w-4" />
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !isDirty}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          title={!isDirty ? 'No changes to save' : ''}
        >
          {saving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Saving...
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Save
            </>
          )}
        </button>
      </div>
    </div>
  )
}

// ============================================================================
// InlineEditableList - For achievements (one per line)
// ============================================================================

interface InlineEditableListProps {
  items: string[]
  onSave: (items: string[]) => Promise<void>
  placeholder?: string
  className?: string
}

export const InlineEditableList: React.FC<InlineEditableListProps> = ({
  items,
  onSave,
  placeholder = 'Enter items...',
  className
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editedValue, setEditedValue] = useState('')
  const [isDirty, setIsDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isEditing) {
      setEditedValue(items.join('\n'))
      setIsDirty(false)
    }
  }, [isEditing, items])

  useEffect(() => {
    if (isEditing) {
      const editedItems = editedValue.split('\n').filter(item => item.trim())
      const hasChanges = JSON.stringify(editedItems) !== JSON.stringify(items)
      setIsDirty(hasChanges)
    }
  }, [editedValue, items, isEditing])

  const handleSave = async () => {
    if (!isDirty) {
      setIsEditing(false)
      return
    }

    const itemsToSave = editedValue.split('\n').filter(item => item.trim())

    setSaving(true)
    try {
      await onSave(itemsToSave)
      setIsEditing(false)
    } catch (error) {
      console.error('Save failed:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    if (isDirty) {
      const confirmDiscard = window.confirm(
        'You have unsaved changes. Are you sure you want to discard them?'
      )
      if (!confirmDiscard) return
    }

    setEditedValue(items.join('\n'))
    setIsDirty(false)
    setIsEditing(false)
  }

  if (!isEditing) {
    return (
      <div
        className={cn(
          'group cursor-pointer hover:bg-purple-50/30 rounded p-3 transition-colors relative',
          className
        )}
        onClick={() => setIsEditing(true)}
      >
        {items.length > 0 ? (
          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={index} className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 text-xs font-semibold flex items-center justify-center mt-0.5">
                  {index + 1}
                </span>
                <span className="text-sm text-gray-800 leading-relaxed">{item}</span>
              </div>
            ))}
          </div>
        ) : (
          <span className="text-sm text-gray-400">{placeholder}</span>
        )}
        <Edit2 className="h-4 w-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity absolute top-2 right-2" />
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)}>
      <textarea
        value={editedValue}
        onChange={(e) => setEditedValue(e.target.value)}
        rows={6}
        className="w-full px-3 py-2 border-2 border-purple-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
        placeholder={`${placeholder}\n(One item per line)`}
        autoFocus
      />
      <CharacterCounter current={editedValue.length} />

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleCancel}
          disabled={saving}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <X className="h-4 w-4" />
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !isDirty}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          title={!isDirty ? 'No changes to save' : ''}
        >
          {saving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Saving...
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Save
            </>
          )}
        </button>
      </div>
    </div>
  )
}
