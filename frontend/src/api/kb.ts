import { http } from './http'
import type {
  Chunk,
  DocumentItem,
  KnowledgeBase,
  Paginated,
  Wiki,
} from './types'

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  const { data } = await http.get<KnowledgeBase[]>('/api/v1/knowledge-bases')
  return data
}

export async function listAdminKnowledgeBases(): Promise<KnowledgeBase[]> {
  const { data } = await http.get<KnowledgeBase[]>('/api/v1/admin/knowledge-bases')
  return data
}

export async function createKnowledgeBase(payload: {
  name: string
  description: string
  default_chunk_size: number
  default_chunk_overlap: number
  retrieval_mode: 'dense' | 'hybrid'
}): Promise<KnowledgeBase> {
  const { data } = await http.post<KnowledgeBase>('/api/v1/admin/knowledge-bases', payload)
  return data
}

export async function getKnowledgeBase(id: string): Promise<KnowledgeBase> {
  const { data } = await http.get<KnowledgeBase>(`/api/v1/admin/knowledge-bases/${id}`)
  return data
}

export async function updateKnowledgeBase(
  id: string,
  payload: Partial<{
    name: string
    description: string
    default_chunk_size: number
    default_chunk_overlap: number
    retrieval_mode: 'dense' | 'hybrid'
  }>,
): Promise<KnowledgeBase> {
  const { data } = await http.patch<KnowledgeBase>(
    `/api/v1/admin/knowledge-bases/${id}`,
    payload,
  )
  return data
}

export async function deleteKnowledgeBase(id: string): Promise<void> {
  await http.delete(`/api/v1/admin/knowledge-bases/${id}`)
}

export async function listDocuments(
  kbId: string,
  params: { page?: number; page_size?: number; status?: string } = {},
): Promise<Paginated<DocumentItem>> {
  const { data } = await http.get<Paginated<DocumentItem>>(
    `/api/v1/admin/knowledge-bases/${kbId}/documents`,
    { params },
  )
  return data
}

export async function getDocument(id: string): Promise<DocumentItem> {
  const { data } = await http.get<DocumentItem>(`/api/v1/admin/documents/${id}`)
  return data
}

export async function uploadDocument(
  kbId: string,
  file: File,
  options: { chunk_size?: number; chunk_overlap?: number; onProgress?: (percent: number) => void },
): Promise<DocumentItem> {
  const form = new FormData()
  form.append('file', file)
  if (options.chunk_size) form.append('chunk_size', String(options.chunk_size))
  if (options.chunk_overlap !== undefined) {
    form.append('chunk_overlap', String(options.chunk_overlap))
  }
  const { data } = await http.post<DocumentItem>(
    `/api/v1/admin/knowledge-bases/${kbId}/documents`,
    form,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000,
      onUploadProgress: (event) => {
        if (event.total && options.onProgress) {
          options.onProgress(Math.round((event.loaded / event.total) * 100))
        }
      },
    },
  )
  return data
}

export async function deleteDocument(id: string): Promise<void> {
  await http.delete(`/api/v1/admin/documents/${id}`)
}

export async function reparseDocument(
  id: string,
  payload: { chunk_size?: number; chunk_overlap?: number } = {},
): Promise<DocumentItem> {
  const { data } = await http.post<DocumentItem>(
    `/api/v1/admin/documents/${id}/reparse`,
    payload,
  )
  return data
}

export async function listChunks(
  docId: string,
  params: { page?: number; page_size?: number; q?: string } = {},
): Promise<Paginated<Chunk>> {
  const { data } = await http.get<Paginated<Chunk>>(
    `/api/v1/admin/documents/${docId}/chunks`,
    { params },
  )
  return data
}

export async function updateChunk(id: string, content: string): Promise<Chunk> {
  const { data } = await http.patch<Chunk>(`/api/v1/admin/chunks/${id}`, { content })
  return data
}

export async function deleteChunk(id: string): Promise<void> {
  await http.delete(`/api/v1/admin/chunks/${id}`)
}

export async function fetchDocumentWiki(id: string): Promise<Wiki> {
  const { data } = await http.get<Wiki>(`/api/v1/admin/documents/${id}/wiki`)
  return data
}

export async function fetchKnowledgeBaseWiki(id: string): Promise<Wiki> {
  const { data } = await http.get<Wiki>(`/api/v1/admin/knowledge-bases/${id}/wiki`)
  return data
}

export async function downloadWiki(
  kind: 'document' | 'knowledge-base',
  id: string,
): Promise<Blob> {
  const path =
    kind === 'document'
      ? `/api/v1/admin/documents/${id}/wiki`
      : `/api/v1/admin/knowledge-bases/${id}/wiki`
  const { data } = await http.get(path, { params: { download: true }, responseType: 'blob' })
  return data as Blob
}
