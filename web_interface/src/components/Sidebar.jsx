import { useState, useEffect, useCallback } from 'react'
import { api } from '../api.js'

function avatarInitials(phone) {
  const digits = phone.replace(/\D/g, '')
  return digits.slice(-2) || '??'
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now - d
  const diffDays = Math.floor(diffMs / 86400000)
  if (diffDays === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (diffDays === 1) return 'Yesterday'
  return d.toLocaleDateString([], { day: '2-digit', month: '2-digit' })
}

const statusDot = {
  pending: 'bg-yellow-400',
  sent: 'bg-green-400',
  failed: 'bg-red-500',
}

export default function Sidebar({ selectedPhone, onSelect, refreshKey, onLogout }) {
  const [conversations, setConversations] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [newPhone, setNewPhone] = useState('')
  const [showNewForm, setShowNewForm] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await api.getConversations()
      setConversations(data)
    } catch {
      // 401 is handled globally in api.js
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load, refreshKey])

  useEffect(() => {
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [load])

  function handleNewConversation(e) {
    e.preventDefault()
    const phone = newPhone.trim()
    if (!phone) return
    onSelect(phone)
    setNewPhone('')
    setShowNewForm(false)
  }

  const filtered = conversations.filter(
    (c) =>
      c.phone_number.includes(search) ||
      c.last_message.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <aside className="w-80 bg-white border-r border-slate-200 flex flex-col flex-shrink-0">
      {/* Header */}
      <div className="px-4 py-4 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <span className="font-semibold text-slate-800">SMS Gateway</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowNewForm((v) => !v)}
            title="New conversation"
            className="text-slate-400 hover:text-indigo-600 transition p-1.5 rounded-lg hover:bg-indigo-50"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
          <button
            onClick={onLogout}
            title="Sign out"
            className="text-slate-400 hover:text-slate-600 transition p-1.5 rounded-lg hover:bg-slate-100"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>

      {/* New conversation form */}
      {showNewForm && (
        <form onSubmit={handleNewConversation} className="px-4 py-3 border-b border-slate-100 bg-indigo-50">
          <p className="text-xs font-medium text-indigo-700 mb-2">New conversation</p>
          <div className="flex gap-2">
            <input
              type="tel"
              value={newPhone}
              onChange={(e) => setNewPhone(e.target.value)}
              placeholder="+33612345678"
              autoFocus
              className="flex-1 px-3 py-2 border border-indigo-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
            />
            <button
              type="submit"
              className="px-3 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
            >
              Go
            </button>
          </div>
        </form>
      )}

      {/* Search */}
      <div className="px-4 py-3">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
            fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search conversations…"
            className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <p className="text-center text-slate-400 text-sm py-10">Loading…</p>
        ) : filtered.length === 0 ? (
          <p className="text-center text-slate-400 text-sm py-10">
            {search ? 'No results' : 'No conversations yet'}
          </p>
        ) : (
          filtered.map((conv) => (
            <button
              key={conv.phone_number}
              onClick={() => onSelect(conv.phone_number)}
              className={`w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-slate-50 transition border-b border-slate-50 ${
                selectedPhone === conv.phone_number
                  ? 'bg-indigo-50 border-l-[3px] border-l-indigo-500'
                  : 'border-l-[3px] border-l-transparent'
              }`}
            >
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-400 to-blue-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                {avatarInitials(conv.phone_number)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-800 text-sm truncate">
                    {conv.phone_number}
                  </span>
                  <span className="text-xs text-slate-400 ml-2 flex-shrink-0">
                    {formatTime(conv.created_at)}
                  </span>
                </div>
                <div className="flex items-center gap-1 mt-0.5">
                  {conv.direction === 'outbound' && (
                    <svg className="w-3 h-3 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  )}
                  <p className="text-xs text-slate-500 truncate">{conv.last_message}</p>
                </div>
              </div>
              {conv.direction === 'outbound' && (
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot[conv.status] || 'bg-slate-300'}`} />
              )}
            </button>
          ))
        )}
      </div>
    </aside>
  )
}
