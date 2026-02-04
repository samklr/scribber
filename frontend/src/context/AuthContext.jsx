import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Get stored token
  const getToken = useCallback(() => {
    return localStorage.getItem('access_token')
  }, [])

  // Fetch current user
  const fetchUser = useCallback(async () => {
    const token = getToken()
    if (!token) {
      setLoading(false)
      return
    }

    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
      } else {
        // Token invalid, clear it
        localStorage.removeItem('access_token')
        setUser(null)
      }
    } catch (err) {
      console.error('Failed to fetch user:', err)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [getToken])

  // Initialize auth state
  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  // Sign in
  const signIn = async (email, password) => {
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to sign in')
      }

      localStorage.setItem('access_token', data.access_token)
      setUser(data.user)
      return { success: true }
    } catch (err) {
      setError(err.message)
      return { success: false, error: err.message }
    }
  }

  // Sign up
  const signUp = async (email, password, name, captchaToken) => {
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, name, captcha_token: captchaToken }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to sign up')
      }

      localStorage.setItem('access_token', data.access_token)
      setUser(data.user)
      return { success: true }
    } catch (err) {
      setError(err.message)
      return { success: false, error: err.message }
    }
  }

  // Sign out
  const signOut = async () => {
    try {
      const token = getToken()
      if (token) {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })
      }
    } catch (err) {
      console.error('Logout error:', err)
    } finally {
      localStorage.removeItem('access_token')
      setUser(null)
    }
  }

  // Get auth header for API requests
  const getAuthHeader = useCallback(() => {
    const token = getToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [getToken])

  const value = {
    user,
    loading,
    error,
    signIn,
    signUp,
    signOut,
    getToken,
    getAuthHeader,
    refreshUser: fetchUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
