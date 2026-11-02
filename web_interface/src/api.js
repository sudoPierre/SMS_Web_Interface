const BASE_URL = import.meta.env.VITE_BACKEND_API_URL || ''
const TOKEN_KEY = 'sms_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)
export const isAuthenticated = () => !!getToken()

async function request(path, options = {}) {
  const token = getToken()
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (res.status === 401) {
    clearToken()
    window.location.reload()
    return
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const detail = Array.isArray(err.detail) ? err.detail[0]?.msg : err.detail
    throw new Error(detail || 'Request failed')
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  login: (identifier, password) =>
    request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ identifier, password }),
    }),

  getConversations: () => request('/api/conversations'),

  getMessages: (phoneNumber) =>
    request(`/api/conversations/${encodeURIComponent(phoneNumber)}`),

  sendMessage: (phoneNumber, message) =>
    request('/api/messages/send', {
      method: 'POST',
      body: JSON.stringify({ phoneNumber, message }),
    }),

  getAuthorizedNumbers: () => request('/api/authorized-numbers'),

  addAuthorizedNumber: (phone_number, label) =>
    request('/api/authorized-numbers', {
      method: 'POST',
      body: JSON.stringify({ phone_number, label }),
    }),

  updateAuthorizedNumber: (phoneNumber, changes) =>
    request(`/api/authorized-numbers/${encodeURIComponent(phoneNumber)}`, {
      method: 'PATCH',
      body: JSON.stringify(changes),
    }),

  deleteAuthorizedNumber: (phoneNumber) =>
    request(`/api/authorized-numbers/${encodeURIComponent(phoneNumber)}`, {
      method: 'DELETE',
    }),
}
