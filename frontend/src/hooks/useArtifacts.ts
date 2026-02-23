import { useState } from 'react'
import toast from 'react-hot-toast'
import { useArtifactStore } from '@/stores/artifactStore'
import { apiClient } from '@/services/apiClient'
import type { ArtifactCreateData } from '@/types'

export function useArtifacts() {
  const {
    artifacts,
    selectedArtifacts,
    isLoading,
    error,
    addArtifact,
    updateArtifact,
    deleteArtifact,
    setLoading,
    setError,
    loadArtifacts,
  } = useArtifactStore()

  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({})

  const createArtifact = async (data: ArtifactCreateData, files?: File[]) => {
    setLoading(true)
    setError(null)
    try {
      // Create artifact
      const artifact = await apiClient.createArtifact(data)
      addArtifact(artifact)

      // Upload files if provided
      if (files && files.length > 0) {
        const uploadId = `upload-${Date.now()}`
        setUploadProgress({ [uploadId]: 0 })

        try {
          await apiClient.uploadArtifactFiles(artifact.id, files)
          setUploadProgress({ [uploadId]: 100 })

          // Reload the artifact to get updated file information
          const updatedArtifact = await apiClient.getArtifact(artifact.id)
          updateArtifact(artifact.id, updatedArtifact)
        } catch (uploadError) {
          console.error('File upload failed:', uploadError)
          toast.error('Artifact created but file upload failed')
        } finally {
          setTimeout(() => {
            setUploadProgress(prev => {
              const newProgress = { ...prev }
              delete newProgress[uploadId]
              return newProgress
            })
          }, 2000)
        }
      }

      toast.success('Artifact created successfully!')
      return artifact
    } catch (error) {
      console.error('Failed to create artifact:', error)
      setError('Failed to create artifact')
      toast.error('Failed to create artifact')
      throw error
    } finally {
      setLoading(false)
    }
  }

  const updateArtifactData = async (id: number, data: Partial<ArtifactCreateData>) => {
    setLoading(true)
    setError(null)
    try {
      const updatedArtifact = await apiClient.updateArtifact(id, data)
      updateArtifact(id, updatedArtifact)
      toast.success('Artifact updated successfully!')
      return updatedArtifact
    } catch (error) {
      console.error('Failed to update artifact:', error)
      setError('Failed to update artifact')
      toast.error('Failed to update artifact')
      throw error
    } finally {
      setLoading(false)
    }
  }

  const removeArtifact = async (id: number) => {
    setLoading(true)
    setError(null)
    try {
      await apiClient.deleteArtifact(id)
      deleteArtifact(id)
      toast.success('Artifact deleted successfully!')
    } catch (error) {
      console.error('Failed to delete artifact:', error)
      setError('Failed to delete artifact')
      toast.error('Failed to delete artifact')
      throw error
    } finally {
      setLoading(false)
    }
  }

  const bulkDelete = async (ids: number[]) => {
    setLoading(true)
    setError(null)
    try {
      await Promise.all(ids.map(id => apiClient.deleteArtifact(id)))
      ids.forEach(id => deleteArtifact(id))
      toast.success(`${ids.length} artifacts deleted successfully!`)
    } catch (error) {
      console.error('Failed to delete artifacts:', error)
      setError('Failed to delete artifacts')
      toast.error('Failed to delete some artifacts')
      throw error
    } finally {
      setLoading(false)
    }
  }

  const suggestSkills = async (query: string) => {
    try {
      return await apiClient.suggestSkills(query)
    } catch (error) {
      console.error('Failed to get skill suggestions:', error)
      return []
    }
  }

  // Note: loadArtifacts is called explicitly by components when needed

  return {
    artifacts,
    selectedArtifacts,
    isLoading,
    error,
    uploadProgress,
    loadArtifacts,
    createArtifact,
    updateArtifact: updateArtifactData,
    deleteArtifact: removeArtifact,
    bulkDelete,
    suggestSkills,
  }
}