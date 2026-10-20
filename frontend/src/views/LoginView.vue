<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { fetchCaptcha } from '@/api/auth'
import { apiErrorMessage } from '@/api/http'
import type { Captcha } from '@/api/types'
import AuthShell from '@/components/layout/AuthShell.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const form = reactive({
  username: '',
  password: '',
  captcha_code: '',
})
const captcha = ref<Captcha | null>(null)
const captchaLoading = ref(false)
const error = ref('')

async function refreshCaptcha() {
  captchaLoading.value = true
  try {
    captcha.value = await fetchCaptcha()
    form.captcha_code = ''
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    captchaLoading.value = false
  }
}

async function submit() {
  error.value = ''
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入账号和密码。')
    return
  }
  if (!captcha.value) {
    ElMessage.warning('验证码加载中，请稍候。')
    return
  }
  if (!form.captcha_code.trim()) {
    ElMessage.warning('请输入图形验证码。')
    return
  }
  try {
    await auth.login({
      username: form.username.trim(),
      password: form.password,
      captcha_id: captcha.value.captcha_id,
      captcha_code: form.captcha_code.trim(),
    })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/chat'
    await router.push(redirect)
  } catch (err) {
    error.value = apiErrorMessage(err)
    await refreshCaptcha()
  }
}

onMounted(refreshCaptcha)
</script>

<template>
  <AuthShell eyebrow="WELCOME BACK" title="欢迎回来" subtitle="登录后，选择一个知识库开始提问。">
    <form class="auth-form" @submit.prevent="submit">
      <label class="zc-label" for="login-username">账号</label>
      <input
        id="login-username"
        v-model="form.username"
        class="zc-input"
        autocomplete="username"
        placeholder="请输入账号"
        data-testid="login-username"
      />

      <label class="zc-label auth-form__gap" for="login-password">密码</label>
      <input
        id="login-password"
        v-model="form.password"
        class="zc-input"
        type="password"
        autocomplete="current-password"
        placeholder="请输入密码"
        data-testid="login-password"
      />

      <label class="zc-label auth-form__gap" for="login-captcha">图形验证码</label>
      <div class="captcha-row">
        <input
          id="login-captcha"
          v-model="form.captcha_code"
          class="zc-input captcha-row__input"
          maxlength="6"
          placeholder="输入右侧字符"
          data-testid="login-captcha"
        />
        <button
          class="captcha"
          type="button"
          :aria-busy="captchaLoading"
          title="点击刷新验证码"
          data-testid="login-captcha-refresh"
          @click="refreshCaptcha"
        >
          <img
            v-if="captcha"
            :src="`data:image/png;base64,${captcha.image_base64}`"
            alt="图形验证码"
          />
          <span v-else>加载中</span>
        </button>
      </div>

      <p v-if="error" class="auth-error" data-testid="login-error">{{ error }}</p>

      <button class="zc-btn zc-btn--primary auth-submit" type="submit" :disabled="auth.loading" data-testid="login-submit">
        {{ auth.loading ? '登录中…' : '登录' }}
      </button>

      <p class="auth-switch">
        还没有账号？
        <RouterLink to="/register">立即注册</RouterLink>
      </p>
    </form>
  </AuthShell>
</template>

<style scoped>
.auth-form {
  display: flex;
  flex-direction: column;
}

.auth-form__gap {
  margin-top: 17px;
}

.captcha-row {
  display: flex;
  align-items: stretch;
  gap: 10px;
}

.captcha-row__input {
  flex: 1;
  min-width: 0;
}

.captcha {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 132px;
  min-height: 42px;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--zc-line);
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  transition: border-color var(--zc-transition);
}

.captcha:hover {
  border-color: var(--zc-primary);
}

.captcha img {
  display: block;
  width: 100%;
  height: 40px;
  object-fit: cover;
}

.captcha span {
  color: var(--zc-muted-2);
  font-size: 12px;
}

.auth-error {
  margin-top: 14px;
  padding: 9px 12px;
  border: 1px solid #f3cfcc;
  border-radius: 10px;
  color: var(--zc-danger);
  background: var(--zc-danger-soft);
  font-size: 12.5px;
}

.auth-submit {
  width: 100%;
  min-height: 44px;
  margin-top: 22px;
  font-size: 14px;
}

.auth-switch {
  margin-top: 18px;
  color: var(--zc-muted);
  font-size: 12.5px;
  text-align: center;
}

.auth-switch a {
  color: var(--zc-primary-strong);
  font-weight: 700;
}
</style>
