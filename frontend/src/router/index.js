import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { guest: true }
  },
  {
    path: '/',
    component: () => import('@/views/chat/ChatView.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'ChatHome',
        component: () => import('@/views/chat/ChatPanelView.vue')
      },
      {
        path: 'workspace',
        name: 'Workspace',
        component: () => import('@/views/workspace/WorkspaceView.vue')
      },
      {
        path: 'history',
        name: 'HistoryManage',
        component: () => import('@/views/history/HistoryManageView.vue')
      },
      {
        path: 'workspace/model/:id',
        name: 'ModelDetail',
        component: () => import('@/views/workspace/ModelDetailView.vue')
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('@/views/knowledge/KnowledgeView.vue')
      },
      {
        path: 'kg',
        name: 'KnowledgeGraph',
        component: () => import('@/views/kg/KnowledgeGraphView.vue')
      }
    ]
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/admin/AdminView.vue'),
    meta: { requiresAuth: true, adminOnly: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  if (authStore.isAuthenticated && !authStore.user) {
    await authStore.fetchUser()
  }
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login' })
  } else if (to.meta.adminOnly && !authStore.isAdmin) {
    next({ name: 'ChatHome' })
  } else if (to.meta.guest && authStore.isAuthenticated) {
    next({ name: 'ChatHome' })
  } else {
    next()
  }
})

export default router
