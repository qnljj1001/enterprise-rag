import { describe, expect, it } from 'vitest'

import { formatBytes, statusLabel, statusType } from './format'

describe('format helpers', () => {
  it('formats bytes', () => {
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(1024)).toBe('1.0 KB')
    expect(formatBytes(1024 * 1024)).toBe('1.0 MB')
  })

  it('maps status labels and types', () => {
    expect(statusLabel('ready')).toBe('已就绪')
    expect(statusType('failed')).toBe('danger')
    expect(statusLabel('unknown')).toBe('unknown')
  })
})
