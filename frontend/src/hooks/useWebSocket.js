/**
 * WebSocket hook for real-time project updates.
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ||
  `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1`

export function useWebSocket(projectId, onUpdate) {
  const { getToken } = useAuth()
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const pingIntervalRef = useRef(null)

  const connect = useCallback(() => {
    if (!projectId) return

    const token = getToken()
    if (!token) {
      setError('Not authenticated')
      return
    }

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close()
    }

    try {
      const wsUrl = `${WS_BASE_URL}/ws/projects/${projectId}?token=${token}`
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        setConnected(true)
        setError(null)
        console.log('WebSocket connected')

        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, 25000)
      }

      ws.onmessage = (event) => {
        // Handle pong
        if (event.data === 'pong' || event.data === 'ping') {
          return
        }

        try {
          const data = JSON.parse(event.data)
          if (onUpdate) {
            onUpdate(data)
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('Connection error')
      }

      ws.onclose = (event) => {
        setConnected(false)
        console.log('WebSocket closed:', event.code, event.reason)

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = null
        }

        // Attempt reconnect if not intentionally closed
        if (event.code !== 1000 && event.code !== 4001 && event.code !== 4003) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect...')
            connect()
          }, 3000)
        }
      }

      wsRef.current = ws
    } catch (e) {
      console.error('Failed to create WebSocket:', e)
      setError('Failed to connect')
    }
  }, [projectId, getToken, onUpdate])

  const disconnect = useCallback(() => {
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    // Clear ping interval
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected')
      wsRef.current = null
    }

    setConnected(false)
  }, [])

  const requestStatus = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send('status')
    }
  }, [])

  // Connect when projectId changes
  useEffect(() => {
    if (projectId) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [projectId, connect, disconnect])

  return {
    connected,
    error,
    connect,
    disconnect,
    requestStatus,
  }
}
