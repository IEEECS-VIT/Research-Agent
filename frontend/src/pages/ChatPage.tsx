import { useState, useRef, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../services/api'
import type { ChatMessage, ChatSession, Source } from '../services/api'
import { Send, MessageSquare, Plus, Trash2, ChevronLeft, ChevronRight, Loader2, FileText, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

function SourceCard({ source }: { source: Source }) {
  const badgeColor = source.relation_type === 'CONTRADICT'
    ? 'badge-danger'
    : source.relation_type === 'SUPPORT'
    ? 'badge-success'
    : 'badge-neutral'

  const scoreColor = source.confidence != null
    ? source.confidence >= 0.7 ? 'text-green-600 dark:text-green-400'
      : source.confidence >= 0.4 ? 'text-yellow-600 dark:text-yellow-400'
      : 'text-red-600 dark:text-red-400'
    : ''

  return (
    <div className="card p-3 animate-fade-in">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <span className="text-xs font-medium truncate" style={{ color: 'var(--color-text-secondary)' }}>
          {source.filename || source.doc_id || 'Unknown source'}
        </span>
        {source.relation_type && (
          <span className={`badge text-[10px] ${badgeColor}`}>
            {source.relation_type === 'CONTRADICT' ? <XCircle size={10} /> : source.relation_type === 'SUPPORT' ? <CheckCircle size={10} /> : <AlertTriangle size={10} />}
            {source.relation_type}
          </span>
        )}
      </div>
      {source.section && (
        <p className="text-[10px] font-medium uppercase tracking-wider mb-1" style={{ color: 'var(--color-text-muted)' }}>
          {source.section}
        </p>
      )}
      {source.text && (
        <p className="text-xs leading-relaxed mb-1.5" style={{ color: 'var(--color-text-secondary)' }}>
          "{source.text}"
        </p>
      )}
      {source.confidence != null && (
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-semibold uppercase" style={{ color: 'var(--color-text-muted)' }}>Confidence:</span>
          <span className={`text-xs font-bold ${scoreColor}`}>
            {(source.confidence * 100).toFixed(0)}%
          </span>
        </div>
      )}
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      <div className={`max-w-[80%] ${isUser ? 'order-1' : 'order-1'}`}>
        <div
          className={`px-4 py-3 ${
            isUser
              ? 'text-white'
              : 'card'
          }`}
          style={{
            background: isUser ? 'var(--color-primary)' : 'var(--color-surface)',
            border: isUser ? 'none' : '1px solid var(--color-border)',
          }}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>

        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider flex items-center gap-1" style={{ color: 'var(--color-text-muted)' }}>
              <FileText size={12} />
              Sources ({message.sources.length})
            </p>
            <div className="space-y-2">
              {message.sources.map((s, i) => (
                <SourceCard key={i} source={s} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ChatSidebar({
  sessions,
  activeId,
  onSelect,
  onDelete,
  onNew,
  collapsed,
  onToggleCollapse,
}: {
  sessions: ChatSession[]
  activeId: string | null
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onNew: () => void
  collapsed: boolean
  onToggleCollapse: () => void
}) {
  return (
    <div
      className="flex flex-col border-r shrink-0 transition-all duration-200"
      style={{
        width: collapsed ? '48px' : '260px',
        borderColor: 'var(--color-border)',
        background: 'var(--color-surface)',
      }}
    >
      <div className="h-14 flex items-center gap-2 px-2 border-b" style={{ borderColor: 'var(--color-border)' }}>
        {!collapsed && (
          <button onClick={onNew} className="btn btn-primary btn-sm flex-1 flex items-center gap-1.5">
            <Plus size={14} />
            New Chat
          </button>
        )}
        <button onClick={onToggleCollapse} className="btn btn-ghost btn-sm p-1.5" title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`group flex items-center gap-2 px-2.5 py-2 text-sm cursor-pointer transition-colors ${
              s.id === activeId ? 'bg-blue-50 dark:bg-blue-950/30' : 'hover:bg-gray-50 dark:hover:bg-gray-900'
            }`}
            style={{
              background: s.id === activeId ? 'var(--color-primary-light)' : undefined,
            }}
            onClick={() => onSelect(s.id)}
          >
            <MessageSquare size={14} className="shrink-0" style={{ color: 'var(--color-text-muted)' }} />
            {!collapsed && (
              <>
                <span className="flex-1 truncate text-xs" style={{ color: 'var(--color-text)' }}>
                  {s.title || 'New conversation'}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(s.id) }}
                  className="opacity-0 group-hover:opacity-100 btn btn-ghost p-0.5"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  <Trash2 size={12} />
                </button>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export function ChatPage() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  const { data: sessions = [], isLoading: sessionsLoading } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: async () => {
      const res = await api.get<ChatSession[]>('/chat/sessions')
      return res.data
    },
  })

  const { data: activeSession, isLoading: messagesLoading } = useQuery({
    queryKey: ['chat-session', activeSessionId],
    queryFn: async () => {
      if (!activeSessionId) return null
      const res = await api.get<{ id: string; title: string | null; messages: ChatMessage[] }>(`/chat/sessions/${activeSessionId}`)
      return res.data
    },
    enabled: !!activeSessionId,
  })

  const createSessionMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post<ChatSession>('/chat/sessions')
      return res.data
    },
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      setActiveSessionId(session.id)
    },
  })

  const deleteSessionMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/chat/sessions/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      if (activeSessionId && activeSessionId === activeSessionId) {
        setActiveSessionId(null)
      }
    },
  })

  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      const res = await api.post<ChatMessage>('/chat/messages', {
        session_id: activeSessionId,
        message,
      })
      return res.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['chat-session', data.session_id] })
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      setActiveSessionId(data.session_id)
    },
  })

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [activeSession?.messages, scrollToBottom])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || sendMessageMutation.isPending) return
    setInput('')
    sendMessageMutation.mutate(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleNewSession = () => {
    createSessionMutation.mutate()
  }

  const handleDeleteSession = (id: string) => {
    deleteSessionMutation.mutate(id)
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] -m-6 lg:-m-8" style={{ background: 'var(--color-bg)' }}>
      <ChatSidebar
        sessions={sessions}
        activeId={activeSessionId}
        onSelect={setActiveSessionId}
        onDelete={handleDeleteSession}
        onNew={handleNewSession}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {activeSession ? (
          <>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messagesLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 size={24} className="animate-spin" style={{ color: 'var(--color-text-muted)' }} />
                </div>
              ) : activeSession.messages && activeSession.messages.length > 0 ? (
                activeSession.messages.map((m) => (
                  <MessageBubble key={m.id} message={m} />
                ))
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-center py-12">
                  <MessageSquare size={40} style={{ color: 'var(--color-text-muted)' }} />
                  <h3 className="text-lg font-semibold mt-4" style={{ color: 'var(--color-text)' }}>
                    Start a conversation
                  </h3>
                  <p className="text-sm mt-1 max-w-md" style={{ color: 'var(--color-text-secondary)' }}>
                    Ask questions about your research papers, explore the knowledge graph, or find supporting evidence for claims.
                  </p>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 border-t" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}>
              <div className="flex gap-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a research question..."
                  rows={2}
                  className="input resize-none"
                  style={{ background: 'var(--color-bg)' }}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || sendMessageMutation.isPending}
                  className="btn btn-primary btn-lg self-end"
                >
                  {sendMessageMutation.isPending ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <Send size={18} />
                  )}
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <div
              className="w-16 h-16 flex items-center justify-center mb-4"
              style={{ background: 'var(--color-primary-light)' }}
            >
              <MessageSquare size={28} style={{ color: 'var(--color-primary)' }} />
            </div>
            <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--color-text)' }}>
              Research RAG Agent
            </h2>
            <p className="text-sm max-w-lg mb-6" style={{ color: 'var(--color-text-secondary)' }}>
              Chat with your research knowledge graph. Ask about contradictions, find supporting evidence, explore relationships between claims, or get literature-review-style answers.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-lg text-left">
              {[
                'What papers support the claim that X causes Y?',
                'Summarize all contradictions found in my knowledge graph.',
                'How reliable is the evidence for claim Z?',
                'What is the overall consensus about mechanism M?',
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    handleNewSession()
                    setTimeout(() => setInput(q), 300)
                  }}
                  className="card card-hover p-3 text-xs text-left transition-colors"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  "{q}"
                </button>
              ))}
            </div>
            <button onClick={handleNewSession} className="btn btn-primary btn-lg mt-8">
              <Plus size={18} />
              Start a conversation
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
