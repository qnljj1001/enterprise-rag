export interface User {
  id: string
  username: string
  role: 'admin' | 'user' | string
  created_at: string
  last_login_at?: string | null
}

export interface Captcha {
  captcha_id: string
  image_base64: string
  expires_in: number
  debug_code?: string | null
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface KnowledgeBase {
  id: string
  name: string
  description: string
  default_chunk_size: number
  default_chunk_overlap: number
  retrieval_mode: 'dense' | 'hybrid' | string
  embedding_model: string
  embedding_dim: number
  document_count: number
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface DocumentItem {
  id: string
  kb_id: string
  filename: string
  file_type: string
  size_bytes: number
  chunk_size: number
  chunk_overlap: number
  status: string
  progress: number
  chunk_count: number
  error_message?: string | null
  created_at: string
  updated_at: string
}

export interface Chunk {
  id: string
  kb_id: string
  document_id: string
  chunk_index: number
  content: string
  char_start: number
  char_end: number
  page_no?: number | null
  chunk_metadata: Record<string, unknown>
  updated_at: string
}

export interface ChatSession {
  id: string
  title: string
  settings: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface Citation {
  chunk_id: string
  document_id: string
  filename: string
  kb_name: string
  page_no?: number | null
  content: string
  score: number
}

export interface ChatMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant' | string
  content: string
  citations: Citation[]
  model: string
  params: Record<string, unknown>
  status: string
  error_message?: string | null
  created_at: string
}

export interface Meta {
  app_title: string
  llm_model: string
  llm_thinking: string
  embedding_model: string
  embedding_dim: number
  retrieval_modes: string[]
  upload_types: string[]
  max_upload_mb: number
  top_p_note: string
}

export interface Wiki {
  title: string
  markdown: string
  generated_at: string
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ChatPayload {
  content: string
  kb_ids: string[]
  temperature: number
  top_p: number
  max_tokens: number
  history_rounds: number
}

export interface ChatSettings {
  kb_ids: string[]
  temperature: number
  top_p: number
  max_tokens: number
  history_rounds: number
}
