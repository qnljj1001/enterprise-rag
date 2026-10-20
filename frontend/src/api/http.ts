import axios, { AxiosError } from 'axios'

const TOKEN_KEY = 'enterprise-rag.token'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export const http = axios.create({
  baseURL: '',
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && !window.location.pathname.startsWith('/login')) {
      clearToken()
      window.location.assign('/login')
    }
    return Promise.reject(error)
  },
)

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object') {
      const message = (detail as { message?: unknown }).message
      if (typeof message === 'string' && message) return message
    }
    if (error.code === 'ECONNABORTED') return '请求超时，请稍后重试。'
    if (!error.response) return '无法连接后端服务，请确认服务已启动。'
    return `请求失败（HTTP ${error.response.status}）`
  }
  if (error instanceof Error) return error.message
  return '操作失败，请稍后重试。'
}
