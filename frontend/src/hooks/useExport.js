/**
 * Export hook for sending transcriptions to external services.
 */
import { useState, useEffect, useCallback } from 'react'
import { useApi } from './useApi'

export function useExport() {
  const api = useApi()
  const [status, setStatus] = useState({
    email_configured: false,
    google_drive_configured: false,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Fetch export service status
  const fetchStatus = useCallback(async () => {
    try {
      const data = await api.get('/export/status')
      setStatus(data)
    } catch (err) {
      console.error('Failed to fetch export status:', err)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  // Send via email
  const sendEmail = useCallback(async (projectId, toEmail, options = {}) => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.post('/export/email', {
        project_id: projectId,
        to_email: toEmail,
        include_summary: options.includeSummary ?? true,
        include_attachment: options.includeAttachment ?? true,
      })
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Start Google Drive OAuth
  const startGoogleDriveAuth = useCallback(async (projectId) => {
    setLoading(true)
    setError(null)
    try {
      const redirectUri = `${window.location.origin}/oauth/google-drive/callback`
      const result = await api.post('/export/google-drive/auth', {
        project_id: projectId,
        redirect_uri: redirectUri,
      })
      // Redirect to Google OAuth
      window.location.href = result.authorization_url
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Complete Google Drive OAuth (called after redirect)
  const completeGoogleDriveAuth = useCallback(async (code, state) => {
    setLoading(true)
    setError(null)
    try {
      const redirectUri = `${window.location.origin}/oauth/google-drive/callback`
      const result = await api.post('/export/google-drive/callback', {
        code,
        state,
        redirect_uri: redirectUri,
      })
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Upload to Google Drive
  const uploadToGoogleDrive = useCallback(async (projectId, accessToken, folderName = 'Scribber') => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.post('/export/google-drive/upload', {
        project_id: projectId,
        access_token: accessToken,
        folder_name: folderName,
      })
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Refresh Google Drive token
  const refreshGoogleDriveToken = useCallback(async (refreshToken) => {
    try {
      const result = await api.post('/export/google-drive/refresh', null, {
        params: { refresh_token: refreshToken },
      })
      return result
    } catch (err) {
      setError(err.message)
      throw err
    }
  }, [])

  return {
    status,
    loading,
    error,
    sendEmail,
    startGoogleDriveAuth,
    completeGoogleDriveAuth,
    uploadToGoogleDrive,
    refreshGoogleDriveToken,
    fetchStatus,
  }
}
