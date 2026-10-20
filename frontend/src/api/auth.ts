import { http } from './http'
import type { Captcha, TokenResponse, User } from './types'

export async function fetchCaptcha(): Promise<Captcha> {
  const { data } = await http.get<Captcha>('/api/v1/auth/captcha')
  return data
}

export async function register(payload: {
  username: string
  password: string
  confirm_password: string
  captcha_id: string
  captcha_code: string
}): Promise<TokenResponse> {
  const { data } = await http.post<TokenResponse>('/api/v1/auth/register', payload)
  return data
}

export async function login(payload: {
  username: string
  password: string
  captcha_id: string
  captcha_code: string
}): Promise<TokenResponse> {
  const { data } = await http.post<TokenResponse>('/api/v1/auth/login', payload)
  return data
}

export async function fetchMe(): Promise<User> {
  const { data } = await http.get<User>('/api/v1/auth/me')
  return data
}

export async function logout(): Promise<void> {
  await http.post('/api/v1/auth/logout')
}
