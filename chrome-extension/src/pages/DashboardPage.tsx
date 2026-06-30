import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import { progressApi, problemApi, solveApi } from '../lib/api'
import { motion, AnimatePresence } from 'framer-motion'

function useTimer() {
  const [seconds, setSeconds] = useState(0)
  const [running, setRunning] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => setSeconds(s => s + 1), 1000)
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [running])

  const format = (s: number) => {
    const m = Math.floor(s / 60).toString().padStart(2, '0')
    const sec = (s % 60).toString().padStart(2, '0')
    return `${m}:${sec}`
  }

  return { seconds, running, setRunning, reset: () => { setSeconds(0); setRunning(false) }, format }
}

interface Recommendation {
  slug: string
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
  url: string
  solved?: boolean
}

export function DashboardPage({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const { user, token } = useAuth()
  const timer = useTimer()

  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [stats, setStats] = useState<any>({ streak_days: 0, total_solves: 0, xp: 0 })
  const [loading, setLoading] = useState(true)
  const [solvingSlug, setSolvingSlug] = useState<string | null>(null)
  const [solvedToday, setSolvedToday] = useState<string[]>([])
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    if (!user?.id || !token) return

    const loadDashboard = async () => {
      try {
        const [userStats, recentSolves, recs] = await Promise.all([
          progressApi.getStats(user.id, token),
          progressApi.getRecentSolves(user.id, token),
          problemApi.getRecommendations(user.id, token).catch(() => []),
        ])

        setStats(userStats)

        // Mark which recommendations the user solved today
        const todayStr = new Date().toISOString().split('T')[0]
        const todaySlugs = (recentSolves as any[])
          .filter(s => s.solved_at?.startsWith(todayStr))
          .map(s => s.problem_slug)
        setSolvedToday(todaySlugs)

        // Merge recommendations + mark already-solved ones
        const recList = (recs as any[]).map(r => ({
          ...r,
          solved: todaySlugs.includes(r.slug),
        }))
        setRecommendations(recList)
      } catch (err) {
        console.error('Failed to load dashboard data:', err)
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [user, token])

  const handleMarkSolved = async (rec: Recommendation) => {
    if (!user?.id || !token || rec.solved) return
    setSolvingSlug(rec.slug)
    try {
      await solveApi.recordSolve(user.id, token, {
        problem_slug: rec.slug,
        difficulty: rec.difficulty,
        tags: rec.tags,
      })
      setRecommendations(prev =>
        prev.map(r => r.slug === rec.slug ? { ...r, solved: true } : r)
      )
      setSolvedToday(prev => [...prev, rec.slug])
      // Refresh stats after solve
      const updated = await progressApi.getStats(user.id, token)
      setStats(updated)
    } catch (e) {
      console.error('Failed to record solve:', e)
    } finally {
      setSolvingSlug(null)
    }
  }

  const handleSyncLeetCode = async () => {
    if (!user?.id || !token) return
    setSyncing(true)
    try {
      const res = await fetch('https://leetcode.com/api/problems/all/')
      if (!res.ok) throw new Error('Not logged into LeetCode or request blocked')
      const data = await res.json()
      
      const solvedSlugs = data.stat_status_pairs
        .filter((p: any) => p.status === 'ac')
        .map((p: any) => p.stat.question__title_slug)
        
      if (solvedSlugs.length > 0) {
        await progressApi.syncLeetCodeSolves(user.id, token, solvedSlugs)
        const updatedStats = await progressApi.getStats(user.id, token)
        setStats(updatedStats)
        // Refresh recommendations
        const recs = await problemApi.getRecommendations(user.id, token).catch(() => [])
        const todayStr = new Date().toISOString().split('T')[0]
        const recList = (recs as any[]).map((r: any) => ({
          ...r,
          solved: solvedToday.includes(r.slug),
        }))
        setRecommendations(recList)
      }
    } catch (err) {
      console.error('Failed to sync LeetCode:', err)
      alert('Failed to sync. Make sure you are logged into LeetCode.com in this browser.')
    } finally {
      setSyncing(false)
    }
  }

  const solvedCount = recommendations.filter(r => r.solved).length || solvedToday.length
  const totalGoal = Math.max(recommendations.length, 5)

  const difficultyConfig = {
    easy:   { color: 'var(--accent-emerald)', bg: 'rgba(52,211,153,0.12)' },
    medium: { color: 'var(--accent-amber)',   bg: 'rgba(251,191,36,0.12)' },
    hard:   { color: 'var(--accent-red)',     bg: 'rgba(248,113,113,0.12)' },
  }

  return (
    <div className="main-content fade-in">
      {/* Streak Card */}
      <motion.div className="card" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div className="streak-bar">
          <div className="streak-fire">🔥</div>
          <div className="streak-info">
            <div className="streak-count">{stats.streak_days}</div>
            <div className="streak-label">Day Streak</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Today's Goal</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>
              {solvedCount}/{totalGoal}
            </div>
          </div>
        </div>
        <div className="streak-progress" style={{ marginTop: 12 }}>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${Math.min(100, (solvedCount / totalGoal) * 100)}%` }} />
          </div>
          <div className="progress-meta">
            <span>{solvedCount} solved today</span>
            <span>{Math.max(0, totalGoal - solvedCount)} remaining</span>
          </div>
        </div>
      </motion.div>

      {/* Stats Row */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <div className="section-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Overall Progress</span>
          <button 
            className="btn btn-ghost btn-sm" 
            onClick={handleSyncLeetCode} 
            disabled={syncing}
            style={{ fontSize: 10, padding: '2px 6px', height: 'auto', background: 'rgba(99,120,255,0.1)' }}
          >
            {syncing ? 'Syncing...' : '↻ Sync LeetCode'}
          </button>
        </div>
        <div className="stat-grid" style={{ marginTop: 8 }}>
          <div className="stat-chip">
            <div className="stat-chip-value">{stats.total_solves}</div>
            <div className="stat-chip-label">Total Solved</div>
          </div>
          <div className="stat-chip">
            <div className="stat-chip-value">{stats.level ?? 1}</div>
            <div className="stat-chip-label">Level</div>
          </div>
          <div className="stat-chip">
            <div className="stat-chip-value">{stats.xp ?? 0}</div>
            <div className="stat-chip-label">XP</div>
          </div>
        </div>
      </motion.div>

      {/* Session Timer */}
      <motion.div className="card" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <div className="card-header">
          <div className="card-title">
            <div className="card-title-icon" style={{ background: 'rgba(99,120,255,0.12)', color: 'var(--accent-primary)' }}>⏱</div>
            Session Timer
          </div>
          {timer.running && <div className="status-dot" />}
        </div>
        <div className="timer-display">{timer.format(timer.seconds)}</div>
        <div className="timer-controls">
          <button
            className={`btn btn-sm ${timer.running ? 'btn-ghost' : 'btn-primary'}`}
            onClick={() => timer.setRunning(r => !r)}
          >
            {timer.running ? '⏸ Pause' : '▶ Start'}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={timer.reset}>↺ Reset</button>
        </div>
      </motion.div>

      {/* Daily Recommendations */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <div className="card-header">
          <div className="section-title">Today's Problems</div>
          <button
            onClick={() => onNavigate && onNavigate('journal')}
            style={{ fontSize: 10, color: 'var(--accent-primary)', fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer' }}
          >
            View Journal →
          </button>
        </div>

        <div className="problem-list">
          {loading ? (
            <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
              <div className="spinner" style={{ width: 20, height: 20 }} />
              <span style={{ fontSize: 11 }}>Loading recommendations…</span>
            </div>
          ) : recommendations.length === 0 ? (
            <div className="no-problem-detected">
              <div className="empty-icon">📚</div>
              <p>No problems in the database yet.</p>
              <p style={{ fontSize: 11 }}>The problem library will populate as you browse LeetCode.</p>
            </div>
          ) : (
            <AnimatePresence>
              {recommendations.map((rec, i) => {
                const dc = difficultyConfig[rec.difficulty] || difficultyConfig.medium
                return (
                  <motion.div
                    key={rec.slug}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.22 + i * 0.05 }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '10px 12px',
                      background: rec.solved ? 'rgba(52,211,153,0.06)' : 'var(--bg-elevated)',
                      border: `1px solid ${rec.solved ? 'rgba(52,211,153,0.25)' : 'var(--border-subtle)'}`,
                      borderRadius: 'var(--radius-md)',
                      transition: 'all 0.2s',
                    }}
                  >
                    {/* Difficulty dot */}
                    <div style={{
                      width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                      background: dc.color,
                      boxShadow: `0 0 6px ${dc.color}`,
                    }} />

                    {/* Problem info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                        {rec.title}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                        <span style={{ color: dc.color, fontWeight: 600 }}>
                          {rec.difficulty.charAt(0).toUpperCase() + rec.difficulty.slice(1)}
                        </span>
                        {rec.tags.slice(0, 2).map(t => (
                          <span key={t} style={{ marginLeft: 6, opacity: 0.7 }}>#{t}</span>
                        ))}
                      </div>
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <a
                        href={rec.url}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          fontSize: 10, padding: '3px 8px', borderRadius: 'var(--radius-sm)',
                          background: 'rgba(99,120,255,0.12)', color: 'var(--accent-primary)',
                          textDecoration: 'none', fontWeight: 600,
                        }}
                      >
                        Solve →
                      </a>
                      {!rec.solved ? (
                        <button
                          onClick={() => handleMarkSolved(rec)}
                          disabled={solvingSlug === rec.slug}
                          style={{
                            fontSize: 10, padding: '3px 8px', borderRadius: 'var(--radius-sm)',
                            background: 'rgba(52,211,153,0.12)', color: 'var(--accent-emerald)',
                            border: 'none', cursor: 'pointer', fontWeight: 600,
                            opacity: solvingSlug === rec.slug ? 0.6 : 1,
                          }}
                        >
                          {solvingSlug === rec.slug ? '…' : '✓ Done'}
                        </button>
                      ) : (
                        <span style={{ fontSize: 14 }}>✅</span>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>
          )}
        </div>
      </motion.div>
    </div>
  )
}
