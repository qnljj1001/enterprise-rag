import { http } from './http'
import type { Meta } from './types'

export async function fetchMeta(): Promise<Meta> {
  const { data } = await http.get<Meta>('/api/v1/meta')
  return data
}
