import type { ChatPayload, ChatSettings } from '@/api/types'

export const DEFAULT_CHAT_SETTINGS: ChatSettings = {
  kb_ids: [],
  temperature: 0.7,
  top_p: 0.8,
  max_tokens: 2048,
  history_rounds: 5,
}

export function normalizeChatSettings(input: Partial<ChatSettings> | null | undefined): ChatSettings {
  const value = input || {}
  return {
    kb_ids: Array.isArray(value.kb_ids) ? value.kb_ids.filter((item) => Boolean(item)) : [],
    temperature: clamp(Number(value.temperature ?? DEFAULT_CHAT_SETTINGS.temperature), 0, 2),
    top_p: clamp(Number(value.top_p ?? DEFAULT_CHAT_SETTINGS.top_p), 0.1, 1),
    max_tokens: Math.round(
      clamp(Number(value.max_tokens ?? DEFAULT_CHAT_SETTINGS.max_tokens), 128, 4096),
    ),
    history_rounds: Math.round(
      clamp(Number(value.history_rounds ?? DEFAULT_CHAT_SETTINGS.history_rounds), 0, 20),
    ),
  }
}

export function buildChatPayload(content: string, settings: ChatSettings): ChatPayload {
  const normalized = normalizeChatSettings(settings)
  return {
    content: content.trim(),
    kb_ids: normalized.kb_ids,
    temperature: normalized.temperature,
    top_p: normalized.top_p,
    max_tokens: normalized.max_tokens,
    history_rounds: normalized.history_rounds,
  }
}

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min
  return Math.min(max, Math.max(min, value))
}
