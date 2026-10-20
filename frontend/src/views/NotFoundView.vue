<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="app-canvas not-found">
    <div class="aurora aurora--violet" aria-hidden="true" />
    <div class="not-found__card zc-card">
      <p class="not-found__code">404</p>
      <h1>页面不存在</h1>
      <p>你访问的页面可能已被移动或删除。</p>
      <button class="zc-btn zc-btn--primary" type="button" @click="router.push('/chat')">返回对话</button>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}

.not-found__card {
  position: relative;
  z-index: 1;
  width: min(420px, calc(100% - 32px));
  padding: 40px 32px;
  text-align: center;
}

.not-found__code {
  color: transparent;
  background: linear-gradient(120deg, #6d5df6, #22d3ee);
  -webkit-background-clip: text;
  background-clip: text;
  font-size: 66px;
  font-weight: 900;
  letter-spacing: -0.06em;
}

.not-found h1 {
  margin-top: 4px;
  font-size: 22px;
  font-weight: 800;
}

.not-found p {
  margin: 8px 0 22px;
  color: var(--zc-muted);
  font-size: 13px;
}
</style>
