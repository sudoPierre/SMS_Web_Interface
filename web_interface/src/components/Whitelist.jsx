import { useState, useEffect, useCallback } from 'react'
import { api } from '../api.js'

export default function Whitelist({ onClose }) {
  const [numbers, setNumbers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [phone, setPhone] = useState('')
  const [label, setLabel] = useState('')
  const [saving, setSaving] = useState(false)
  const [busy, setBusy] = useState(null)

  const load = useCallback(async () => {
    try {
      setNumbers(await api.getAuthorizedNumbers())
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleAdd(e) {
    e.preventDefault()
    if (!phone.trim()) return
    setSaving(true)
    setError('')
    try {
      await api.addAuthorizedNumber(phone.trim(), label.trim())
      setPhone('')
      setLabel('')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function run(phoneNumber, action) {
    setBusy(phoneNumber)
    setError('')
    try {
      await action()
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  function handleToggle(n) {
    run(n.phone_number, () => api.updateAuthorizedNumber(n.phone_number, { enabled: !n.enabled }))
  }

  function handleLabel(n, value) {
    if ((value.trim() || null) === n.label) return
    run(n.phone_number, () => api.updateAuthorizedNumber(n.phone_number, { label: value }))
  }

  function handleDelete(n) {
    if (!window.confirm(`Remove ${n.phone_number} from the whitelist?`)) return
    run(n.phone_number, () => api.deleteAuthorizedNumber(n.phone_number))
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-white border-b border-slate-200 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-slate-800">Command whitelist</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Only these numbers can run SMS commands such as <code className="text-indigo-600">/help</code>
          </p>
        </div>
        <button
          onClick={onClose}
          title="Close"
          className="text-slate-400 hover:text-slate-600 transition p-1.5 rounded-lg hover:bg-slate-100"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* Add form */}
        <form onSubmit={handleAdd} className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap gap-2">
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+33612345678"
            className="flex-1 min-w-[10rem] px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Label (optional)"
            maxLength={100}
            className="flex-1 min-w-[10rem] px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={saving || !phone.trim()}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {saving ? 'Adding…' : 'Add'}
          </button>
        </form>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</p>
        )}

        {/* List */}
        <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
          {loading ? (
            <p className="text-center text-slate-400 text-sm py-10">Loading…</p>
          ) : numbers.length === 0 ? (
            <p className="text-center text-slate-400 text-sm py-10">No authorized numbers yet</p>
          ) : (
            numbers.map((n) => (
              <div
                key={n.phone_number}
                className={`px-4 py-3 flex items-center gap-3 ${busy === n.phone_number ? 'opacity-50' : ''}`}
              >
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${n.enabled ? 'text-slate-800' : 'text-slate-400 line-through'}`}>
                    {n.phone_number}
                  </p>
                  {n.source === 'env' ? (
                    <p className="text-xs text-slate-400">Set by AUTHORIZED_NUMBERS (edit it in the deployment config)</p>
                  ) : (
                    <input
                      type="text"
                      defaultValue={n.label || ''}
                      placeholder="Add a label"
                      maxLength={100}
                      onBlur={(e) => handleLabel(n, e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
                      className="w-full text-xs text-slate-500 bg-transparent border-none p-0 focus:outline-none focus:ring-0 placeholder:text-slate-300"
                    />
                  )}
                </div>
                {n.source === 'env' ? (
                  <span className="text-xs font-medium text-slate-500 bg-slate-100 rounded-full px-2 py-0.5">env</span>
                ) : (
                  <>
                    <button
                      onClick={() => handleToggle(n)}
                      disabled={busy === n.phone_number}
                      title={n.enabled ? 'Disable' : 'Enable'}
                      className={`relative w-10 h-6 rounded-full transition ${n.enabled ? 'bg-indigo-600' : 'bg-slate-300'}`}
                    >
                      <span
                        className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                          n.enabled ? 'translate-x-4' : ''
                        }`}
                      />
                    </button>
                    <button
                      onClick={() => handleDelete(n)}
                      disabled={busy === n.phone_number}
                      title="Remove"
                      className="text-slate-400 hover:text-red-600 transition p-1.5 rounded-lg hover:bg-red-50"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
