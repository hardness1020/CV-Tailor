import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Download,
  FileText,
  Link as LinkIcon,
  QrCode,
  FileDown,
  X,
  CheckCircle,
  AlertCircle,
  Loader2
} from 'lucide-react'
import { useExport } from '@/hooks/useExport'
import { cn } from '@/utils/cn'
import type { } from '@/types'

const exportSchema = z.object({
  format: z.enum(['pdf', 'docx']),
  templateId: z.number().min(1, 'Please select a template'),
  options: z.object({
    includeEvidence: z.boolean().default(true),
    evidenceFormat: z.enum(['hyperlinks', 'footnotes', 'qr_codes']).default('hyperlinks'),
    pageMargins: z.enum(['narrow', 'normal', 'wide']).default('normal'),
    fontSize: z.number().min(10).max(14).default(11),
    colorScheme: z.enum(['monochrome', 'accent', 'full_color']).default('monochrome'),
  }),
  sections: z.object({
    includeProfessionalSummary: z.boolean().default(true),
    includeSkills: z.boolean().default(true),
    includeExperience: z.boolean().default(true),
    includeProjects: z.boolean().default(true),
    includeEducation: z.boolean().default(true),
    includeCertifications: z.boolean().default(true),
  }),
  watermark: z.object({
    text: z.string().min(1),
    opacity: z.number().min(0.1).max(0.5).default(0.3),
  }).optional(),
})

type ExportForm = z.infer<typeof exportSchema>

interface ExportDialogProps {
  generationId: string
  isOpen: boolean
  onClose: () => void
  onExportComplete?: (exportId: string) => void
}

const TEMPLATES = [
  {
    id: 1,
    name: 'Professional',
    description: 'Clean and professional design suitable for most industries',
    preview: '/templates/professional.png',
    category: 'modern',
  },
  {
    id: 2,
    name: 'Modern Tech',
    description: 'Contemporary design perfect for tech and startup roles',
    preview: '/templates/modern-tech.png',
    category: 'modern',
  },
  {
    id: 3,
    name: 'Classic',
    description: 'Traditional format preferred by conservative industries',
    preview: '/templates/classic.png',
    category: 'classic',
  },
  {
    id: 4,
    name: 'Creative',
    description: 'Stylish design for creative and design-focused roles',
    preview: '/templates/creative.png',
    category: 'creative',
  },
]

export default function ExportDialog({
  generationId,
  isOpen,
  onClose,
  onExportComplete,
}: ExportDialogProps) {
  const [currentExportId, setCurrentExportId] = useState<string | null>(null)
  const [step, setStep] = useState<'configure' | 'exporting' | 'completed'>('configure')

  const { exportDocument, completedExports } = useExport()

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid },
  } = useForm<ExportForm>({
    resolver: zodResolver(exportSchema),
    defaultValues: {
      format: 'pdf',
      templateId: 1,
      options: {
        includeEvidence: true,
        evidenceFormat: 'hyperlinks',
        pageMargins: 'normal',
        fontSize: 11,
        colorScheme: 'monochrome',
      },
      sections: {
        includeProfessionalSummary: true,
        includeSkills: true,
        includeExperience: true,
        includeProjects: true,
        includeEducation: true,
        includeCertifications: true,
      },
    },
  })

  const selectedFormat = watch('format')
  const selectedTemplate = watch('templateId')
  const includeEvidence = watch('options.includeEvidence')

  // Watch for export completion
  useEffect(() => {
    if (currentExportId) {
      const completedExport = completedExports.find(exp => exp.id === currentExportId)
      if (completedExport) {
        setStep('completed')
        onExportComplete?.(currentExportId)
      }
    }
  }, [completedExports, currentExportId, onExportComplete])

  const onSubmit = async (data: ExportForm) => {
    try {
      setStep('exporting')
      const exportData = {
        ...data,
        watermark: data.watermark?.text && data.watermark.text.trim() !== '' ? data.watermark : undefined,
      }
      const exportId = await exportDocument(generationId, exportData)
      setCurrentExportId(exportId)
    } catch (error) {
      console.error('Export failed:', error)
      setStep('configure')
    }
  }

  const handleDownload = async () => {
    if (currentExportId) {
      const exportJob = completedExports.find(exp => exp.id === currentExportId)
      if (exportJob?.downloadUrl) {
        // Use the download URL from the API response
        window.open(exportJob.downloadUrl, '_blank')
      }
    }
  }

  const resetDialog = () => {
    setStep('configure')
    setCurrentExportId(null)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={onClose} />

        <div className="inline-block w-full max-w-4xl my-8 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-lg">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">
              {step === 'configure' ? 'Export Document' :
               step === 'exporting' ? 'Exporting Document' :
               'Export Complete'}
            </h3>
            <button
              onClick={step === 'completed' ? resetDialog : onClose}
              className="text-gray-400 hover:text-gray-500 focus:outline-none focus:text-gray-500"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="px-6 py-4">
            {step === 'configure' && (
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                {/* Template Selection */}
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-4">Choose Template</h4>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {TEMPLATES.map((template) => (
                      <div
                        key={template.id}
                        className={cn(
                          'border-2 rounded-lg p-3 cursor-pointer transition-all',
                          selectedTemplate === template.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        )}
                        onClick={() => setValue('templateId', template.id)}
                      >
                        <div className="aspect-[3/4] bg-gray-100 rounded mb-2 flex items-center justify-center">
                          <FileText className="h-8 w-8 text-gray-400" />
                        </div>
                        <h5 className="font-medium text-sm text-gray-900">{template.name}</h5>
                        <p className="text-xs text-gray-500 mt-1">{template.description}</p>
                      </div>
                    ))}
                  </div>
                  {errors.templateId && (
                    <p className="mt-1 text-sm text-red-600">{errors.templateId.message}</p>
                  )}
                </div>

                {/* Format Selection */}
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Export Format</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <label className={cn(
                      'flex items-center p-4 border-2 rounded-lg cursor-pointer transition-all',
                      selectedFormat === 'pdf' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    )}>
                      <input
                        {...register('format')}
                        type="radio"
                        value="pdf"
                        className="sr-only"
                      />
                      <FileDown className="h-6 w-6 text-red-500 mr-3" />
                      <div>
                        <div className="font-medium text-gray-900">PDF</div>
                        <div className="text-sm text-gray-500">Best for online sharing and ATS</div>
                      </div>
                    </label>

                    <label className={cn(
                      'flex items-center p-4 border-2 rounded-lg cursor-pointer transition-all',
                      selectedFormat === 'docx' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    )}>
                      <input
                        {...register('format')}
                        type="radio"
                        value="docx"
                        className="sr-only"
                      />
                      <FileText className="h-6 w-6 text-blue-500 mr-3" />
                      <div>
                        <div className="font-medium text-gray-900">Word Document</div>
                        <div className="text-sm text-gray-500">Editable format for customization</div>
                      </div>
                    </label>
                  </div>
                </div>

                {/* Formatting Options */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-3">Page Layout</h4>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm text-gray-700 mb-1">Page Margins</label>
                        <select
                          {...register('options.pageMargins')}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="narrow">Narrow (more content)</option>
                          <option value="normal">Normal (balanced)</option>
                          <option value="wide">Wide (more whitespace)</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm text-gray-700 mb-1">Font Size</label>
                        <select
                          {...register('options.fontSize', { valueAsNumber: true })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value={10}>10pt (compact)</option>
                          <option value={11}>11pt (standard)</option>
                          <option value={12}>12pt (readable)</option>
                          <option value={13}>13pt (large)</option>
                          <option value={14}>14pt (extra large)</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-3">Styling</h4>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm text-gray-700 mb-1">Color Scheme</label>
                        <select
                          {...register('options.colorScheme')}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="monochrome">Black & White (ATS-safe)</option>
                          <option value="accent">Accent Colors</option>
                          <option value="full_color">Full Color</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Evidence Links */}
                <div>
                  <div className="flex items-center space-x-2 mb-3">
                    <input
                      {...register('options.includeEvidence')}
                      type="checkbox"
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label className="text-sm font-medium text-gray-900">
                      Include Evidence Links
                    </label>
                  </div>

                  {includeEvidence && (
                    <div className="ml-6 space-y-2">
                      <label className="flex items-center space-x-2">
                        <input
                          {...register('options.evidenceFormat')}
                          type="radio"
                          value="hyperlinks"
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                        />
                        <LinkIcon className="h-4 w-4 text-gray-400" />
                        <span className="text-sm text-gray-700">Clickable hyperlinks (PDF only)</span>
                      </label>

                      <label className="flex items-center space-x-2">
                        <input
                          {...register('options.evidenceFormat')}
                          type="radio"
                          value="footnotes"
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                        />
                        <FileText className="h-4 w-4 text-gray-400" />
                        <span className="text-sm text-gray-700">Numbered footnotes</span>
                      </label>

                      <label className="flex items-center space-x-2">
                        <input
                          {...register('options.evidenceFormat')}
                          type="radio"
                          value="qr_codes"
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                        />
                        <QrCode className="h-4 w-4 text-gray-400" />
                        <span className="text-sm text-gray-700">QR codes (for printed copies)</span>
                      </label>
                    </div>
                  )}
                </div>

                {/* Sections to Include */}
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Sections to Include</h4>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { key: 'includeProfessionalSummary', label: 'Professional Summary' },
                      { key: 'includeSkills', label: 'Key Skills' },
                      { key: 'includeExperience', label: 'Work Experience' },
                      { key: 'includeProjects', label: 'Projects' },
                      { key: 'includeEducation', label: 'Education' },
                      { key: 'includeCertifications', label: 'Certifications' },
                    ].map((section) => (
                      <label key={section.key} className="flex items-center space-x-2">
                        <input
                          {...register(`sections.${section.key}` as any)}
                          type="checkbox"
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <span className="text-sm text-gray-700">{section.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!isValid}
                    className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    <Download className="h-4 w-4" />
                    <span>Export {selectedFormat.toUpperCase()}</span>
                  </button>
                </div>
              </form>
            )}

            {step === 'exporting' && currentExportId && (
              <ExportProgress exportId={currentExportId} />
            )}

            {step === 'completed' && (
              <div className="text-center py-8">
                <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Export Complete!</h3>
                <p className="text-gray-600 mb-6">
                  Your document has been successfully exported and is ready for download.
                </p>
                <div className="flex justify-center space-x-3">
                  <button
                    onClick={handleDownload}
                    className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center space-x-2"
                  >
                    <Download className="h-4 w-4" />
                    <span>Download File</span>
                  </button>
                  <button
                    onClick={resetDialog}
                    className="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
                  >
                    Export Another
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

interface ExportProgressProps {
  exportId: string
}

function ExportProgress({ exportId }: ExportProgressProps) {
  const { activeExports } = useExport()
  const exportJob = activeExports.find(exp => exp.id === exportId)

  if (!exportJob) {
    return (
      <div className="text-center py-8">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin mx-auto mb-4" />
        <p className="text-gray-600">Initializing export...</p>
      </div>
    )
  }

  if (exportJob.status === 'failed') {
    return (
      <div className="text-center py-8">
        <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Export Failed</h3>
        <p className="text-gray-600 mb-6">
          {exportJob.errorMessage || 'Something went wrong during export. Please try again.'}
        </p>
      </div>
    )
  }

  return (
    <div className="text-center py-8">
      <div className="inline-flex items-center space-x-3 mb-6">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
        <span className="text-lg font-medium text-gray-900">Exporting Document...</span>
      </div>

      <div className="w-full max-w-md mx-auto bg-gray-200 rounded-full h-3 mb-4">
        <div
          className="bg-blue-600 h-3 rounded-full transition-all duration-500"
          style={{ width: `${exportJob.progressPercentage}%` }}
        />
      </div>

      <p className="text-sm text-gray-500 mb-6">{exportJob.progressPercentage}% complete</p>

      <div className="space-y-2 text-sm text-gray-600">
        <p>• Applying template formatting...</p>
        <p>• Generating document structure...</p>
        <p>• Processing evidence links...</p>
        <p>• Optimizing for compatibility...</p>
      </div>

      {exportJob.fileSize && (
        <p className="text-xs text-gray-500 mt-4">
          File size: {(exportJob.fileSize / 1024 / 1024).toFixed(1)} MB
        </p>
      )}
    </div>
  )
}