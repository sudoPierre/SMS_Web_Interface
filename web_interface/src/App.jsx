import { useState } from 'react'
import { isAuthenticated, clearToken } from './api.js'
import Login from './components/Login.jsx'
import Sidebar from './components/Sidebar.jsx'
import MessageThread from './components/MessageThread.jsx'
import ComposeBar from './components/ComposeBar.jsx'

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated())
  const [selectedPhone, setSelectedPhone] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const refresh = () => setRefreshKey((k) => k + 1)

  function handleLogout() {
    clearToken()
    setAuthed(false)
    setSelectedPhone(null)
  }

  if (!authed) {
    return <Login onSuccess={() => setAuthed(true)} />
  }

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden">
      <Sidebar
        selectedPhone={selectedPhone}
        onSelect={setSelectedPhone}
        refreshKey={refreshKey}
        onLogout={handleLogout}
      />
      <main className="flex-1 flex flex-col overflow-hidden">
        {selectedPhone ? (
          <>
            <MessageThread phone={selectedPhone} refreshKey={refreshKey} />
            <ComposeBar phone={selectedPhone} onSent={refresh} />
          </>
        ) : (
          <EmptyState />
        )}
      </main>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center text-slate-400 select-none">
      <div className="text-center">
        <div className="mx-auto mb-4 w-16 h-16 bg-slate-200 rounded-2xl flex items-center justify-center">
          <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </div>
        <p className="text-base font-medium text-slate-600">Select a conversation</p>
        <p className="text-sm mt-1">or start a new one from the sidebar</p>
      </div>
    </div>
  )
}
