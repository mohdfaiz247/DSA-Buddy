import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

interface User {
  id: string
  username: string
  email: string
  xp: number
  level: number
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>
  register: (username: string, email: string, password: string) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

const API = 'http://localhost/api/auth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Load token from chrome.storage or localStorage (fallback for dev)
    const loadAuth = async () => {
      try {
        const stored = localStorage.getItem('dsabuddy_token')
        const storedUser = localStorage.getItem('dsabuddy_user')
        if (stored && storedUser) {
          setToken(stored)
          setUser(JSON.parse(storedUser))
        }
      } catch {}
      setLoading(false)
    }
    loadAuth()
  }, [])

  const login = async (username: string, password: string) => {
    try {
      const res = await fetch(`${API}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await res.json()
      if (res.ok) {
        setToken(data.access_token)
        // Decode JWT payload for user info (basic)
        const payload = JSON.parse(atob(data.access_token.split('.')[1]))
        const u: User = { id: payload.sub, username: payload.username, email: '', xp: 0, level: 1 }
        setUser(u)
        localStorage.setItem('dsabuddy_token', data.access_token)
        localStorage.setItem('dsabuddy_user', JSON.stringify(u))
        return { success: true }
      }
      return { success: false, error: data.detail || 'Login failed' }
    } catch (e: any) {
      return { success: false, error: 'Cannot reach server. Is Docker running?' }
    }
  }

  const register = async (username: string, email: string, password: string) => {
    try {
      const res = await fetch(`${API}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      })
      const data = await res.json()
      if (res.ok) return { success: true }
      return { success: false, error: data.detail || 'Registration failed' }
    } catch (e: any) {
      return { success: false, error: 'Cannot reach server. Is Docker running?' }
    }
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('dsabuddy_token')
    localStorage.removeItem('dsabuddy_user')
  }

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
