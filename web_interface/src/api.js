const BASE_URL = import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000'
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
    throw new Error(err.detail || 'Request failed')
  }

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
}
