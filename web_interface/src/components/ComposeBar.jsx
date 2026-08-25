import { useState, useRef, useEffect } from 'react'
import { api } from '../api.js'

export default function ComposeBar({ phone, onSent }) {
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const textareaRef = useRef(null)

  useEffect(() => {
    setMessage('')
    setError('')
    textareaRef.current?.focus()
  }, [phone])

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 128)}px`
  }, [message])

  async function handleSend() {
    const text = message.trim()
    if (!text || sending) return
    setSending(true)
    setError('')
    try {
      await api.sendMessage(phone, text)
      setMessage('')
      onSent()
    } catch (err) {
      setError(err.message || 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="bg-white border-t border-slate-200 px-6 py-4 flex-shrink-0">
      {error && (
        <p className="text-xs text-red-500 mb-2">{error}</p>
      )}
      <div className="flex items-end gap-3">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Message ${phone}…`}
          rows={1}
          className="flex-1 resize-none bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition overflow-y-auto"
          style={{ minHeight: '44px', maxHeight: '128px' }}
        />
        <button
          onClick={handleSend}
          disabled={!message.trim() || sending}
          className="w-11 h-11 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl flex items-center justify-center transition flex-shrink-0"
          title="Send (Enter)"
        >
          {sending ? (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          )}
        </button>
      </div>
      <p className="text-xs text-slate-400 mt-1.5">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  )
}
