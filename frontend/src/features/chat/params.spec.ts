import { describe, expect, it } from 'vitest'

import { buildChatPayload, normalizeChatSettings } from './params'

describe('chat params', () => {
  it('normalizes invalid values', () => {
    const settings = normalizeChatSettings({
      kb_ids: ['kb_1', ''],
      temperature: 9,
      top_p: 0,
      max_tokens: 99999,
      history_rounds: -1,
    })
    expect(settings.kb_ids).toEqual(['kb_1'])
    expect(settings.temperature).toBe(2)
    expect(settings.top_p).toBe(0.1)
    expect(settings.max_tokens).toBe(4096)
    expect(settings.history_rounds).toBe(0)
  })

  it('builds payload without model field', () => {
    const payload = buildChatPayload('  服务期是几年？  ', normalizeChatSettings({ kb_ids: ['kb_1'] }))
    expect(payload.content).toBe('服务期是几年？')
    expect(payload.kb_ids).toEqual(['kb_1'])
    expect('model' in payload).toBe(false)
  })
})
