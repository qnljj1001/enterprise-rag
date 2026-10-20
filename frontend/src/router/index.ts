import { createRouter, createWebHistory } from 'vue-router'

import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/chat' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: '登录', public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { title: '注册', public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppShell.vue'),
      children: [
        {
          path: 'chat',
          name: 'chat',
          component: () => import('@/views/ChatView.vue'),
          meta: { title: '对话', requiresAuth: true },
        },
        {
          path: 'admin/knowledge',
          name: 'admin-knowledge',
          component: () => import('@/views/admin/KnowledgeListView.vue'),
          meta: { title: '知识库管理', requiresAuth: true, requiresAdmin: true },
        },
        {
          path: 'admin/knowledge/:kbId',
          name: 'admin-knowledge-detail',
          component: () => import('@/views/admin/KnowledgeDetailView.vue'),
          meta: { title: '知识库详情', requiresAuth: true, requiresAdmin: true },
        },
        {
          path: 'admin/knowledge/:kbId/wiki',
          name: 'admin-knowledge-wiki',
          component: () => import('@/views/admin/WikiView.vue'),
          props: { kind: 'knowledge-base' },
          meta: { title: '知识库 Wiki', requiresAuth: true, requiresAdmin: true },
        },
        {
          path: 'admin/documents/:docId',
          name: 'admin-document',
          component: () => import('@/views/admin/DocumentView.vue'),
          meta: { title: '文档预览', requiresAuth: true, requiresAdmin: true },
        },
        {
          path: 'admin/documents/:docId/wiki',
          name: 'admin-document-wiki',
          component: () => import('@/views/admin/WikiView.vue'),
          props: { kind: 'document' },
          meta: { title: '文档 Wiki', requiresAuth: true, requiresAdmin: true },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { title: '页面不存在', public: true },
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore(pinia)
  if (!auth.initialized) await auth.bootstrap()
  if (to.meta.requiresAdmin && auth.user?.role !== 'admin') {
    return { name: 'chat' }
  }
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if ((to.name === 'login' || to.name === 'register') && auth.isLoggedIn) {
    return { name: 'chat' }
  }
  return true
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : ''
  document.title = title ? `${title} · 知策` : '知策 · 政策知识问答'
})

export default router
