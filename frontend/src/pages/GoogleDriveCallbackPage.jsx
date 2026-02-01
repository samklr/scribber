/**
 * Google Drive OAuth Callback Page.
 * Handles the OAuth redirect and completes the export flow.
 */
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useExport } from '../hooks/useExport'

export default function GoogleDriveCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { completeGoogleDriveAuth, uploadToGoogleDrive } = useExport()
  const [status, setStatus] = useState('processing')
  const [message, setMessage] = useState('Completing Google Drive authorization...')
  const [uploadResult, setUploadResult] = useState(null)

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const error = searchParams.get('error')

      if (error) {
        setStatus('error')
        setMessage(`Authorization failed: ${error}`)
        return
      }

      if (!code || !state) {
        setStatus('error')
        setMessage('Missing authorization parameters')
        return
      }

      try {
        // Exchange code for tokens
        setMessage('Exchanging authorization code...')
        const tokenResult = await completeGoogleDriveAuth(code, state)

        // Upload to Google Drive
        setMessage('Uploading to Google Drive...')
        const result = await uploadToGoogleDrive(
          tokenResult.project_id,
          tokenResult.access_token
        )

        setStatus('success')
        setMessage('Successfully uploaded to Google Drive!')
        setUploadResult(result)

      } catch (err) {
        setStatus('error')
        setMessage(`Export failed: ${err.message}`)
      }
    }

    handleCallback()
  }, [searchParams])

  return (
    <div className="oauth-callback-page">
      <div className="callback-card">
        <div className="callback-icon">
          {status === 'processing' && <div className="spinner"></div>}
          {status === 'success' && (
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M9 12l2 2 4-4" />
            </svg>
          )}
          {status === 'error' && (
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M15 9l-6 6M9 9l6 6" />
            </svg>
          )}
        </div>

        <h1>{status === 'success' ? 'Export Complete!' : status === 'error' ? 'Export Failed' : 'Exporting...'}</h1>
        <p>{message}</p>

        {uploadResult?.web_view_link && (
          <a
            href={uploadResult.web_view_link}
            target="_blank"
            rel="noopener noreferrer"
            className="primary-btn"
            style={{ marginTop: '1rem', textDecoration: 'none' }}
          >
            View in Google Drive
          </a>
        )}

        <button
          className="secondary-btn"
          onClick={() => navigate('/')}
          style={{ marginTop: '1rem' }}
        >
          Back to Dashboard
        </button>
      </div>
    </div>
  )
}
