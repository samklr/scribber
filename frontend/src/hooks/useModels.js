/**
 * Hook for managing AI models.
 */
import { useState, useCallback, useEffect } from 'react'
import { useApi } from './useApi'

export function useModels() {
  const api = useApi()
  const [transcriptionModels, setTranscriptionModels] = useState([])
  const [summarizationModels, setSummarizationModels] = useState([])
  const [selectedTranscriptionModel, setSelectedTranscriptionModel] = useState(null)
  const [selectedSummarizationModel, setSelectedSummarizationModel] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchModels = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get('/models')
      setTranscriptionModels(data.transcription)
      setSummarizationModels(data.summarization)

      // Set default models
      const defaultTranscription = data.transcription.find(m => m.is_default) || data.transcription[0]
      const defaultSummarization = data.summarization.find(m => m.is_default) || data.summarization[0]

      if (defaultTranscription && !selectedTranscriptionModel) {
        setSelectedTranscriptionModel(defaultTranscription)
      }
      if (defaultSummarization && !selectedSummarizationModel) {
        setSelectedSummarizationModel(defaultSummarization)
      }

      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [api])

  return {
    transcriptionModels,
    summarizationModels,
    selectedTranscriptionModel,
    selectedSummarizationModel,
    setSelectedTranscriptionModel,
    setSelectedSummarizationModel,
    loading,
    error,
    fetchModels,
  }
}
