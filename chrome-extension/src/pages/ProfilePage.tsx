import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { progressApi, analyticsApi } from '../lib/api'
import { motion } from 'framer-motion'

const LEVELS = ['Newbie', 'Initiate', 'Practitioner', 'Expert', 'Master', 'Grandmaster']

export function ProfilePage() {
  const { user, token, logout } = useAuth()
  const levelName = LEVELS[Math.min((user?.level ?? 1) - 1, LEVELS.length - 1)]
  
  const [stats, setStats] = useState<any>({ total_solves: 0, streak_days: 0 })
  const [patterns, setPatterns] = useState<any[]>([])
  
  useEffect(() => {
    if (!user?.id || !token) return;
    
    progressApi.getStats(user.id, token)
      .then(data => setStats(data))
      .catch(err => console.error("Error fetching stats:", err));
      
    analyticsApi.getPatterns(user.id, token)
      .then(data => setPatterns(data))
      .catch(err => console.error("Error fetching patterns:", err));
  }, [user, token])

  return (
    <div className="main-content fade-in">
      {/* Profile Hero */}
      <motion.div
        className="card"
        style={{ textAlign: 'center', paddingTop: 24, paddingBottom: 24 }}
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
      >
        <div style={{
          width: 64, height: 64, borderRadius: '50%',
          background: 'var(--gradient-primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 26, margin: '0 auto 12px',
          boxShadow: '0 4px 24px rgba(99,120,255,0.4)'
        }}>
          {user?.username?.charAt(0).toUpperCase() ?? '?'}
        </div>
        <div style={{ fontSize: 16, fontWeight: 700 }}>{user?.username}</div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{user?.email || 'No email set'}</div>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 10,
          padding: '4px 14px', background: 'rgba(99,120,255,0.12)',
          border: '1px solid var(--border-muted)', borderRadius: 99,
          fontSize: 11, color: 'var(--accent-primary)', fontWeight: 600
        }}>
          ⭐ {levelName} — Level {user?.level ?? 1}
        </div>
      </motion.div>

      {/* XP Progress */}
      <motion.div className="card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <div className="card-header">
          <div className="card-title">
            <div className="card-title-icon" style={{ background: 'rgba(99,120,255,0.12)', color: 'var(--accent-primary)' }}>⚡</div>
            Experience Points
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--accent-secondary)' }}>
            {user?.xp ?? 0} XP
          </span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${(user?.xp ?? 0) % 100}%` }} />
        </div>
        <div className="progress-meta">
          <span>Level {user?.level ?? 1} → {(user?.level ?? 1) + 1}</span>
          <span>{100 - ((user?.xp ?? 0) % 100)} XP to go</span>
        </div>
      </motion.div>

      {/* Achievement Stats */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <div className="section-title">Achievements</div>
        <div className="stat-grid" style={{ marginTop: 8 }}>
          <div className="stat-chip">
            <div className="stat-chip-value" style={{ fontSize: 18 }}>{stats.total_solves || 0}</div>
            <div className="stat-chip-label">Total Solved</div>
          </div>
          <div className="stat-chip">
            <div className="stat-chip-value" style={{ fontSize: 18 }}>{stats.streak_days || 0}🔥</div>
            <div className="stat-chip-label">Streak</div>
          </div>
          <div className="stat-chip">
            <div className="stat-chip-value" style={{ fontSize: 18 }}>{patterns.length}</div>
            <div className="stat-chip-label">Patterns Mastered</div>
          </div>
        </div>
      </motion.div>

      {/* DSA Patterns */}
      <motion.div className="card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <div className="card-title" style={{ marginBottom: 12 }}>
          <div className="card-title-icon" style={{ background: 'rgba(251,191,36,0.12)', color: 'var(--accent-amber)' }}>🏅</div>
          Top Patterns
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {patterns.slice(0, 4).map(p => (
            <div key={p.tag} style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
              padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)', fontSize: 16
            }}>
              <span style={{ fontSize: 11, color: 'var(--text-primary)', textAlign: 'center', fontWeight: 'bold' }}>{p.tag}</span>
              <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>{p.count} solves</span>
            </div>
          ))}
          {patterns.length === 0 && (
             <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Solve problems to uncover your mastered patterns.</span>
          )}
        </div>
      </motion.div>

      {/* Logout */}
      <motion.button
        className="btn btn-ghost btn-full"
        style={{ color: 'var(--accent-red)', borderColor: 'rgba(248,113,113,0.2)', marginTop: 16 }}
        onClick={logout}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.25 }}
      >
        Sign Out
      </motion.button>
    </div>
  )
}
