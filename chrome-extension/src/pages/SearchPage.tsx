import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'

interface SearchResult { title: string; slug: string }

const REVIEW_DUE = [
  { title: 'Binary Search', slug: 'binary-search', due: 'Now' },
  { title: 'Merge Intervals', slug: 'merge-intervals', due: '1h' },
  { title: 'LRU Cache', slug: 'lru-cache', due: '3h' },
]

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!query.trim()) { setResults([]); return }
    setLoading(true)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`http://localhost/api/problems/search?q=${encodeURIComponent(query)}`)
        const data = await res.json()
        setResults(Array.isArray(data) ? data : [])
      } catch {
        setResults([])
      }
      setLoading(false)
    }, 300)
  }, [query])

  return (
    <div className="main-content fade-in">
      {/* Search Bar */}
      <div className="search-wrap">
        <svg className="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          className="search-input"
          placeholder="Search problems by title…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          autoFocus
        />
      </div>

      {/* Search Results */}
      {query && (
        <div>
          <div className="section-title">Results</div>
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '20px 0' }}>
              <div className="spinner" />
            </div>
          ) : results.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 12, padding: '16px 0' }}>No problems found.</div>
          ) : (
            <div className="problem-list" style={{ marginTop: 8 }}>
              {results.map((r, i) => (
                <motion.a
                  key={r.slug}
                  className="problem-row"
                  href={`https://leetcode.com/problems/${r.slug}`}
                  target="_blank"
                  rel="noreferrer"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                >
                  <span className="problem-title-text">{r.title}</span>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
                  </svg>
                </motion.a>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Spaced Review */}
      {!query && (
        <div>
          <div className="card-header">
            <div className="section-title" style={{ marginBottom: 0 }}>Due for Review</div>
            <span style={{ fontSize: 10, color: 'var(--accent-red)', fontWeight: 600 }}>{REVIEW_DUE.length} pending</span>
          </div>
          <div className="problem-list" style={{ marginTop: 8 }}>
            {REVIEW_DUE.map((p, i) => (
              <motion.div
                key={p.slug}
                className="problem-row"
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-amber)" strokeWidth="2.2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
                <span className="problem-title-text">{p.title}</span>
                <span style={{ fontSize: 10, color: p.due === 'Now' ? 'var(--accent-red)' : 'var(--text-muted)', fontWeight: 600, flexShrink: 0 }}>
                  {p.due}
                </span>
              </motion.div>
            ))}
          </div>

          {/* Topic Graph Teaser */}
          <div className="card" style={{ marginTop: 14 }}>
            <div className="card-title" style={{ marginBottom: 10 }}>
              <div className="card-title-icon" style={{ background: 'rgba(52,211,153,0.12)', color: 'var(--accent-emerald)' }}>🗺</div>
              Suggested Next Topics
            </div>
            <div className="tag-list">
              {['Sliding Window', 'Binary Search', 'Two Pointers', 'DFS/BFS', 'Heap', 'Trie', 'DP'].map(t => (
                <span key={t} className="tag">{t}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
