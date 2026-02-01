/**
 * Audio Recorder Component with waveform visualization.
 */
import { useAudioRecorder } from '../hooks/useAudioRecorder'

export default function AudioRecorder({ onRecordingComplete, disabled }) {
  const {
    isRecording,
    isPaused,
    formattedDuration,
    audioBlob,
    audioUrl,
    audioLevel,
    error,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    clearRecording,
  } = useAudioRecorder()

  const handleUseRecording = () => {
    if (audioBlob && onRecordingComplete) {
      // Create a File object from the blob
      const file = new File([audioBlob], `recording-${Date.now()}.webm`, {
        type: audioBlob.type,
      })
      onRecordingComplete(file)
      clearRecording()
    }
  }

  // Generate bars for waveform visualization
  const bars = Array.from({ length: 20 }, (_, i) => {
    const height = isRecording && !isPaused
      ? Math.max(4, Math.random() * audioLevel * 40 + 4)
      : 4
    return height
  })

  return (
    <div className="audio-recorder">
      {error && (
        <div className="recorder-error">{error}</div>
      )}

      {/* Waveform visualization */}
      <div className="waveform">
        {bars.map((height, i) => (
          <div
            key={i}
            className="waveform-bar"
            style={{
              height: `${height}px`,
              backgroundColor: isRecording && !isPaused ? '#6366f1' : '#cbd5e1',
            }}
          />
        ))}
      </div>

      {/* Timer */}
      <div className="recorder-timer">
        <span className={isRecording ? 'recording-indicator' : ''}>
          {isRecording && '●'} {formattedDuration}
        </span>
      </div>

      {/* Controls */}
      <div className="recorder-controls">
        {!isRecording && !audioUrl && (
          <button
            className="record-btn"
            onClick={startRecording}
            disabled={disabled}
            title="Start Recording"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="12" r="8" />
            </svg>
            Record
          </button>
        )}

        {isRecording && (
          <>
            {isPaused ? (
              <button
                className="resume-btn"
                onClick={resumeRecording}
                title="Resume Recording"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5,3 19,12 5,21" />
                </svg>
                Resume
              </button>
            ) : (
              <button
                className="pause-btn"
                onClick={pauseRecording}
                title="Pause Recording"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="4" width="4" height="16" />
                  <rect x="14" y="4" width="4" height="16" />
                </svg>
                Pause
              </button>
            )}
            <button
              className="stop-btn"
              onClick={stopRecording}
              title="Stop Recording"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <rect x="4" y="4" width="16" height="16" rx="2" />
              </svg>
              Stop
            </button>
          </>
        )}

        {audioUrl && !isRecording && (
          <>
            <audio src={audioUrl} controls className="audio-preview" />
            <div className="recording-actions">
              <button
                className="use-recording-btn"
                onClick={handleUseRecording}
              >
                Use Recording
              </button>
              <button
                className="discard-btn"
                onClick={clearRecording}
              >
                Discard
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
