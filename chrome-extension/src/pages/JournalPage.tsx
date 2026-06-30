import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { journalApi } from '../lib/api'
import { motion } from 'framer-motion'

export function JournalPage() {
  const { user, token } = useAuth()
  const [entries, setEntries] = useState<any[]>([])
  const [composing, setComposing] = useState(false)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [selected, setSelected] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user?.id || !token) return;
    journalApi.getEntries(user.id, token)
      .then(data => setEntries(data))
      .catch(err => console.error("Error fetching journals", err))
      .finally(() => setLoading(false))
  }, [user, token]);

  const saveEntry = async () => {
    if (!title.trim() || !content.trim() || !user?.id || !token) return
    
    // Fallback logic for problemSlug extraction
    let problemSlug = 'general'
    if (title.toLowerCase().includes('two sum')) problemSlug = 'two-sum'
    else problemSlug = title.toLowerCase().replace(/[^a-z0-9]+/g, '-')
    
    try {
      const newEntry = await journalApi.createEntry(user.id, problemSlug, content, token)
      setEntries(e => [{...newEntry, title}, ...e])
      setTitle('')
      setContent('')
      setComposing(false)
    } catch (e) {
      console.error("Failed to save entry", e)
    }
  }

  if (selected) {
    return (
      <div className="main-content fade-in">
        <button className="btn btn-ghost btn-sm" style={{ alignSelf: 'flex-start' }} onClick={() => setSelected(null)}>
          ← Back
        </button>
        <div className="card">
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>{selected.title || selected.problem_slug}</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7, fontFamily: 'var(--font-mono)' }}>{selected.reflection}</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 10 }}>{new Date(selected.created_at).toLocaleDateString()}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="main-content fade-in">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div className="section-title">Journal</div>
        <button className="btn btn-primary btn-sm" onClick={() => setComposing(c => !c)}>
          {composing ? '✕ Cancel' : '+ New Entry'}
        </button>
      </div>

      {composing && (
        <motion.div
          className="card"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <input
            className="form-input"
            placeholder="Entry title or Problem Name…"
            value={title}
            onChange={e => setTitle(e.target.value)}
            style={{ marginBottom: 10 }}
          />
          <textarea
            style={{
              width: '100%', minHeight: 90, background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)',
              fontSize: 12, padding: '10px 12px', outline: 'none', resize: 'vertical', lineHeight: 1.6
            }}
            placeholder="Write your notes, approach, or 'aha' moment…"
            value={content}
            onChange={e => setContent(e.target.value)}
            onFocus={e => (e.target.style.borderColor = 'var(--accent-primary)')}
            onBlur={e => (e.target.style.borderColor = 'var(--border-subtle)')}
          />
          <button className="btn btn-primary btn-sm btn-full" style={{ marginTop: 10 }} onClick={saveEntry}>
            Save Entry
          </button>
        </motion.div>
      )}

      <div className="journal-list">
        {loading ? <div style={{ color: 'var(--text-muted)' }}>Loading...</div> : entries.map((entry, i) => (
          <motion.div
            key={entry.id}
            className="journal-card"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            onClick={() => setSelected(entry)}
          >
            <div className="journal-card-title">{entry.title || entry.problem_slug}</div>
            <div className="journal-card-preview">{entry.reflection}</div>
            <div className="journal-card-footer">
              <span className="journal-card-date">{new Date(entry.created_at).toLocaleDateString()}</span>
            </div>
          </motion.div>
        ))}
      </div>

      {!loading && entries.length === 0 && (
        <div className="no-problem-detected">
          <div className="empty-icon">📓</div>
          <p>No journal entries yet</p>
          <p style={{ fontSize: 11 }}>Document your approaches and aha-moments as you solve problems.</p>
        </div>
      )}
    </div>
  )
}
