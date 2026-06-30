import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { motion, AnimatePresence } from 'framer-motion'

export function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    let res
    if (mode === 'login') {
      res = await login(username, password)
    } else {
      if (!email) { setError('Email is required'); setLoading(false); return }
      res = await register(username, email, password)
      if (res.success) {
        setMode('login')
        setError('')
        setPassword('')
        setLoading(false)
        return
      }
    }
    if (!res.success) setError(res.error || 'Something went wrong')
    setLoading(false)
  }

  return (
    <div className="auth-page">
      <div className="auth-logo">⚡</div>
      <h1 className="auth-headline">DSA Buddy</h1>
      <p className="auth-subtitle">
        {mode === 'login' ? 'Welcome back! Keep the streak alive.' : 'Start your DSA mastery journey.'}
      </p>

      <AnimatePresence mode="wait">
        <motion.form
          key={mode}
          className="auth-form"
          onSubmit={handleSubmit}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.22 }}
        >
          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              className="form-input"
              placeholder="your_username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoComplete="username"
            />
          </div>

          {mode === 'register' && (
            <motion.div
              className="form-group"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              <label className="form-label">Email</label>
              <input
                className="form-input"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                autoComplete="email"
              />
            </motion.div>
          )}

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              className="form-input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          {error && <div className="error-msg">⚠ {error}</div>}

          <button className="btn btn-primary btn-full" type="submit" disabled={loading}>
            {loading
              ? <span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
              : mode === 'login' ? '→ Sign In' : '→ Create Account'}
          </button>
        </motion.form>
      </AnimatePresence>

      <div className="auth-switch">
        {mode === 'login'
          ? <>Don't have an account? <span onClick={() => { setMode('register'); setError('') }}>Register</span></>
          : <>Already have an account? <span onClick={() => { setMode('login'); setError('') }}>Sign in</span></>}
      </div>
    </div>
  )
}
