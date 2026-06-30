import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from './context/AuthContext'
import { AuthPage } from './pages/AuthPage'
import { DashboardPage } from './pages/DashboardPage'
import { HintPage } from './pages/HintPage'
import { SearchPage } from './pages/SearchPage'
import { JournalPage } from './pages/JournalPage'
import { ProfilePage } from './pages/ProfilePage'

type Tab = 'dashboard' | 'hint' | 'search' | 'journal' | 'profile'

function NavIcon({ id, tab, label, children, onClick }: {
  id: Tab; tab: Tab; label: string; children: React.ReactNode; onClick: () => void
}) {
  return (
    <button className={`tab-btn ${tab === id ? 'active' : ''}`} onClick={onClick} title={label}>
      {children}
      <span>{label}</span>
    </button>
  )
}

function AppContent() {
  const { user, loading } = useAuth()
  const [tab, setTab] = useState<Tab>('dashboard')

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 600 }}>
        <div className="spinner" style={{ width: 36, height: 36 }} />
      </div>
    )
  }

  if (!user) return <AuthPage />

  const pages: Record<Tab, React.ReactNode> = {
    dashboard: <DashboardPage onNavigate={(t) => setTab(t as Tab)} />,
    hint: <HintPage />,
    search: <SearchPage />,
    journal: <JournalPage />,
    profile: <ProfilePage />,
  }

  return (
    <div className="app-shell">
      {/* Top Nav */}
      <div className="top-nav">
        <div className="brand">
          <div className="brand-icon">⚡</div>
          <div className="brand-name">DSA Buddy</div>
        </div>
        <div className="nav-actions">
          <div className="status-dot" title="Connected" />
          <button className="icon-btn" title="Settings" onClick={() => setTab('profile')}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Page Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={tab}
          style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
          initial={{ opacity: 0, x: 8 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.18 }}
        >
          {pages[tab]}
        </motion.div>
      </AnimatePresence>

      {/* Bottom Tab Bar */}
      <div className="bottom-nav">
        <NavIcon id="dashboard" tab={tab} label="Home" onClick={() => setTab('dashboard')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
        </NavIcon>
        <NavIcon id="hint" tab={tab} label="Hints" onClick={() => setTab('hint')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <path d="M9.663 17h4.673M12 3v1m6.364 1.636-.707.707M21 12h-1M4 12H3m3.343-5.657-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
          </svg>
        </NavIcon>
        <NavIcon id="search" tab={tab} label="Search" onClick={() => setTab('search')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
        </NavIcon>
        <NavIcon id="journal" tab={tab} label="Journal" onClick={() => setTab('journal')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
          </svg>
        </NavIcon>
        <NavIcon id="profile" tab={tab} label="Profile" onClick={() => setTab('profile')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
          </svg>
        </NavIcon>
      </div>
    </div>
  )
}

export default function App() {
  return <AppContent />
}
