import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import { motion, AnimatePresence } from 'framer-motion'
import { problemApi } from '../lib/api'

interface ProblemState {
  platform: string
  slug: string
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
  url: string
  userCode?: string
  isAccepted?: boolean
}

/** Ask the service worker for the currently detected problem */
function useDetectedProblem() {
  const [problem, setProblem] = useState<ProblemState | null>(null)
  const [detecting, setDetecting] = useState(true)

  useEffect(() => {
    const fetchProblem = () => {
      if (typeof chrome !== 'undefined' && chrome.runtime) {
        chrome.runtime.sendMessage({ type: 'GET_CURRENT_PROBLEM' }, (res) => {
          setProblem(res?.problem ?? null)
          setDetecting(false)
        })
      } else {
        // Dev fallback outside extension
        setDetecting(false)
      }
    }

    fetchProblem()
    // Re-check every 3s in case user navigated to a problem after opening popup
    const interval = setInterval(fetchProblem, 3000)
    return () => clearInterval(interval)
  }, [])

  return { problem, detecting }
}

export function HintPage() {
  const { user } = useAuth()
  const { problem, detecting } = useDetectedProblem()

  const [hints, setHints] = useState<string[]>([])
  const [unlockedCount, setUnlockedCount] = useState(0)
  const [loadingHints, setLoadingHints] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hintLevel, setHintLevel] = useState(3)
  const [codeSnippet, setCodeSnippet] = useState<string>('')
  
  const [review, setReview] = useState<any>(null)
  const [loadingReview, setLoadingReview] = useState(false)
  const [reviewError, setReviewError] = useState<string | null>(null)

  // Update code snippet whenever problem updates
  useEffect(() => {
    if (problem?.userCode) {
      setCodeSnippet(problem.userCode.slice(0, 200)) // show first 200 chars as preview
    }
  }, [problem])

  // Fetch Review if Accepted
  useEffect(() => {
    if (!problem?.isAccepted || !user?.id) return
    
    let isSubscribed = true
    const fetchReview = async () => {
      setLoadingReview(true)
      try {
        const token = await new Promise<string>((resolve) => {
          chrome.storage.local.get(['accessToken'], (data) => resolve(data.accessToken as string))
        })
        
        // Poll for review up to 15 times
        for (let i = 0; i < 15; i++) {
          if (!isSubscribed) return
          const res = await problemApi.getReview(user.id, problem.slug, token)
          const data = await res.json()
          if (data.status === 'ready') {
            setReview(data.review)
            setLoadingReview(false)
            return
          }
          // wait 2s before next poll
          await new Promise(r => setTimeout(r, 2000))
        }
        if (isSubscribed) setReviewError("Review generation timed out.")
      } catch (err: any) {
        if (isSubscribed) setReviewError(err.message)
      } finally {
        if (isSubscribed) setLoadingReview(false)
      }
    }
    
    fetchReview()
    return () => { isSubscribed = false }
  }, [problem?.isAccepted, problem?.slug, user?.id])

  const requestHints = useCallback(async () => {
    if (!problem || !user?.id) return
    setLoadingHints(true)
    setError(null)
    setHints([])
    setUnlockedCount(0)

    try {
      if (typeof chrome !== 'undefined' && chrome.runtime) {
        const res = await new Promise<any>((resolve) => {
          chrome.runtime.sendMessage({
            type: 'REQUEST_HINTS',
            payload: {
              userId: user.id,
              problem,
              hintLevel,
            },
          }, resolve)
        })

        if (res?.ok && res.hints?.length > 0) {
          setHints(res.hints)
          setUnlockedCount(1) // start with first hint visible
        } else if (res?.pending) {
          setError('Hint generation is taking longer than expected. Try again in a moment.')
        } else {
          setError(res?.error || 'Failed to generate hints. Check that the backend is running.')
        }
      } else {
        setError('Extension runtime not available.')
      }
    } catch (e: any) {
      setError(e.message || 'Unknown error')
    } finally {
      setLoadingHints(false)
    }
  }, [problem, user, hintLevel])

  const unlockNext = useCallback(() => {
    setUnlockedCount(n => Math.min(n + 1, hints.length))
  }, [hints.length])

  // ─── States ───────────────────────────────────────────────────────────────

  if (detecting) {
    return (
      <div className="main-content">
        <div className="no-problem-detected">
          <div className="spinner" style={{ width: 32, height: 32 }} />
          <p style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Scanning active tab for a DSA problem…</p>
        </div>
      </div>
    )
  }

  if (!problem) {
    return (
      <div className="main-content">
        <div className="no-problem-detected">
          <div className="empty-icon">🔍</div>
          <p>No DSA problem detected</p>
          <p style={{ fontSize: 11 }}>Open a problem on LeetCode, Codeforces, HackerRank, or AtCoder to get AI-powered hints tailored to your code.</p>
        </div>
      </div>
    )
  }

  const diffColor = problem.difficulty === 'easy' ? 'var(--accent-emerald)'
    : problem.difficulty === 'hard' ? 'var(--accent-red)'
    : 'var(--accent-amber)'

  return (
    <div className="main-content fade-in">
      {/* Problem Card */}
      <motion.div className="hint-container" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="hint-header">
          <div className="hint-icon-wrap">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M9.663 17h4.673M12 3v1m6.364 1.636-.707.707M21 12h-1M4 12H3m3.343-5.657-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="hint-problem-title" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {problem.title}
            </div>
            <div className="hint-problem-meta">
              <span className={`badge badge-${problem.difficulty}`}>
                {problem.difficulty.charAt(0).toUpperCase() + problem.difficulty.slice(1)}
              </span>
              {problem.tags.slice(0, 2).map(t => <span key={t} className="tag">{t}</span>)}
            </div>
          </div>
          {problem.isAccepted && (
            <span style={{ fontSize: 18 }} title="Accepted!">✅</span>
          )}
        </div>

        {/* Code Snapshot Preview */}
        {codeSnippet && (
          <div style={{
            background: 'var(--bg-deep)', borderRadius: 'var(--radius-sm)',
            padding: '8px 10px', marginBottom: 12, border: '1px solid var(--border-subtle)',
          }}>
            <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Your current code (Gemini will analyze this)
            </div>
            <pre style={{
              fontSize: 10, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)',
              overflow: 'hidden', maxHeight: 60, margin: 0,
            }}>
              {codeSnippet}{codeSnippet.length >= 200 ? '…' : ''}
            </pre>
          </div>
        )}

        {/* Hint Level Selector */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 12, alignItems: 'center' }}>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', flexShrink: 0 }}>Hints depth:</span>
          {[1, 2, 3, 4, 5].map(n => (
            <button
              key={n}
              onClick={() => setHintLevel(n)}
              style={{
                width: 26, height: 26, borderRadius: '50%', border: 'none', cursor: 'pointer',
                background: hintLevel >= n ? 'var(--accent-primary)' : 'var(--bg-elevated)',
                color: hintLevel >= n ? '#fff' : 'var(--text-muted)',
                fontSize: 10, fontWeight: 700, transition: 'all 0.15s',
              }}
            >{n}</button>
          ))}
        </div>

        {/* Get Hints Button */}
        {hints.length === 0 && !problem.isAccepted && (
          <button
            className="btn btn-primary btn-full"
            onClick={requestHints}
            disabled={loadingHints}
            style={{ marginBottom: 4 }}
          >
            {loadingHints ? (
              <>
                <div className="spinner" style={{ width: 14, height: 14 }} />
                Asking Gemini…
              </>
            ) : (
              <>💡 {codeSnippet ? 'Get Hints for My Approach' : 'Get Hints'}</>
            )}
          </button>
        )}

        {error && (
          <div className="error-msg" style={{ marginTop: 8 }}>{error}</div>
        )}
      </motion.div>

      {/* AI Code Critic / Post-Solve Review */}
      {problem.isAccepted && (
        <motion.div className="card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} style={{ padding: 14, marginBottom: 16 }}>
          <div className="section-title" style={{ marginBottom: 10, color: 'var(--accent-emerald)' }}>
            📝 AI Code Critic
          </div>
          {loadingReview ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, padding: '20px 0' }}>
              <div className="spinner" style={{ width: 24, height: 24, borderTopColor: 'var(--accent-emerald)' }} />
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Analyzing Time & Space Complexity...</div>
            </div>
          ) : reviewError ? (
            <div className="error-msg">{reviewError}</div>
          ) : review ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', gap: 8 }}>
                <div style={{ flex: 1, background: 'var(--bg-deep)', padding: 8, borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Time Complexity</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent-emerald)', marginTop: 4 }}>{review.time_complexity}</div>
                </div>
                <div style={{ flex: 1, background: 'var(--bg-deep)', padding: 8, borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Space Complexity</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent-emerald)', marginTop: 4 }}>{review.space_complexity}</div>
                </div>
              </div>
              
              {review.suggestions?.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>Suggestions:</div>
                  <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11, color: 'var(--text-secondary)' }}>
                    {review.suggestions.map((s: string, i: number) => <li key={i} style={{ marginBottom: 4 }}>{s}</li>)}
                  </ul>
                </div>
              )}

              {review.refactored_code && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>Senior Engineer Rewrite:</div>
                  <pre style={{
                    fontSize: 10, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)',
                    background: 'var(--bg-deep)', padding: 10, borderRadius: 'var(--radius-sm)',
                    overflowX: 'auto', margin: 0, border: '1px solid var(--border-subtle)'
                  }}>
                    {review.refactored_code}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Waiting for code submission...</div>
          )}
        </motion.div>
      )}

      {/* Progressive Hints */}
      <AnimatePresence>
        {hints.length > 0 && (
          <motion.div
            className="card"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ padding: 14 }}
          >
            <div className="section-title" style={{ marginBottom: 10 }}>
              Progressive Hints
              {codeSnippet && <span style={{ marginLeft: 6, fontSize: 9, color: diffColor, fontWeight: 600 }}>● Code-aware</span>}
            </div>

            <div className="hint-steps">
              {hints.map((hint, i) => {
                const unlocked = i < unlockedCount
                return (
                  <motion.div
                    key={i}
                    className={`hint-step ${!unlocked ? 'locked' : ''}`}
                    initial={unlocked ? { opacity: 0, y: 6 } : {}}
                    animate={unlocked ? { opacity: 1, y: 0 } : {}}
                    transition={{ delay: i * 0.07 }}
                    onClick={() => { if (!unlocked && i === unlockedCount) unlockNext() }}
                  >
                    <div className="hint-step-num">{unlocked ? i + 1 : '🔒'}</div>
                    <div className="hint-step-text">
                      {unlocked ? hint : 'Click to unlock the next hint…'}
                    </div>
                  </motion.div>
                )
              })}
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              {unlockedCount < hints.length && (
                <button className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={unlockNext}>
                  Unlock Next Hint →
                </button>
              )}
              <button className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={requestHints}>
                ↺ New Hints
              </button>
            </div>

            {unlockedCount === hints.length && (
              <div style={{ textAlign: 'center', marginTop: 10, fontSize: 11, color: 'var(--accent-emerald)' }}>
                ✓ All hints revealed — you got this!
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* XP Widget */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <div className="card-title-icon" style={{ background: 'rgba(167,139,250,0.15)', color: 'var(--accent-secondary)' }}>⚡</div>
            Session XP
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>LV {user?.level ?? 1}</span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${(user?.xp ?? 0) % 100}%` }} />
        </div>
        <div className="progress-meta">
          <span>{user?.xp ?? 0} XP</span>
          <span>Next level: {100 - ((user?.xp ?? 0) % 100)} XP away</span>
        </div>
      </div>
    </div>
  )
}
