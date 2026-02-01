/**
 * API hook for making authenticated requests.
 */
import { useAuth } from '../context/AuthContext'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export function useApi() {
  const { getAuthHeader, signOut } = useAuth()

  const request = async (endpoint, options = {}) => {
    const url = `${API_BASE_URL}${endpoint}`
    const headers = {
      ...getAuthHeader(),
      ...options.headers,
    }

    // Don't set Content-Type for FormData (let browser set it with boundary)
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      })

      // Handle 401 - session expired
      if (response.status === 401) {
        signOut()
        throw new Error('Session expired. Please sign in again.')
      }

      // Handle other errors
      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.detail || `Request failed: ${response.status}`)
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return null
      }

      return response.json()
    } catch (error) {
      throw error
    }
  }

  const get = (endpoint) => request(endpoint, { method: 'GET' })

  const post = (endpoint, data) => {
    const options = { method: 'POST' }
    if (data instanceof FormData) {
      options.body = data
    } else {
      options.body = JSON.stringify(data)
    }
    return request(endpoint, options)
  }

  const put = (endpoint, data) =>
    request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    })

  const del = (endpoint) => request(endpoint, { method: 'DELETE' })

  return { get, post, put, del, request }
}
