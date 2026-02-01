import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

function ItemsPage() {
  const { getAuthHeader } = useAuth()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [newItem, setNewItem] = useState({ name: '', description: '', price: '' })
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    fetchItems()
  }, [])

  const fetchItems = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/items`, {
        headers: getAuthHeader(),
      })
      if (!response.ok) throw new Error('Failed to fetch items')
      const data = await response.json()
      setItems(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const createItem = async (e) => {
    e.preventDefault()
    if (!newItem.name || !newItem.price) return

    try {
      setIsCreating(true)
      const response = await fetch(`${API_BASE}/items`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          name: newItem.name,
          description: newItem.description || null,
          price: parseFloat(newItem.price),
        }),
      })

      if (!response.ok) throw new Error('Failed to create item')

      const created = await response.json()
      setItems([...items, created])
      setNewItem({ name: '', description: '', price: '' })
    } catch (err) {
      setError(err.message)
    } finally {
      setIsCreating(false)
    }
  }

  const deleteItem = async (id) => {
    try {
      const response = await fetch(`${API_BASE}/items/${id}`, {
        method: 'DELETE',
        headers: getAuthHeader(),
      })

      if (!response.ok) throw new Error('Failed to delete item')

      setItems(items.filter((item) => item.id !== id))
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="container">
      <h1>Items</h1>

      {/* Create Item Form */}
      <div className="card">
        <h2>Create New Item</h2>
        <form onSubmit={createItem} className="item-form">
          <div className="form-group">
            <label htmlFor="name">Name *</label>
            <input
              type="text"
              id="name"
              value={newItem.name}
              onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
              placeholder="Item name"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="description">Description</label>
            <input
              type="text"
              id="description"
              value={newItem.description}
              onChange={(e) =>
                setNewItem({ ...newItem, description: e.target.value })
              }
              placeholder="Optional description"
            />
          </div>
          <div className="form-group">
            <label htmlFor="price">Price *</label>
            <input
              type="number"
              id="price"
              step="0.01"
              min="0"
              value={newItem.price}
              onChange={(e) => setNewItem({ ...newItem, price: e.target.value })}
              placeholder="0.00"
              required
            />
          </div>
          <button type="submit" disabled={isCreating}>
            {isCreating ? 'Creating...' : 'Create Item'}
          </button>
        </form>
      </div>

      {/* Items List */}
      <div className="card">
        <div className="card-header">
          <h2>All Items</h2>
          <button
            onClick={fetchItems}
            disabled={loading}
            className="btn-secondary"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {error && <p className="error-message">Error: {error}</p>}

        {!loading && !error && items.length === 0 && (
          <p className="empty-state">No items yet. Create one above!</p>
        )}

        {!loading && !error && items.length > 0 && (
          <ul className="items-list">
            {items.map((item) => (
              <li key={item.id} className="item-card">
                <div className="item-info">
                  <h3>{item.name}</h3>
                  <p>{item.description || 'No description'}</p>
                </div>
                <div className="item-actions">
                  <span className="item-price">${item.price.toFixed(2)}</span>
                  <button
                    onClick={() => deleteItem(item.id)}
                    className="btn-danger"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default ItemsPage
