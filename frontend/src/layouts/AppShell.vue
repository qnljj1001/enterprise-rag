<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { ChatDotRound, Collection, SwitchButton } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)

const navItems = computed(() => {
  const items = [{ to: '/chat', label: '对话', icon: ChatDotRound }]
  if (auth.isAdmin) {
    items.push({ to: '/admin/knowledge', label: '知识库管理', icon: Collection })
  }
  return items
})

const activePath = computed(() => {
  if (route.path.startsWith('/admin')) return '/admin/knowledge'
  return '/chat'
})

const avatarText = computed(() => (auth.user?.username || '?').slice(0, 1).toUpperCase())

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '退出登录', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-canvas shell">
    <div class="aurora aurora--violet" aria-hidden="true" />
    <div class="aurora aurora--cyan" aria-hidden="true" />

    <header class="shell-header">
      <div class="shell-header__inner">
        <RouterLink to="/chat" class="brand" aria-label="返回对话">
          <span class="brand__mark">知</span>
          <span class="brand__copy">
            <span class="brand__title">知策</span>
            <span class="brand__subtitle">政策知识问答</span>
          </span>
        </RouterLink>

        <nav class="nav" aria-label="主导航">
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="nav__link"
            :class="{ 'is-active': activePath === item.to }"
          >
            <el-icon :size="16"><component :is="item.icon" /></el-icon>
            {{ item.label }}
          </RouterLink>
        </nav>

        <div class="shell-tools">
          <span class="zc-chip zc-chip--primary model-chip">
            <span class="model-dot" aria-hidden="true" />
            DeepSeek Flash
          </span>
          <el-dropdown trigger="click" @command="(command: string) => command === 'logout' && handleLogout()">
            <button class="user" type="button">
              <span class="user__avatar">{{ avatarText }}</span>
              <span class="user__name">{{ auth.user?.username }}</span>
              <span class="user__role">{{ auth.isAdmin ? '管理员' : '用户' }}</span>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <button class="mobile-toggle" type="button" aria-label="打开导航" @click="mobileOpen = true">
            <span />
            <span />
            <span />
          </button>
        </div>
      </div>
    </header>

    <el-drawer v-model="mobileOpen" direction="rtl" size="82%" :with-header="false">
      <div class="mobile-nav">
        <div class="brand">
          <span class="brand__mark">知</span>
          <span class="brand__copy">
            <span class="brand__title">知策</span>
            <span class="brand__subtitle">政策知识问答</span>
          </span>
        </div>
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="mobile-nav__link"
          :class="{ 'is-active': activePath === item.to }"
          @click="mobileOpen = false"
        >
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          {{ item.label }}
        </RouterLink>
        <button class="zc-btn zc-btn--danger mobile-nav__logout" type="button" @click="mobileOpen = false; handleLogout()">
          退出登录
        </button>
      </div>
    </el-drawer>

    <main class="shell-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.shell-header {
  position: sticky;
  z-index: 30;
  top: 0;
  border-bottom: 1px solid rgba(232, 231, 244, 0.8);
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(18px);
}

.shell-header__inner {
  display: flex;
  align-items: center;
  gap: 28px;
  width: min(1320px, calc(100% - 40px));
  height: var(--zc-header-height);
  margin: 0 auto;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}

.brand__mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 13px;
  color: #fff;
  background: linear-gradient(135deg, #6d5df6 0%, #8b5cf6 52%, #06b6d4 120%);
  box-shadow: 0 10px 20px rgba(109, 93, 246, 0.28);
  font-size: 18px;
  font-weight: 800;
}

.brand__copy {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand__title {
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.brand__subtitle {
  margin-top: 2px;
  color: var(--zc-muted-2);
  font-size: 10.5px;
  letter-spacing: 0.08em;
}

.nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav__link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 14px;
  border-radius: 11px;
  color: var(--zc-muted);
  font-size: 13.5px;
  font-weight: 650;
  transition:
    color var(--zc-transition),
    background var(--zc-transition);
}

.nav__link:hover {
  color: var(--zc-ink);
  background: rgba(109, 93, 246, 0.06);
}

.nav__link.is-active {
  color: var(--zc-primary-strong);
  background: var(--zc-primary-soft);
}

.shell-tools {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.model-chip {
  padding-inline: 11px;
}

.model-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--zc-primary);
  box-shadow: 0 0 0 4px rgba(109, 93, 246, 0.14);
}

.user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 4px;
  border: 1px solid var(--zc-line);
  border-radius: 999px;
  background: #fff;
  cursor: pointer;
  transition:
    border-color var(--zc-transition),
    box-shadow var(--zc-transition);
}

.user:hover {
  border-color: var(--zc-line-strong);
  box-shadow: 0 6px 18px rgba(18, 20, 43, 0.07);
}

.user__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  color: #fff;
  background: linear-gradient(135deg, #8b5cf6, #22d3ee);
  font-size: 12px;
  font-weight: 800;
}

.user__name {
  max-width: 90px;
  overflow: hidden;
  font-size: 12.5px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user__role {
  color: var(--zc-muted-2);
  font-size: 10.5px;
}

.mobile-toggle {
  display: none;
  flex-direction: column;
  gap: 4px;
  width: 36px;
  height: 36px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--zc-line);
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
}

.mobile-toggle span {
  width: 15px;
  height: 1.5px;
  border-radius: 2px;
  background: var(--zc-ink-soft);
}

.mobile-nav {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-nav__link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 12px;
  border-radius: 12px;
  color: var(--zc-ink-soft);
  font-weight: 650;
}

.mobile-nav__link.is-active {
  color: var(--zc-primary-strong);
  background: var(--zc-primary-soft);
}

.mobile-nav__logout {
  margin-top: 18px;
}

.shell-main {
  position: relative;
  z-index: 1;
  display: flex;
  flex: 1;
  min-height: 0;
}

@media (max-width: 980px) {
  .nav,
  .model-chip {
    display: none;
  }
  .mobile-toggle {
    display: flex;
  }
  .shell-header__inner {
    gap: 16px;
  }
}

@media (max-width: 560px) {
  .shell-header__inner {
    width: calc(100% - 24px);
  }
  .user__name,
  .user__role {
    display: none;
  }
  .user {
    border: 0;
    padding: 0;
    background: transparent;
  }
}
</style>
