/**
 * Hook for managing transcription projects.
 */
import { useState, useCallback } from 'react'
import { useApi } from './useApi'

export function useProjects() {
  const api = useApi()
  const [projects, setProjects] = useState([])
  const [currentProject, setCurrentProject] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchProjects = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get('/projects')
      setProjects(data)
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [api])

  const fetchProject = useCallback(async (projectId) => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get(`/projects/${projectId}`)
      setCurrentProject(data)
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [api])

  const createProject = useCallback(async (title, audioFile) => {
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('title', title)
      formData.append('audio_file', audioFile)

      const data = await api.post('/projects', formData)
      setCurrentProject(data)
      // Add to projects list
      setProjects(prev => [data, ...prev])
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [api])

  const updateProject = useCallback(async (projectId, updates) => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.put(`/projects/${projectId}`, updates)
      setCurrentProject(data)
      // Update in projects list
      setProjects(prev => prev.map(p => p.id === projectId ? { ...p, ...data } : p))
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [api])

  const deleteProject = useCallback(async (projectId) => {
    setLoading(true)
    setError(null)
    try {
      await api.del(`/projects/${projectId}`)
      // Remove from projects list
      setProjects(prev => prev.filter(p => p.id !== projectId))
      if (currentProject?.id === projectId) {
        setCurrentProject(null)
      }
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [api, currentProject])

  const startTranscription = useCallback(async (projectId, modelId) => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.post(`/projects/${projectId}/transcribe`, { model_id: modelId })
      setCurrentProject(data)
      // Update in projects list
      setProjects(prev => prev.map(p => p.id === projectId ? { ...p, status: data.status } : p))
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [api])

  const startSummarization = useCallback(async (projectId, modelId) => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.post(`/projects/${projectId}/summarize`, { model_id: modelId })
      setCurrentProject(data)
      // Update in projects list
      setProjects(prev => prev.map(p => p.id === projectId ? { ...p, status: data.status } : p))
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [api])

  const getProjectStatus = useCallback(async (projectId) => {
    try {
      return await api.get(`/projects/${projectId}/status`)
    } catch (err) {
      throw err
    }
  }, [api])

  return {
    projects,
    currentProject,
    loading,
    error,
    setCurrentProject,
    fetchProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject,
    startTranscription,
    startSummarization,
    getProjectStatus,
  }
}
