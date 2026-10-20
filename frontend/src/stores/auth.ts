import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as authApi from '@/api/auth'
import { clearToken, getToken, setToken } from '@/api/http'
import type { User } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken())
  const user = ref<User | null>(null)
  const initialized = ref(false)
  const loading = ref(false)

  const isAdmin = computed(() => user.value?.role === 'admin')
  const isLoggedIn = computed(() => Boolean(token.value))

  function applyToken(value: string, nextUser: User) {
    token.value = value
    user.value = nextUser
    setToken(value)
    initialized.value = true
  }

  async function bootstrap() {
    if (initialized.value) return
    if (!token.value) {
      initialized.value = true
      return
    }
    try {
      user.value = await authApi.fetchMe()
    } catch {
      token.value = ''
      user.value = null
      clearToken()
    } finally {
      initialized.value = true
    }
  }

  async function login(payload: {
    username: string
    password: string
    captcha_id: string
    captcha_code: string
  }) {
    loading.value = true
    try {
      const data = await authApi.login(payload)
      applyToken(data.access_token, data.user)
      return data
    } finally {
      loading.value = false
    }
  }

  async function register(payload: {
    username: string
    password: string
    confirm_password: string
    captcha_id: string
    captcha_code: string
  }) {
    loading.value = true
    try {
      const data = await authApi.register(payload)
      applyToken(data.access_token, data.user)
      return data
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // 本地登出即可
    }
    token.value = ''
    user.value = null
    clearToken()
    initialized.value = true
  }

  return {
    token,
    user,
    initialized,
    loading,
    isAdmin,
    isLoggedIn,
    bootstrap,
    login,
    register,
    logout,
  }
})
