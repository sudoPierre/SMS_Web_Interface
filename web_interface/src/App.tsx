import { type KeyboardEvent, type SubmitEvent, useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  Bot,
  ChevronLeft,
  Clock,
  MessageSquare,
  Phone,
  Search,
  Send,
  UserPlus,
  User,
} from 'lucide-react'

type Conversation = {
  id: number
  name: string
  alias?: string
  unread: number
  lastActive: string
  isAlert?: boolean
}

type Message = {
  id: number
  text: string
  sender: 'user' | 'llm' | 'system' | 'admin'
  timestamp: string
  isAlert?: boolean
}

type MessagesByConversation = Record<number, Message[]>

const countryDialCodes = [
  { label: 'France (+33)', value: '+33' },
  { label: 'United Kingdom (+44)', value: '+44' },
  { label: 'United States (+1)', value: '+1' },
  { label: 'Germany (+49)', value: '+49' },
  { label: 'Spain (+34)', value: '+34' },
  { label: 'Italy (+39)', value: '+39' },
  { label: 'French Guiana (+594)', value: '+594' },
  { label: 'Martinique (+596)', value: '+596' },
  { label: 'Guadeloupe (+590)', value: '+590' },
]

const initialConversations: Conversation[] = [
  {
    id: 1,
    name: '+33 6 12 34 56 78',
    alias: 'Alice (Client A)',
    unread: 0,
    lastActive: '10:42',
  },
  {
    id: 2,
    name: '+33 6 98 76 54 32',
    alias: 'Prod Server',
    unread: 2,
    lastActive: '09:15',
    isAlert: true,
  },
  { id: 3, name: '+33 7 11 22 33 44', alias: 'Bob', unread: 0, lastActive: 'Yesterday' },
]

const initialMessages: MessagesByConversation = {
  1: [
    {
      id: 101,
      text: 'Hello, what is the status of my order?',
      sender: 'user',
      timestamp: '10:30',
    },
    {
      id: 102,
      text: 'Hi Alice, your order is currently out for delivery. It should arrive tomorrow.',
      sender: 'llm',
      timestamp: '10:31',
    },
    { id: 103, text: 'Thanks for the update!', sender: 'user', timestamp: '10:40' },
    {
      id: 104,
      text: "You're welcome. Feel free to ask if you have any other questions.",
      sender: 'llm',
      timestamp: '10:42',
    },
  ],
  2: [
    {
      id: 201,
      text: 'CRITICAL ALERT: CPU load > 95% on the main server.',
      sender: 'system',
      isAlert: true,
      timestamp: '09:10',
    },
    {
      id: 202,
      text: 'Alert received, restarting cache services now.',
      sender: 'user',
      timestamp: '09:12',
    },
    {
      id: 203,
      text: 'Action confirmed. The LLM logged the intervention.',
      sender: 'llm',
      timestamp: '09:13',
    },
    {
      id: 204,
      text: 'Services restarted. Load is decreasing.',
      sender: 'user',
      timestamp: '09:15',
    },
  ],
  3: [
    {
      id: 301,
      text: 'Hi, is the appointment still confirmed for 2 PM?',
      sender: 'user',
      timestamp: 'Yesterday',
    },
    {
      id: 302,
      text: 'Hi Bob, yes, the appointment is confirmed for 2 PM.',
      sender: 'llm',
      timestamp: 'Yesterday',
    },
    {
      id: 303,
      text: 'Please remember to bring your full file.',
      sender: 'admin',
      timestamp: 'Yesterday',
    },
  ],
}

export default function App() {
  const [conversations, setConversations] = useState(initialConversations)
  const [messages, setMessages] = useState(initialMessages)
  const [activeConvId, setActiveConvId] = useState(1)
  const [inputText, setInputText] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [showConversationList, setShowConversationList] = useState(true)
  const [showRegisterForm, setShowRegisterForm] = useState(false)
  const [newContactDialCode, setNewContactDialCode] = useState('+33')
  const [newContactPhone, setNewContactPhone] = useState('')
  const [newContactAlias, setNewContactAlias] = useState('')
  const [registerError, setRegisterError] = useState('')

  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, activeConvId])

  const activeConversation = conversations.find((c) => c.id === activeConvId)
  const currentMessages = messages[activeConvId] || []

  const handleSendMessage = () => {
    if (!inputText.trim()) {
      return
    }

    const newMessage: Message = {
      id: Date.now(),
      text: inputText,
      sender: 'admin',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages((prev) => ({
      ...prev,
      [activeConvId]: [...(prev[activeConvId] || []), newMessage],
    }))

    setInputText('')

    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeConvId ? { ...c, lastActive: newMessage.timestamp, unread: 0 } : c,
      ),
    )
  }

  const handleRegisterContact = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault()

    const phone = newContactPhone.trim()
    const fullPhone = `${newContactDialCode} ${phone}`
    const alias = newContactAlias.trim()

    if (!phone) {
      setRegisterError('Phone number is required.')
      return
    }

    if (conversations.some((c) => c.name === fullPhone)) {
      setRegisterError('This phone number is already registered.')
      return
    }

    const nextId = conversations.reduce((maxId, c) => Math.max(maxId, c.id), 0) + 1
    const newConversation: Conversation = {
      id: nextId,
      name: fullPhone,
      alias: alias || undefined,
      unread: 0,
      lastActive: 'Just now',
    }

    setConversations((prev) => [newConversation, ...prev])
    setMessages((prev) => ({ ...prev, [nextId]: [] }))
    setActiveConvId(nextId)
    setShowConversationList(false)
    setShowRegisterForm(false)
    setNewContactDialCode('+33')
    setNewContactPhone('')
    setNewContactAlias('')
    setRegisterError('')
  }

  const filteredConversations = conversations.filter(
    (c) =>
      c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.alias && c.alias.toLowerCase().includes(searchTerm.toLowerCase())),
  )

  return (
    <div className="relative flex h-screen overflow-hidden bg-gray-50 font-sans text-gray-800">
      <div
        className={`absolute inset-y-0 left-0 z-20 flex w-full max-w-none flex-col border-r border-gray-200 bg-white shadow-sm transition-transform md:static md:w-1/3 md:max-w-sm md:translate-x-0 ${
          showConversationList ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="border-b border-gray-200 bg-gray-900 p-4 text-white">
          <div className="flex items-center justify-between gap-2">
            <h1 className="flex items-center gap-2 text-xl font-bold">
              <MessageSquare className="h-6 w-6 text-blue-400" />
              SMS Gateway
            </h1>
            <button
              type="button"
              className="rounded-md border border-white/30 px-2 py-1 text-xs text-white md:hidden"
              onClick={() => setShowConversationList(false)}
            >
              Close
            </button>
          </div>
        </div>

        <div className="border-b border-gray-200 p-3">
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search contact..."
              className="w-full rounded-lg border-transparent bg-gray-100 py-2 pl-9 pr-4 text-sm outline-none transition-all focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-200"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <button
            type="button"
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            onClick={() => {
              setShowRegisterForm((prev) => !prev)
              setRegisterError('')
            }}
          >
            <UserPlus className="h-4 w-4" />
            Register contact
          </button>

          {showRegisterForm && (
            <form
              onSubmit={handleRegisterContact}
              className="mt-3 space-y-2 rounded-lg border border-gray-200 bg-gray-50 p-3"
            >
              <div className="grid grid-cols-[140px_1fr] gap-2">
                <select
                  value={newContactDialCode}
                  onChange={(e) => setNewContactDialCode(e.target.value)}
                  className="w-full rounded-md border border-gray-300 bg-white px-2 py-2 text-sm outline-none focus:border-blue-500"
                >
                  {countryDialCodes.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
                <input
                  type="text"
                  value={newContactPhone}
                  onChange={(e) => setNewContactPhone(e.target.value)}
                  placeholder="Phone number"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
                />
              </div>
              <input
                type="text"
                value={newContactAlias}
                onChange={(e) => setNewContactAlias(e.target.value)}
                placeholder="Display name (optional)"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
              />
              {registerError && <p className="text-xs text-red-600">{registerError}</p>}
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600"
                  onClick={() => {
                    setShowRegisterForm(false)
                    setNewContactDialCode('+33')
                    setNewContactPhone('')
                    setNewContactAlias('')
                    setRegisterError('')
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
                >
                  Save
                </button>
              </div>
            </form>
          )}
        </div>

        <div className="flex-1 overflow-y-auto">
          {filteredConversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => {
                setActiveConvId(conv.id)
                setConversations((prev) =>
                  prev.map((c) => (c.id === conv.id ? { ...c, unread: 0 } : c)),
                )
                setShowConversationList(false)
              }}
              className={`flex cursor-pointer items-start gap-3 border-b border-gray-100 p-4 transition-colors hover:bg-gray-50 ${
                activeConvId === conv.id
                  ? 'border-l-4 border-l-blue-500 bg-blue-50/50'
                  : 'border-l-4 border-l-transparent'
              }`}
            >
              <div className="relative">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 font-bold text-blue-600">
                  {conv.alias ? (
                    conv.alias.charAt(0).toUpperCase()
                  ) : (
                    <Phone className="h-5 w-5" />
                  )}
                </div>
                {conv.unread > 0 && (
                  <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full border-2 border-white bg-red-500 text-xs font-bold text-white">
                    {conv.unread}
                  </span>
                )}
                {conv.isAlert && (
                  <span className="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full border-2 border-white bg-yellow-500 text-white">
                    <AlertTriangle className="h-2 w-2" />
                  </span>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex items-baseline justify-between">
                  <h3 className="truncate font-semibold text-gray-900">{conv.alias || conv.name}</h3>
                  <span className="ml-2 whitespace-nowrap text-xs text-gray-500">{conv.lastActive}</span>
                </div>
                <p className="truncate text-sm text-gray-500">{conv.name}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="relative flex flex-1 flex-col bg-[#e5ddd5]">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'radial-gradient(#000 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
        />

        {activeConversation ? (
          <>
            <div className="z-10 flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 shadow-sm sm:px-6 sm:py-4">
              <div className="flex min-w-0 items-center gap-3 sm:gap-4">
                <button
                  type="button"
                  className="mr-1 flex h-8 w-8 items-center justify-center rounded-full border border-gray-200 text-gray-600 md:hidden"
                  onClick={() => setShowConversationList(true)}
                  aria-label="Back to conversations"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-blue-600">
                  {activeConversation.alias ? (
                    activeConversation.alias.charAt(0).toUpperCase()
                  ) : (
                    <Phone className="h-5 w-5" />
                  )}
                </div>
                <div className="min-w-0">
                  <h2 className="truncate text-base font-bold text-gray-800 sm:text-lg">
                    {activeConversation.alias || activeConversation.name}
                  </h2>
                  <p className="flex items-center gap-1 truncate text-xs text-gray-500 sm:text-sm">
                    <Phone className="h-3 w-3" /> {activeConversation.name}
                  </p>
                </div>
              </div>
              <div className="hidden gap-2 sm:flex">
                <span className="flex items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
                  <Bot className="h-3 w-3" /> LLM Active
                </span>
              </div>
            </div>

            <div className="z-10 flex-1 space-y-4 overflow-y-auto p-3 sm:p-6">
              {currentMessages.map((msg) => {
                const isSystemAlert = msg.isAlert
                const isSentByUs = msg.sender === 'llm' || msg.sender === 'admin'
                const isManual = msg.sender === 'admin'

                if (isSystemAlert) {
                  return (
                    <div key={msg.id} className="my-4 flex justify-center">
                      <div className="flex max-w-md flex-col items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-center text-sm text-red-700 shadow-sm">
                        <AlertTriangle className="mb-1 h-5 w-5 text-red-500" />
                        <span className="font-medium">{msg.text}</span>
                        <span className="mt-1 text-[10px] text-red-400">{msg.timestamp}</span>
                      </div>
                    </div>
                  )
                }

                return (
                  <div key={msg.id} className={`flex ${isSentByUs ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`flex max-w-[85%] flex-col sm:max-w-[75%] ${
                        isSentByUs ? 'items-end' : 'items-start'
                      }`}
                    >
                      {isSentByUs && (
                        <div className="mb-1 flex items-center gap-1 px-1 text-xs text-gray-500">
                          {isManual ? (
                            <>
                              <User className="h-3 w-3" /> <span>Sent manually</span>
                            </>
                          ) : (
                            <>
                              <Bot className="h-3 w-3" /> <span>Sent by LLM</span>
                            </>
                          )}
                        </div>
                      )}

                      <div
                        className={`relative rounded-2xl px-4 py-2 shadow-sm ${
                          isSentByUs
                            ? isManual
                              ? 'rounded-tr-sm bg-emerald-500 text-white'
                              : 'rounded-tr-sm bg-blue-500 text-white'
                            : 'rounded-tl-sm border border-gray-100 bg-white text-gray-800'
                        }`}
                      >
                        <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{msg.text}</p>

                        <div
                          className={`mt-1.5 flex items-center justify-end gap-1 text-right text-[10px] ${
                            isSentByUs ? 'text-white/80' : 'text-gray-400'
                          }`}
                        >
                          <Clock className="h-3 w-3" />
                          {msg.timestamp}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
              <div ref={messagesEndRef} />
            </div>

            <div className="z-10 border-t border-gray-200 bg-gray-100 p-3 sm:p-4">
              <form
                onSubmit={(e: SubmitEvent<HTMLFormElement>) => {
                  e.preventDefault()
                  handleSendMessage()
                }}
                className="mx-auto flex max-w-4xl items-end gap-2 sm:gap-3"
              >
                <div className="flex flex-1 flex-col overflow-hidden rounded-xl border border-gray-300 bg-white shadow-sm transition-all focus-within:border-transparent focus-within:ring-2 focus-within:ring-blue-500">
                  <div className="flex items-center gap-1 border-b border-gray-100 bg-gray-50 px-3 py-1 text-xs text-gray-500">
                    <User className="h-3 w-3" />
                    Manual intervention: This message will bypass the LLM.
                  </div>
                  <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Type your manual message..."
                    className="max-h-32 w-full resize-none bg-transparent px-4 py-3 text-gray-800 outline-none"
                    rows={2}
                    onKeyDown={(e: KeyboardEvent<HTMLTextAreaElement>) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSendMessage()
                      }
                    }}
                  />
                </div>
                <button
                  type="submit"
                  disabled={!inputText.trim()}
                  className="mb-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-600 p-2.5 text-white shadow-md transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300 sm:h-12 sm:w-12 sm:p-3"
                >
                  <Send className="ml-1 h-5 w-5" />
                </button>
              </form>
            </div>
          </>
        ) : (
          <div className="z-10 flex flex-1 items-center justify-center">
            <div className="text-center text-gray-500">
              <MessageSquare className="mx-auto mb-4 h-16 w-16 text-gray-300" />
              <p className="text-lg font-medium">Select a conversation</p>
              <p className="text-sm">to view messages or intervene manually.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
