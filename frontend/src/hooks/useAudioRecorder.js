/**
 * Audio recording hook using MediaRecorder API.
 */
import { useState, useRef, useCallback, useEffect } from 'react'

export function useAudioRecorder() {
  const [isRecording, setIsRecording] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [duration, setDuration] = useState(0)
  const [audioBlob, setAudioBlob] = useState(null)
  const [audioUrl, setAudioUrl] = useState(null)
  const [error, setError] = useState(null)
  const [audioLevel, setAudioLevel] = useState(0)

  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const streamRef = useRef(null)
  const timerRef = useRef(null)
  const analyserRef = useRef(null)
  const animationRef = useRef(null)

  // Cleanup function
  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
    }
  }, [audioUrl])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup()
    }
  }, [cleanup])

  // Update audio level visualization
  const updateAudioLevel = useCallback(() => {
    if (!analyserRef.current) return

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(dataArray)

    // Calculate average level
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
    setAudioLevel(average / 255)

    if (isRecording && !isPaused) {
      animationRef.current = requestAnimationFrame(updateAudioLevel)
    }
  }, [isRecording, isPaused])

  // Start recording
  const startRecording = useCallback(async () => {
    try {
      setError(null)
      setAudioBlob(null)
      setAudioUrl(null)
      audioChunksRef.current = []

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100,
        }
      })
      streamRef.current = stream

      // Set up audio analyser for visualization
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      const source = audioContext.createMediaStreamSource(stream)
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      // Create MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4'

      const mediaRecorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = mediaRecorder

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: mimeType })
        setAudioBlob(blob)
        setAudioUrl(URL.createObjectURL(blob))
      }

      // Start recording
      mediaRecorder.start(1000) // Collect data every second
      setIsRecording(true)
      setIsPaused(false)
      setDuration(0)

      // Start timer
      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1)
      }, 1000)

      // Start audio level visualization
      updateAudioLevel()

    } catch (err) {
      console.error('Failed to start recording:', err)
      if (err.name === 'NotAllowedError') {
        setError('Microphone access denied. Please allow microphone access.')
      } else if (err.name === 'NotFoundError') {
        setError('No microphone found. Please connect a microphone.')
      } else {
        setError('Failed to start recording: ' + err.message)
      }
    }
  }, [updateAudioLevel])

  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setIsPaused(false)

      // Stop timer
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }

      // Stop audio level
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
        animationRef.current = null
      }
      setAudioLevel(0)

      // Stop stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
        streamRef.current = null
      }
    }
  }, [isRecording])

  // Pause recording
  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording && !isPaused) {
      mediaRecorderRef.current.pause()
      setIsPaused(true)

      // Pause timer
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }

      // Stop audio level animation
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
        animationRef.current = null
      }
      setAudioLevel(0)
    }
  }, [isRecording, isPaused])

  // Resume recording
  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording && isPaused) {
      mediaRecorderRef.current.resume()
      setIsPaused(false)

      // Resume timer
      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1)
      }, 1000)

      // Resume audio level
      updateAudioLevel()
    }
  }, [isRecording, isPaused, updateAudioLevel])

  // Clear recording
  const clearRecording = useCallback(() => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
    }
    setAudioBlob(null)
    setAudioUrl(null)
    setDuration(0)
    audioChunksRef.current = []
  }, [audioUrl])

  // Format duration as MM:SS
  const formatDuration = useCallback((seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }, [])

  return {
    isRecording,
    isPaused,
    duration,
    formattedDuration: formatDuration(duration),
    audioBlob,
    audioUrl,
    audioLevel,
    error,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    clearRecording,
  }
}
