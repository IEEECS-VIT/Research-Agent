import axios from 'axios'
import { auth } from './firebase'
import { getIdToken } from 'firebase/auth'

const api = axios.create({
  baseURL: '/api/v1',
})

api.interceptors.request.use(async (config) => {
  const user = auth.currentUser
  if (user) {
    const token = await getIdToken(user)
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      auth.signOut()
    }
    return Promise.reject(err)
  }
)

export interface Document {
  id: string
  filename: string
  source_type: 'draft' | 'paper'
  version_id: string
  total_sections: number
  processing_status: string
  created_at: string
}

export interface DocumentList {
  documents: Document[]
  total: number
}

export interface AnalysisSession {
  id: string
  name: string | null
  status: string
  created_at: string
}

export interface ComparisonResult {
  id: string
  source_doc_id: string
  target_doc_id: string
  source_section: string | null
  target_section: string | null
  source_text: string | null
  target_text: string | null
  support_score: number
  contradiction_score: number
  confidence: number
  verifier_status: string | null
  relation_type: string | null
  confidence_state: string | null
}

export const documentsApi = {
  upload: (file: File, sourceType: 'draft' | 'paper') => {
    const form = new FormData()
    form.append('file', file)
    form.append('source_type', sourceType)
    return api.post<Document>('/documents/upload', form)
  },
  list: (params?: { source_type?: string; skip?: number; limit?: number }) =>
    api.get<DocumentList>('/documents', { params }),
  get: (id: string) => api.get<Document>(`/documents/${id}`),
  delete: (id: string) => api.delete(`/documents/${id}`),
  rollVersion: () => api.post('/documents/roll-version'),
}

export const analysisApi = {
  createSession: (data: { name?: string; draft_document_ids: string[]; paper_document_ids: string[] }) =>
    api.post<AnalysisSession>('/analysis/sessions', data),
  listSessions: () => api.get<AnalysisSession[]>('/analysis/sessions'),
  getSession: (id: string) => api.get<{ id: string; name: string | null; status: string; created_at: string; comparisons: ComparisonResult[] }>(`/analysis/sessions/${id}`),
  getGraph: (id: string) => api.get<{ nodes: { id: string; label: string; type: string }[]; edges: { source: string; target: string; support_score: number; contradiction_score: number; confidence: number; relation_type: string }[] }>(`/analysis/sessions/${id}/graph`),
}

export interface ChatSession {
  id: string
  title: string | null
  created_at: string
  updated_at: string
}

export interface Source {
  doc_id: string | null
  filename: string | null
  section: string | null
  text: string | null
  confidence: number | null
  relation_type: string | null
  support_score: number | null
  contradiction_score: number | null
}

export interface ChatMessage {
  id: string
  session_id: string
  role: string
  content: string
  sources: Source[]
  created_at: string
}

export const chatApi = {
  listSessions: () => api.get<ChatSession[]>('/chat/sessions'),
  getSession: (id: string) => api.get<{ id: string; title: string | null; messages: ChatMessage[] }>(`/chat/sessions/${id}`),
  createSession: () => api.post<ChatSession>('/chat/sessions'),
  deleteSession: (id: string) => api.delete(`/chat/sessions/${id}`),
  sendMessage: (data: { session_id?: string | null; message: string }) => api.post<ChatMessage>('/chat/messages', data),
}

export default api
