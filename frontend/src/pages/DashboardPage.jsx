/**
 * Main Dashboard Page for Scribber.
 * Two-column layout with audio input and project list on the left,
 * transcription and summary on the right.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import { useProjects } from '../hooks/useProjects'
import { useModels } from '../hooks/useModels'
import { useWebSocket } from '../hooks/useWebSocket'
import { useExport } from '../hooks/useExport'
import AudioRecorder from '../components/AudioRecorder'
import ProcessingStatus from '../components/ProcessingStatus'

// Model Selector Component
function ModelSelector({ label, models, selected, onChange }) {
  return (
    <div className="model-selector">
      <label>{label}</label>
      <select
        value={selected?.id || ''}
        onChange={(e) => {
          const model = models.find(m => m.id === parseInt(e.target.value))
          onChange(model)
        }}
      >
        {models.map(model => (
          <option key={model.id} value={model.id}>
            {model.display_name} {model.is_default && '(Default)'}
          </option>
        ))}
      </select>
    </div>
  )
}

// Audio Input Component with drag-and-drop and recorder
function AudioInput({ onUpload, loading }) {
  const [title, setTitle] = useState('')
  const [inputMode, setInputMode] = useState('upload') // 'upload' or 'record'

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0]
      const autoTitle = title || file.name.replace(/\.[^/.]+$/, '')
      onUpload(autoTitle, file)
      setTitle('')
    }
  }, [onUpload, title])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac'],
      'video/mp4': ['.mp4'],
    },
    maxFiles: 1,
    disabled: loading,
  })

  const handleRecordingComplete = (file) => {
    const autoTitle = title || `Recording ${new Date().toLocaleString()}`
    onUpload(autoTitle, file)
    setTitle('')
  }

  return (
    <div className="audio-input-widget">
      <div className="input-mode-tabs">
        <button
          className={`mode-tab ${inputMode === 'upload' ? 'active' : ''}`}
          onClick={() => setInputMode('upload')}
        >
          Upload
        </button>
        <button
          className={`mode-tab ${inputMode === 'record' ? 'active' : ''}`}
          onClick={() => setInputMode('record')}
        >
          Record
        </button>
      </div>

      <input
        type="text"
        placeholder="Project title (optional)"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="title-input"
      />

      {inputMode === 'upload' ? (
        <div
          {...getRootProps()}
          className={`dropzone ${isDragActive ? 'active' : ''} ${loading ? 'disabled' : ''}`}
        >
          <input {...getInputProps()} />
          {loading ? (
            <div className="dropzone-content">
              <div className="spinner-small"></div>
              <p>Uploading...</p>
            </div>
          ) : isDragActive ? (
            <div className="dropzone-content">
              <p>Drop the audio file here...</p>
            </div>
          ) : (
            <div className="dropzone-content">
              <div className="upload-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17,8 12,3 7,8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <p>Drag & drop an audio file here</p>
              <p className="hint">or click to select</p>
              <p className="formats">MP3, WAV, M4A, WebM, OGG, FLAC</p>
            </div>
          )}
        </div>
      ) : (
        <AudioRecorder
          onRecordingComplete={handleRecordingComplete}
          disabled={loading}
        />
      )}
    </div>
  )
}

// Project List Component
function ProjectList({ projects, currentProject, onSelect, onDelete }) {
  const getStatusBadge = (status) => {
    const statusMap = {
      pending: { label: 'Ready', class: 'badge-pending' },
      uploading: { label: 'Uploading', class: 'badge-uploading' },
      transcribing: { label: 'Transcribing', class: 'badge-processing' },
      summarizing: { label: 'Summarizing', class: 'badge-processing' },
      completed: { label: 'Completed', class: 'badge-completed' },
      failed: { label: 'Failed', class: 'badge-failed' },
    }
    return statusMap[status] || { label: status, class: 'badge-pending' }
  }

  if (projects.length === 0) {
    return (
      <div className="project-list-widget">
        <h3>Recent Projects</h3>
        <p className="empty-state">No projects yet. Upload or record audio to get started.</p>
      </div>
    )
  }

  return (
    <div className="project-list-widget">
      <h3>Recent Projects</h3>
      <div className="project-list">
        {projects.map(project => {
          const status = getStatusBadge(project.status)
          const isActive = currentProject?.id === project.id
          return (
            <div
              key={project.id}
              className={`project-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelect(project.id)}
            >
              <div className="project-info">
                <span className="project-title">{project.title}</span>
                <span className="project-date">
                  {new Date(project.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="project-actions">
                <span className={`status-badge ${status.class}`}>{status.label}</span>
                <button
                  className="delete-btn"
                  onClick={(e) => {
                    e.stopPropagation()
                    if (confirm('Delete this project?')) {
                      onDelete(project.id)
                    }
                  }}
                  title="Delete project"
                >
                  &times;
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Transcription Widget Component
function TranscriptionWidget({
  project,
  model,
  onTranscribe,
  onUpdate,
  loading,
  wsConnected
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState('')

  const canTranscribe = project && project.audio_url && project.status === 'pending'
  const isProcessing = project?.status === 'transcribing'

  const handleEdit = () => {
    setEditText(project?.transcription || '')
    setIsEditing(true)
  }

  const handleSave = () => {
    onUpdate(project.id, { transcription: editText })
    setIsEditing(false)
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(project?.transcription || '')
  }

  return (
    <div className="transcription-widget">
      <div className="widget-header">
        <h3>
          Transcription
          {wsConnected && isProcessing && (
            <span className="live-indicator" title="Live updates">LIVE</span>
          )}
        </h3>
        <div className="widget-actions">
          {project?.transcription && !isEditing && (
            <>
              <button className="action-btn" onClick={handleCopy} title="Copy">
                Copy
              </button>
              <button className="action-btn" onClick={handleEdit} title="Edit">
                Edit
              </button>
            </>
          )}
          {canTranscribe && model && (
            <button
              className="primary-btn"
              onClick={() => onTranscribe(project.id, model.id)}
              disabled={loading}
            >
              {loading ? 'Starting...' : `Transcribe with ${model.display_name}`}
            </button>
          )}
        </div>
      </div>

      <div className="widget-content">
        {isProcessing ? (
          <div className="processing-state">
            <div className="spinner-small"></div>
            <p>Transcribing audio...</p>
            <p className="hint">This may take a few minutes for longer recordings.</p>
          </div>
        ) : isEditing ? (
          <div className="edit-mode">
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={12}
            />
            <div className="edit-actions">
              <button className="secondary-btn" onClick={() => setIsEditing(false)}>
                Cancel
              </button>
              <button className="primary-btn" onClick={handleSave}>
                Save
              </button>
            </div>
          </div>
        ) : project?.transcription ? (
          <div className="transcription-text">
            {project.transcription}
          </div>
        ) : project ? (
          <div className="empty-state">
            {project.status === 'failed' ? (
              <div className="error-state">
                <p className="error-text">Error: {project.error_message || 'Transcription failed'}</p>
                {model && (
                  <button
                    className="secondary-btn retry-btn"
                    onClick={() => onTranscribe(project.id, model.id)}
                    disabled={loading}
                    style={{ marginTop: '1rem' }}
                  >
                    Retry with {model.display_name}
                  </button>
                )}
              </div>
            ) : (
              'No transcription yet. Click "Transcribe" to start.'
            )}
          </div>
        ) : (
          <p className="empty-state">Select a project or upload an audio file to get started.</p>
        )}
      </div>
    </div>
  )
}

// Summary Widget Component
function SummaryWidget({
  project,
  model,
  onSummarize,
  onUpdate,
  loading
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState('')

  const canSummarize = project && project.transcription && !project.summary && project.status !== 'summarizing'
  const isProcessing = project?.status === 'summarizing'

  const handleEdit = () => {
    setEditText(project?.summary || '')
    setIsEditing(true)
  }

  const handleSave = () => {
    onUpdate(project.id, { summary: editText })
    setIsEditing(false)
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(project?.summary || '')
  }

  return (
    <div className="summary-widget">
      <div className="widget-header">
        <h3>Summary</h3>
        <div className="widget-actions">
          {project?.summary && !isEditing && (
            <>
              <button className="action-btn" onClick={handleCopy} title="Copy">
                Copy
              </button>
              <button className="action-btn" onClick={handleEdit} title="Edit">
                Edit
              </button>
            </>
          )}
          {canSummarize && model && (
            <button
              className="primary-btn"
              onClick={() => onSummarize(project.id, model.id)}
              disabled={loading}
            >
              {loading ? 'Starting...' : `Summarize with ${model.display_name}`}
            </button>
          )}
        </div>
      </div>

      <div className="widget-content">
        {isProcessing ? (
          <div className="processing-state">
            <div className="spinner-small"></div>
            <p>Generating summary...</p>
          </div>
        ) : isEditing ? (
          <div className="edit-mode">
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={8}
            />
            <div className="edit-actions">
              <button className="secondary-btn" onClick={() => setIsEditing(false)}>
                Cancel
              </button>
              <button className="primary-btn" onClick={handleSave}>
                Save
              </button>
            </div>
          </div>
        ) : project?.summary ? (
          <div className="summary-text">
            {project.summary}
          </div>
        ) : project?.transcription ? (
          <p className="empty-state">
            Click "Summarize" to generate a summary of the transcription.
          </p>
        ) : (
          <div className="empty-state">
            {project?.status === 'failed' && project?.transcription ? (
              <div className="error-state">
                <p className="error-text">Error: {project.error_message || 'Summarization failed'}</p>
                {model && (
                  <button
                    className="secondary-btn retry-btn"
                    onClick={() => onSummarize(project.id, model.id)}
                    disabled={loading}
                    style={{ marginTop: '1rem' }}
                  >
                    Retry with {model.display_name}
                  </button>
                )}
              </div>
            ) : (
              'Transcribe audio first to generate a summary.'
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// Export Buttons Component
function ExportButtons({ project, exportService }) {
  const [showEmailDialog, setShowEmailDialog] = useState(false)
  const [email, setEmail] = useState('')
  const [exporting, setExporting] = useState(false)

  const canExport = project && (project.transcription || project.summary)

  const handleGoogleDrive = async () => {
    if (!exportService.status.google_drive_configured) {
      alert('Google Drive export is not configured. Please contact your administrator.')
      return
    }
    try {
      await exportService.startGoogleDriveAuth(project.id)
    } catch (err) {
      alert(`Failed to start Google Drive export: ${err.message}`)
    }
  }

  const handleEmailClick = () => {
    if (exportService.status.email_configured) {
      setShowEmailDialog(true)
    } else {
      // Fallback to mailto:
      const subject = encodeURIComponent(`Scribber: ${project.title}`)
      const body = encodeURIComponent(
        `Transcription:\n\n${project.transcription || 'N/A'}\n\n` +
        `Summary:\n\n${project.summary || 'N/A'}`
      )
      window.open(`mailto:?subject=${subject}&body=${body}`)
    }
  }

  const handleSendEmail = async () => {
    if (!email) return
    setExporting(true)
    try {
      await exportService.sendEmail(project.id, email)
      alert('Email sent successfully!')
      setShowEmailDialog(false)
      setEmail('')
    } catch (err) {
      alert(`Failed to send email: ${err.message}`)
    } finally {
      setExporting(false)
    }
  }

  const handleWhatsApp = () => {
    const text = encodeURIComponent(
      `*${project.title}*\n\n` +
      `Summary:\n${project.summary || project.transcription?.substring(0, 500) + '...'}`
    )
    window.open(`https://wa.me/?text=${text}`)
  }

  if (!canExport) return null

  return (
    <div className="export-buttons">
      <h4>Export</h4>
      <div className="button-group">
        <button
          className="export-btn google-drive"
          onClick={handleGoogleDrive}
          disabled={exportService.loading}
        >
          Google Drive
        </button>
        <button
          className="export-btn email"
          onClick={handleEmailClick}
          disabled={exportService.loading}
        >
          Email
        </button>
        <button className="export-btn whatsapp" onClick={handleWhatsApp}>
          WhatsApp
        </button>
      </div>

      {/* Email Dialog */}
      {showEmailDialog && (
        <div className="email-dialog-overlay" onClick={() => setShowEmailDialog(false)}>
          <div className="email-dialog" onClick={(e) => e.stopPropagation()}>
            <h4>Send via Email</h4>
            <p>Enter the recipient's email address:</p>
            <input
              type="email"
              placeholder="recipient@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="email-input"
            />
            <div className="dialog-actions">
              <button
                className="secondary-btn"
                onClick={() => setShowEmailDialog(false)}
              >
                Cancel
              </button>
              <button
                className="primary-btn"
                onClick={handleSendEmail}
                disabled={!email || exporting}
              >
                {exporting ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Main Dashboard Page
export default function DashboardPage() {
  const {
    projects,
    currentProject,
    loading: projectsLoading,
    error: projectsError,
    setCurrentProject,
    fetchProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject,
    startTranscription,
    startSummarization,
    getProjectStatus,
  } = useProjects()

  const {
    transcriptionModels,
    summarizationModels,
    selectedTranscriptionModel,
    selectedSummarizationModel,
    setSelectedTranscriptionModel,
    setSelectedSummarizationModel,
    fetchModels,
  } = useModels()

  const exportService = useExport()

  // WebSocket for real-time updates
  const handleWebSocketUpdate = useCallback((data) => {
    if (data.type === 'status' || data.type === 'completed' || data.type === 'error') {
      // Update current project with new data
      if (currentProject) {
        setCurrentProject(prev => ({
          ...prev,
          status: data.status,
          transcription: data.transcription ?? prev.transcription,
          summary: data.summary ?? prev.summary,
          error_message: data.error_message ?? prev.error_message,
        }))

        // Refresh project list if status changed
        if (data.status === 'completed' || data.status === 'failed') {
          fetchProjects()
        }
      }
    }
  }, [currentProject, setCurrentProject, fetchProjects])

  const { connected: wsConnected } = useWebSocket(
    currentProject?.id,
    handleWebSocketUpdate
  )

  const pollingRef = useRef(null)

  // Load models and projects on mount
  useEffect(() => {
    fetchModels()
    fetchProjects()
  }, [])

  // Fallback polling when WebSocket is not connected
  useEffect(() => {
    const shouldPoll = currentProject &&
      ['transcribing', 'summarizing'].includes(currentProject.status) &&
      !wsConnected

    if (shouldPoll) {
      pollingRef.current = setInterval(async () => {
        try {
          const status = await getProjectStatus(currentProject.id)
          if (status.status !== currentProject.status) {
            // Status changed, fetch full project
            await fetchProject(currentProject.id)
            fetchProjects()
          }
        } catch (err) {
          console.error('Polling error:', err)
        }
      }, 3000)
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [currentProject?.id, currentProject?.status, wsConnected])

  const handleUpload = async (title, file) => {
    try {
      await createProject(title, file)
    } catch (err) {
      alert(`Upload failed: ${err.message}`)
    }
  }

  const handleSelectProject = async (projectId) => {
    try {
      await fetchProject(projectId)
    } catch (err) {
      alert(`Failed to load project: ${err.message}`)
    }
  }

  return (
    <div className="dashboard">
      {/* Model Selectors */}
      <div className="model-selectors">
        <ModelSelector
          label="Transcription Model"
          models={transcriptionModels}
          selected={selectedTranscriptionModel}
          onChange={setSelectedTranscriptionModel}
        />
        <ModelSelector
          label="Summarization Model"
          models={summarizationModels}
          selected={selectedSummarizationModel}
          onChange={setSelectedSummarizationModel}
        />
      </div>

      {/* Main Content */}
      <div className="dashboard-content">
        {/* Left Column */}
        <div className="left-column">
          <AudioInput onUpload={handleUpload} loading={projectsLoading} />
          <ProjectList
            projects={projects}
            currentProject={currentProject}
            onSelect={handleSelectProject}
            onDelete={deleteProject}
          />
        </div>

        {/* Right Column */}
        <div className="right-column">
          {/* Processing Status */}
          {currentProject && ['uploading', 'transcribing', 'summarizing', 'failed'].includes(currentProject.status) && (
            <ProcessingStatus
              status={currentProject.status}
              error={currentProject.error_message}
            />
          )}

          <TranscriptionWidget
            project={currentProject}
            model={selectedTranscriptionModel}
            onTranscribe={startTranscription}
            onUpdate={updateProject}
            loading={projectsLoading}
            wsConnected={wsConnected}
          />
          <SummaryWidget
            project={currentProject}
            model={selectedSummarizationModel}
            onSummarize={startSummarization}
            onUpdate={updateProject}
            loading={projectsLoading}
          />
          <ExportButtons project={currentProject} exportService={exportService} />
        </div>
      </div>

      {/* Error Display */}
      {projectsError && (
        <div className="error-toast">
          {projectsError}
        </div>
      )}
    </div>
  )
}
