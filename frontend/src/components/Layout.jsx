import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function Layout() {
  const { user, signOut } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const isActive = (path) => location.pathname === path

  const handleSignOut = async () => {
    await signOut()
    navigate('/sign-in')
  }

  return (
    <div className="app-layout">
      <header className="header">
        <div className="header-content">
          <Link to="/" className="logo">
            Project Template
          </Link>

          <nav className="nav">
            <Link
              to="/"
              className={`nav-link ${isActive('/') ? 'active' : ''}`}
            >
              Home
            </Link>
            <Link
              to="/items"
              className={`nav-link ${isActive('/items') ? 'active' : ''}`}
            >
              Items
            </Link>
          </nav>

          <div className="user-section">
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
        <p>Project Template - Self-hosted Authentication</p>
      </footer>
    </div>
  )
}

export default Layout
