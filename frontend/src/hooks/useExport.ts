import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/apiClient'
import type { ExportRequest, ExportJob } from '@/types'

export function useExport() {
  const [activeExports, setActiveExports] = useState<Map<string, ExportJob>>(new Map())
  const [completedExports, setCompletedExports] = useState<ExportJob[]>([])
  const [isExporting, setIsExporting] = useState(false)
  const [pollingIntervals, setPollingIntervals] = useState<Record<string, NodeJS.Timeout>>({})

  const exportDocument = async (generationId: string, exportRequest: ExportRequest) => {
    try {
      const response = await apiClient.exportDocument(generationId, exportRequest)
      const exportId = response.exportId

      // Add to active exports
      const exportJob: ExportJob = {
        id: exportId,
        status: 'processing',
        progressPercentage: 0,
      }

      setActiveExports(prev => new Map(prev).set(exportId, exportJob))
      setIsExporting(true)

      // Start polling for updates
      startPolling(exportId)

      toast.success('Export started!')
      return exportId
    } catch (error) {
      console.error('Failed to start export:', error)
      toast.error('Failed to start export')
      throw error
    }
  }

  const startPolling = useCallback((exportId: string) => {
    // Clear existing interval if any
    if (pollingIntervals[exportId]) {
      clearInterval(pollingIntervals[exportId])
    }

    const interval = setInterval(async () => {
      try {
        const exportJob = await apiClient.getExportStatus(exportId)

        setActiveExports(prev => {
          const newMap = new Map(prev)
          newMap.set(exportId, exportJob)
          return newMap
        })

        if (exportJob.status === 'completed') {
          // Move to completed exports
          setCompletedExports(prev => [exportJob, ...prev])
          setActiveExports(prev => {
            const newMap = new Map(prev)
            newMap.delete(exportId)
            return newMap
          })

          // Clear interval
          clearInterval(interval)
          setPollingIntervals(prev => {
            const newIntervals = { ...prev }
            delete newIntervals[exportId]
            return newIntervals
          })

          // Update exporting state
          setIsExporting(activeExports.size > 1)

          toast.success('Export completed!')
        } else if (exportJob.status === 'failed') {
          // Remove from active exports
          setActiveExports(prev => {
            const newMap = new Map(prev)
            newMap.delete(exportId)
            return newMap
          })

          // Clear interval
          clearInterval(interval)
          setPollingIntervals(prev => {
            const newIntervals = { ...prev }
            delete newIntervals[exportId]
            return newIntervals
          })

          // Update exporting state
          setIsExporting(activeExports.size > 1)

          toast.error(exportJob.errorMessage || 'Export failed')
        }
      } catch (error: any) {
        console.error('Failed to poll export status:', error)
        // Continue polling unless it's a 404 (export not found)
        if (error.response?.status === 404) {
          setActiveExports(prev => {
            const newMap = new Map(prev)
            newMap.delete(exportId)
            return newMap
          })
          clearInterval(interval)
          setPollingIntervals(prev => {
            const newIntervals = { ...prev }
            delete newIntervals[exportId]
            return newIntervals
          })
          setIsExporting(activeExports.size > 1)
        }
      }
    }, 1000) // Poll every second for exports (faster than generation)

    setPollingIntervals(prev => ({
      ...prev,
      [exportId]: interval
    }))
  }, [activeExports.size, pollingIntervals])

  const downloadExport = async (exportId: string, filename?: string) => {
    try {
      const blob = await apiClient.downloadExport(exportId)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename || `export-${exportId}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      toast.success('Download started!')
    } catch (error) {
      console.error('Failed to download export:', error)
      toast.error('Failed to download file')
      throw error
    }
  }

  const cancelExport = (exportId: string) => {
    // Clear polling
    if (pollingIntervals[exportId]) {
      clearInterval(pollingIntervals[exportId])
      setPollingIntervals(prev => {
        const newIntervals = { ...prev }
        delete newIntervals[exportId]
        return newIntervals
      })
    }

    // Remove from active exports
    setActiveExports(prev => {
      const newMap = new Map(prev)
      newMap.delete(exportId)
      return newMap
    })

    // Update exporting state
    setIsExporting(activeExports.size > 1)

    toast.success('Export cancelled')
  }

  const loadUserExports = async () => {
    try {
      const exports = await apiClient.getUserExports()
      // Add completed exports to state
      const completed = exports.filter(exp => exp.status === 'completed')
      setCompletedExports(completed)
    } catch (error) {
      console.error('Failed to load user exports:', error)
    }
  }

  const getAvailableTemplates = async () => {
    try {
      return await apiClient.getExportTemplates()
    } catch (error) {
      console.error('Failed to load export templates:', error)
      return []
    }
  }

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollingIntervals).forEach(interval => {
        clearInterval(interval)
      })
    }
  }, [pollingIntervals])

  // Load user exports on mount
  useEffect(() => {
    loadUserExports()
  }, [])

  return {
    activeExports: Array.from(activeExports.values()),
    completedExports,
    isExporting,
    exportDocument,
    downloadExport,
    cancelExport,
    loadUserExports,
    getAvailableTemplates,
  }
}