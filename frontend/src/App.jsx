import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'

import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import AdminPage from './pages/AdminPage'
import SignInPage from './pages/SignInPage'
import SignUpPage from './pages/SignUpPage'
import GoogleDriveCallbackPage from './pages/GoogleDriveCallbackPage'

// Protected route wrapper
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/sign-in" replace />
  }

  return children
}

// Public route - redirect to home if already logged in
function PublicRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    )
  }

  if (user) {
    return <Navigate to="/" replace />
  }

  return children
}

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/sign-in"
        element={
          <PublicRoute>
            <SignInPage />
          </PublicRoute>
        }
      />
      <Route
        path="/sign-up"
        element={
          <PublicRoute>
            <SignUpPage />
          </PublicRoute>
        }
      />

      {/* Protected routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>

      {/* OAuth callbacks (protected) */}
      <Route
        path="/oauth/google-drive/callback"
        element={
          <ProtectedRoute>
            <GoogleDriveCallbackPage />
          </ProtectedRoute>
        }
      />

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
