/**
 * Admin Dashboard Page.
 * Tabs for managing models, users, and viewing usage statistics.
 */
import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'

// --- Add Model Modal ---

function AddModelModal({ onClose, onSubmit, loading }) {
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    provider: 'openai',
    model_type: 'transcription',
    api_endpoint: '',
    is_active: true,
    is_default: false,
  })

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit(formData)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Add New Model</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="model-form">
          <div className="form-row">
            <div className="form-group">
              <label>Model Name (ID)</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g., whisper-large-v3"
                required
              />
              <small>Unique identifier for the model</small>
            </div>
            <div className="form-group">
              <label>Display Name</label>
              <input
                type="text"
                name="display_name"
                value={formData.display_name}
                onChange={handleChange}
                placeholder="e.g., Whisper Large V3"
                required
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Provider</label>
              <select name="provider" value={formData.provider} onChange={handleChange}>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="google">Google</option>
                <option value="elevenlabs">ElevenLabs</option>
                <option value="qwen">Qwen</option>
                <option value="local">Local</option>
              </select>
            </div>
            <div className="form-group">
              <label>Model Type</label>
              <select name="model_type" value={formData.model_type} onChange={handleChange}>
                <option value="transcription">Transcription</option>
                <option value="summarization">Summarization</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>API Endpoint (optional)</label>
            <input
              type="text"
              name="api_endpoint"
              value={formData.api_endpoint}
              onChange={handleChange}
              placeholder="e.g., https://api.openai.com/v1/audio/transcriptions"
            />
          </div>

          <div className="form-row checkbox-row">
            <label className="checkbox-label">
              <input
                type="checkbox"
                name="is_active"
                checked={formData.is_active}
                onChange={handleChange}
              />
              <span>Active</span>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                name="is_default"
                checked={formData.is_default}
                onChange={handleChange}
              />
              <span>Set as Default</span>
            </label>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="primary-btn" disabled={loading}>
              {loading ? 'Adding...' : 'Add Model'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// --- Delete Confirmation Modal ---

function DeleteConfirmModal({ model, onClose, onConfirm, loading }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-small" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Delete Model</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <p>Are you sure you want to delete <strong>{model.display_name}</strong>?</p>
          <p className="warning-text">This action cannot be undone.</p>
        </div>
        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="danger-btn"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Deleting...' : 'Delete Model'}
          </button>
        </div>
      </div>
    </div>
  )
}

// --- Tab Components ---

function ModelsTab({ api }) {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [showAddModal, setShowAddModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(null)
  const [actionLoading, setActionLoading] = useState(false)

  const fetchModels = async () => {
    setLoading(true)
    try {
      const data = await api.get('/admin/models?include_inactive=true')
      setModels(data)
    } catch (err) {
      console.error('Failed to fetch models:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchModels()
  }, [])

  const handleToggle = async (modelId) => {
    try {
      await api.post(`/admin/models/${modelId}/toggle`)
      fetchModels()
    } catch (err) {
      alert(`Failed to toggle model: ${err.message}`)
    }
  }

  const handleAddModel = async (formData) => {
    setActionLoading(true)
    try {
      await api.post('/admin/models', formData)
      setShowAddModal(false)
      fetchModels()
    } catch (err) {
      alert(`Failed to add model: ${err.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const handleDeleteModel = async () => {
    if (!showDeleteModal) return
    setActionLoading(true)
    try {
      await api.del(`/admin/models/${showDeleteModal.id}`)
      setShowDeleteModal(null)
      fetchModels()
    } catch (err) {
      alert(`Failed to delete model: ${err.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const handleSetDefault = async (modelId) => {
    try {
      await api.put(`/admin/models/${modelId}`, { is_default: true })
      fetchModels()
    } catch (err) {
      alert(`Failed to set default: ${err.message}`)
    }
  }

  const filteredModels = models.filter(m => {
    if (filter === 'all') return true
    return m.model_type === filter
  })

  return (
    <div className="admin-section">
      <div className="section-header">
        <h2>AI Models</h2>
        <div className="header-actions">
          <div className="filter-tabs">
            <button
              className={`filter-tab ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All
            </button>
            <button
              className={`filter-tab ${filter === 'transcription' ? 'active' : ''}`}
              onClick={() => setFilter('transcription')}
            >
              Transcription
            </button>
            <button
              className={`filter-tab ${filter === 'summarization' ? 'active' : ''}`}
              onClick={() => setFilter('summarization')}
            >
              Summarization
            </button>
          </div>
          <button className="primary-btn add-model-btn" onClick={() => setShowAddModal(true)}>
            + Add Model
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner-small"></div>
          <span>Loading models...</span>
        </div>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Provider</th>
              <th>Type</th>
              <th>Status</th>
              <th>Default</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredModels.map(model => (
              <tr key={model.id} className={!model.is_active ? 'inactive' : ''}>
                <td>
                  <strong>{model.display_name}</strong>
                  <span className="model-id">{model.name}</span>
                </td>
                <td>{model.provider}</td>
                <td>
                  <span className={`type-badge ${model.model_type}`}>
                    {model.model_type}
                  </span>
                </td>
                <td>
                  <span className={`status-indicator ${model.is_active ? 'active' : 'inactive'}`}>
                    {model.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>
                  {model.is_default ? (
                    <span className="default-badge">Default</span>
                  ) : (
                    <button
                      className="small-link-btn"
                      onClick={() => handleSetDefault(model.id)}
                      title="Set as default"
                    >
                      Set default
                    </button>
                  )}
                </td>
                <td>
                  <div className="action-buttons">
                    <button
                      className={`toggle-btn ${model.is_active ? 'deactivate' : 'activate'}`}
                      onClick={() => handleToggle(model.id)}
                    >
                      {model.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      className="small-btn danger"
                      onClick={() => setShowDeleteModal(model)}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {filteredModels.length === 0 && !loading && (
        <div className="empty-state">
          <p>No models found. Add your first model to get started.</p>
        </div>
      )}

      {showAddModal && (
        <AddModelModal
          onClose={() => setShowAddModal(false)}
          onSubmit={handleAddModel}
          loading={actionLoading}
        />
      )}

      {showDeleteModal && (
        <DeleteConfirmModal
          model={showDeleteModal}
          onClose={() => setShowDeleteModal(null)}
          onConfirm={handleDeleteModel}
          loading={actionLoading}
        />
      )}
    </div>
  )
}

function UsersTab({ api }) {
  const [users, setUsers] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 20

  const fetchStats = async () => {
    try {
      const data = await api.get('/admin/users/stats')
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch user stats:', err)
    }
  }

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const data = await api.get(`/admin/users?page=${page}&page_size=${pageSize}`)
      setUsers(data.users)
      setTotal(data.total)
    } catch (err) {
      console.error('Failed to fetch users:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
    fetchUsers()
  }, [page])

  const handleToggleAdmin = async (userId) => {
    try {
      await api.post(`/admin/users/${userId}/toggle-admin`)
      fetchUsers()
    } catch (err) {
      alert(`Failed to toggle admin: ${err.message}`)
    }
  }

  const handleToggleActive = async (userId) => {
    try {
      await api.post(`/admin/users/${userId}/toggle-active`)
      fetchUsers()
      fetchStats()
    } catch (err) {
      alert(`Failed to toggle user: ${err.message}`)
    }
  }

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="admin-section">
      {/* Stats Cards */}
      {stats && (
        <div className="stats-cards">
          <div className="stat-card">
            <div className="stat-value">{stats.total_users}</div>
            <div className="stat-label">Total Users</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.active_users}</div>
            <div className="stat-label">Active Users</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.admin_users}</div>
            <div className="stat-label">Admins</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.new_users_this_month}</div>
            <div className="stat-label">New This Month</div>
          </div>
        </div>
      )}

      <div className="section-header">
        <h2>Users</h2>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner-small"></div>
          <span>Loading users...</span>
        </div>
      ) : (
        <>
          <table className="admin-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Projects</th>
                <th>Usage</th>
                <th>Status</th>
                <th>Role</th>
                <th>Joined</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id} className={!user.is_active ? 'inactive' : ''}>
                  <td>
                    <strong>{user.name || 'No name'}</strong>
                    <span className="user-email">{user.email}</span>
                  </td>
                  <td>{user.project_count}</td>
                  <td>{formatDuration(user.total_usage_seconds)}</td>
                  <td>
                    <span className={`status-indicator ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    {user.is_admin && <span className="admin-badge">Admin</span>}
                  </td>
                  <td>{new Date(user.created_at).toLocaleDateString()}</td>
                  <td>
                    <div className="action-buttons">
                      <button
                        className="small-btn"
                        onClick={() => handleToggleAdmin(user.id)}
                        title={user.is_admin ? 'Remove admin' : 'Make admin'}
                      >
                        {user.is_admin ? 'Revoke Admin' : 'Make Admin'}
                      </button>
                      <button
                        className={`small-btn ${user.is_active ? 'danger' : 'success'}`}
                        onClick={() => handleToggleActive(user.id)}
                      >
                        {user.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
              >
                Previous
              </button>
              <span>Page {page} of {totalPages}</span>
              <button
                disabled={page === totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function UsageTab({ api }) {
  const [summary, setSummary] = useState(null)
  const [dailyData, setDailyData] = useState([])
  const [modelUsage, setModelUsage] = useState([])
  const [topUsers, setTopUsers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const [summaryData, daily, models, users] = await Promise.all([
          api.get('/admin/usage/summary'),
          api.get('/admin/usage/daily?days=14'),
          api.get('/admin/usage/by-model'),
          api.get('/admin/usage/top-users?limit=5'),
        ])
        setSummary(summaryData)
        setDailyData(daily)
        setModelUsage(models)
        setTopUsers(users)
      } catch (err) {
        console.error('Failed to fetch usage data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  const formatCost = (cost) => {
    return `$${cost.toFixed(4)}`
  }

  if (loading) {
    return (
      <div className="admin-section">
        <div className="loading-state">
          <div className="spinner-small"></div>
          <span>Loading usage data...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-section">
      {/* Summary Stats */}
      {summary && (
        <div className="stats-cards">
          <div className="stat-card">
            <div className="stat-value">{summary.total_projects}</div>
            <div className="stat-label">Total Projects</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{summary.total_transcriptions}</div>
            <div className="stat-label">Transcriptions</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{summary.total_summaries}</div>
            <div className="stat-label">Summaries</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{formatDuration(summary.total_audio_seconds)}</div>
            <div className="stat-label">Audio Processed</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{formatCost(summary.estimated_total_cost)}</div>
            <div className="stat-label">Estimated Cost</div>
          </div>
        </div>
      )}

      {/* Daily Activity Chart (simplified) */}
      <div className="chart-section">
        <h3>Activity (Last 14 Days)</h3>
        <div className="simple-chart">
          {dailyData.map(day => (
            <div key={day.date} className="chart-bar-container">
              <div
                className="chart-bar"
                style={{
                  height: `${Math.min((day.projects / Math.max(...dailyData.map(d => d.projects), 1)) * 100, 100)}%`
                }}
                title={`${day.date}: ${day.projects} projects`}
              />
              <span className="chart-label">
                {new Date(day.date).getDate()}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Two-column layout for model usage and top users */}
      <div className="admin-grid">
        {/* Model Usage */}
        <div className="admin-card">
          <h3>Usage by Model</h3>
          <table className="compact-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Uses</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {modelUsage.map(model => (
                <tr key={model.model_id}>
                  <td>
                    <span className={`type-badge small ${model.model_type}`}>
                      {model.model_type.charAt(0).toUpperCase()}
                    </span>
                    {model.model_name}
                  </td>
                  <td>{model.usage_count}</td>
                  <td>{formatCost(model.estimated_cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Top Users */}
        <div className="admin-card">
          <h3>Top Users</h3>
          <table className="compact-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Projects</th>
                <th>Audio</th>
              </tr>
            </thead>
            <tbody>
              {topUsers.map(user => (
                <tr key={user.user_id}>
                  <td>
                    <span className="user-email">{user.email}</span>
                  </td>
                  <td>{user.project_count}</td>
                  <td>{formatDuration(user.total_audio_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// --- Main Admin Page ---

export default function AdminPage() {
  const api = useApi()
  const [activeTab, setActiveTab] = useState('usage')

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>Admin Dashboard</h1>
      </div>

      <div className="admin-tabs">
        <button
          className={`admin-tab ${activeTab === 'usage' ? 'active' : ''}`}
          onClick={() => setActiveTab('usage')}
        >
          Usage
        </button>
        <button
          className={`admin-tab ${activeTab === 'models' ? 'active' : ''}`}
          onClick={() => setActiveTab('models')}
        >
          Models
        </button>
        <button
          className={`admin-tab ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          Users
        </button>
      </div>

      <div className="admin-content">
        {activeTab === 'usage' && <UsageTab api={api} />}
        {activeTab === 'models' && <ModelsTab api={api} />}
        {activeTab === 'users' && <UsersTab api={api} />}
      </div>
    </div>
  )
}
