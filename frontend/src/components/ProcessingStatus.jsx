/**
 * Processing Status Component - Shows real-time status of transcription/summarization.
 */

export default function ProcessingStatus({ status, progress, error }) {
  if (!status || status === 'pending' || status === 'completed') {
    return null
  }

  const getStatusInfo = () => {
    switch (status) {
      case 'uploading':
        return {
          label: 'Uploading audio...',
          details: 'Preparing your audio file',
          className: '',
        }
      case 'transcribing':
        return {
          label: 'Transcribing audio...',
          details: 'Converting speech to text',
          className: '',
        }
      case 'summarizing':
        return {
          label: 'Generating summary...',
          details: 'Analyzing transcription',
          className: '',
        }
      case 'failed':
        return {
          label: 'Processing failed',
          details: error || 'An error occurred',
          className: 'failed',
        }
      default:
        return {
          label: 'Processing...',
          details: '',
          className: '',
        }
    }
  }

  const statusInfo = getStatusInfo()

  return (
    <div className={`processing-status ${statusInfo.className}`}>
      <div className="processing-status-content">
        {status !== 'failed' && <div className="processing-spinner" />}
        <div className="processing-info">
          <div className="processing-label">{statusInfo.label}</div>
          {statusInfo.details && (
            <div className="processing-details">{statusInfo.details}</div>
          )}
        </div>
      </div>
      {progress !== undefined && progress > 0 && status !== 'failed' && (
        <div className="processing-progress">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${Math.min(progress, 100)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
