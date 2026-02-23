import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Card } from '@/components/ui/Card'
import { Modal } from '@/components/ui/Modal'
import type { EvidenceLink } from '@/types'
import { apiClient } from '@/services/apiClient'

interface EvidenceLinkManagerProps {
  artifactId: number
  links: EvidenceLink[]
  onUpdate: () => void
}

export interface LinkFormData {
  url: string
  evidenceType: string
  description: string
}

const LINK_TYPES = [
  { value: 'github', label: 'GitHub Repository' },
  { value: 'document', label: 'Document/PDF' }
]

const getLinkIcon = (linkType: string) => {
  switch (linkType) {
    case 'github':
      return '🔗'
    case 'document':
      return '📄'
    default:
      return '🔗'
  }
}

const getEvidenceUrl = (link: EvidenceLink): string => {
  // For document type, check if URL is relative path (starts with /) and prefix with backend URL
  if (link.evidenceType === 'document' && link.url.startsWith('/')) {
    const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    return `${backendUrl}${link.url}`
  }
  return link.url
}

const EvidenceLinkItem: React.FC<{
  link: EvidenceLink
  onEdit: () => void
  onDelete: () => void
}> = ({ link, onEdit, onDelete }) => {
  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this evidence link?')) {
      onDelete()
    }
  }

  const getLinkTypeLabel = (type: string) => {
    const linkType = LINK_TYPES.find(t => t.value === type)
    return linkType ? linkType.label : type
  }

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-lg">{getLinkIcon(link.evidenceType)}</span>
            <span className="font-medium text-gray-900">{getLinkTypeLabel(link.evidenceType)}</span>
          </div>

          <a
            href={getEvidenceUrl(link)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 underline block truncate"
          >
            {link.url}
          </a>

          {link.description && (
            <p className="text-gray-600 mt-1 text-sm">{link.description}</p>
          )}

          <div className="flex items-center space-x-4 mt-2">
            <div className="flex items-center space-x-1">
              {link.isAccessible ? (
                <>
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  <span className="text-sm text-green-600">Accessible</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                  <span className="text-sm text-red-600">Not accessible</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 ml-4">
          <Button
            size="sm"
            variant="secondary"
            onClick={onEdit}
          >
            Edit
          </Button>
          <Button
            size="sm"
            variant="danger"
            onClick={handleDelete}
          >
            Delete
          </Button>
        </div>
      </div>
    </div>
  )
}

export const AddEvidenceLinkForm: React.FC<{
  onSave: (data: LinkFormData) => Promise<void>
  onUpload?: (files: File[], description?: string) => Promise<void>
  onCancel: () => void
}> = ({ onSave, onUpload, onCancel }) => {
  const [mode, setMode] = useState<'link' | 'upload'>('link')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [uploadDescription, setUploadDescription] = useState('')
  const [isUploading, setIsUploading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<LinkFormData>({
    defaultValues: {
      url: '',
      evidenceType: 'website',
      description: ''
    }
  })

  const onSubmit = async (data: LinkFormData) => {
    await onSave(data)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    setSelectedFiles(files)
  }

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!onUpload || selectedFiles.length === 0) return

    setIsUploading(true)
    try {
      await onUpload(selectedFiles, uploadDescription)
      setSelectedFiles([])
      setUploadDescription('')
    } catch (error) {
      console.error('Upload failed:', error)
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
      {/* Mode Toggle */}
      <div className="flex items-center gap-4 mb-4">
        <button
          type="button"
          onClick={() => setMode('link')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            mode === 'link'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Add Link
        </button>
        {onUpload && (
          <button
            type="button"
            onClick={() => setMode('upload')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              mode === 'upload'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Upload File
          </button>
        )}
      </div>

      {/* Link Mode Form */}
      {mode === 'link' && (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Input
            label="URL"
            placeholder="https://..."
            error={errors.url?.message}
            required
            {...register('url', {
              required: 'URL is required',
              pattern: {
                value: /^https?:\/\/.+/,
                message: 'Please enter a valid URL starting with http:// or https://'
              }
            })}
          />
        </div>

        <div>
          <Select
            label="Link Type"
            options={LINK_TYPES}
            error={errors.evidenceType?.message}
            {...register('evidenceType', { required: 'Link type is required' })}
          />
        </div>

        <div>
          <Input
            label="Description (optional)"
            placeholder="Brief description of this link"
            error={errors.description?.message}
            {...register('description', {
              maxLength: { value: 255, message: 'Description must be less than 255 characters' }
            })}
          />
        </div>

          <div className="flex items-center justify-end space-x-3">
            <Button
              type="button"
              variant="secondary"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={isSubmitting}
              disabled={isSubmitting}
            >
              Add Link
            </Button>
          </div>
        </form>
      )}

      {/* Upload Mode Form */}
      {mode === 'upload' && onUpload && (
        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select File(s)
            </label>
            <input
              type="file"
              onChange={handleFileSelect}
              multiple
              accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png"
              className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent p-2"
            />
            <p className="text-xs text-gray-500 mt-1">
              Supported formats: PDF, DOC, DOCX, TXT, JPG, PNG (Max 10MB per file)
            </p>

            {/* Selected Files Preview */}
            {selectedFiles.length > 0 && (
              <div className="mt-3 space-y-1">
                <p className="text-sm font-medium text-gray-700">Selected files:</p>
                {selectedFiles.map((file, index) => (
                  <div key={index} className="text-sm text-gray-600 flex items-center gap-2">
                    <span>📄</span>
                    <span>{file.name}</span>
                    <span className="text-gray-400">({(file.size / 1024).toFixed(1)} KB)</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description (optional)
            </label>
            <input
              type="text"
              value={uploadDescription}
              onChange={(e) => setUploadDescription(e.target.value)}
              placeholder="Brief description of the file(s)"
              maxLength={255}
              className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent p-2"
            />
          </div>

          <div className="flex items-center justify-end space-x-3">
            <Button
              type="button"
              variant="secondary"
              onClick={onCancel}
              disabled={isUploading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={isUploading}
              disabled={isUploading || selectedFiles.length === 0}
            >
              Upload {selectedFiles.length > 0 && `(${selectedFiles.length})`}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}

export const EditEvidenceLinkModal: React.FC<{
  link: EvidenceLink
  isOpen: boolean
  onClose: () => void
  onSave: (linkId: number, data: Partial<LinkFormData>) => Promise<void>
}> = ({ link, isOpen, onClose, onSave }) => {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<LinkFormData>({
    defaultValues: {
      url: link.url,
      evidenceType: link.evidenceType,
      description: link.description || ''
    }
  })

  const onSubmit = async (data: LinkFormData) => {
    await onSave(link.id, data)
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Evidence Link">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Input
            label="URL"
            placeholder="https://..."
            error={errors.url?.message}
            required
            {...register('url', {
              required: 'URL is required',
              pattern: {
                value: /^https?:\/\/.+/,
                message: 'Please enter a valid URL starting with http:// or https://'
              }
            })}
          />
        </div>

        <div>
          <Select
            label="Link Type"
            options={LINK_TYPES}
            error={errors.evidenceType?.message}
            {...register('evidenceType', { required: 'Link type is required' })}
          />
        </div>

        <div>
          <Input
            label="Description (optional)"
            placeholder="Brief description of this link"
            error={errors.description?.message}
            {...register('description', {
              maxLength: { value: 255, message: 'Description must be less than 255 characters' }
            })}
          />
        </div>

        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            loading={isSubmitting}
            disabled={isSubmitting}
          >
            Save Changes
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export const EvidenceLinkManager: React.FC<EvidenceLinkManagerProps> = ({
  artifactId,
  links,
  onUpdate
}) => {
  const [isAdding, setIsAdding] = useState(false)
  const [editingLink, setEditingLink] = useState<EvidenceLink | null>(null)

  const handleAddLink = async (linkData: LinkFormData) => {
    try {
      await apiClient.addEvidenceLink(artifactId, linkData)
      onUpdate()
      setIsAdding(false)
      toast.success('Evidence link added successfully')
    } catch (error) {
      console.error('Failed to add evidence link:', error)
      toast.error('Failed to add evidence link')
      throw error
    }
  }

  const handleEditLink = async (linkId: number, linkData: Partial<LinkFormData>) => {
    try {
      await apiClient.updateEvidenceLink(linkId, linkData)
      onUpdate()
      toast.success('Evidence link updated successfully')
    } catch (error) {
      console.error('Failed to update evidence link:', error)
      toast.error('Failed to update evidence link')
      throw error
    }
  }

  const handleDeleteLink = async (linkId: number) => {
    try {
      await apiClient.deleteEvidenceLink(linkId)
      onUpdate()
      toast.success('Evidence link deleted successfully')
    } catch (error) {
      console.error('Failed to delete evidence link:', error)
      toast.error('Failed to delete evidence link')
    }
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Evidence Links</h3>
          <p className="text-gray-600 text-sm">
            Add links to repositories, live applications, and supporting documents
          </p>
        </div>

        {!isAdding && (
          <Button
            onClick={() => setIsAdding(true)}
            size="sm"
          >
            + Add Evidence Link
          </Button>
        )}
      </div>

      <div className="space-y-4">
        {links.map(link => (
          <EvidenceLinkItem
            key={link.id}
            link={link}
            onEdit={() => setEditingLink(link)}
            onDelete={() => handleDeleteLink(link.id)}
          />
        ))}

        {links.length === 0 && !isAdding && (
          <div className="text-center py-8 text-gray-500">
            <p>No evidence links added yet</p>
            <p className="text-sm">Add links to showcase your work</p>
          </div>
        )}

        {isAdding && (
          <AddEvidenceLinkForm
            onSave={handleAddLink}
            onCancel={() => setIsAdding(false)}
          />
        )}
      </div>

      {editingLink && (
        <EditEvidenceLinkModal
          link={editingLink}
          isOpen={!!editingLink}
          onClose={() => setEditingLink(null)}
          onSave={handleEditLink}
        />
      )}
    </Card>
  )
}