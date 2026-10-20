<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { fetchCaptcha } from '@/api/auth'
import { apiErrorMessage } from '@/api/http'
import type { Captcha } from '@/api/types'
import AuthShell from '@/components/layout/AuthShell.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const form = reactive({
  username: '',
  password: '',
  confirm_password: '',
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
  if (form.username.trim().length < 3) {
    ElMessage.warning('账号至少 3 个字符。')
    return
  }
  if (form.password.length < 8) {
    ElMessage.warning('密码至少 8 位。')
    return
  }
  if (form.password !== form.confirm_password) {
    ElMessage.warning('两次输入的密码不一致。')
    return
  }
  if (!captcha.value || !form.captcha_code.trim()) {
    ElMessage.warning('请输入图形验证码。')
    return
  }
  try {
    await auth.register({
      username: form.username.trim(),
      password: form.password,
      confirm_password: form.confirm_password,
      captcha_id: captcha.value.captcha_id,
      captcha_code: form.captcha_code.trim(),
    })
    await router.push('/chat')
  } catch (err) {
    error.value = apiErrorMessage(err)
    await refreshCaptcha()
  }
}

onMounted(refreshCaptcha)
</script>

<template>
  <AuthShell eyebrow="CREATE ACCOUNT" title="创建账号" subtitle="注册后即可使用管理员维护的全部知识库。">
    <form class="auth-form" @submit.prevent="submit">
      <label class="zc-label" for="register-username">账号</label>
      <input
        id="register-username"
        v-model="form.username"
        class="zc-input"
        autocomplete="username"
        placeholder="3–32 位，中英文/数字/下划线"
        data-testid="register-username"
      />

      <label class="zc-label auth-form__gap" for="register-password">密码</label>
      <input
        id="register-password"
        v-model="form.password"
        class="zc-input"
        type="password"
        autocomplete="new-password"
        placeholder="至少 8 位"
        data-testid="register-password"
      />

      <label class="zc-label auth-form__gap" for="register-confirm">确认密码</label>
      <input
        id="register-confirm"
        v-model="form.confirm_password"
        class="zc-input"
        type="password"
        autocomplete="new-password"
        placeholder="再次输入密码"
        data-testid="register-confirm"
      />

      <label class="zc-label auth-form__gap" for="register-captcha">图形验证码</label>
      <div class="captcha-row">
        <input
          id="register-captcha"
          v-model="form.captcha_code"
          class="zc-input captcha-row__input"
          maxlength="6"
          placeholder="输入右侧字符"
          data-testid="register-captcha"
        />
        <button class="captcha" type="button" title="点击刷新验证码" @click="refreshCaptcha">
          <img
            v-if="captcha"
            :src="`data:image/png;base64,${captcha.image_base64}`"
            alt="图形验证码"
          />
          <span v-else>加载中</span>
        </button>
      </div>

      <p v-if="error" class="auth-error" data-testid="register-error">{{ error }}</p>

      <button class="zc-btn zc-btn--primary auth-submit" type="submit" :disabled="auth.loading" data-testid="register-submit">
        {{ auth.loading ? '注册中…' : '注册并登录' }}
      </button>

      <p class="auth-switch">
        已有账号？
        <RouterLink to="/login">返回登录</RouterLink>
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
  margin-top: 15px;
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
