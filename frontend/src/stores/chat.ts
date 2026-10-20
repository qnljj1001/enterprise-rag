import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as chatApi from '@/api/chat'
import type { ChatMessage, ChatSettings, ChatSession, Citation } from '@/api/types'

const DEFAULT_SETTINGS: ChatSettings = {
  kb_ids: [],
  temperature: 0.7,
  top_p: 0.8,
  max_tokens: 2048,
  history_rounds: 5,
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<ChatSession[]>([])
  const currentSessionId = ref('')
  const messages = ref<ChatMessage[]>([])
  const settings = ref<ChatSettings>({ ...DEFAULT_SETTINGS })
  const loadingSessions = ref(false)
  const loadingMessages = ref(false)
  const streaming = ref(false)
  const error = ref('')
  const activeAssistantId = ref('')
  let controller: AbortController | null = null

  const currentSession = computed(
    () => sessions.value.find((item) => item.id === currentSessionId.value) || null,
  )

  function applySessionSettings(session: ChatSession | null) {
    const stored = (session?.settings || {}) as Partial<ChatSettings>
    const currentKbIds = settings.value.kb_ids
    const storedKbIds = Array.isArray(stored.kb_ids) ? stored.kb_ids : []
    settings.value = {
      ...DEFAULT_SETTINGS,
      ...stored,
      kb_ids: storedKbIds.length > 0 ? storedKbIds : currentKbIds,
    }
  }

  async function loadSessions() {
    loadingSessions.value = true
    try {
      sessions.value = await chatApi.listSessions()
      if (!currentSessionId.value && sessions.value.length > 0) {
        await selectSession(sessions.value[0].id)
      }
    } finally {
      loadingSessions.value = false
    }
  }

  async function selectSession(id: string) {
    if (streaming.value) stop()
    currentSessionId.value = id
    const session = sessions.value.find((item) => item.id === id) || null
    applySessionSettings(session)
    await loadMessages()
  }

  async function loadMessages() {
    if (!currentSessionId.value) {
      messages.value = []
      return
    }
    loadingMessages.value = true
    try {
      messages.value = await chatApi.listMessages(currentSessionId.value)
    } finally {
      loadingMessages.value = false
    }
  }

  async function createSession(title = '新对话') {
    const session = await chatApi.createSession(title)
    sessions.value.unshift(session)
    currentSessionId.value = session.id
    messages.value = []
    applySessionSettings(session)
    return session
  }

  async function ensureSession(): Promise<ChatSession> {
    if (currentSession.value) return currentSession.value
    return createSession()
  }

  async function renameSession(id: string, title: string) {
    const updated = await chatApi.updateSession(id, title)
    const index = sessions.value.findIndex((item) => item.id === id)
    if (index >= 0) sessions.value[index] = updated
    if (currentSessionId.value === id) applySessionSettings(updated)
  }

  async function removeSession(id: string) {
    await chatApi.deleteSession(id)
    sessions.value = sessions.value.filter((item) => item.id !== id)
    if (currentSessionId.value === id) {
      currentSessionId.value = ''
      messages.value = []
      if (sessions.value.length > 0) await selectSession(sessions.value[0].id)
    }
  }

  function buildPayload(content: string) {
    return {
      content,
      kb_ids: settings.value.kb_ids,
      temperature: settings.value.temperature,
      top_p: settings.value.top_p,
      max_tokens: settings.value.max_tokens,
      history_rounds: settings.value.history_rounds,
    }
  }

  async function send(content: string) {
    const text = content.trim()
    if (!text || streaming.value) return
    if (settings.value.kb_ids.length === 0) {
      error.value = '请先选择至少一个知识库。'
      return
    }
    error.value = ''
    const payload = buildPayload(text)
    const session = await ensureSession()
    const localUser: ChatMessage = {
      id: `local-user-${Date.now()}`,
      session_id: session.id,
      role: 'user',
      content: text,
      citations: [],
      model: '',
      params: {},
      status: 'ok',
      created_at: new Date().toISOString(),
    }
    const localAssistant: ChatMessage = {
      id: `local-assistant-${Date.now()}`,
      session_id: session.id,
      role: 'assistant',
      content: '',
      citations: [],
      model: 'deepseek-flash',
      params: {},
      status: 'streaming',
      created_at: new Date().toISOString(),
    }
    messages.value.push(localUser, localAssistant)
    activeAssistantId.value = localAssistant.id
    streaming.value = true
    controller = new AbortController()

    const updateAssistant = (patch: Partial<ChatMessage>) => {
      const target = messages.value.find((item) => item.id === activeAssistantId.value)
      if (target) Object.assign(target, patch)
    }

    try {
      await chatApi.streamChat(
        session.id,
        payload,
        {
          onMeta: (data) => {
            const target = messages.value.find((item) => item.id === activeAssistantId.value)
            if (target) {
              target.id = data.message_id
              activeAssistantId.value = data.message_id
              target.model = data.model
            }
          },
          onCitations: (items: Citation[]) => updateAssistant({ citations: items }),
          onDelta: (delta: string) => {
            const target = messages.value.find((item) => item.id === activeAssistantId.value)
            if (target) target.content += delta
          },
          onDone: () => {
            updateAssistant({ status: 'ok' })
          },
          onError: (err) => {
            error.value = err.message
            updateAssistant({ status: 'error', error_message: err.message })
          },
        },
        controller.signal,
      )
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        updateAssistant({ status: 'aborted' })
      } else {
        error.value = (err as Error).message || '问答失败，请稍后重试。'
        updateAssistant({ status: 'error', error_message: error.value })
      }
    } finally {
      streaming.value = false
      controller = null
      await loadSessions().catch(() => undefined)
      if (currentSessionId.value === session.id) {
        await loadMessages().catch(() => undefined)
      }
    }
  }

  function stop() {
    if (controller) {
      controller.abort()
      controller = null
    }
    streaming.value = false
  }

  function reset() {
    stop()
    sessions.value = []
    currentSessionId.value = ''
    messages.value = []
    settings.value = { ...DEFAULT_SETTINGS }
    error.value = ''
  }

  return {
    sessions,
    currentSessionId,
    currentSession,
    messages,
    settings,
    loadingSessions,
    loadingMessages,
    streaming,
    error,
    activeAssistantId,
    loadSessions,
    selectSession,
    loadMessages,
    createSession,
    renameSession,
    removeSession,
    send,
    stop,
    reset,
  }
})
