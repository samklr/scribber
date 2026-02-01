import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function Layout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate('/sign-in')
  }

  return (
    <div className="app-layout">
      <header className="header">
        <div className="header-content">
          <Link to="/" className="logo">
            <svg className="logo-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
            Scribber
          </Link>

          <div className="user-section">
            {user?.is_admin && (
              <Link to="/admin" className="admin-link">
                Admin
              </Link>
            )}
            <span className="user-name">{user?.name || user?.email}</span>
            <button onClick={handleSignOut} className="btn-secondary">
              Sign Out
            </button>
          </div>
        </div>
      </header>

      <main className="main-content">
        <Outlet />
      </main>

      <footer className="footer">
        <p>Scribber - Audio Transcription & Summarization</p>
      </footer>
    </div>
  )
}

export default Layout
