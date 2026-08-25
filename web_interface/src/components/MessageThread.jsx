import { useEffect, useRef, useCallback, useState } from 'react'
import { api } from '../api.js'

function formatDateTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString([], {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function StatusIcon({ status }) {
  if (status === 'pending') {
    return (
      <svg className="w-3 h-3 text-indigo-300" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
          clipRule="evenodd" />
      </svg>
    )
  }
  if (status === 'sent') {
    return (
      <svg className="w-3 h-3 text-indigo-300" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd"
          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
          clipRule="evenodd" />
      </svg>
    )
  }
  if (status === 'failed') {
    return (
      <svg className="w-3 h-3 text-red-400" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
          clipRule="evenodd" />
      </svg>
    )
  }
  return null
}

export default function MessageThread({ phone, refreshKey }) {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)
  const bottomRef = useRef(null)
  const isFirstLoad = useRef(true)

  const load = useCallback(async () => {
    try {
      const data = await api.getMessages(phone)
      setMessages(data)
    } catch {
      // 401 handled globally
    } finally {
      setLoading(false)
    }
  }, [phone])

  // Reset on phone change
  useEffect(() => {
    setLoading(true)
    setMessages([])
    isFirstLoad.current = true
    load()
  }, [phone, load])

  // Refresh on parent signal
  useEffect(() => { load() }, [refreshKey, load])

  // Auto-poll
  useEffect(() => {
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [load])

  // Scroll to bottom
  useEffect(() => {
    if (messages.length === 0) return
    const behavior = isFirstLoad.current ? 'instant' : 'smooth'
    bottomRef.current?.scrollIntoView({ behavior })
    isFirstLoad.current = false
  }, [messages])

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Thread header */}
      <div className="px-6 py-3.5 bg-white border-b border-slate-200 flex items-center gap-3 flex-shrink-0">
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-400 to-blue-500 flex items-center justify-center text-white text-xs font-bold">
          {phone.replace(/\D/g, '').slice(-2)}
        </div>
        <div>
          <p className="font-semibold text-slate-800 text-sm">{phone}</p>
          <p className="text-xs text-slate-400">
            {messages.length} message{messages.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
        {loading ? (
          <p className="text-center text-slate-400 text-sm py-10">Loading…</p>
        ) : messages.length === 0 ? (
          <p className="text-center text-slate-400 text-sm py-10">
            No messages yet — send one below
          </p>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2.5 rounded-2xl text-sm shadow-sm ${
                  msg.direction === 'outbound'
                    ? 'bg-indigo-600 text-white rounded-tr-sm'
                    : 'bg-white text-slate-800 rounded-tl-sm border border-slate-100'
                }`}
              >
                <p className="leading-relaxed whitespace-pre-wrap break-words">{msg.body}</p>
                <div
                  className={`flex items-center gap-1 mt-1 ${
                    msg.direction === 'outbound' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <span
                    className={`text-xs ${
                      msg.direction === 'outbound' ? 'text-indigo-200' : 'text-slate-400'
                    }`}
                  >
                    {formatDateTime(msg.created_at)}
                  </span>
                  {msg.direction === 'outbound' && <StatusIcon status={msg.status} />}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
