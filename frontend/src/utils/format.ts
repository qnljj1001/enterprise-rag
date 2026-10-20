import dayjs from 'dayjs'

export function formatDate(value?: string | null): string {
  if (!value) return '—'
  return dayjs(value).format('YYYY-MM-DD HH:mm')
}

export function formatBytes(value: number): string {
  if (!value) return '0 B'
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

export const STATUS_LABELS: Record<string, string> = {
  pending: '等待解析',
  parsing: '解析中',
  chunking: '切块中',
  embedding: '向量化中',
  indexing: '写入索引',
  ready: '已就绪',
  failed: '失败',
}

export const STATUS_TYPES: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
  ready: 'success',
  failed: 'danger',
  pending: 'info',
  parsing: 'warning',
  chunking: 'warning',
  embedding: 'warning',
  indexing: 'warning',
}

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] || status
}

export function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  return STATUS_TYPES[status] || 'info'
}

export function formatScore(score: number): string {
  if (!Number.isFinite(score)) return '—'
  return score.toFixed(3)
}
