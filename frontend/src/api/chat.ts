import { getToken } from './http'
import { readSSEStream } from './sse'
import type { ChatMessage, ChatPayload, ChatSession, Citation } from './types'

export interface ChatStreamHandlers {
  onMeta?: (data: { session_id: string; message_id: string; request_id: string; model: string }) => void
  onCitations?: (items: Citation[]) => void
  onDelta?: (text: string) => void
  onDone?: (data: { message_id: string; finish_reason: string; usage?: unknown }) => void
  onError?: (error: { code: string; message: string; request_id?: string }) => void
  onPing?: () => void
}

export async function listSessions(): Promise<ChatSession[]> {
  const response = await fetch('/api/v1/chat/sessions', {
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  if (!response.ok) throw new Error('加载会话失败')
  return response.json()
}

export async function createSession(title = '新对话'): Promise<ChatSession> {
  const response = await fetch('/api/v1/chat/sessions', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${getToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title, settings: {} }),
  })
  if (!response.ok) throw new Error('创建会话失败')
  return response.json()
}

export async function updateSession(id: string, title: string): Promise<ChatSession> {
  const response = await fetch(`/api/v1/chat/sessions/${id}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${getToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  })
  if (!response.ok) throw new Error('重命名会话失败')
  return response.json()
}

export async function deleteSession(id: string): Promise<void> {
  const response = await fetch(`/api/v1/chat/sessions/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  if (!response.ok) throw new Error('删除会话失败')
}

export async function listMessages(id: string): Promise<ChatMessage[]> {
  const response = await fetch(`/api/v1/chat/sessions/${id}/messages`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  if (!response.ok) throw new Error('加载消息失败')
  return response.json()
}

export async function streamChat(
  sessionId: string,
  payload: ChatPayload,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`/api/v1/chat/sessions/${sessionId}/messages/stream`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${getToken()}`,
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(payload),
    signal,
  })
  if (!response.ok) {
    let message = `请求失败（HTTP ${response.status}）`
    try {
      const data = (await response.json()) as { detail?: { message?: string } }
      if (data.detail?.message) message = data.detail.message
    } catch {
      // ignore
    }
    throw new Error(message)
  }
  if (!response.body) throw new Error('服务端未返回流式响应')
  await readSSEStream(response.body, (frame) => {
    let data: unknown
    try {
      data = JSON.parse(frame.data)
    } catch {
      return
    }
    if (frame.event === 'meta') handlers.onMeta?.(data as never)
    else if (frame.event === 'citations') {
      const items = (data as { items?: Citation[] }).items || []
      handlers.onCitations?.(items)
    } else if (frame.event === 'delta') handlers.onDelta?.((data as { text?: string }).text || '')
    else if (frame.event === 'done') handlers.onDone?.(data as never)
    else if (frame.event === 'error') handlers.onError?.(data as never)
    else if (frame.event === 'ping') handlers.onPing?.()
  })
}
