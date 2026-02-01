import { useAuth } from '../context/AuthContext'
import { useState, useEffect } from 'react'

function HomePage() {
  const { user } = useAuth()
  const [health, setHealth] = useState({ status: 'loading' })

  useEffect(() => {
    checkHealth()
  }, [])

  const checkHealth = async () => {
    try {
      const response = await fetch('/health/ready')
      const data = await response.json()
      setHealth({ status: 'healthy', data })
    } catch (err) {
      setHealth({ status: 'error', message: err.message })
    }
  }

  return (
    <div className="container">
      <h1>Welcome, {user?.name || 'User'}!</h1>

      <div className="card">
        <h2>Getting Started</h2>
        <p>You are now signed in and can access protected resources.</p>
        <ul>
          <li>
            View and manage <a href="/items">Items</a>
          </li>
          <li>
            Access the{' '}
            <a href="/docs" target="_blank" rel="noopener">
              API Documentation
            </a>
          </li>
        </ul>
      </div>

      <div className="card">
        <h2>API Health Status</h2>
        <div className={`status ${health.status}`}>
          {health.status === 'loading' && 'Checking API health...'}
          {health.status === 'healthy' && 'API is healthy and ready'}
          {health.status === 'error' && `API Error: ${health.message}`}
        </div>
      </div>

      <div className="card">
        <h2>Your Profile</h2>
        <div className="profile-info">
          <p>
            <strong>Email:</strong> {user?.email}
          </p>
          <p>
            <strong>Name:</strong> {user?.name || 'Not set'}
          </p>
          <p>
            <strong>User ID:</strong> {user?.id}
          </p>
          <p>
            <strong>Member since:</strong>{' '}
            {user?.created_at
              ? new Date(user.created_at).toLocaleDateString()
              : 'N/A'}
          </p>
        </div>
      </div>
    </div>
  )
}

export default HomePage
